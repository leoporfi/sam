# sam/web/backend/api.py
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.apigw_client import ApiGatewayClient
from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector
from sam.web.backend import database as db_service
from sam.web.backend.dependencies import get_aa_client, get_apigw_client, get_db

logger = logging.getLogger(__name__)

router = APIRouter()


def _handle_endpoint_errors(endpoint_name: str, e: Exception, tag: str = "General"):
    """Manejador centralizado de errores para los endpoints."""
    error_msg = f"Error en endpoint {tag}/{endpoint_name}: {str(e)}"
    logger.error(error_msg, exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Ocurrió un error interno al procesar la solicitud.",
    )


# Task Wrappers para sincronización
async def run_robot_sync_task(db: DatabaseConnector, aa_client: AutomationAnywhereClient, app_state):
    """Wrapper para ejecutar y gestionar el estado de la tarea de sync de robots."""
    lock = app_state.sync_lock
    try:
        # Poner el estado en "running"
        async with lock:
            app_state.sync_status["robots"] = "running"

        # Ejecutar la tarea real
        await db_service.sync_robots_only(db, aa_client)

    except Exception as e:
        logger.error(f"Fallo en la tarea de fondo 'sync_robots_only': {e}", exc_info=True)
    finally:
        # Poner el estado de vuelta en "idle", incluso si falló
        async with lock:
            app_state.sync_status["robots"] = "idle"


async def run_equipo_sync_task(db: DatabaseConnector, aa_client: AutomationAnywhereClient, app_state):
    """Wrapper para ejecutar y gestionar el estado de la tarea de sync de equipos."""
    lock = app_state.sync_lock
    try:
        async with lock:
            app_state.sync_status["equipos"] = "running"
        await db_service.sync_equipos_only(db, aa_client)
    except Exception as e:
        logger.error(f"Fallo en la tarea de fondo 'sync_equipos_only': {e}", exc_info=True)
    finally:
        async with lock:
            app_state.sync_status["equipos"] = "idle"


# ------------------------------------------------------------------
# Sync routes
# ------------------------------------------------------------------
@router.post("/api/sync/robots", tags=["Sincronización"], status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync_robots(
    request: Request,
    background_tasks: BackgroundTasks,
    db: DatabaseConnector = Depends(get_db),
    aa_client: AutomationAnywhereClient = Depends(get_aa_client),
):
    """Inicia la sincronización de robots en segundo plano."""
    app_state = request.app.state  # Accedemos al estado de la app

    async with app_state.sync_lock:
        # Comprobar si ya hay una tarea corriendo
        if app_state.sync_status["robots"] == "running":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Ya hay una sincronización de robots en curso."
            )

        # Usamos el wrapper, no la tarea directa
        background_tasks.add_task(run_robot_sync_task, db, aa_client, app_state)

    return {"message": "Sincronización de robots iniciada."}


@router.post("/api/sync/equipos", tags=["Sincronización"], status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync_equipos(
    request: Request,
    background_tasks: BackgroundTasks,
    db: DatabaseConnector = Depends(get_db),
    aa_client: AutomationAnywhereClient = Depends(get_aa_client),
):
    """Inicia la sincronización de equipos en segundo plano."""
    app_state = request.app.state
    async with app_state.sync_lock:
        if app_state.sync_status["equipos"] == "running":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Ya hay una sincronización de equipos en curso."
            )

        # Usamos el wrapper de equipos
        background_tasks.add_task(run_equipo_sync_task, db, aa_client, app_state)

    return {"message": "Sincronización de equipos iniciada."}


@router.get("/api/sync/status", tags=["Sincronización"])
async def get_sync_status(request: Request):
    """Obtiene el estado actual de las tareas de sincronización."""
    # Simplemente devuelve el diccionario de estado
    return request.app.state.sync_status


@router.get("/api/robots", tags=["Robots"])
def get_robots(
    active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
    sort_by: str = Query("Robot"),
    sort_dir: str = Query("asc"),
    db: DatabaseConnector = Depends(get_db),
):
    """Obtiene el listado de robots."""
    try:
        return db_service.get_robots(db=db, active=active, page=page, size=size, sort_by=sort_by, sort_dir=sort_dir)
    except Exception as e:
        _handle_endpoint_errors("get_robots", e, "Robots")


