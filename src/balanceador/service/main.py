# SAM/src/Balanceador/service/main.py

import atexit
import math
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

import schedule

# --- Importaciones de Módulos Comunes y Específicos ---
from balanceador.clients.clouders_client import CloudersClient  # Nueva importación
from balanceador.database.historico_client import HistoricoBalanceoClient
from balanceador.service.balanceo import Balanceo
from common.database.sql_client import DatabaseConnector
from common.utils.config_manager import ConfigManager
from common.utils.logging_setup import setup_logging
from common.utils.mail_client import EmailAlertClient

# --- Configurar Logger para el Balanceador ---
log_cfg_balanceador = ConfigManager.get_log_config()  #
logger_name = "balanceador.service.main"
logger = setup_logging(
    log_config=log_cfg_balanceador,
    logger_name=logger_name,
    log_file_name_override=log_cfg_balanceador.get("app_log_filename_balanceador"),  #
)


class Balanceador:
    """
    Versión mejorada del Balanceador SAM.

    Con protección contra thrashing, sistema de prioridades, concurrencia y registro histórico.
    """

    def __init__(self):
        """Inicializa el Balanceador SAM."""
        logger.info("Inicializando SAM Balanceador...")

        self.cfg_balanceador_specifics = ConfigManager.get_balanceador_config()
        self.cfg_email_balanceador = ConfigManager.get_email_config("EMAIL")

        # Configuración de balanceo
        self.intervalo_ciclo_seg = self.cfg_balanceador_specifics.get("intervalo_ciclo_balanceo_seg", 60)
        self.default_tickets_por_equipo = self.cfg_balanceador_specifics.get("default_tickets_por_equipo", 10)
        self.mapa_robots = self.cfg_balanceador_specifics.get("mapa_robots", {})

        # Configuración de concurrencia
        self.max_workers = self.cfg_balanceador_specifics.get("max_workers_balanceo", 4)
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

        # Conector a la BD SAM
        cfg_sql_sam = ConfigManager.get_sql_server_config("SQL_SAM")
        self.db_sam = DatabaseConnector(
            servidor=cfg_sql_sam["server"],
            base_datos=cfg_sql_sam["database"],
            usuario=cfg_sql_sam["uid"],
            contrasena=cfg_sql_sam["pwd"],
            db_config_prefix="SQL_SAM",
        )

        # Conector a la BD rpa360
        cfg_sql_rpa360 = ConfigManager.get_sql_server_config("SQL_RPA360")
        self.db_rpa360 = DatabaseConnector(
            servidor=cfg_sql_rpa360["server"],
            base_datos=cfg_sql_rpa360["database"],
            usuario=cfg_sql_rpa360["uid"],
            contrasena=cfg_sql_rpa360["pwd"],
            db_config_prefix="SQL_RPA360",
        )

        # Reemplazar la inicialización del cliente MySQL por el nuevo CloudersClient
        self.cfg_clouders = ConfigManager.get_clouders_api_config()  # Nuevo método necesario
        self.clouders_client = CloudersClient(
            config=self.cfg_clouders,
            mapa_robots=self.mapa_robots,
            logger_instance=logger
        )

        # Cliente para notificaciones
        self.notificador = EmailAlertClient()

        # Cliente para histórico de balanceo
        self.historico_client = HistoricoBalanceoClient(self.db_sam)

        # Inicializar el módulo de balanceo
        self.balanceo = Balanceo(self)

        # Control de estado y sincronización
        self._is_shutting_down = False
        self.shutdown_event = threading.Event()
        self._lock = RLock()

        # Registrar handlers de salida
        atexit.register(self.limpiar_al_salir)

        # Configurar tarea programada
        self.configurar_tarea_programada()
        logger.info("SAM Balanceador inicializado y tarea de ciclo programada.")

    def configurar_tarea_programada(self):
        """Configura la tarea programada para el ciclo de balanceo."""
        intervalo: int = max(1, self.intervalo_ciclo_seg)

        # Programar el ciclo de balanceo cada X segundos
        schedule.every(intervalo).seconds.do(self.ejecutar_ciclo_balanceo)

        logger.info(f"Tarea de balanceo programada cada {intervalo} segundos.")

    def _obtener_carga_de_trabajo_consolidada(self) -> Dict[int, int]:
        """
        Obtiene la carga de trabajo consolidada de todas las fuentes.

        Returns: Dict[int, int]: Mapa de {RobotId: CantidadTickets}
        """
        logger.debug("Obteniendo carga de trabajo consolidada...")
        mapa_nombres_a_ids = self._obtener_mapeo_nombres_a_ids()
        carga_por_nombre: Dict[str, int] = {}

        # Ejecutar consultas en paralelo
        future_rpa360 = self.executor.submit(self._obtener_carga_rpa360)
        future_clouders = self.executor.submit(self._obtener_carga_clouders)

        # Procesar resultados
        self._procesar_carga_rpa360(future_rpa360.result(), carga_por_nombre, mapa_nombres_a_ids)
        self._procesar_carga_clouders(future_clouders.result(), carga_por_nombre)

        # Convertir a formato final
        return self._convertir_carga_a_formato_final(carga_por_nombre, mapa_nombres_a_ids)

    def _obtener_carga_rpa360(self) -> List[Dict[str, Any]]:
        """Obtiene la carga de trabajo desde rpa360."""
        try:
            query_rpa360 = "EXEC dbo.usp_obtener_tickets_pendientes_por_robot;"
            tickets_rpa360 = self.db_rpa360.ejecutar_consulta(query_rpa360, es_select=True)
            logger.info(f"Carga obtenida de rpa360: {len(tickets_rpa360 or [])} registros procesados.")
            return tickets_rpa360 or []
        except Exception as e:
            logger.error(f"Error obteniendo carga de trabajo de rpa360: {e}", exc_info=True)
            return []

    def _obtener_carga_clouders(self) -> List[Dict[str, Any]]:
        """Obtiene la carga de trabajo desde clouders."""
        try:
            # Usar el nuevo cliente
            tickets_clouders = self.clouders_client.obtener_tickets_pendientes()
            logger.info(f"Carga obtenida de clouders: {len(tickets_clouders or [])} registros procesados.")
            return tickets_clouders or []
        except Exception as e:
            logger.error(f"Error obteniendo carga de trabajo de clouders (API): {e}", exc_info=True)
            return []

    def _procesar_carga_rpa360(self, tickets_rpa360: List[Dict[str, Any]], carga_por_nombre: Dict[str, int], mapa_nombres_a_ids: Dict[str, int]):
        """Procesa la carga de trabajo de rpa360."""
        for item in tickets_rpa360:
            robot_id_rpa360 = item.get("RobotId")
            robot_nombre_rpa360 = item.get("Robot")
            tickets_rpa360_val = item.get("CantidadTickets")

            if tickets_rpa360_val is not None and int(tickets_rpa360_val) > 0:
                if robot_nombre_rpa360:
                    carga_por_nombre[robot_nombre_rpa360] = carga_por_nombre.get(robot_nombre_rpa360, 0) + int(tickets_rpa360_val)
                elif robot_id_rpa360 is not None:
                    for nombre, id_sam in mapa_nombres_a_ids.items():
                        if id_sam == int(robot_id_rpa360):
                            carga_por_nombre[nombre] = carga_por_nombre.get(nombre, 0) + int(tickets_rpa360_val)
                            break

    def _procesar_carga_clouders(self, tickets_clouders: List[Dict[str, Any]], carga_por_nombre: Dict[str, int]):
        """Procesa la carga de trabajo de clouders."""
        mapa_robots_clouders = self.mapa_robots
        for item_raw in tickets_clouders:
            robot_name_clouders = item_raw.get("robot_name")
            tickets_str = item_raw.get("CantidadTickets")

            if robot_name_clouders and tickets_str:
                try:
                    tickets = int(tickets_str)
                    if tickets > 0:
                        robot_name_sam = mapa_robots_clouders.get(robot_name_clouders, robot_name_clouders)
                        carga_por_nombre[robot_name_sam] = carga_por_nombre.get(robot_name_sam, 0) + tickets
                except ValueError:
                    logger.warning(f"Valor no numérico para CantidadTickets ('{tickets_str}') desde clouders para robot '{robot_name_clouders}'.")

    def _convertir_carga_a_formato_final(self, carga_por_nombre: Dict[str, int], mapa_nombres_a_ids: Dict[str, int]) -> Dict[int, int]:
        """Convierte la carga por nombre a carga por ID."""
        carga_total: Dict[int, int] = {}
        mapa_ids_a_nombres: Dict[int, str] = {}

        for nombre_robot, tickets in carga_por_nombre.items():
            if nombre_robot in mapa_nombres_a_ids:
                robot_id: int = mapa_nombres_a_ids[nombre_robot]
                carga_total[robot_id] = tickets
                mapa_ids_a_nombres[robot_id] = nombre_robot

        detalle_con_nombres: Dict[str, int] = {f"{robot_id} ({mapa_ids_a_nombres[robot_id]})": tickets for robot_id, tickets in carga_total.items()}
        logger.info(f"Carga de trabajo consolidada final: {len(carga_total)} robots con demanda. Detalle: {str(detalle_con_nombres)[:200]}...")
        return carga_total

    def _obtener_mapeo_nombres_a_ids(self) -> Dict[str, int]:
        """
        Obtiene un mapeo de nombres de robots a sus IDs en la base de datos SAM.

        Returns: Dict[str, int]: Mapa de {NombreRobot: RobotId}
        """
        logger.debug("Obteniendo mapeo de nombres de robots a IDs...")

        try:
            query = "SELECT RobotId, Robot FROM dbo.Robots WHERE Activo = 1;"
            robots = self.db_sam.ejecutar_consulta(query, es_select=True) or []

            mapa_nombres_a_ids = {}
            for robot in robots:
                nombre = robot.get("Robot")
                robot_id = robot.get("RobotId")
                if nombre and robot_id is not None:
                    mapa_nombres_a_ids[nombre] = int(robot_id)

            logger.debug(f"Obtenido mapeo para {len(mapa_nombres_a_ids)} robots")
            return mapa_nombres_a_ids
        except Exception as e:
            logger.error(f"Error al obtener mapeo de nombres a IDs: {e}", exc_info=True)
            return {}

    def _calcular_equipos_necesarios_para_robot(self, tickets_actuales: int, robot_config: Dict[str, Any]) -> int:
        """
        Calcula la cantidad de equipos necesarios para un robot.

        Args: tickets_actuales: Cantidad actual de tickets
              robot_config: Configuración del robot

        Returns: int: Cantidad de equipos necesarios
        """
        min_equipos = robot_config.get("MinEquipos", 1)
        max_equipos_cfg = robot_config.get("MaxEquipos", -1)
        tickets_por_equipo_adic_cfg = robot_config.get("TicketsPorEquipoAdicional")

        if tickets_actuales <= 0:
            return 0

        ratio_aplicable = (
            tickets_por_equipo_adic_cfg if tickets_por_equipo_adic_cfg and tickets_por_equipo_adic_cfg > 0 else self.default_tickets_por_equipo
        )
        if ratio_aplicable <= 0:
            ratio_aplicable = 1  # Evitar división por cero

        equipos_por_tickets: int = math.ceil(tickets_actuales / ratio_aplicable)
        equipos_necesarios = max(min_equipos, int(equipos_por_tickets))

        if max_equipos_cfg != -1:
            equipos_necesarios = min(equipos_necesarios, max_equipos_cfg)

        return equipos_necesarios

    def ejecutar_ciclo_balanceo(self):
        """
        Ejecuta el ciclo de balanceo completo, orquestando las diferentes etapas.
        """
        if self._is_shutting_down:
            logger.info("SAM Balanceador: Ciclo abortado (cierre general).")
            return

        logger.info("=" * 20 + " INICIANDO CICLO DE BALANCEO " + "=" * 20)

        # Invocar la nueva secuencia de lógica de balanceo
        try:
            # Etapa 1: Limpieza Global
            # Este método ahora devuelve el estado limpio y consolidado
            estado_limpio = self.balanceo.ejecutar_limpieza_global()
            if self._is_shutting_down:
                return

            # Etapa 2: Balanceo Interno de cada Pool
            pools_activos = self.balanceo.obtener_pools_activos()

            # Procesar cada pool específico
            for pool in pools_activos:
                self.balanceo.ejecutar_balanceo_interno_de_pool(pool["PoolId"], estado_limpio)
                if self._is_shutting_down:
                    return

            # Procesar el Pool General
            self.balanceo.ejecutar_balanceo_interno_de_pool(None, estado_limpio)
            if self._is_shutting_down:
                return

            # Etapa 3: Desborde y Demanda Adicional Global
            self.balanceo.ejecutar_fase_de_desborde_global(estado_limpio)

        except Exception as e:
            logger.critical(f"Error fatal durante la orquestación del ciclo de balanceo: {e}", exc_info=True)
            # Aquí podrías agregar una notificación por email
            self.notificador.send_alert(
                subject="Error Crítico en Ciclo de Balanceador SAM",
                message=f"Se ha producido un error irrecuperable en el ciclo principal del balanceador.\n\nError: {e}",
                is_critical=True,
            )

        logger.info("=" * 20 + " CICLO DE BALANCEO COMPLETADO " + "=" * 20)

    def limpiar_al_salir(self):
        """Realiza limpieza de recursos al salir."""
        logger.info("SAM Balanceador: Realizando limpieza de recursos al salir (atexit)...")
        self.finalizar_servicio()

    def finalizar_servicio(self):
        """Finaliza el servicio de forma segura."""
        logger.info("SAM Balanceador: Iniciando proceso de finalización del servicio...")
        with self._lock:
            if self._is_shutting_down:
                logger.info("SAM Balanceador: El servicio ya está en proceso de finalización.")
                return
            self._is_shutting_down = True

        self.shutdown_event.set()
        logger.info("SAM Balanceador: Evento de cierre (shutdown_event) activado.")

        logger.info("SAM Balanceador: Limpiando tareas de 'schedule'...")
        schedule.clear()

        # Cerrar ThreadPoolExecutor
        if hasattr(self, "executor") and self.executor:
            logger.info("Cerrando ThreadPoolExecutor del Balanceador...")
            self.executor.shutdown(wait=True)
            self.executor = None

        time.sleep(1)  # Pequeña pausa para que los hilos puedan notar el cierre

        # Cerrar conexiones a bases de datos
        if hasattr(self, "db_sam") and self.db_sam:
            self.db_sam.cerrar_conexion_hilo_actual()
        if hasattr(self, "db_rpa360") and self.db_rpa360:
            self.db_rpa360.cerrar_conexion_hilo_actual()
        # Eliminar la línea de cierre del mysql_clouders ya que no lo usaremos más

        logger.info("SAM Balanceador: Finalización de servicio completada.")


