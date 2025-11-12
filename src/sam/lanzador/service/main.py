# sam/lanzador/service/main.py
import asyncio
import logging
from typing import Dict, List, Set

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
        logger.info("Inicializando el orquestador del LanzadorService...")
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
        self._equipos_alertados: Set[int] = set()  # Equipos ya notificados
        self._umbral_alertas_412 = cfg_lanzador.get("umbral_alertas_412", 20)

        self._validar_configuracion_critica()
        logger.info("Orquestador del LanzadorService inicializado correctamente.")

    def _validar_configuracion_critica(self):
        """Valida que la configuración esencial para el servicio esté presente."""
        logger.info("Validando configuración crítica para el servicio...")
        claves_criticas = [
            "intervalo_lanzamiento",
            "intervalo_sincronizacion",
            "intervalo_conciliacion",
            "conciliador_max_intentos_fallidos",
        ]
        faltantes = [clave for clave in claves_criticas if clave not in self._lanzador_cfg]
        if faltantes:
            raise ValueError(f"Configuración crítica faltante en LanzadorService: {', '.join(faltantes)}")
        logger.info("Validación de configuración completada.")

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
                logger.info(f"Iniciando ciclo de {cycle_name}...")

                # Ejecutar la lógica
                resultado = await getattr(logic_component, method_name)()

                # Tracking de errores 412 (solo para ciclo de lanzamiento)
                if cycle_name == "Lanzamiento" and resultado:
                    self._procesar_resultados_despliegue(resultado)

                logger.info(f"Ciclo de {cycle_name} completado.")
            except Exception as e:
                logger.critical(f"Error fatal en el ciclo de {cycle_name}: {e}", exc_info=True)
                self._notificador.send_alert(
                    subject=f"Error Crítico en Ciclo de {cycle_name}",
                    message=f"Se ha producido un error irrecuperable en el ciclo de {cycle_name}.\n\nError: {e}",
                )
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
                    self._equipos_alertados.discard(equipo_id)
                    logger.info(f"Equipo {equipo_id} recuperado. Contador de fallos 412 reseteado.")

            elif status == "fallido" and error_type == "412":
                # Incrementar contador de fallos 412
                contador = self._fallos_412_por_equipo.get(equipo_id, 0) + 1
                self._fallos_412_por_equipo[equipo_id] = contador

                # Alertar si cruza el umbral (solo la primera vez)
                if contador >= self._umbral_alertas_412 and equipo_id not in self._equipos_alertados:
                    logger.warning(
                        f"Equipo {equipo_id} ha alcanzado {contador} fallos consecutivos (412). Enviando alerta..."
                    )
                    try:
                        self._notificador.send_alert(
                            subject="[SAM] Dispositivo Offline Persistente",
                            message=(
                                f"El EquipoId {equipo_id} ha fallado {contador} despliegues consecutivos.\n\n"
                                f"Error: 412 Precondition Failed (Dispositivo offline/ocupado)\n\n"
                                f"Acción requerida: Verificar conectividad y estado del Bot Runner en A360."
                            ),
                        )
                        self._equipos_alertados.add(equipo_id)
                    except Exception as e:
                        logger.error(f"Error al enviar alerta para equipo {equipo_id}: {e}")

    async def _run_sync_cycle(self, interval: int):
        await self._run_generic_cycle(self._sincronizador, "sincronizar_entidades", interval, "Sincronización")

    async def _run_launcher_cycle(self, interval: int):
        await self._run_generic_cycle(self._desplegador, "desplegar_robots_pendientes", interval, "Lanzamiento")

    async def _run_conciliador_cycle(self, interval: int):
        await self._run_generic_cycle(self._conciliador, "conciliar_ejecuciones", interval, "Conciliación")
