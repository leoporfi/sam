# sam/lanzador/service/conciliador.py
import logging
from datetime import datetime
from typing import Optional

import pytz
from dateutil import parser as dateutil_parser

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.database import DatabaseConnector

logger = logging.getLogger(__name__)


class Conciliador:
    """
    Componente 'cerebro' responsable de la lógica de conciliación de estados
    de ejecuciones entre SAM y Automation Anywhere.
    """

    ESTADO_INFERIDO = "COMPLETED_INFERRED"

    def __init__(self, db_connector: DatabaseConnector, aa_client: AutomationAnywhereClient, config: dict):
        """
        Inicializa el Conciliador con sus dependencias.

        Args:
            db_connector: Conector a la base de datos de SAM.
            aa_client: Cliente para la API de Automation Anywhere.
            max_intentos_fallidos: Parámetro legacy (no usado, mantener por compatibilidad).
        """
        self._db_connector = db_connector
        self._aa_client = aa_client
        self._config = config
        self.ESTADOS_VALIDOS_API = {
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

    async def conciliar_ejecuciones(self):
        """
        Orquesta un ciclo completo de conciliación de ejecuciones.
        """
        logger.debug("Iniciando conciliación de ejecuciones en curso...")
        try:
            ejecuciones_en_curso = self._db_connector.obtener_ejecuciones_en_curso()
            if not ejecuciones_en_curso:
                logger.info("No hay ejecuciones activas para conciliar.")
                return

            mapa_deploy_a_ejecucion = {
                imp["DeploymentId"]: imp["EjecucionId"]
                for imp in ejecuciones_en_curso
                if imp.get("DeploymentId") and imp.get("EjecucionId")
            }
            deployment_ids = list(mapa_deploy_a_ejecucion.keys())

            if not deployment_ids:
                logger.info("No se encontraron DeploymentIds válidos en las ejecuciones activas.")
                return

            # Estrategia Única (Híbrida: Global + Verificación)
            # Combina eficiencia (vista global) con precisión (consulta puntual para desaparecidos)
            await self._conciliar_hibrido(ejecuciones_en_curso)

            self._marcar_unknown_por_antiguedad()

        except Exception as e:
            logger.error(f"Error grave durante el ciclo de conciliación: {e}", exc_info=True)

    async def _conciliar_hibrido(self, ejecuciones_en_curso: list):
        """
        Estrategia de Conciliación Híbrida (Estándar):
        1. Obtiene TODAS las ejecuciones activas de A360 (Vista Global).
        2. Actualiza las locales que coinciden (RUNNING, QUEUED, etc.).
        3. Para las que NO están en la lista activa (desaparecieron):
           a. Consulta específicamente por sus ID para obtener estado final real y fechas (COMPLETED, FAILED, etc.).
           b. Si A360 devuelve datos, actualiza con el estado real.
           c. Si A360 NO devuelve datos (purged/perdido), infiere finalización.
        """
        logger.info("Iniciando conciliación (Estrategia Híbrida)...")

        try:
            # 1. Obtener lista global de activos
            activas_api = await self._aa_client.obtener_ejecuciones_activas()
        except Exception as e:
            logger.error(f"Fallo al obtener ejecuciones activas: {e}")
            return

        # Mapa para búsqueda rápida: deploymentId -> data
        ids_activos_api = {item.get("deploymentId") for item in activas_api if item.get("deploymentId")}

        # 2. Identificar cuáles de las locales siguen activas y cuáles desaparecieron
        mapa_deploy_a_ejecucion = {
            imp["DeploymentId"]: imp["EjecucionId"]
            for imp in ejecuciones_en_curso
            if imp.get("DeploymentId") and imp.get("EjecucionId")
        }
        mapa_deploy_a_data = {imp["DeploymentId"]: imp for imp in ejecuciones_en_curso if imp.get("DeploymentId")}

        # A) Las que siguen activas: Actualizamos sus estados (RUNNING, etc.) usando la info de la API
        detalles_relevantes = [item for item in activas_api if item.get("deploymentId") in mapa_deploy_a_ejecucion]

        if detalles_relevantes:
            logger.debug(f"Actualizando {len(detalles_relevantes)} ejecuciones que siguen activas...")
            self._actualizar_estados_encontrados(detalles_relevantes, mapa_deploy_a_ejecucion)

        # B) Las que desaparecieron de la lista de activos
        ids_locales = set(mapa_deploy_a_ejecucion.keys())
        ids_desaparecidos = ids_locales - ids_activos_api

        if ids_desaparecidos:
            logger.info(
                f"Se detectaron {len(ids_desaparecidos)} ejecuciones que ya no están en la lista de activos. "
                "Consultando estado final real..."
            )

            # 3. Consultar específicamente por estos IDs para obtener su estado final real (COMPLETED, FAILED, etc.)
            try:
                detalles_finales = await self._aa_client.obtener_detalles_por_deployment_ids(list(ids_desaparecidos))

                # Actualizar con lo que encontremos (Estado Real)
                if detalles_finales:
                    self._actualizar_estados_encontrados(detalles_finales, mapa_deploy_a_ejecucion)

                # Identificar cuáles NO devolvieron nada (realmente perdidos/purged)
                ids_encontrados_finales = {
                    item.get("deploymentId") for item in detalles_finales if item.get("deploymentId")
                }
                ids_definitivamente_perdidos = ids_desaparecidos - ids_encontrados_finales

                # 4. Inferir finalización (con tolerancia de intentos)
                if ids_definitivamente_perdidos:
                    max_intentos = int(self._config.get("conciliador_max_intentos_inferencia", 5))

                    ids_para_inferir = set()
                    ids_para_incrementar = set()

                    for dep_id in ids_definitivamente_perdidos:
                        data = mapa_deploy_a_data.get(dep_id)
                        if not data:
                            continue

                        intentos_actuales = data.get("IntentosConciliadorFallidos") or 0

                        if intentos_actuales + 1 >= max_intentos:
                            ids_para_inferir.add(dep_id)
                        else:
                            ids_para_incrementar.add(dep_id)

                    if ids_para_inferir:
                        logger.info(
                            f"Inferiendo finalización para {len(ids_para_inferir)} ejecuciones "
                            f"(Superaron {max_intentos} intentos fallidos)."
                        )
                        self._marcar_como_inferidas(ids_para_inferir, mapa_deploy_a_ejecucion)

                    if ids_para_incrementar:
                        logger.info(
                            f"Incrementando contador de intentos fallidos para {len(ids_para_incrementar)} ejecuciones "
                            f"(Aún no superan el límite de {max_intentos})."
                        )
                        self._incrementar_intentos_fallidos(ids_para_incrementar, mapa_deploy_a_ejecucion)

            except Exception as e:
                logger.error(f"Error al consultar detalles finales de ejecuciones desaparecidas: {e}")
                # En caso de error en esta segunda fase, podríamos optar por no inferir nada
                # para evitar falsos positivos si la API falló momentáneamente.

    def _marcar_como_inferidas(self, ids_desaparecidos: set, mapa_deploy_a_ejecucion: dict):
        """Marca las ejecuciones desaparecidas con el estado inferido."""
        estado_inferido = self.ESTADO_INFERIDO
        mensaje_inferido = self._config.get(
            "conciliador_mensaje_inferido", "Finalizado (Inferido por ausencia en lista de activos)"
        )

        updates_inferidos = []
        for dep_id in ids_desaparecidos:
            ejecucion_id = mapa_deploy_a_ejecucion.get(dep_id)
            if ejecucion_id:
                updates_inferidos.append((estado_inferido, mensaje_inferido, ejecucion_id))

        if updates_inferidos:
            query = """
                UPDATE dbo.Ejecuciones
                SET Estado = ?,
                    FechaFin = GETDATE(),
                    FechaInicioReal = COALESCE(FechaInicioReal, GETDATE()),
                    FechaActualizacion = GETDATE(),
                    CallbackInfo = ?,
                    IntentosConciliadorFallidos = 0
                WHERE EjecucionId = ? AND CallbackInfo IS NULL;
            """
            count = self._db_connector.ejecutar_consulta_multiple(query, updates_inferidos, usar_fast_executemany=False)
            logger.info(f"Se actualizaron {count} ejecuciones a estado '{estado_inferido}'.")

    def _actualizar_estados_encontrados(self, detalles_api: list, mapa_deploy_a_ejecucion: dict):
        """Actualiza la BD con los estados de los deployments encontrados en la API."""
        if not detalles_api:
            return

        updates_params = []
        updates_unknown_params = []

        for detalle in detalles_api:
            dep_id = detalle.get("deploymentId")
            status_api = detalle.get("status")
            end_date_str = detalle.get("endDateTime")
            start_date_str = detalle.get("startDateTime")
            ejecucion_id = mapa_deploy_a_ejecucion.get(dep_id)

            if not all([dep_id, status_api, ejecucion_id]):
                continue

            # CAMBIO: UNKNOWN ya no se trata como estado final
            if status_api == "UNKNOWN":
                logger.warning(
                    f"Deployment {dep_id} (EjecucionId {ejecucion_id}) reportó 'UNKNOWN' desde A360. "
                    f"Se marcará como transitorio y se reintentará en próximos ciclos."
                )
                # Actualizar a UNKNOWN pero SIN FechaFin (no es final)
                # Registrar timestamp para control
                updates_unknown_params.append((ejecucion_id,))
                continue

            # Estados válidos finales
            final_status_db = "RUNNING" if status_api == "UPDATE" else status_api
            if final_status_db not in self.ESTADOS_VALIDOS_API:
                continue

            fecha_fin_dt = self._convertir_utc_a_local_sam(end_date_str)
            fecha_inicio_api_dt = self._convertir_utc_a_local_sam(start_date_str)

            # Lógica para FechaInicioReal:
            # 1. Si la API da una fecha, usamos esa.
            # 2. Si no da fecha pero el estado es de ejecución (RUNNING, etc), usamos GETDATE() como fallback.
            # 3. Si está en cola (QUEUED, PENDING), no forzamos GETDATE().
            if fecha_inicio_api_dt:
                fecha_inicio_final = fecha_inicio_api_dt
            elif final_status_db in ["RUNNING", "COMPLETED", "RUN_COMPLETED", "RUN_FAILED", "RUN_ABORTED"]:
                # Estado implica que empezó o terminó, si no hay fecha en API, usamos la actual como fallback
                fecha_inicio_final = datetime.now()
            else:
                # Sigue en cola o pendiente, mantenemos lo que haya en DB (NULL probablemente)
                fecha_inicio_final = None

            updates_params.append((final_status_db, fecha_fin_dt, fecha_inicio_final, ejecucion_id))

        # Actualizar estados (Tanto finales como en curso)
        if updates_params:
            query = """
                UPDATE dbo.Ejecuciones
                SET Estado = ?,
                    FechaFin = ?,
                    FechaInicioReal = COALESCE(?, FechaInicioReal),
                    FechaActualizacion = GETDATE(),
                    IntentosConciliadorFallidos = 0
                WHERE EjecucionId = ? AND CallbackInfo IS NULL;
            """
            affected_count = self._db_connector.ejecutar_consulta_multiple(
                query, updates_params, usar_fast_executemany=False
            )
            logger.debug(f"Se actualizaron {affected_count} registros (estados y fechas) desde la API.")

        # Actualizar los que reportaron UNKNOWN (sin marcar como final)
        if updates_unknown_params:
            query_unknown = """
                UPDATE dbo.Ejecuciones
                SET Estado = 'UNKNOWN',
                    FechaUltimoUNKNOWN = GETDATE(),
                    FechaActualizacion = GETDATE(),
                    IntentosConciliadorFallidos = IntentosConciliadorFallidos + 1
                WHERE EjecucionId = ? AND CallbackInfo IS NULL;
            """
            affected_unknown = self._db_connector.ejecutar_consulta_multiple(
                query_unknown, updates_unknown_params, usar_fast_executemany=False
            )
            logger.debug(
                f"Se marcaron {affected_unknown} registros como UNKNOWN (transitorio). "
                f"Se reintentarán en próximos ciclos."
            )

    def _marcar_unknown_por_antiguedad(self):
        """Marca como UNKNOWN ejecuciones que superan el umbral de días de tolerancia."""
        dias_tolerancia = self._config.get("dias_tolerancia_unknown", 30)

        query_select = """
            SELECT EjecucionId, DeploymentId, Hora
            FROM dbo.Ejecuciones
            WHERE Estado NOT IN ('COMPLETED', 'RUN_COMPLETED', 'RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED', 'UNKNOWN')
            AND CallbackInfo IS NULL
            AND DATEDIFF(DAY, FechaInicio, GETDATE()) > ?
        """

        ejecuciones_antiguas = self._db_connector.ejecutar_consulta(query_select, (dias_tolerancia,), es_select=True)

        if not ejecuciones_antiguas:
            return

        ids_a_actualizar = [reg["EjecucionId"] for reg in ejecuciones_antiguas]

        for reg in ejecuciones_antiguas:
            logger.warning(
                f"Deployment {reg['DeploymentId']} (EjecucionId {reg['EjecucionId']}) marcado como UNKNOWN "
                f"tras {dias_tolerancia} días sin respuesta de A360. Hora programada: {reg['Hora']}"
            )

        placeholders = ",".join("?" * len(ids_a_actualizar))
        query_update = f"""
            UPDATE dbo.Ejecuciones
            SET Estado = 'UNKNOWN',
                FechaFin = GETDATE(),
                FechaInicioReal = COALESCE(FechaInicioReal, GETDATE()),
                FechaActualizacion = GETDATE()
            WHERE EjecucionId IN ({placeholders});
        """
        self._db_connector.ejecutar_consulta(query_update, tuple(ids_a_actualizar), es_select=False)
        logger.debug(f"Se marcaron {len(ids_a_actualizar)} ejecuciones como UNKNOWN por antigüedad.")

    def _convertir_utc_a_local_sam(self, fecha_utc_str: Optional[str]) -> Optional[datetime]:
        """Convierte una fecha en formato ISO UTC a la zona horaria local de SAM."""
        if not fecha_utc_str or fecha_utc_str.startswith("1970"):
            return None
        try:
            dt_utc = dateutil_parser.isoparse(fecha_utc_str)
            tz_local_sam = pytz.timezone("America/Argentina/Buenos_Aires")
            return dt_utc.astimezone(tz_local_sam)
        except Exception as e:
            logger.error(f"Error al convertir fecha UTC '{fecha_utc_str}': {e}", exc_info=True)
            return None

    def _incrementar_intentos_fallidos(self, ids_para_incrementar: set, mapa_deploy_a_ejecucion: dict):
        """Incrementa el contador de intentos fallidos para las ejecuciones dadas."""
        updates = []
        for dep_id in ids_para_incrementar:
            ejecucion_id = mapa_deploy_a_ejecucion.get(dep_id)
            if ejecucion_id:
                updates.append((ejecucion_id,))

        if updates:
            query = """
                UPDATE dbo.Ejecuciones
                SET IntentosConciliadorFallidos = ISNULL(IntentosConciliadorFallidos, 0) + 1,
                    FechaActualizacion = GETDATE()
                WHERE EjecucionId = ?;
            """
            self._db_connector.ejecutar_consulta_multiple(query, updates, usar_fast_executemany=False)
