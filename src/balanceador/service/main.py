# SAM/src/balanceador/service/main.py ()
import logging
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import schedule

from src.balanceador.clients.clouders_client import CloudersClient
from src.balanceador.service.balanceo import Balanceo
from src.common.database.sql_client import DatabaseConnector
from src.common.utils.config_manager import ConfigManager
from src.common.utils.mail_client import EmailAlertClient

logger = logging.getLogger(__name__)


class BalanceadorService:
    """
    Servicio de Balanceo de SAM, encapsulado en una clase para un control claro
    del ciclo de vida y los recursos.
    """

    def __init__(self):
        """Inicializa el servicio Balanceador."""
        logger.info("Inicializando componentes del BalanceadorService...")

        # --- Carga de Configuración ---
        self.cfg_balanceador_specifics = ConfigManager.get_balanceador_config()

        # --- Configuración de Clientes y Conectores ---
        cfg_sql_sam = ConfigManager.get_sql_server_config("SQL_SAM")
        self.db_sam = DatabaseConnector(
            servidor=cfg_sql_sam["server"],
            base_datos=cfg_sql_sam["database"],
            usuario=cfg_sql_sam["uid"],
            contrasena=cfg_sql_sam["pwd"],
            db_config_prefix="SQL_SAM",
        )

        cfg_sql_rpa360 = ConfigManager.get_sql_server_config("SQL_RPA360")
        self.db_rpa360 = DatabaseConnector(
            servidor=cfg_sql_rpa360["server"],
            base_datos=cfg_sql_rpa360["database"],
            usuario=cfg_sql_rpa360["uid"],
            contrasena=cfg_sql_rpa360["pwd"],
            db_config_prefix="SQL_RPA360",
        )

        self.clouders_client = CloudersClient()

        self.notificador = EmailAlertClient(service_name="Balanceador")

        # --- Componentes del Servicio ---
        self.balanceo = Balanceo(self)
        self.executor = ThreadPoolExecutor(max_workers=4)

        # --- Control de Estado ---
        self._shutdown_event = threading.Event()
        self._is_shutting_down = False
        logger.info("BalanceadorService inicializado correctamente.")

    def run(self):
        """Inicia el ciclo principal del servicio."""
        intervalo = self.cfg_balanceador_specifics.get("intervalo_ciclo_balanceo_seg", 60)
        schedule.every(intervalo).seconds.do(self._execute_cycle)

        logger.info(f"Ciclo de balanceo programado cada {intervalo} segundos. El servicio está activo.")

        # Ejecutar un ciclo inmediatamente al arrancar
        self._execute_cycle()

        while not self._shutdown_event.is_set():
            schedule.run_pending()
            time.sleep(1)

        self._cleanup()

    def stop(self):
        """Detiene el servicio de forma ordenada."""
        logger.info("Recibida solicitud de parada para BalanceadorService.")
        self._is_shutting_down = True
        self._shutdown_event.set()

    # --- MÉTODO AÑADIDO ---
    def obtener_pools_activos(self) -> List[Dict[str, Any]]:
        """Obtiene todos los pools activos de la base de datos."""
        try:
            logger.info("Obteniendo la lista de pools de balanceo activos...")
            query = "SELECT PoolId, Nombre FROM dbo.Pools WHERE Activo = 1 ORDER BY Nombre;"
            pools = self.db_sam.ejecutar_consulta(query, es_select=True)
            logger.info(f"Se encontraron {len(pools or [])} pools activos.")
            return pools or []
        except Exception as e:
            logger.error(f"Error crítico al obtener pools activos: {e}", exc_info=True)
            return []

    def _execute_cycle(self):
        """Ejecuta un único ciclo de la lógica de balanceo."""
        if self._shutdown_event.is_set():
            return

        logger.info("=" * 20 + " INICIANDO CICLO DE BALANCEO " + "=" * 20)
        try:
            # Etapa 0: Obtener la fotografía completa del estado del sistema UNA SOLA VEZ
            estado_global = self.balanceo._obtener_estado_inicial_global()
            if self._shutdown_event.is_set():
                return

            # Etapa 1: Limpieza Global (ahora pasamos el estado)
            mapa_config_robots = self.balanceo.ejecutar_limpieza_global(estado_global)
            if self._shutdown_event.is_set():
                return

            # Etapa 2: Balanceo Interno de cada Pool
            pools_activos = self.obtener_pools_activos()

            # Procesar cada pool específico
            for pool in pools_activos:
                self.balanceo.ejecutar_balanceo_interno_de_pool(pool["PoolId"], estado_global)
                if self._shutdown_event.is_set():
                    return

            # Procesar el Pool General (PoolId = None)
            self.balanceo.ejecutar_balanceo_interno_de_pool(None, estado_global)
            if self._shutdown_event.is_set():
                return

            # Etapa 3: Desborde y Demanda Adicional Global
            self.balanceo.ejecutar_fase_de_desborde_global(estado_global, mapa_config_robots)

        except Exception as e:
            logger.critical(f"Error fatal durante el ciclo de balanceo: {e}", exc_info=True)
            self.notificador.send_alert(
                subject="Error Crítico en Ciclo de Balanceador SAM",
                message=f"Se ha producido un error irrecuperable en el ciclo principal del balanceador.\n\nError: {e}",
                is_critical=True,
            )
        logger.info("=" * 20 + " CICLO DE BALANCEO COMPLETADO " + "=" * 20)

    def _cleanup(self):
        """Libera todos los recursos del servicio."""
        logger.info("Iniciando limpieza de recursos del BalanceadorService...")
        schedule.clear()

        if self.executor:
            self.executor.shutdown(wait=True)

        if self.db_sam:
            self.db_sam.cerrar_conexion()

        if self.db_rpa360:
            self.db_rpa360.cerrar_conexion()

        logger.info("Limpieza de recursos completada.")

    def _obtener_carga_de_trabajo_consolidada(self) -> Dict[int, int]:
        """Obtiene la carga de trabajo de todas las fuentes de forma concurrente."""
        logger.debug("Obteniendo carga de trabajo consolidada...")
        mapa_nombres_a_ids = self._obtener_mapeo_nombres_a_ids()

        future_rpa360 = self.executor.submit(self._obtener_carga_rpa360)
        future_clouders = self.executor.submit(self._obtener_carga_clouders)

        carga_rpa360 = future_rpa360.result()
        carga_clouders = future_clouders.result()

        carga_total_por_nombre: Dict[str, int] = {}

        # Procesar carga de rpa360
        for item in carga_rpa360:
            nombre = item.get("Robot")
            tickets = item.get("CantidadTickets", 0)
            if nombre and tickets > 0:
                carga_total_por_nombre[nombre] = carga_total_por_nombre.get(nombre, 0) + tickets

        # Procesar carga de Clouders
        for item in carga_clouders:
            nombre_sam = item.get("robot_name_sam", item.get("robot_name"))
            tickets = item.get("CantidadTickets", 0)
            if nombre_sam and tickets > 0:
                carga_total_por_nombre[nombre_sam] = carga_total_por_nombre.get(nombre_sam, 0) + tickets

        # Convertir a carga por ID
        carga_final_por_id: Dict[int, int] = {}
        for nombre, tickets in carga_total_por_nombre.items():
            if nombre in mapa_nombres_a_ids:
                robot_id = mapa_nombres_a_ids[nombre]
                carga_final_por_id[robot_id] = tickets

        logger.info(f"Carga consolidada final: {len(carga_final_por_id)} robots con demanda.")
        return carga_final_por_id

    def _obtener_carga_rpa360(self) -> List[Dict[str, Any]]:
        """Obtiene la carga de trabajo desde la BD rpa360."""
        try:
            return self.db_rpa360.ejecutar_consulta("EXEC dbo.usp_obtener_tickets_pendientes_por_robot;", es_select=True) or []
        except Exception as e:
            logger.error(f"Error obteniendo carga de rpa360: {e}", exc_info=True)
            return []

    def _obtener_carga_clouders(self) -> List[Dict[str, Any]]:
        """Obtiene la carga de trabajo desde la API de Clouders."""
        try:
            return self.clouders_client.obtener_tickets_pendientes()
        except Exception as e:
            logger.error(f"Error obteniendo carga de Clouders API: {e}", exc_info=True)
            return []

    def _obtener_mapeo_nombres_a_ids(self) -> Dict[str, int]:
        """Obtiene un mapa de Nombre de Robot -> RobotId desde la BD SAM."""
        try:
            robots = self.db_sam.ejecutar_consulta("SELECT RobotId, Robot FROM dbo.Robots WHERE Activo = 1;", es_select=True) or []
            return {r["Robot"]: r["RobotId"] for r in robots if "Robot" in r and "RobotId" in r}
        except Exception as e:
            logger.error(f"Error al obtener mapeo de nombres a IDs: {e}", exc_info=True)
            return {}

    def _calcular_equipos_necesarios_para_robot(self, tickets: int, config: Dict) -> int:
        """Calcula los equipos necesarios para un robot basado en su carga y configuración."""
        if tickets <= 0:
            return 0

        min_equipos = config.get("MinEquipos", 1)
        max_equipos = config.get("MaxEquipos", -1)
        ratio = config.get("TicketsPorEquipoAdicional") or self.cfg_balanceador_specifics.get("default_tickets_por_equipo", 10)

        equipos_calculados = max(min_equipos, math.ceil(tickets / ratio))

        return min(equipos_calculados, max_equipos) if max_equipos != -1 else equipos_calculados
