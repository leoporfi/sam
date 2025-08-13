# src/lanzador/service/main.py (Versión Corregida y Simplificada)
import asyncio
import logging

from common.utils.config_manager import ConfigManager
from common.utils.logging_setup import setup_logging

# Configuración del logger
log_cfg = ConfigManager.get_log_config()
logger_name = "lanzador.service.main"
logger = setup_logging(log_config=log_cfg, logger_name=logger_name, log_file_name_override=log_cfg.get("app_log_filename_lanzador"))

from common.clients.aa_client import AutomationAnywhereClient
from common.database.sql_client import DatabaseConnector
from lanzador.service.conciliador import ConciliadorImplementaciones

# Evento para manejar el cierre limpio del servicio
shutdown_event = asyncio.Event()


def handle_shutdown_signal():
    """Activa el evento de cierre cuando se recibe una señal del sistema."""
    logger.info("Señal de apagado recibida. Finalizando ciclos de tareas...")
    shutdown_event.set()


async def run_sync_cycle(aa_client: AutomationAnywhereClient, db: DatabaseConnector, interval: int):
    """Ciclo asíncrono para la sincronización de tablas maestras."""
    while not shutdown_event.is_set():
        try:
            logger.info("SYNC: Iniciando ciclo de sincronización de tablas...")
            # Ejecutamos las llamadas a la API en paralelo para máxima eficiencia
            robots_task = aa_client.obtener_robots()
            devices_task = aa_client.obtener_devices()
            users_task = aa_client.obtener_usuarios_detallados()
            robots, devices, users = await asyncio.gather(robots_task, devices_task, users_task)

            # Procesamiento de datos antes del merge
            users_by_id = {user["UserId"]: user for user in users if isinstance(user, dict) and user.get("UserId")}

            # Procesar devices con la información de usuarios
            devices_procesados = []
            for device in devices:
                if isinstance(device, dict):
                    user_id = device.get("UserId")
                    if user_id in users_by_id:
                        device["Licencia"] = users_by_id[user_id].get("Licencia")
                    devices_procesados.append(device)

            # Lógica de procesamiento y merge
            db.merge_robots(robots)
            db.merge_equipos(devices_procesados)
            logger.info(f"SYNC: Ciclo completado. {len(robots)} robots y {len(devices_procesados)} equipos sincronizados.")
        except Exception as e:
            logger.error(f"SYNC: Error en el ciclo: {e}", exc_info=True)

        try:
            # Espera el intervalo de tiempo o hasta que se active la señal de cierre
            await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass  # Es el comportamiento esperado, simplemente continuamos el bucle


async def run_launcher_cycle(aa_client: AutomationAnywhereClient, db: DatabaseConnector, interval: int):
    """Ciclo asíncrono para el lanzamiento de robots."""
    while not shutdown_event.is_set():
        try:
            logger.info("LAUNCHER: Buscando robots para ejecutar...")
            robots_a_ejecutar = db.obtener_robots_ejecutables()
            if robots_a_ejecutar:
                logger.info(f"LAUNCHER: {len(robots_a_ejecutar)} robots encontrados. Desplegando...")

                # Para cada robot, lanzamos y guardamos su ejecución
                for robot in robots_a_ejecutar:
                    try:
                        # Desplegamos el robot
                        deployment_result = await aa_client.desplegar_bot(robot["RobotId"], [robot["UserId"]])

                        # Verificamos si el despliegue fue exitoso
                        if deployment_result and "deploymentId" in deployment_result:
                            # Guardamos el registro de ejecución
                            db.insertar_registro_ejecucion(
                                id_despliegue=deployment_result["deploymentId"],
                                db_robot_id=robot["RobotId"],
                                db_equipo_id=robot.get("EquipoId"),
                                a360_user_id=robot["UserId"],
                                marca_tiempo_programada=robot.get("MarcaTiempoProgramada"),
                                estado="DEPLOYED",
                            )
                            logger.info(f"LAUNCHER: Robot {robot['RobotId']} desplegado con deploymentId: {deployment_result['deploymentId']}")
                        else:
                            logger.error(f"LAUNCHER: Fallo al obtener deploymentId para robot {robot['RobotId']}")

                    except Exception as robot_error:
                        logger.error(f"LAUNCHER: Error al desplegar robot {robot['RobotId']}: {robot_error}", exc_info=True)
            else:
                logger.info("LAUNCHER: No hay robots para ejecutar en este ciclo.")

        except Exception as e:
            logger.error(f"LAUNCHER: Error en el ciclo: {e}", exc_info=True)

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


async def run_conciliador_cycle(conciliador: ConciliadorImplementaciones, interval: int):
    """Ciclo asíncrono para la conciliación de estados."""
    while not shutdown_event.is_set():
        try:
            logger.info("CONCILIADOR: Iniciando ciclo de conciliación...")
            await conciliador.conciliar_implementaciones()
            logger.info("CONCILIADOR: Ciclo de conciliación completado.")
        except Exception as e:
            logger.error(f"CONCILIADOR: Error en el ciclo: {e}", exc_info=True)

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


async def start_lanzador():
    """Punto de entrada principal que inicializa y ejecuta los ciclos del servicio."""
    # --- Configuración e Inicialización ---
    lanzador_cfg = ConfigManager.get_lanzador_config()
    db_cfg = ConfigManager.get_sql_server_config("SQL_SAM")
    aa_cfg = ConfigManager.get_aa_config()

    db_connector = DatabaseConnector(servidor=db_cfg["server"], base_datos=db_cfg["database"], usuario=db_cfg["uid"], contrasena=db_cfg["pwd"])
    aa_client = AutomationAnywhereClient(control_room_url=aa_cfg["url"], username=aa_cfg["user"], password=aa_cfg["pwd"])
    conciliador = ConciliadorImplementaciones(db_connector, aa_client)

    logger.info("Servicio Lanzador Asíncrono iniciado. Creando tareas de ciclo...")

    # --- Creación y Ejecución de Tareas Concurrentes ---
    tasks = []

    # El sync_task es opcional basado en la configuración
    if lanzador_cfg.get("habilitar_sync", True):  # True por defecto para mantener compatibilidad
        sync_task = asyncio.create_task(run_sync_cycle(aa_client, db_connector, lanzador_cfg["intervalo_sync_tablas_seg"]))
        tasks.append(sync_task)
        logger.info("Tarea de sincronización habilitada")
    else:
        logger.info("Tarea de sincronización deshabilitada por configuración")

    # Estas tareas siempre se crean
    launcher_task = asyncio.create_task(run_launcher_cycle(aa_client, db_connector, lanzador_cfg["intervalo_lanzador_seg"]))
    conciliador_task = asyncio.create_task(run_conciliador_cycle(conciliador, lanzador_cfg["intervalo_conciliador_seg"]))

    tasks.extend([launcher_task, conciliador_task])

    # Esperamos a que todas las tareas habilitadas finalicen
    await asyncio.gather(*tasks)

    # --- Cierre Limpio de Recursos ---
    await aa_client.close()
    db_connector.cerrar_conexion()
    logger.info("Servicio Lanzador finalizado limpiamente.")