@router.get("/api/equipos", tags=["Equipos"])
def get_equipos(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
    sort_by: str = Query("Equipo"),
    sort_dir: str = Query("asc"),
    db: DatabaseConnector = Depends(get_db),
):
    """Obtiene el listado de equipos."""
    try:
        return db_service.get_devices(db=db, page=page, size=size, sort_by=sort_by, sort_dir=sort_dir)
    except Exception as e:
        _handle_endpoint_errors("get_equipos", e, "Equipos")


@router.get("/api/analytics/status", tags=["Analytics"])
def get_system_status(db: DatabaseConnector = Depends(get_db)):
    """Obtiene un resumen del estado del sistema."""
    try:
        status_data = db_service.get_system_status(db)
        return status_data
    except Exception as e:
        logger.error(f"Error obteniendo estado del sistema: {e}", exc_info=True)
        _handle_endpoint_errors("get_system_status", e, "Analytics")


@router.get("/api/analytics/callbacks", tags=["Analytics"])
def get_callbacks_dashboard(
    fecha_inicio: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DDTHH:mm:ss)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DDTHH:mm:ss)"),
    robot_id: Optional[int] = Query(None, description="ID del robot para filtrar"),
    incluir_detalle_horario: bool = Query(True, description="Incluir análisis por hora"),
    db: DatabaseConnector = Depends(get_db),
):
    """
    Obtiene el dashboard de análisis de callbacks.
    """
    try:
        from datetime import datetime

        # Parsear fechas si se proporcionan
        fecha_inicio_dt = None
        fecha_fin_dt = None
        if fecha_inicio:
            try:
                fecha_inicio_dt = datetime.fromisoformat(fecha_inicio.replace("Z", "+00:00"))
            except ValueError:
                # Intentar formato alternativo
                fecha_inicio_dt = datetime.fromisoformat(fecha_inicio)
        if fecha_fin:
            try:
                fecha_fin_dt = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))
            except ValueError:
                fecha_fin_dt = datetime.fromisoformat(fecha_fin)

        return db_service.get_callbacks_dashboard(
            db=db,
            fecha_inicio=fecha_inicio_dt,
            fecha_fin=fecha_fin_dt,
            robot_id=robot_id,
            incluir_detalle_horario=incluir_detalle_horario,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Formato de fecha inválido: {ve}")
    except Exception as e:
        logger.error(f"Error obteniendo dashboard de callbacks: {e}", exc_info=True)
        _handle_endpoint_errors("get_callbacks_dashboard", e, "Analytics")


@router.get("/api/analytics/balanceador", tags=["Analytics"])
def get_balanceador_dashboard(
    fecha_inicio: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DDTHH:mm:ss)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DDTHH:mm:ss)"),
    pool_id: Optional[int] = Query(None, description="ID del pool para filtrar"),
    db: DatabaseConnector = Depends(get_db),
):
    """
    Obtiene el dashboard de análisis del balanceador.
    """
    try:
        from datetime import datetime

        fecha_inicio_dt = datetime.fromisoformat(fecha_inicio) if fecha_inicio else None
        fecha_fin_dt = datetime.fromisoformat(fecha_fin) if fecha_fin else None

        return db_service.get_balanceador_dashboard(
            db=db,
            fecha_inicio=fecha_inicio_dt,
            fecha_fin=fecha_fin_dt,
            pool_id=pool_id,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Formato de fecha inválido: {ve}")
    except Exception as e:
        logger.error(f"Error obteniendo dashboard de balanceador: {e}", exc_info=True)
        _handle_endpoint_errors("get_balanceador_dashboard", e, "Analytics")


@router.get("/api/analytics/tiempos-ejecucion", tags=["Analytics"])
def get_tiempos_ejecucion_dashboard(
    excluir_porcentaje_inferior: Optional[float] = Query(
        None, description="Percentil inferior a excluir (0.0-1.0, default: 0.15)"
    ),
    excluir_porcentaje_superior: Optional[float] = Query(
        None, description="Percentil superior a excluir (0.0-1.0, default: 0.85)"
    ),
    incluir_solo_completadas: bool = Query(True, description="Solo ejecuciones completadas"),
    meses_hacia_atras: Optional[int] = Query(None, description="Meses hacia atrás para el análisis (default: 1)"),
    db: DatabaseConnector = Depends(get_db),
):
    """
    Obtiene el dashboard de análisis de tiempos de ejecución por robot.

    Considera:
    - FechaInicioReal (inicio real reportado por A360) cuando está disponible
    - Número de repeticiones del robot (extraído de Parametros JSON)
    - Datos históricos (Ejecuciones_Historico)
    - Calcula tiempo por repetición (tiempo total / número de repeticiones)
    - Calcula latencia (delay entre disparo e inicio real)
    """
    try:
        # Validar percentiles si se proporcionan
        if excluir_porcentaje_inferior is not None and (
            excluir_porcentaje_inferior < 0 or excluir_porcentaje_inferior >= 1
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="excluir_porcentaje_inferior debe estar entre 0.0 y 1.0",
            )
        if excluir_porcentaje_superior is not None and (
            excluir_porcentaje_superior <= 0 or excluir_porcentaje_superior > 1
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="excluir_porcentaje_superior debe estar entre 0.0 y 1.0",
            )
        if (
            excluir_porcentaje_inferior is not None
            and excluir_porcentaje_superior is not None
            and excluir_porcentaje_inferior >= excluir_porcentaje_superior
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="excluir_porcentaje_inferior debe ser menor que excluir_porcentaje_superior",
            )

        return db_service.get_tiempos_ejecucion_dashboard(
            db=db,
            excluir_porcentaje_inferior=excluir_porcentaje_inferior,
            excluir_porcentaje_superior=excluir_porcentaje_superior,
            incluir_solo_completadas=incluir_solo_completadas,
            meses_hacia_atras=meses_hacia_atras,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo dashboard de tiempos de ejecución: {e}", exc_info=True)
        _handle_endpoint_errors("get_tiempos_ejecucion_dashboard", e, "Analytics")


@router.get("/api/analytics/executions", tags=["Analytics"])
def get_recent_executions(
    limit: int = Query(50, ge=1, le=200),
    critical_only: bool = Query(True),
    db: DatabaseConnector = Depends(get_db),
):
    """
    Obtiene un listado de ejecuciones recientes con detección inteligente de críticos.

    Incluye:
    - Fallos: RUN_FAILED, DEPLOY_FAILED, RUN_ABORTED
    - Demoradas: RUNNING/DEPLOYED que exceden umbral dinámico o fijo
    - Huérfanas: QUEUED sin DEPLOYED/RUNNING correspondiente
    """
    try:
        # Leer configuraciones del sistema
        umbral_fijo = db_service.get_system_config(db, "UMBRAL_EJECUCION_DEMORADA_MINUTOS")
        factor_dinamico = db_service.get_system_config(db, "FACTOR_UMBRAL_DINAMICO")

        # Valores por defecto si no existen en la configuración
        umbral_fijo_minutos = int(umbral_fijo) if umbral_fijo else 25
        factor_umbral_dinamico = float(factor_dinamico) if factor_dinamico else 1.5

        return db_service.get_recent_executions(
            db,
            limit=limit,
            critical_only=critical_only,
            umbral_fijo_minutos=umbral_fijo_minutos,
            factor_umbral_dinamico=factor_umbral_dinamico,
        )
    except Exception as e:
        logger.error(f"Error obteniendo ejecuciones recientes: {e}", exc_info=True)
        _handle_endpoint_errors("get_recent_executions", e, "Analytics")


@router.post("/api/executions/{deployment_id}/unlock", tags=["Analytics"])
async def unlock_execution(
    deployment_id: str,
    db: DatabaseConnector = Depends(get_db),
    aa_client: AutomationAnywhereClient = Depends(get_aa_client),
    apigw_client: ApiGatewayClient = Depends(get_apigw_client),
):
    """
    Orquesta el proceso de destrabar una ejecución 'trabada'.
    Flujo:
    1. Obtener ID interno de A360.
    2. Intentar detener en A360 (/v3/activity/manage) usando ID interno.
    3. Si falla, resetear device en A360 (/v2/devices/reset) y mover a histórico (/v1/activity/auditunknown).
    4. Notificar vía callback local (apiinternos) para sincronizar estado.
    """
    logger.info(f"[UNLOCK] Iniciando proceso para deployment: {deployment_id}")

    # 1. Obtener información de la ejecución desde la BD local
    info = db_service.obtener_info_ejecucion(db, deployment_id)
    if not info:
        logger.warning(f"[UNLOCK] No se encontró la ejecución {deployment_id} en la base de datos.")
        raise HTTPException(status_code=404, detail=f"No se encontró la ejecución {deployment_id}")

    device_id = info.get("EquipoId")
    user_id = info.get("UserId")
    actions_taken = []

    # 2. Obtener el ID interno de A360 primero
    internal_id = None
    try:
        detalles = await aa_client.obtener_detalles_por_deployment_ids([deployment_id])
        if detalles:
            internal_id = detalles[0].get("id")
            logger.info(f"[UNLOCK] ID interno de A360 encontrado: {internal_id}")
    except Exception as e:
        logger.warning(f"[UNLOCK] No se pudo obtener el ID interno de A360: {e}")

    # 3. Intentar detener el deployment en A360
    success_stop = False
    try:
        # Usamos el internal_id si lo tenemos, sino el deployment_id como fallback
        id_to_stop = internal_id if internal_id else deployment_id
        success_stop = await aa_client.detener_deployment(id_to_stop)
        if success_stop:
            actions_taken.append("A360_STOP_SUCCESS")
        else:
            actions_taken.append("A360_STOP_FAILED")

            # 4. Si falla el stop, intentar reset del device y mover a histórico
            if device_id:
                logger.info(f"[UNLOCK] Intentando reset de device {device_id}...")
                try:
                    await aa_client.reset_device(str(device_id))
                    actions_taken.append("A360_DEVICE_RESET_SUCCESS")
                except Exception as e:
                    logger.error(f"[UNLOCK] Error al resetear device {device_id}: {e}")
                    actions_taken.append(f"A360_DEVICE_RESET_ERROR: {str(e)[:50]}")

            # 5. Mover a histórico en A360 (auditunknown) solo si el stop falló
            try:
                success_historic = await aa_client.mover_a_historico_a360(deployment_id)
                if success_historic:
                    actions_taken.append("A360_HISTORIC_MOVE_SUCCESS")
                else:
                    actions_taken.append("A360_HISTORIC_MOVE_FAILED")
            except Exception as e:
                logger.error(f"[UNLOCK] Error al mover a histórico en A360: {e}")
                actions_taken.append(f"A360_HISTORIC_ERROR: {str(e)[:50]}")

    except Exception as e:
        logger.error(f"[UNLOCK] Error durante acciones de detención en A360: {e}")
        actions_taken.append(f"A360_ACTION_ERROR: {str(e)[:50]}")

    # 6. Notificar al callback local (él debería encargarse de actualizar la BD)
    success_callback = False
    try:
        callback_url = ConfigManager.get_aa360_web_config().get("callback_url_deploy")
        if callback_url:
            # Reemplazar dominio público por interno para evitar problemas de ruteo/firewall
            callback_url = callback_url.replace("api.movistar.com.ar", "apiinternos.movistar.com.ar")

            payload = {
                "deploymentId": deployment_id,
                "status": "RUN_ABORTED",
                "deviceId": str(device_id) if device_id else None,
                "userId": str(user_id) if user_id else None,
                "botOutput": {"message": "Destrabado manualmente"},
            }
            success_callback = await apigw_client.notificar_callback(callback_url, payload)
            if success_callback:
                actions_taken.append("LOCAL_CALLBACK_NOTIFIED")
            else:
                actions_taken.append("LOCAL_CALLBACK_FAILED")
    except Exception as e:
        logger.error(f"[UNLOCK] Error al notificar callback: {e}")
        actions_taken.append(f"CALLBACK_ERROR: {str(e)[:50]}")

    # 7. Fallback: Si el callback falló, actualizamos la BD local directamente
    if not success_callback:
        logger.warning(f"[UNLOCK] Callback falló para {deployment_id}. Forzando actualización manual en BD.")
        try:
            db_service.mover_ejecucion_a_historico(
                db, deployment_id, "RUN_ABORTED", "Destrabado manualmente (Fallback)"
            )
            actions_taken.append("LOCAL_DB_UPDATED_FALLBACK")
        except Exception as e:
            logger.error(f"[UNLOCK] Error en fallback de BD para {deployment_id}: {e}")
            actions_taken.append(f"LOCAL_DB_ERROR: {str(e)[:50]}")
    else:
        actions_taken.append("LOCAL_DB_UPDATE_SKIPPED_BY_CALLBACK")

    return {
        "success": True,
        "deployment_id": deployment_id,
        "actions": actions_taken,
        "message": "Proceso de destrabado completado. El estado debería actualizarse en breve.",
    }


@router.get("/api/analytics/utilizacion", tags=["Analytics"])
def get_utilization_analysis(
    fecha_inicio: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DDTHH:mm:ss)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DDTHH:mm:ss)"),
    dias_hacia_atras: Optional[int] = Query(30, description="Días hacia atrás si no se especifican fechas"),
    db: DatabaseConnector = Depends(get_db),
):
    """
    Obtiene el análisis de utilización de recursos.
    """
    try:
        from datetime import datetime, timedelta

        fecha_inicio_dt = None
        fecha_fin_dt = None

        if fecha_inicio:
            try:
                fecha_inicio_dt = datetime.fromisoformat(fecha_inicio.replace("Z", "+00:00"))
            except ValueError:
                fecha_inicio_dt = datetime.fromisoformat(fecha_inicio)

        if fecha_fin:
            try:
                fecha_fin_dt = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))
            except ValueError:
                fecha_fin_dt = datetime.fromisoformat(fecha_fin)

        # Si no hay fechas, usar dias_hacia_atras
        if not fecha_inicio_dt and not fecha_fin_dt and dias_hacia_atras:
            fecha_fin_dt = datetime.now()
            fecha_inicio_dt = fecha_fin_dt - timedelta(days=dias_hacia_atras)

        return db_service.get_utilization_analysis(
            db=db,
            fecha_inicio=fecha_inicio_dt,
            fecha_fin=fecha_fin_dt,
        )
    except Exception as e:
        logger.error(f"Error obteniendo análisis de utilización: {e}", exc_info=True)
        _handle_endpoint_errors("get_utilization_analysis", e, "Analytics")


