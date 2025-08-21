# src/lanzador/service/main.py (Corregido)
import asyncio
import logging
from typing import List

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
        lanzador_cfg = ConfigManager.get_lanzador_config()
        db_cfg = ConfigManager.get_sql_server_config("SQL_SAM")
        aa_cfg = ConfigManager.get_aa_config()
        # Obtener la nueva configuración del API Gateway
        gateway_cfg = ConfigManager.get_api_gateway_config()

        self.db_connector = DatabaseConnector(
            servidor=db_cfg["server"], base_datos=db_cfg["database"], usuario=db_cfg["uid"], contrasena=db_cfg["pwd"]
        )
        self.aa_client = AutomationAnywhereClient(
            control_room_url=aa_cfg["url"], username=aa_cfg["user"], password=aa_cfg["pwd"], callback_url_deploy=aa_cfg.get("url_callback")
        )
        self.api_gateway_client = ApiGatewayClient(gateway_cfg)
        self.conciliador = ConciliadorImplementaciones(self.db_connector, self.aa_client)
        logger.info("Componentes del servicio inicializados correctamente.")

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

    # --- Lógica de los Ciclos (sin cambios) ---

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

    async def _run_launcher_cycle(self, interval: int):
        """Ciclo asíncrono para el lanzamiento de robots."""
        lanzador_cfg = ConfigManager.get_lanzador_config()
        bot_input = {"in_NumRepeticion": {"type": "NUMBER", "number": lanzador_cfg.get("repeticiones", 1)}}

        while not self._shutdown_event.is_set():
            try:
                logger.info("LAUNCHER: Buscando robots para ejecutar...")
                robots_a_ejecutar = self.db_connector.obtener_robots_ejecutables()
                if robots_a_ejecutar:
                    auth_headers = {}  # Inicializar como diccionario vacío por defecto
                    try:
                        logger.info("LAUNCHER: Obteniendo token de autorización para callbacks...")
                        auth_headers = await self.api_gateway_client.get_auth_header()
                        if not auth_headers:
                            # Si get_auth_header devuelve un diccionario vacío, significa que falló la obtención
                            logger.warning("LAUNCHER: No se pudo obtener el token del API Gateway. Los robots se lanzarán sin cabecera de callback.")
                    except Exception as token_error:
                        logger.error(
                            f"LAUNCHER: Excepción al obtener token del API Gateway: {token_error}. Se continuará sin cabecera de callback.",
                            exc_info=True,
                        )

                    logger.info(f"LAUNCHER: {len(robots_a_ejecutar)} robots encontrados. Desplegando...")
                    for robot in robots_a_ejecutar:
                        try:
                            # 2. Pasar las cabeceras al método de despliegue.
                            deployment_result = await self.aa_client.desplegar_bot(
                                robot["RobotId"], [robot["UserId"]], bot_input=bot_input, callback_auth_headers=auth_headers # <-- Pasamos el token (o un dict vacío si falló)
                            )
                            if deployment_result and "deploymentId" in deployment_result:
                                self.db_connector.insertar_registro_ejecucion(
                                    id_despliegue=deployment_result["deploymentId"],
                                    db_robot_id=robot["RobotId"],
                                    db_equipo_id=robot.get("EquipoId"),
                                    a360_user_id=robot["UserId"],
                                    marca_tiempo_programada=robot.get("Hora"),
                                    estado="DEPLOYED",
                                )
                                logger.info(f"LAUNCHER: Robot {robot['RobotId']} desplegado con ID: {deployment_result['deploymentId']}")
                            else:
                                logger.error(f"LAUNCHER: Fallo al obtener deploymentId para robot {robot['RobotId']}")
                        except Exception as robot_error:
                            logger.error(f"LAUNCHER: Error al desplegar robot {robot['RobotId']}: {robot_error}", exc_info=True)
                else:
                    logger.info("LAUNCHER: No hay robots para ejecutar en este ciclo.")
            except Exception as e:
                logger.error(f"LAUNCHER: Error en el ciclo: {e}", exc_info=True)
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