# --- Funciones de Nivel de Módulo para el Punto de Entrada ---
app_instance_balanceador: Optional[Balanceador] = None


def main():
    """Lógica principal del servicio."""
    global app_instance_balanceador
    app_instance_balanceador = Balanceador()

    logger.info("SAM Balanceador: Ejecutando ciclo inicial de balanceo...")
    if not app_instance_balanceador.shutdown_event.is_set():
        try:
            app_instance_balanceador.ejecutar_ciclo_balanceo()
        except Exception as e_init_cycle:
            logger.error(f"Error en el ciclo inicial de balanceo: {e_init_cycle}", exc_info=True)

    logger.info("SAM Balanceador: Iniciando bucle principal de 'schedule'. El servicio está corriendo.")
    while not app_instance_balanceador.shutdown_event.is_set():
        schedule.run_pending()
        app_instance_balanceador.shutdown_event.wait(timeout=1)  # Espera interrumpible
    logger.info("SAM Balanceador: Bucle principal de 'schedule' terminado.")


def signal_handler_main(sig, frame):
    """Manejador de señales de terminación."""
    logger.warning(f"Señal de terminación {signal.Signals(sig).name} recibida. Cerrando SAM Balanceador...")
    if app_instance_balanceador:
        app_instance_balanceador.finalizar_servicio()


def start_balanceador():
    """Punto de entrada principal del script."""
    signal.signal(signal.SIGINT, signal_handler_main)
    signal.signal(signal.SIGTERM, signal_handler_main)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, signal_handler_main)

    try:
        main()
    except Exception as e:
        logger.critical(f"Error fatal en la lógica principal del servicio SAM Balanceador: {e}", exc_info=True)
        if app_instance_balanceador:
            app_instance_balanceador.finalizar_servicio()
    finally:
        logger.info("SAM Balanceador: Script principal (main_for_run_script) ha finalizado.")


if __name__ == "__main__":
    start_balanceador()
