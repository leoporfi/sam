# service/conciliador.py
import time
import logging
from datetime import datetime
from datetime import datetime, timezone
from typing import Optional
# from dateutil import parser
from dateutil import parser as dateutil_parser
import pytz

# --- Configuración de Path (si es necesario, aunque service/main ya debería haberlo hecho) ---
from pathlib import Path
import sys 
SAM_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent # Raíz de SAM
if str(SAM_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SAM_PROJECT_ROOT))

from lanzador.clients.aa_client import AutomationAnywhereClient
# --- CAMBIAR ESTA LÍNEA ---
# from lanzador.database.sql_client import DatabaseConnector # <-- LÍNEA ANTIGUA
from common.database.sql_client import DatabaseConnector    # <-- LÍNEA NUEVA Y CORRECTA
# --- FIN DEL CAMBIO ---

# Si setup_logging se define en lanzador.utils.config y es el que quieres usar aquí:
# from lanzador.utils.config import get_lanzador_logger # Asumiendo que tienes esta función
# logger = get_lanzador_logger(__name__) # O un nombre específico como "SAMLanzador.Conciliador"

# O si quieres usar el setup_logging común directamente (necesitarías ConfigManager común):
from common.utils.logging_setup import setup_logging
from common.utils.config_manager import ConfigManager
log_cfg = ConfigManager.get_log_config()
logger_name = "lanzador.service.conciliador"  # Nombre del logger para este módulo
logger = setup_logging(
    log_config=log_cfg, 
    logger_name=logger_name, 
    log_file_name_override=log_cfg.get("app_log_filename_lanzador")
)



