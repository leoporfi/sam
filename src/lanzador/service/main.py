# src/lanzador/service/main.py
import asyncio
import logging
from datetime import datetime, time
from typing import Dict, List, Tuple

import httpx
import pytz

from src.common.clients.aa_client import AutomationAnywhereClient
from src.common.clients.api_gateway_client import ApiGatewayClient
from src.common.database.sql_client import DatabaseConnector
from src.common.utils.config_manager import ConfigManager
from src.lanzador.service.conciliador import ConciliadorImplementaciones

logger = logging.getLogger(__name__)


class LanzadorService:
    """
    Clase que encapsula toda la lógica del servicio Lanzador.
    """

    def __init__(self):
        """
        Inicializa el servicio. Obtiene la configuración directamente
        del ConfigManager estático.
        """
        logger.info("Inicializando componentes del LanzadorService...")
        self._shutdown_event = asyncio.Event()
        self._tasks: List[asyncio.Task] = []

        # --- Obtener configuración y crear clientes ---
        db_cfg = ConfigManager.get_sql_server_config("SQL_SAM")
        aa_cfg = ConfigManager.get_aa_config()
        # Obtener la nueva configuración del API Gateway
        gateway_cfg = ConfigManager.get_api_gateway_config()
        # Obtener configuración del servidor de callbacks
        callback_server_cfg = ConfigManager.get_callback_server_config()
        self.static_callback_api_key = callback_server_cfg.get("callback_api_key")

        self.db_connector = DatabaseConnector(
            servidor=db_cfg["server"], base_datos=db_cfg["database"], usuario=db_cfg["uid"], contrasena=db_cfg["pwd"]
        )

        self.aa_client = AutomationAnywhereClient(
            control_room_url=aa_cfg["url"],
            username=aa_cfg["user"],
            password=aa_cfg["pwd"],
            callback_url_deploy=aa_cfg.get("url_callback"),
            api_timeout_seconds=aa_cfg.get("api_timeout_seconds"),
        )

        self.api_gateway_client = ApiGatewayClient(gateway_cfg)
        self.conciliador = ConciliadorImplementaciones(self.db_connector, self.aa_client)
        logger.info("Componentes del servicio inicializados correctamente.")

    # --- Lógica de Pausa ---
    def _is_in_pause_window(self, config: Dict) -> bool:
        """
        Verifica si la hora actual se encuentra dentro de la ventana de pausa definida en la configuración.
        Maneja correctamente los intervalos que cruzan la medianoche (ej: 23:00 a 05:00).
        """
        start_str = config.get("pausa_lanzamiento_inicio_hhmm")
        end_str = config.get("pausa_lanzamiento_fin_hhmm")

        if not start_str or not end_str:
            return False

        try:
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()

            # Usar la misma zona horaria que el conciliador para consistencia
            tz = pytz.timezone("America/Argentina/Buenos_Aires")
            current_time = datetime.now(tz).time()

            # Lógica para manejar pausas que cruzan la medianoche
            if start_time > end_time:
                # Pausa va desde la noche hasta la mañana del día siguiente
                if current_time >= start_time or current_time < end_time:
                    return True
            else:
                # Pausa ocurre en el mismo día
                if start_time <= current_time < end_time:
                    return True

            return False
        except (ValueError, pytz.exceptions.UnknownTimeZoneError) as e:
            logger.error(f"Error al procesar la ventana de pausa. Verifique el formato HH:MM y la zona horaria. Error: {e}")
            return False

    def run(self):
        """Punto de entrada para ejecutar el servicio."""
        try:
            asyncio.run(self._main_loop())
        except KeyboardInterrupt:
            logger.info("Ejecución interrumpida por el usuario.")
        finally:
            logger.info("El bucle principal de asyncio ha finalizado.")

    async def _main_loop(self):
        """Crea y gestiona las tareas asíncronas del servicio."""
        lanzador_cfg = ConfigManager.get_lanzador_config()
        logger.info("Creando tareas de ciclo del servicio...")

        if lanzador_cfg.get("habilitar_sync", True):
            self._tasks.append(asyncio.create_task(self._run_sync_cycle(lanzador_cfg["intervalo_sync_tablas_seg"])))
            logger.info("Tarea de sincronización habilitada.")
        else:
            logger.info("Tarea de sincronización deshabilitada por configuración.")

        self._tasks.append(asyncio.create_task(self._run_launcher_cycle(lanzador_cfg["intervalo_lanzador_seg"])))
        self._tasks.append(asyncio.create_task(self._run_conciliador_cycle(lanzador_cfg["intervalo_conciliador_seg"])))

        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._cleanup()

    def stop(self):
        """Activa el evento de cierre para detener los ciclos."""
        logger.info("Iniciando la detención del servicio Lanzador...")
        self._shutdown_event.set()

    async def _cleanup(self):
        """Cierra las conexiones y libera los recursos."""
        logger.info("Realizando limpieza de recursos...")
        if self.aa_client:
            await self.aa_client.close()
        if self.api_gateway_client:
            await self.api_gateway_client.close()
        if self.db_connector:
            self.db_connector.cerrar_conexion()
        logger.info("Recursos liberados. El servicio ha finalizado limpiamente.")

    async def _run_launcher_cycle(self, interval: int):
        """Ciclo asíncrono para el lanzamiento de robots de forma concurrente."""
        while not self._shutdown_event.is_set():
            try:
                lanzador_cfg = ConfigManager.get_lanzador_config()

                # --- Verificación de Pausa ---
                if self._is_in_pause_window(lanzador_cfg):
                    logger.info("LAUNCHER: El servicio se encuentra en la ventana de pausa operacional. No se lanzarán robots.")
                    # Espera el intervalo y salta al siguiente ciclo
                    try:
                        await asyncio.wait_for(self._shutdown_event.wait(), timeout=interval)
                    except asyncio.TimeoutError:
                        continue  # Salta el resto del código del ciclo

                bot_input = {"in_NumRepeticion": {"type": "NUMBER", "number": lanzador_cfg.get("repeticiones", 1)}}
                concurrency_limit = lanzador_cfg.get("max_lanzamientos_concurrentes", 10)

                logger.info("LAUNCHER: Buscando robots para ejecutar...")
                robots_a_ejecutar = self.db_connector.obtener_robots_ejecutables()

                if robots_a_ejecutar:
                    # Preparar ambas cabeceras de autorización
                    combined_headers = {}
                    try:
                        logger.info("LAUNCHER: Obteniendo token dinámico del API Gateway...")
                        gateway_headers = await self.api_gateway_client.get_auth_header()
                        if gateway_headers:
                            combined_headers.update(gateway_headers)
                        else:
                            logger.warning("LAUNCHER: No se pudo obtener token del API Gateway.")
                    except Exception as token_error:
                        logger.error(f"LAUNCHER: Excepción al obtener token del API Gateway: {token_error}.", exc_info=True)

                    if self.static_callback_api_key:
                        logger.info("LAUNCHER: Añadiendo ApiKey (X-Authorization).")
                        combined_headers["X-Authorization"] = self.static_callback_api_key
                    else:
                        logger.warning("LAUNCHER: El apikey (CALLBACK_API_KEY) no está configurado.")

                    logger.info(f"LAUNCHER: {len(robots_a_ejecutar)} robots encontrados. Desplegando en paralelo (límite: {concurrency_limit})...")

                    # Crear una lista de tareas de despliegue
                    tasks = []
                    for robot_info in robots_a_ejecutar:
                        task = asyncio.create_task(self._deploy_and_register_robot(robot_info, bot_input, combined_headers))
                        tasks.append(task)

                    # Ejecutar tareas en lotes para respetar el límite de concurrencia
                    successful_deploys = 0
                    failed_deploys = 0
                    for i in range(0, len(tasks), concurrency_limit):
                        batch = tasks[i : i + concurrency_limit]
                        results = await asyncio.gather(*batch)
                        successful_deploys += sum(1 for _, success in results if success)
                        failed_deploys += sum(1 for _, success in results if not success)

                    logger.info(f"LAUNCHER: Ciclo de despliegue completado. Exitosos: {successful_deploys}, Fallidos: {failed_deploys}.")
                else:
                    logger.info("LAUNCHER: No hay robots para ejecutar en este ciclo.")
            except Exception as e:
                logger.error(f"LAUNCHER: Error fatal en el ciclo de lanzamiento: {e}", exc_info=True)

            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    async def _run_sync_cycle(self, interval: int):
        """Ciclo asíncrono para la sincronización de tablas maestras."""
        while not self._shutdown_event.is_set():
            try:
                logger.info("SYNC: Iniciando ciclo de sincronización...")
                robots_task = self.aa_client.obtener_robots()
                devices_task = self.aa_client.obtener_devices()
                users_task = self.aa_client.obtener_usuarios_detallados()
                robots, devices, users = await asyncio.gather(robots_task, devices_task, users_task)

                users_by_id = {user["UserId"]: user for user in users if isinstance(user, dict) and user.get("UserId")}
                devices_procesados = []
                for device in devices:
                    if isinstance(device, dict):
                        user_id = device.get("UserId")
                        if user_id in users_by_id:
                            device["Licencia"] = users_by_id[user_id].get("Licencia")
                        devices_procesados.append(device)

                self.db_connector.merge_robots(robots)
                self.db_connector.merge_equipos(devices_procesados)
                logger.info(f"SYNC: Ciclo completado. {len(robots)} robots y {len(devices_procesados)} equipos sincronizados.")
            except Exception as e:
                logger.error(f"SYNC: Error en el ciclo: {e}", exc_info=True)
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    async def _run_conciliador_cycle(self, interval: int):
        """Ciclo asíncrono para la conciliación de estados."""
        while not self._shutdown_event.is_set():
            try:
                logger.info("CONCILIADOR: Iniciando ciclo de conciliación...")
                await self.conciliador.conciliar_implementaciones()
                logger.info("CONCILIADOR: Ciclo de conciliación completado.")
            except Exception as e:
                logger.error(f"CONCILIADOR: Error en el ciclo: {e}", exc_info=True)
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    async def _deploy_and_register_robot(self, robot_info: Dict, bot_input: Dict, auth_headers: Dict) -> Tuple[int, bool]:
        """
        Encapsula la lógica para desplegar un robot y registrar su ejecución,
        incluyendo reintentos para errores específicos.
        """
        robot_id = robot_info["RobotId"]
        lanzador_cfg = ConfigManager.get_lanzador_config()
        max_attempts = 1 + lanzador_cfg.get("max_reintentos_deploy", 1)  # Intentos = 1 original + N reintentos
        delay_seconds = lanzador_cfg.get("delay_reintento_deploy_seg", 15)

        for attempt in range(1, max_attempts + 1):
            try:
                deployment_result = await self.aa_client.desplegar_bot_v4(
                    file_id=robot_id, user_ids=[robot_info["UserId"]], bot_input=bot_input, callback_auth_headers=auth_headers
                )

                if deployment_result and "deploymentId" in deployment_result:
                    self.db_connector.insertar_registro_ejecucion(
                        id_despliegue=deployment_result["deploymentId"],
                        db_robot_id=robot_id,
                        db_equipo_id=robot_info.get("EquipoId"),
                        a360_user_id=robot_info["UserId"],
                        marca_tiempo_programada=robot_info.get("Hora"),
                        estado="DEPLOYED",
                    )
                    logger.info(
                        f"LAUNCHER: Robot {robot_id} desplegado con ID: {deployment_result['deploymentId']} (Intento {attempt}/{max_attempts})"
                    )
                    return robot_id, True  # Éxito, salir de la función
                else:
                    error_msg = deployment_result.get("error", "Fallo al obtener deploymentId")
                    logger.error(f"LAUNCHER: Error de API al desplegar robot {robot_id}: {error_msg}")
                    return robot_id, False  # Error no reintentable, fallar directamente

            except httpx.HTTPStatusError as e:
                # Verificar si es el error específico que queremos reintentar
                is_device_error = e.response.status_code == 400 and "are not active" in e.response.text and "INVALID_ARGUMENT" in e.response.text

                if is_device_error and attempt < max_attempts:
                    logger.warning(
                        f"LAUNCHER: Fallo de despliegue para robot {robot_id} (Intento {attempt}/{max_attempts}): El dispositivo no está activo. Reintentando en {delay_seconds}s..."
                    )
                    await asyncio.sleep(delay_seconds)
                    continue  # Continuar con el siguiente intento del bucle
                else:
                    logger.error(
                        f"LAUNCHER: Fallo de despliegue definitivo para robot {robot_id} (Intento {attempt}/{max_attempts}): {e.response.status_code} - {e.response.text}"
                    )
                    return robot_id, False  # Fallo definitivo

            except Exception as e:
                logger.error(f"LAUNCHER: Excepción inesperada al desplegar robot {robot_id} (Intento {attempt}/{max_attempts}): {e}", exc_info=True)
                return robot_id, False  # Fallo definitivo

        # Si el bucle termina sin éxito
        logger.error(f"LAUNCHER: El despliegue del robot {robot_id} falló después de {max_attempts} intentos.")
        return robot_id, False
