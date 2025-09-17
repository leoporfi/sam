# src/lanzador/service/conciliador.py
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import pytz
from dateutil import parser as dateutil_parser

from src.common.clients.aa_client import AutomationAnywhereClient
from src.common.database.sql_client import DatabaseConnector
from src.common.utils.config_manager import ConfigManager

# --- OBTENER EL LOGGER ---
# Simplemente obtenemos el logger. La configuración ya fue realizada
# por el script de arranque del servicio.
logger = logging.getLogger(__name__)


class ConciliadorImplementaciones:
    def __init__(self, db_connector: DatabaseConnector, aa_client: AutomationAnywhereClient):
        self.db_connector = db_connector
        self.aa_client = aa_client
        lanzador_cfg = ConfigManager.get_lanzador_config()
        self.max_intentos_fallidos = lanzador_cfg.get("conciliador_max_intentos_fallidos", 3)
        # Estados válidos que la API de A360 podría devolver para el conciliador.
        self.ESTADOS_VALIDOS_API_PARA_CONCILIACION = {
            "COMPLETED",
            "DEPLOYED",
            "DEPLOY_FAILED",
            "QUEUED",
            "PENDING_EXECUTION",
            "UPDATE",
            "RUNNING",
            "RUN_FAILED",
            "RUN_PAUSED",
            "RUN_ABORTED",
            "RUN_TIMED_OUT",
            "UNKNOWN",
        }

    def _convertir_utc_a_local_sam(self, fecha_utc_str: Optional[str]) -> Optional[datetime]:
        if not fecha_utc_str or fecha_utc_str in ["1970-01-01T00:00:00Z", ""]:
            return None
        try:
            dt_utc = dateutil_parser.isoparse(fecha_utc_str)
            tz_local_sam = pytz.timezone("America/Argentina/Buenos_Aires")
            dt_local = dt_utc.astimezone(tz_local_sam)
            logger.debug(f"Fecha UTC '{fecha_utc_str}' convertida a local SAM '{dt_local.isoformat()}'")
            return dt_local
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning("Zona horaria 'America/Argentina/Buenos_Aires' desconocida. Usando UTC-3 fijo como fallback.")
            return dt_utc.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-3)))
        except Exception as e:
            logger.error(f"Error al convertir fecha UTC a local SAM para '{fecha_utc_str}': {e}", exc_info=True)
            return None

    async def conciliar_implementaciones(self):
        """Actualiza estados de ejecuciones con la información obtenida desde AA."""
        try:
            ejecuciones_en_curso = self.db_connector.obtener_ejecuciones_en_curso()
            if not ejecuciones_en_curso:
                logger.info("Conciliador: No hay ejecuciones en curso para conciliar.")
                return

            deployment_ids = [imp["DeploymentId"] for imp in ejecuciones_en_curso if imp.get("DeploymentId")]
            if not deployment_ids:
                logger.info("Conciliador: No se encontraron DeploymentIds válidos.")
                return

            logger.info(f"Conciliador: Conciliando {len(deployment_ids)} deployment(s)...")
            detalles_api = await self.aa_client.obtener_detalles_por_deployment_ids(deployment_ids)

            if detalles_api:
                self._actualizar_estados_encontrados_db(detalles_api)

            self._gestionar_deployments_perdidos(deployment_ids, detalles_api)
            logger.info("Conciliador: Proceso de conciliación completado.")

        except Exception as e:
            logger.error(f"Error en conciliar_implementaciones: {e}", exc_info=True)

    def _actualizar_estados_encontrados_db(self, detalles_api: list):
        """Actualiza la BD SAM con los estados de los deployments encontrados en la API."""
        if not detalles_api:
            return

        updates_params = []
        for detalle in detalles_api:
            dep_id = detalle.get("deploymentId")
            status_api = detalle.get("status")
            end_date_str = detalle.get("endDateTime")

            if not dep_id or not status_api:
                logger.warning(f"Conciliador: Item de API sin deploymentId o status, omitiendo: {str(detalle)[:100]}")
                continue

            final_status_db = "RUNNING" if status_api == "UPDATE" else status_api
            if final_status_db not in self.ESTADOS_VALIDOS_API_PARA_CONCILIACION:
                continue

            fecha_fin_dt = self._convertir_utc_a_local_sam(end_date_str)
            updates_params.append((final_status_db, fecha_fin_dt, dep_id, final_status_db))

        if updates_params:
            query = """
                UPDATE dbo.Ejecuciones 
            SET 
                Estado = ?, 
                FechaFin = CASE WHEN ? IS NOT NULL THEN ? ELSE FechaFin END, 
                FechaActualizacion = GETDATE() 
            WHERE DeploymentId = ? AND CallbackInfo IS NULL;
            """

            formatted_params_for_update = [(p[0], p[1], p[1], p[2]) for p in updates_params]

            try:
                affected_count = 0
                for param_tuple in formatted_params_for_update:
                    count = self.db_connector.ejecutar_consulta(query, param_tuple, es_select=False)
                    if count is not None and count > 0:
                        affected_count += count
                logger.info(f"Conciliador: Actualizados {affected_count} registros de ejecuciones desde API con fechas locales.")
            except Exception as e_db_update:
                logger.error(f"Conciliador: Error de BD al actualizar estados encontrados con fechas locales: {e_db_update}", exc_info=True)

    # SIN USO - REEPLAZADO POR _gestionar_deployments_perdidos
    def _actualizar_estados_perdidos_db(self, deployment_ids_en_db: list, detalles_api: list):
        """Marca como UNKNOWN los deployments que estaban en BD pero no se encontraron en la API."""
        if not deployment_ids_en_db:
            return

        ids_encontrados_api = {item.get("deploymentId") for item in detalles_api if item.get("deploymentId")}
        ids_perdidos = [dep_id for dep_id in deployment_ids_en_db if dep_id not in ids_encontrados_api]

        if ids_perdidos:
            logger.warning(f"Conciliador: Deployments no encontrados en API, marcando como UNKNOWN: {ids_perdidos}")
            query = """
                UPDATE dbo.Ejecuciones 
            SET 
                Estado = 'UNKNOWN', 
                FechaFin = GETDATE(), 
                FechaActualizacion = GETDATE()
            WHERE DeploymentId = ?
              AND Estado NOT IN ('COMPLETED','RUN_COMPLETED','RUN_FAILED','RUN_ABORTED','DEPLOY_FAILED', 'UNKNOWN')
              AND CallbackInfo IS NULL 
              AND DATEDIFF(SECOND, FechaInicio, GETDATE()) > 60
            """
            params_perdidos = [(id_perdido,) for id_perdido in ids_perdidos]
            try:
                affected_count = 0
                for param_tuple in params_perdidos:
                    count = self.db_connector.ejecutar_consulta(query, param_tuple, es_select=False)
                    if count is not None and count > 0:
                        affected_count += count
                if affected_count > 0:
                    logger.info(f"Conciliador: Marcados {affected_count} deployments perdidos como UNKNOWN.")
            except Exception as e:
                logger.error(f"Conciliador: Error de BD al actualizar estados perdidos: {e}", exc_info=True)

    def _gestionar_deployments_perdidos(self, deployment_ids_en_db: list, detalles_api: list):
        """
        Incrementa el contador para deployments no encontrados y los marca como UNKNOWN
        si superan el umbral de reintentos.
        """
        if not deployment_ids_en_db:
            return

        ids_encontrados_api = {item.get("deploymentId") for item in detalles_api if item.get("deploymentId")}
        ids_perdidos = [dep_id for dep_id in deployment_ids_en_db if dep_id not in ids_encontrados_api]

        if not ids_perdidos:
            return

        try:
            # 1. Incrementar el contador para todos los deployments perdidos en este ciclo
            placeholders = ",".join("?" for _ in ids_perdidos)
            # Se añade "AND CallbackInfo IS NULL" para no incrementar contadores de ejecuciones que ya terminaron
            query_increment = (
                "UPDATE dbo.Ejecuciones "
                "SET IntentosConciliadorFallidos = IntentosConciliadorFallidos + 1, "
                "FechaActualizacion = GETDATE() "
                f"WHERE DeploymentId IN ({placeholders}) AND CallbackInfo IS NULL;"
            )
            count_incrementados = self.db_connector.ejecutar_consulta(query_increment, tuple(ids_perdidos), es_select=False)
            logger.info(f"Conciliador: Incrementado contador de intentos para {count_incrementados} deployment(s) no encontrados.")

            # 2. Marcar como UNKNOWN aquellos que han superado el umbral
            query_unknown = (
                "UPDATE dbo.Ejecuciones SET "
                "Estado = 'UNKNOWN', "
                "FechaFin = GETDATE(), "
                "FechaActualizacion = GETDATE() "
                f"WHERE DeploymentId IN ({placeholders}) AND IntentosConciliadorFallidos >= ?;"
            )

            params_unknown = tuple(ids_perdidos) + (self.max_intentos_fallidos,)
            count_unknown = self.db_connector.ejecutar_consulta(query_unknown, params_unknown, es_select=False)

            if count_unknown > 0:
                logger.warning(
                    f"Conciliador: Marcados {count_unknown} deployment(s) como UNKNOWN tras superar los {self.max_intentos_fallidos} intentos."
                )

        except Exception as e:
            logger.error(f"Conciliador: Error de BD al gestionar deployments perdidos: {e}", exc_info=True)