@router.get("/api/analytics/patrones-temporales", tags=["Analytics"])
def get_temporal_patterns(
    fecha_inicio: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DDTHH:mm:ss)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DDTHH:mm:ss)"),
    robot_id: Optional[int] = Query(None, description="ID del robot para filtrar"),
    db: DatabaseConnector = Depends(get_db),
):
    """
    Obtiene el análisis de patrones temporales (heatmap).
    """
    try:
        from datetime import datetime

        fecha_inicio_dt = None
        fecha_fin_dt = None

        if fecha_inicio:
            try:
                fecha_inicio_dt = datetime.fromisoformat(fecha_inicio.replace("Z", "+00:00"))
            except ValueError:
                fecha_inicio_dt = datetime.fromisoformat(fecha_inicio)

        if fecha_fin:
            try:
                fecha_fin_dt = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))
            except ValueError:
                fecha_fin_dt = datetime.fromisoformat(fecha_fin)

        return db_service.get_temporal_patterns(
            db=db,
            fecha_inicio=fecha_inicio_dt,
            fecha_fin=fecha_fin_dt,
            robot_id=robot_id,
        )
    except Exception as e:
        logger.error(f"Error obteniendo patrones temporales: {e}", exc_info=True)
        _handle_endpoint_errors("get_temporal_patterns", e, "Analytics")