class ConciliadorImplementaciones:
    def __init__(self, db_connector: DatabaseConnector, aa_client: AutomationAnywhereClient): 
        self.db_connector = db_connector
        self.aa_client = aa_client
        # Estados válidos que la API de A360 podría devolver para el conciliador.
        # Estos son los estados que, si vienen de la API, se consideran para actualizar la BD.
        self.ESTADOS_VALIDOS_API_PARA_CONCILIACION = { 
            "COMPLETED", "DEPLOYED", "DEPLOY_FAILED", "QUEUED", "PENDING_EXECUTION",
            "UPDATE", "RUNNING", "RUN_FAILED", "RUN_PAUSED", "RUN_ABORTED", 
            "RUN_TIMED_OUT", "UNKNOWN",
        }


    def _convertir_utc_a_local_sam(self, fecha_utc_str: Optional[str]) -> Optional[datetime]:
        if not fecha_utc_str or fecha_utc_str in ["1970-01-01T00:00:00Z", ""]:
            return None
        
        try:
            dt_utc = dateutil_parser.isoparse(fecha_utc_str) # Esto devuelve un datetime timezone-aware (UTC)
            
            # Definir la zona horaria local de tu servidor SAM
            # Ejemplo para Argentina (America/Argentina/Buenos_Aires)
            # Necesitas tener la base de datos de zonas horarias IANA (tzdata) en tu sistema
            # o usar una biblioteca como pytz.
            try:
                # tz_local = datetime.now().astimezone().tzinfo # Intenta obtener la zona del sistema (puede no ser fiable)
                tz_local_sam = pytz.timezone("America/Argentina/Buenos_Aires") # Usar pytz para robustez
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning("Zona horaria 'America/Argentina/Buenos_Aires' desconocida para pytz. Usando UTC-3 fijo como fallback.")
                # Fallback a un offset fijo si pytz falla o no está disponible (menos ideal)
                # Esto no maneja el horario de verano correctamente.
                return dt_utc.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-3)))


            dt_local = dt_utc.astimezone(tz_local_sam)
            logger.debug(f"Fecha UTC '{fecha_utc_str}' convertida a local SAM '{dt_local.isoformat()}' ({tz_local_sam.zone})")
            return dt_local
        except ValueError as e:
            logger.warning(f"Conciliador: Formato de fecha inválido para endDateTime '{fecha_utc_str}' al convertir a local: {e}. Se usará NULL para FechaFin.")
            return None
        except Exception as ex: # Otras excepciones como pytz.UnknownTimeZoneError
             logger.error(f"Error al convertir fecha UTC a local SAM para '{fecha_utc_str}': {ex}", exc_info=True)
             return None


    def conciliar_implementaciones(self):
        """Actualiza estados de ejecuciones con la información obtenida desde AA."""
        try:
            ejecuciones_en_curso = self.db_connector.obtener_ejecuciones_en_curso()

            if not ejecuciones_en_curso:
                logger.info("Conciliador: No hay ejecuciones en curso en la BD para conciliar.")
                return

            # Asumiendo que la columna se llama 'DeploymentId' (sensible a mayúsculas/minúsculas)
            deployment_ids = [imp.get("DeploymentId") for imp in ejecuciones_en_curso if imp.get("DeploymentId")]
            # Filtrar Nones por si alguna fila no tuviera DeploymentId por alguna razón extraña

            if not deployment_ids:
                logger.info("Conciliador: No se encontraron DeploymentIds válidos en las ejecuciones en curso.")
                return

            logger.info(f"Conciliador: Conciliando {len(deployment_ids)} deployment(s): {str(deployment_ids)[:200]}...")
            
            # La API puede tener un límite en la cantidad de IDs por petición,
            # aunque obtener_detalles_por_deployment_ids ya podría manejar esto internamente
            # si el payload es muy grande. Por ahora, asumimos que el cliente API lo maneja
            # o que la cantidad no será tan masiva como para necesitar paginación aquí.
            # Si es necesario, replicar la lógica de `grupos_ids` que tenías antes.
            
            start_time = time.time()
            # El método en aa_client ya se llama obtener_detalles_por_deployment_ids
            detalles_api = self.aa_client.obtener_detalles_por_deployment_ids(deployment_ids)
            end_time = time.time()
            logger.info(f"Conciliador: Consulta a API AA para {len(deployment_ids)} IDs tomó {end_time - start_time:.2f}s. Obtenidos {len(detalles_api)} detalles.")

            if detalles_api: # Solo si la API devolvió algo
                self.actualizar_estados_encontrados_db(detalles_api)
            
            # Actualizar los que estaban en BD pero no se encontraron en la API (posiblemente finalizados o error)
            self.actualizar_estados_perdidos_db(deployment_ids, detalles_api)
            
            logger.info(f"Conciliador: Proceso de conciliación completado para {len(deployment_ids)} IDs iniciales.")

        except Exception as e:
            logger.error(f"Error en conciliar_implementaciones: {e}", exc_info=True) # exc_info=True para traceback completo


    def actualizar_estados_encontrados_db(self, detalles_api: list):
        """Actualiza la BD SAM con los estados de los deployments encontrados en la API."""
        if not detalles_api:
            return

        updates_params = []
        for detalle_item_api in detalles_api:
            dep_id = detalle_item_api.get("deploymentId")
            status_api = detalle_item_api.get("status")
            end_date_time_str_api = detalle_item_api.get("endDateTime")
            
            if not dep_id or not status_api:
                logger.warning(f"Conciliador: Item de API sin deploymentId o status, omitiendo: {str(detalle_item_api)[:100]}")
                continue

            final_status_db = "RUNNING" if status_api == "UPDATE" else status_api
            
            if final_status_db not in self.ESTADOS_VALIDOS_API_PARA_CONCILIACION:
                continue

            # Convertir a zona horaria local de SAM ANTES de preparar para BD
            fecha_fin_dt_para_db = self._convertir_utc_a_local_sam(end_date_time_str_api)
            
            params = (
                final_status_db, 
                fecha_fin_dt_para_db, # Este es ahora un objeto datetime en la zona local de SAM (o None)
                dep_id,
                final_status_db
            )
            updates_params.append(params)

        if updates_params:
            query_update = """
            UPDATE dbo.Ejecuciones 
            SET 
                Estado = ?, 
                FechaFin = CASE WHEN ? IS NOT NULL THEN ? ELSE FechaFin END, 
                FechaActualizacion = GETDATE() 
            WHERE DeploymentId = ?
              AND (
                    Estado <> ? OR 
                    (Estado NOT IN ('COMPLETED', 'RUN_COMPLETED', 'RUN_FAILED', 'RUN_ABORTED', 'DEPLOY_FAILED', 'UNKNOWN') AND CallbackInfo IS NULL)
                  );
            """
            formatted_params_for_update = [(p[0], p[1], p[1], p[2], p[3]) for p in updates_params]

            try:
                affected_count = 0
                for param_tuple in formatted_params_for_update:
                    count = self.db_connector.ejecutar_consulta(query_update, param_tuple, es_select=False)
                    if count is not None and count > 0:
                        affected_count += count
                logger.info(f"Conciliador: Actualizados {affected_count} registros de ejecuciones desde API con fechas locales.")
            except Exception as e_db_update:
                 logger.error(f"Conciliador: Error de BD al actualizar estados encontrados con fechas locales: {e_db_update}", exc_info=True)


    def actualizar_estados_encontrados_db_old(self, detalles_api: list):
        """Actualiza la BD SAM con los estados de los deployments encontrados en la API."""
        if not detalles_api:
            return

        updates_params = []
        for detalle_item_api in detalles_api:
            dep_id = detalle_item_api.get("deploymentId")
            status_api = detalle_item_api.get("status")
            end_date_time_str_api = detalle_item_api.get("endDateTime") # Formato: "2022-04-14T06:39:27.438843100Z"
            
            if not dep_id or not status_api:
                logger.warning(f"Conciliador: Item de API sin deploymentId o status, omitiendo: {str(detalle_item_api)[:100]}")
                continue

            final_status_db = "RUNNING" if status_api == "UPDATE" else status_api
            
            if final_status_db not in self.ESTADOS_VALIDOS_API_PARA_CONCILIACION:
                logger.debug(f"Conciliador: Estado API '{final_status_db}' para DeploymentId {dep_id} no está en la lista de estados válidos para conciliación directa, omitiendo.")
                continue

            fecha_fin_dt_para_db: Optional[datetime] = None
            if end_date_time_str_api and end_date_time_str_api not in ["1970-01-01T00:00:00Z", ""]:
                try:
                    # La API devuelve UTC (Z). Convertir a objeto datetime.
                    # pyodbc puede manejar objetos datetime directamente.
                    # No es necesario convertir a zona horaria local aquí si la BD almacena UTC o es indiferente.
                    # Si tu BD está en una zona horaria específica y quieres convertir, usa dateutil.parser
                    from dateutil import parser as dateutil_parser # Importar localmente
                    fecha_fin_dt_para_db = dateutil_parser.isoparse(end_date_time_str_api)
                except ImportError:
                    logger.warning("Modulo dateutil.parser no encontrado. No se podrán parsear fechas complejas de API.")
                    # Intento de parseo simple si dateutil no está
                    try:
                        fecha_fin_dt_para_db = datetime.strptime(end_date_time_str_api.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                         logger.warning(f"Conciliador: Formato de fecha inválido para endDateTime '{end_date_time_str_api}' en DeployID {dep_id}. Se usará NULL para FechaFin.")
                except ValueError: # Error con dateutil.parser o el simple
                    logger.warning(f"Conciliador: Formato de fecha inválido para endDateTime '{end_date_time_str_api}' en DeployID {dep_id}. Se usará NULL para FechaFin.")
            
            # Columnas en dbo.Ejecuciones: Estado, FechaFin, FechaActualizacion (si existe), DeploymentId
            # No actualizamos CallbackInfo aquí, ya que este es el flujo de conciliación, no de callback.
            # Solo actualizar si el estado en BD NO es ya terminal (COMPLETED, RUN_FAILED, etc.) Y si no hay CallbackInfo
            # O si el estado ha cambiado.
            params = (
                final_status_db, 
                fecha_fin_dt_para_db, # Puede ser None
                dep_id,
                final_status_db # Para la condición `Estado <> ?`
            )
            updates_params.append(params)

        if updates_params:
            # Query ajustada para tu tabla Ejecuciones
            # Solo actualiza si el estado ha cambiado O si el estado no es terminal Y aún no hay callback.
            # Y FechaFin solo si se provee una fecha_fin_dt_para_db
            query_update = """
            UPDATE dbo.Ejecuciones 
            SET 
                Estado = ?, 
                FechaFin = CASE WHEN ? IS NOT NULL THEN ? ELSE FechaFin END, 
                FechaActualizacion = GETDATE() -- Si tienes esta columna
            WHERE DeploymentId = ?
              AND (
                    Estado <> ? OR -- Si el estado cambió
                    (Estado NOT IN ('COMPLETED', 'RUN_COMPLETED', 'RUN_FAILED', 'RUN_ABORTED', 'DEPLOY_FAILED', 'UNKNOWN') AND CallbackInfo IS NULL)
                  );
            """
            # Si no tienes FechaActualizacion, quítala.
            # El tercer placeholder para FechaFin es el mismo que el segundo.
            formatted_params_for_update = [(p[0], p[1], p[1], p[2], p[3]) for p in updates_params]

            try:
                # Usar ejecutar_consulta con es_select=False o un método específico para DML si lo tienes.
                # El método merge_... usa un bucle con ejecutar_consulta. Podemos replicar eso o
                # crear un ejecutar_many si es más eficiente y pyodbc lo maneja bien para UPDATEs.
                # Por simplicidad y consistencia con los MERGE, un bucle:
                affected_count = 0
                for param_tuple in formatted_params_for_update:
                    # ejecutar_consulta devuelve rowcount para DML
                    count = self.db_connector.ejecutar_consulta(query_update, param_tuple, es_select=False)
                    if count is not None and count > 0:
                        affected_count += count
                logger.info(f"Conciliador: Actualizados {affected_count} registros de ejecuciones desde API.")
            except Exception as e_db_update:
                 logger.error(f"Conciliador: Error de BD al actualizar estados encontrados: {e_db_update}", exc_info=True)


    def actualizar_estados_perdidos_db(self, deployment_ids_en_db: list, detalles_api: list):
        """Marca como UNKNOWN los deployments que estaban en BD pero no se encontraron en la API."""
        if not deployment_ids_en_db:
            return

        ids_encontrados_api = {item.get("deploymentId") for item in detalles_api if item.get("deploymentId")}
        ids_perdidos_en_api = [dep_id for dep_id in deployment_ids_en_db if dep_id not in ids_encontrados_api]

        if ids_perdidos_en_api:
            logger.warning(f"Conciliador: DeploymentIds en BD pero no encontrados en la consulta API reciente (posiblemente finalizados o error): {ids_perdidos_en_api}")
            
            # Query ajustada para tu tabla Ejecuciones
            query_unknown = """
            UPDATE dbo.Ejecuciones 
            SET 
                Estado = 'UNKNOWN', 
                FechaFin = GETDATE(), 
                FechaActualizacion = GETDATE() -- Si tienes esta columna
            WHERE DeploymentId = ?
              AND Estado NOT IN ('COMPLETED','RUN_COMPLETED','RUN_FAILED','RUN_ABORTED','DEPLOY_FAILED', 'UNKNOWN')
              AND CallbackInfo IS NULL 
              AND DATEDIFF(SECOND, FechaInicio, GETDATE()) > 60 -- Umbral más largo para marcar como UNKNOWN
            """ 
            # Si no tienes FechaActualizacion, quítala.
            
            params_perdidos = [(id_perdido,) for id_perdido in ids_perdidos_en_api]
            
            affected_count = 0
            try:
                for param_tuple in params_perdidos:
                    count = self.db_connector.ejecutar_consulta(query_unknown, param_tuple, es_select=False)
                    if count is not None and count > 0:
                        affected_count += count
                if affected_count > 0:
                    logger.info(f"Conciliador: Marcados {affected_count} deployments perdidos como UNKNOWN.")
            except Exception as e_db_unknown:
                logger.error(f"Conciliador: Error de BD al actualizar estados perdidos: {e_db_unknown}", exc_info=True)


