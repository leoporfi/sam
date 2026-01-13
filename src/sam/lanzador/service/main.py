# sam/lanzador/service/main.py
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from sam.common.alert_types import AlertContext, AlertLevel, AlertScope, AlertType
from sam.common.mail_client import EmailAlertClient

from .conciliador import Conciliador
from .desplegador import Desplegador
from .sincronizador import Sincronizador

logger = logging.getLogger(__name__)


class LanzadorService:
    """
    Clase Orquestadora del servicio Lanzador.
    Su responsabilidad es gestionar el ciclo de vida del servicio y coordinar
    a los componentes de lógica ('cerebros'), pero no contiene la lógica de
    negocio en sí misma.
    """

    def __init__(
        self,
        sincronizador: Sincronizador,
        desplegador: Desplegador,
        conciliador: Conciliador,
        notificador: EmailAlertClient,
        cfg_lanzador: dict,
        sync_enabled: bool,
    ):
        """
        Inicializa el Orquestador con sus componentes de lógica ya creados (Inyección de Dependencias).
        """
        logger.debug("Inicializando el orquestador del LanzadorService...")
        self._sincronizador = sincronizador
        self._desplegador = desplegador
        self._conciliador = conciliador
        self._notificador = notificador
        self._lanzador_cfg = cfg_lanzador
        self._sync_enabled = sync_enabled

        self._shutdown_event = asyncio.Event()
        self._tasks: List[asyncio.Task] = []

        # Tracking de errores 412 persistentes
        self._fallos_412_por_equipo: Dict[int, int] = {}  # {equipo_id: contador_fallos}
        self._equipos_alertados: Dict[int, datetime] = {}  # {equipo_id: last_alert_time}
        self._umbral_alertas_412 = cfg_lanzador.get("umbral_alertas_412", 20)

        self._validar_configuracion_critica()

        # Registrar callbacks de autenticación en el cliente de AA
        self._desplegador._aa_client.set_auth_callbacks(
            on_failure=self._handle_aa_auth_failure, on_success=self._handle_aa_auth_success
        )

        logger.debug("Orquestador del LanzadorService inicializado correctamente.")

    def _validar_configuracion_critica(self):
        """Valida que la configuración esencial para el servicio esté presente."""
        logger.debug("Validando configuración crítica para el servicio...")
        claves_criticas = [
            "intervalo_lanzamiento",
            "intervalo_sincronizacion",
            "intervalo_conciliacion",
        ]
        faltantes = [clave for clave in claves_criticas if clave not in self._lanzador_cfg]
        if faltantes:
            raise ValueError(f"Configuración crítica faltante en LanzadorService: {', '.join(faltantes)}")
        logger.debug("Validación de configuración completada.")

    async def run(self):
        """Crea y gestiona las tareas asíncronas de los ciclos del servicio."""
        logger.info("Creando tareas de ciclo del servicio...")

        if self._sync_enabled:
            self._tasks.append(
                asyncio.create_task(self._run_sync_cycle(self._lanzador_cfg["intervalo_sincronizacion"]))
            )
        else:
            logger.warning("El ciclo de sincronización está DESHABILITADO por configuración.")

        self._tasks.append(asyncio.create_task(self._run_launcher_cycle(self._lanzador_cfg["intervalo_lanzamiento"])))
        self._tasks.append(
            asyncio.create_task(self._run_conciliador_cycle(self._lanzador_cfg["intervalo_conciliacion"]))
        )

        # Espera a que todas las tareas finalicen
        await asyncio.gather(*self._tasks, return_exceptions=True)

    def stop(self):
        """Activa el evento de cierre para detener los ciclos de forma ordenada."""
        logger.info("Iniciando la detención ordenada de los ciclos del servicio...")
        self._shutdown_event.set()

    async def _run_generic_cycle(self, logic_component, method_name: str, interval: int, cycle_name: str):
        """Plantilla genérica para ejecutar un ciclo de lógica."""
        while not self._shutdown_event.is_set():
            try:
                logger.debug(f"Iniciando ciclo de {cycle_name}...")

                # Ejecutar la lógica
                resultado = await getattr(logic_component, method_name)()

                # Tracking de errores 412 (solo para ciclo de lanzamiento)
                if cycle_name == "Lanzamiento" and resultado:
                    self._procesar_resultados_despliegue(resultado)

                logger.debug(f"Ciclo de {cycle_name} completado.")
            except Exception as e:
                logger.critical(f"Error fatal en el ciclo de {cycle_name}: {e}", exc_info=True)
                import traceback

                error_trace = traceback.format_exc()
                alert_sent = self._notificador.send_alert(
                    subject=f"Error Crítico en Ciclo de {cycle_name}",
                    message=(
                        f"Se ha producido un error irrecuperable en el ciclo de {cycle_name}.\n\nError: {e}\n\nStack Trace:\n{error_trace}"
                    ),
                    is_critical=True,
                )
                if not alert_sent:
                    logger.error(f"No se pudo enviar la alerta de error crítico en ciclo de {cycle_name}")
            try:
                # Espera el intervalo o hasta que se active el evento de cierre
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass  # Es el comportamiento esperado, continuar al siguiente ciclo

    def _procesar_resultados_despliegue(self, resultados: List[Dict]):
        """
        Procesa los resultados del despliegue para trackear errores 412 persistentes.
        """
        if not isinstance(resultados, list):
            return

        for resultado in resultados:
            equipo_id = resultado.get("equipo_id")
            status = resultado.get("status")
            error_type = resultado.get("error_type")

            if not equipo_id:
                continue

            if status == "exitoso":
                # Resetear contador si el equipo vuelve a funcionar
                if equipo_id in self._fallos_412_por_equipo:
                    del self._fallos_412_por_equipo[equipo_id]
                    if equipo_id in self._equipos_alertados:
                        del self._equipos_alertados[equipo_id]
                    logger.debug(f"Equipo {equipo_id} recuperado. Contador de fallos 412 reseteado.")

            elif status == "fallido" and error_type == "412":
                # Incrementar contador de fallos 412
                contador = self._fallos_412_por_equipo.get(equipo_id, 0) + 1
                self._fallos_412_por_equipo[equipo_id] = contador

                # Alertar si cruza el umbral (primera vez o cada 30 min)
                should_alert = False
                if contador >= self._umbral_alertas_412:
                    last_alert = self._equipos_alertados.get(equipo_id)
                    if not last_alert:
                        should_alert = True
                    elif (datetime.now() - last_alert).total_seconds() > 1800:  # 30 min
                        should_alert = True

                if should_alert:
                    logger.warning(
                        f"Equipo {equipo_id} ha alcanzado {contador} fallos consecutivos (412). Enviando alerta..."
                    )
                    equipo_nombre = resultado.get("equipo_nombre", "N/A")

                    context = AlertContext(
                        alert_level=AlertLevel.HIGH,
                        alert_scope=AlertScope.DEVICE,
                        alert_type=AlertType.THRESHOLD,
                        subject=f"Equipo '{equipo_nombre}' persistentemente offline",
                        summary=f"El equipo ha fallado {contador} intentos de despliegue consecutivos (Error 412).",
                        technical_details={
                            "Equipo": f"{equipo_nombre} (ID: {equipo_id})",
                            "Fallos Consecutivos": str(contador),
                            "Umbral Configurado": str(self._umbral_alertas_412),
                        },
                        actions=[
                            "Verificar conectividad del equipo",
                            "Verificar estado del Bot Agent en el equipo",
                            "Reiniciar servicio de Automation Anywhere Bot Agent si es necesario",
                        ],
                        frequency_info="Primera alerta. Se repetirá cada 30 minutos si persiste.",
                    )

                    alert_sent = self._notificador.send_alert_v2(context)
                    if alert_sent:
                        self._equipos_alertados[equipo_id] = datetime.now()
                    else:
                        logger.error(
                            f"No se pudo enviar la alerta para equipo {equipo_id}. Se reintentará en el próximo ciclo."
                        )

    async def _run_sync_cycle(self, interval: int):
        await self._run_generic_cycle(self._sincronizador, "sincronizar_entidades", interval, "Sincronización")

    async def _run_launcher_cycle(self, interval: int):
        await self._run_generic_cycle(self._desplegador, "desplegar_robots_pendientes", interval, "Lanzamiento")

    async def _run_conciliador_cycle(self, interval: int):
        await self._run_generic_cycle(self._conciliador, "conciliar_ejecuciones", interval, "Conciliación")

    # --- Handlers de Autenticación ---

    async def _handle_aa_auth_failure(self, status_code: int, error_text: str):
        """Maneja el fallo crítico de autenticación con la API Key."""
        logger.error(f"Handler de fallo de autenticación activado. Status: {status_code}")

        context = AlertContext(
            alert_level=AlertLevel.CRITICAL,
            alert_scope=AlertScope.SYSTEM,
            alert_type=AlertType.PERMANENT,
            subject="API KEY de Automation Anywhere INVÁLIDA o CADUCADA",
            summary="La API Key (AA_CR_API_KEY) ha sido rechazada por el Control Room. Los lanzamientos están DETENIDOS.",
            technical_details={
                "Status Code": str(status_code),
                "Error": error_text[:500],
                "Usuario CR": self._sincronizador._aa_client.cr_user,
                "URL CR": self._sincronizador._aa_client.cr_url,
            },
            actions=[
                "Generar una nueva API Key en el Control Room de Automation Anywhere",
                "Actualizar la variable de entorno AA_CR_API_KEY en el servidor",
                "Reiniciar los servicios de SAM para aplicar el cambio",
            ],
            frequency_info="Esta es una alerta única por proceso hasta que se resuelva.",
        )

        self._notificador.send_alert_v2(context)

    async def _handle_aa_auth_success(self):
        """Maneja la recuperación de la autenticación."""
        logger.info("Handler de recuperación de autenticación activado.")

        context = AlertContext(
            alert_level=AlertLevel.MEDIUM,
            alert_scope=AlertScope.SYSTEM,
            alert_type=AlertType.RECOVERY,
            subject="Autenticación con Automation Anywhere RESTAURADA",
            summary="La conexión con el Control Room se ha normalizado exitosamente.",
            technical_details={
                "Mensaje": "El cliente ha logrado obtener un token válido nuevamente.",
                "Usuario CR": self._sincronizador._aa_client.cr_user,
            },
            actions=["No se requiere acción adicional.", "Verificar que los robots pendientes comiencen a ejecutarse."],
        )

        self._notificador.send_alert_v2(context)