@router.get("/api/analytics/tasas-exito", tags=["Analytics"])
def get_success_analysis(
    fecha_inicio: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DDTHH:mm:ss)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DDTHH:mm:ss)"),
    robot_id: Optional[int] = Query(None, description="ID del robot para filtrar"),
    db: DatabaseConnector = Depends(get_db),
):
    """
    Obtiene el análisis de tasas de éxito y errores.
    """
    try:
        from datetime import datetime

        fecha_inicio_dt = None
        fecha_fin_dt = None

        if fecha_inicio:
            try:
                fecha_inicio_dt = datetime.fromisoformat(fecha_inicio.replace("Z", "+00:00"))
            except ValueError:
                fecha_inicio_dt = datetime.fromisoformat(fecha_inicio)

        if fecha_fin:
            try:
                fecha_fin_dt = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))
            except ValueError:
                fecha_fin_dt = datetime.fromisoformat(fecha_fin)

        return db_service.get_success_analysis(
            db=db,
            fecha_inicio=fecha_inicio_dt,
            fecha_fin=fecha_fin_dt,
            robot_id=robot_id,
        )
    except Exception as e:
        logger.error(f"Error obteniendo tasas de éxito: {e}", exc_info=True)
        _handle_endpoint_errors("get_success_analysis", e, "Analytics")
