# sam/web/backend/api.py

import logging
from typing import Dict, List, Optional

import pyodbc
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, Request, status

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.apigw_client import ApiGatewayClient
from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector
from sam.web.backend import database as db_service
from sam.web.backend.dependencies import get_aa_client, get_apigw_client, get_db
from sam.web.backend.schemas import (
    AssignmentUpdateRequest,
    EquipoCreateRequest,
    EquipoStatusUpdate,
    MapeoRobotCreate,
    MapeoRobotResponse,
    PoolAssignmentsRequest,
    PoolCreate,
    PoolUpdate,
    RobotCreateRequest,
    RobotUpdateRequest,
    ScheduleData,
    ScheduleEditData,
)

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
def get_robots_with_assignments(
    db: DatabaseConnector = Depends(get_db),
    name: Optional[str] = None,
    active: Optional[bool] = None,
    online: Optional[bool] = None,
    programado: Optional[bool] = None,
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    sort_by: Optional[str] = Query("Robot"),
    sort_dir: Optional[str] = Query("asc"),
):
    try:
        return db_service.get_robots(
            db=db,
            name=name,
            active=active,
            online=online,
            programado=programado,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except Exception as e:
        _handle_endpoint_errors("get_robots_with_assignments", e, "Robots")


@router.get("/api/equipos", tags=["Equipos"])
def get_all_equipos(
    db: DatabaseConnector = Depends(get_db),
    name: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    balanceable: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=100),
    sort_by: Optional[str] = Query("Equipo"),
    sort_dir: Optional[str] = Query("asc"),
):
    try:
        return db_service.get_devices(
            db=db,
            name=name,
            active=active,
            balanceable=balanceable,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except Exception as e:
        _handle_endpoint_errors("get_all_equipos", e, "Equipos")


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
    limit: int = Query(50, ge=1, le=500),
    critical_only: bool = Query(True),
    robot_name: Optional[str] = Query(None, description="Filtrar por nombre de robot"),
    equipo_name: Optional[str] = Query(None, description="Filtrar por nombre de equipo"),
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
        piso_dinamico = db_service.get_system_config(db, "PISO_UMBRAL_DINAMICO_MINUTOS")
        filtro_cortas = db_service.get_system_config(db, "FILTRO_EJECUCIONES_CORTAS_MINUTOS")

        # Valores por defecto si no existen en la configuración
        umbral_fijo_minutos = int(umbral_fijo) if umbral_fijo else 25
        factor_umbral_dinamico = float(factor_dinamico) if factor_dinamico else 1.5
        piso_umbral_dinamico_minutos = int(piso_dinamico) if piso_dinamico else 10
        filtro_ejecuciones_cortas_minutos = int(filtro_cortas) if filtro_cortas else 2

        return db_service.get_recent_executions(
            db,
            limit=limit,
            critical_only=critical_only,
            umbral_fijo_minutos=umbral_fijo_minutos,
            factor_umbral_dinamico=factor_umbral_dinamico,
            piso_umbral_dinamico_minutos=piso_umbral_dinamico_minutos,
            filtro_ejecuciones_cortas_minutos=filtro_ejecuciones_cortas_minutos,
            robot_name=robot_name,
            equipo_name=equipo_name,
        )
    except Exception as e:
        logger.error(f"Error obteniendo ejecuciones recientes: {e}", exc_info=True)
        _handle_endpoint_errors("get_recent_executions", e, "Analytics")


@router.post("/api/executions/{deployment_id}/unlock", tags=["Analytics"])
async def unlock_execution(
    deployment_id: str,
    db: DatabaseConnector = Depends(get_db),
    apigw_client: ApiGatewayClient = Depends(get_apigw_client),
):
    """
    Orquesta el proceso de destrabar una ejecución 'trabada'.
    Flujo Simplificado (Solicitud Usuario):
    1. Obtener información de la ejecución.
    2. Notificar vía callback local (apiinternos) con estado final (RUN_ABORTED) para que actualice la BD.
    3. Fallback: Si falla el callback, actualizar la BD local directamente.

    NOTA: Ya no se intenta detener en A360 porque no se dispone del ID interno necesario.
    El usuario debe verificar manualmente en A360 que la ejecución esté detenida.
    """
    logger.info(f"[UNLOCK] Iniciando proceso de destrabado manual para deployment: {deployment_id}")

    # 1. Obtener información de la ejecución desde la BD local
    info = db_service.obtener_info_ejecucion(db, deployment_id)
    if not info:
        logger.warning(f"[UNLOCK] No se encontró la ejecución {deployment_id} en la base de datos.")
        raise HTTPException(status_code=404, detail=f"No se encontró la ejecución {deployment_id}")

    device_id = info.get("EquipoId")
    user_id = info.get("UserId")
    actions_taken = []

    # 2. Notificar al callback local (él debería encargarse de actualizar la BD)
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
                "botOutput": {"message": "Destrabado manualmente por usuario web"},
            }
            success_callback = await apigw_client.notificar_callback(callback_url, payload)
            if success_callback:
                actions_taken.append("LOCAL_CALLBACK_NOTIFIED")
                logger.info(f"[UNLOCK] Callback notificado exitosamente para {deployment_id}")
            else:
                actions_taken.append("LOCAL_CALLBACK_FAILED")
                logger.warning(f"[UNLOCK] Falló la notificación al callback para {deployment_id}")
    except Exception as e:
        logger.error(f"[UNLOCK] Error al notificar callback: {e}")
        actions_taken.append(f"CALLBACK_ERROR: {str(e)[:50]}")

    # 3. Fallback: Si el callback falló, actualizamos la BD local directamente
    if not success_callback:
        logger.warning(
            f"[UNLOCK] Callback falló o no configurado para {deployment_id}. Forzando actualización manual en BD."
        )
        try:
            db_service.mover_ejecucion_a_historico(
                db, deployment_id, "RUN_ABORTED", "Destrabado manualmente (Fallback Web)"
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
        "message": "Solicitud de destrabado enviada. El estado se actualizará en breve.",
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


# ------------------------------------------------------------------
# Robots - Endpoints adicionales
# ------------------------------------------------------------------
@router.patch("/api/robots/{robot_id}", tags=["Robots"])
def update_robot_status(robot_id: int, updates: Dict[str, bool] = Body(...), db: DatabaseConnector = Depends(get_db)):
    """Actualiza el estado de un robot"""
    field = next(iter(updates))
    if field not in {"Activo", "EsOnline"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campo no vÃ¡lido.")
    try:
        db_service.update_robot_status(db, robot_id, field, updates[field])
        return {"message": "Estado del robot actualizado."}
    except ValueError as ve:
        # Regla de negocio (robot programado, etc.)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))
    except pyodbc.Error as dbe:
        _handle_endpoint_errors("update_robot_status", dbe, "Robot", robot_id)
    except Exception as e:
        _handle_endpoint_errors("update_robot_status", e, "Robot", robot_id)


@router.put("/api/robots/{robot_id}", tags=["Robots"])
def update_robot_details(robot_id: int, robot_data: RobotUpdateRequest, db: DatabaseConnector = Depends(get_db)):
    try:
        updated = db_service.update_robot_details(db, robot_id, robot_data)
        if updated:
            return {"message": f"Robot {robot_id} actualizado."}
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Robot no encontrado.")
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        _handle_endpoint_errors("update_robot_details", e, "Robot", robot_id)


@router.post("/api/robots", tags=["Robots"], status_code=status.HTTP_201_CREATED)
def create_robot(robot_data: RobotCreateRequest, db: DatabaseConnector = Depends(get_db)):
    try:
        return db_service.create_robot(db, robot_data)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))
    except Exception as e:
        _handle_endpoint_errors("create_robot", e, "Robot")


# ------------------------------------------------------------------
# Programaciones (Schedules)
# ------------------------------------------------------------------
@router.get("/api/schedules/all", tags=["Programaciones"])
def get_all_schedules_legacy(db: DatabaseConnector = Depends(get_db)):
    try:
        return db_service.get_all_schedules(db)
    except Exception as e:
        _handle_endpoint_errors("get_all_schedules_legacy", e, "Programaciones")


@router.get("/api/schedules", tags=["Programaciones"], response_model=dict)
def get_schedules(
    db: DatabaseConnector = Depends(get_db),
    robot_id: Optional[int] = Query(None, alias="robot"),
    tipo: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    activo: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=300),
):
    """Listado paginado de programaciones con filtros."""
    try:
        return db_service.get_schedules_paginated(
            db, robot_id=robot_id, tipo=tipo, activo=activo, search=search, page=page, size=size
        )
    except Exception as e:
        _handle_endpoint_errors("get_schedules", e, "Programaciones")


@router.get("/api/schedules/robot/{robot_id}", tags=["Programaciones"])
def get_robot_schedules(robot_id: int, db: DatabaseConnector = Depends(get_db)):
    try:
        return db_service.get_robot_schedules(db, robot_id)
    except Exception as e:
        _handle_endpoint_errors("get_robot_schedules", e, "Programaciones", robot_id)


@router.delete(
    "/api/schedules/{programacion_id}/robot/{robot_id}", tags=["Programaciones"], status_code=status.HTTP_204_NO_CONTENT
)
def delete_schedule(programacion_id: int, robot_id: int, db: DatabaseConnector = Depends(get_db)):
    try:
        db_service.delete_schedule(db, programacion_id, robot_id)
    except Exception as e:
        _handle_endpoint_errors("delete_schedule", e, "ProgramaciÃ³n", programacion_id)


@router.post("/api/schedules", tags=["Programaciones"])
def create_schedule(data: ScheduleData, db: DatabaseConnector = Depends(get_db)):
    try:
        db_service.create_schedule(db, data)
        return {"message": "ProgramaciÃ³n creada."}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        _handle_endpoint_errors("create_schedule", e, "ProgramaciÃ³n")


@router.put("/api/schedules/{schedule_id}", tags=["Programaciones"])
def update_schedule(schedule_id: int, data: ScheduleData, db: DatabaseConnector = Depends(get_db)):
    try:
        db_service.update_schedule(db, schedule_id, data)
        return {"message": "ProgramaciÃ³n actualizada."}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        _handle_endpoint_errors("update_schedule", e, "ProgramaciÃ³n", schedule_id)


@router.patch("/api/schedules/{schedule_id}/status", tags=["Programaciones"], status_code=200)
def toggle_schedule_status(
    schedule_id: int,
    body: dict,
    db: DatabaseConnector = Depends(get_db),
):
    """Cambio rÃ¡pido de estado Activo. Espera: {"Activo": true/false}"""
    try:
        activo = body.get("Activo")
        if activo is None:
            raise ValueError("El cuerpo debe contener la clave 'Activo'")
        db_service.toggle_schedule_active(db, schedule_id, activo)
        return {"message": "Estado actualizado"}
    except Exception as e:
        _handle_endpoint_errors("toggle_schedule_status", e, "ProgramaciÃ³n", schedule_id)


@router.put("/api/schedules/{schedule_id}/details", tags=["Programaciones"], status_code=status.HTTP_204_NO_CONTENT)
def update_schedule_details(
    schedule_id: int,
    data: ScheduleEditData,
    db: DatabaseConnector = Depends(get_db),
):
    """
    Endpoint de ediciÃ³n simple desde la pÃ¡gina de Programaciones.
    No requiere el campo 'Equipos'.
    """
    try:
        db_service.update_schedule_simple(db, schedule_id, data)
    except Exception as e:
        _handle_endpoint_errors("update_schedule_details", e, "ProgramaciÃ³n", schedule_id)


@router.get("/api/schedules/{schedule_id}/devices", tags=["Programaciones"])
def get_schedule_devices(schedule_id: int, db: DatabaseConnector = Depends(get_db)):
    try:
        return db_service.get_schedule_devices_data(db, schedule_id)
    except Exception as e:
        _handle_endpoint_errors("get_schedule_devices", e, "Schedules", schedule_id)


@router.put("/api/schedules/{schedule_id}/devices", tags=["Programaciones"])
def update_schedule_devices(
    schedule_id: int, equipo_ids: List[int] = Body(...), db: DatabaseConnector = Depends(get_db)
):
    try:
        db_service.update_schedule_devices_db(db, schedule_id, equipo_ids)
        return {"message": "Asignaciones actualizadas"}
    except Exception as e:
        _handle_endpoint_errors("update_schedule_devices", e, "Schedules", schedule_id)


# ------------------------------------------------------------------
# Equipos - Endpoints adicionales
# ------------------------------------------------------------------
@router.get("/api/equipos/disponibles/{robot_id}", tags=["Equipos"])
def get_available_devices(robot_id: int, db: DatabaseConnector = Depends(get_db)):
    """
    Endpoint para obtener equipos disponibles. El robot_id se mantiene por
    compatibilidad con la ruta, pero la lÃ³gica de negocio (BR-05, BR-06)
    ya no lo requiere.
    """
    try:
        return db_service.get_available_devices_for_robot(db, robot_id)
    except Exception as e:
        _handle_endpoint_errors("get_available_devices", e, "Equipos", robot_id)


@router.patch("/api/equipos/{equipo_id}", tags=["Equipos"])
def update_equipo_status(equipo_id: int, update_data: EquipoStatusUpdate, db: DatabaseConnector = Depends(get_db)):
    """
    Actualiza el estado de un equipo (Activo_SAM o PermiteBalanceoDinamico).
    El SP valida: existe el equipo y que el valor sea distinto.
    """
    try:
        db_service.update_device_status(db, equipo_id, update_data.field, update_data.value)
        return {"message": "Estado del equipo actualizado con Ã©xito."}

    except pyodbc.Error as db_error:
        _handle_endpoint_errors("update_equipo_status", db_error, "Equipo", equipo_id)

    except Exception as e:
        _handle_endpoint_errors("update_equipo_status", e, "Equipo", equipo_id)


@router.post("/api/equipos", tags=["Equipos"], status_code=status.HTTP_201_CREATED)
def create_new_equipo(equipo_data: EquipoCreateRequest, db: DatabaseConnector = Depends(get_db)):
    """Crea un nuevo equipo manualmente."""
    try:
        new_equipo = db_service.create_equipo(db, equipo_data)
        return {"message": "Equipo creado exitosamente.", "equipo": new_equipo}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))
    except pyodbc.Error as dbe:
        _handle_endpoint_errors("create_new_equipo", dbe, "Equipo")
    except Exception as e:
        _handle_endpoint_errors("create_new_equipo", e, "Equipo")


# ------------------------------------------------------------------
# Assignments
# ------------------------------------------------------------------
@router.get("/api/robots/{robot_id}/asignaciones", tags=["Asignaciones"])
def get_robot_assignments(robot_id: int, db: DatabaseConnector = Depends(get_db)):
    try:
        return db_service.get_asignaciones_by_robot(db, robot_id)
    except Exception as e:
        _handle_endpoint_errors("get_robot_assignments", e, "Asignaciones", robot_id)


@router.post("/api/robots/{robot_id}/asignaciones", tags=["Asignaciones"])
def update_robot_assignments(
    robot_id: int, update_data: AssignmentUpdateRequest, db: DatabaseConnector = Depends(get_db)
):
    try:
        result = db_service.update_asignaciones_robot(
            db, robot_id, update_data.asignar_equipo_ids, update_data.desasignar_equipo_ids
        )
        return {"message": "Asignaciones actualizadas.", "detail": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        _handle_endpoint_errors("update_robot_assignments", e, "Asignaciones", robot_id)


# ------------------------------------------------------------------
# Pools
# ------------------------------------------------------------------
@router.get("/api/pools", tags=["Pools"])
def get_all_pools(db: DatabaseConnector = Depends(get_db)):
    try:
        pools = db_service.get_pools(db)
        logger.info(f"Devueltos {len(pools)} pools.")
        return {"pools": pools, "total": len(pools)}
    except Exception as e:
        _handle_endpoint_errors("get_all_pools", e, "Pools")


@router.post("/api/pools", tags=["Pools"], status_code=status.HTTP_201_CREATED)
def create_new_pool(pool_data: PoolCreate, db: DatabaseConnector = Depends(get_db)):
    try:
        pool = db_service.create_pool(db, pool_data.Nombre, pool_data.Descripcion)
        return {"message": "Pool creado.", "pool": pool}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))
    except pyodbc.ProgrammingError as e:
        if "Ya existe un pool" in str(e):
            raise HTTPException(status_code=409, detail="Ya existe un pool con ese nombre.")
        _handle_endpoint_errors("create_new_pool", e, "Pools")
    except Exception as e:
        _handle_endpoint_errors("create_new_pool", e, "Pools")


@router.put("/api/pools/{pool_id}", tags=["Pools"])
def update_existing_pool(pool_id: int, pool_data: PoolUpdate, db: DatabaseConnector = Depends(get_db)):
    try:
        db_service.update_pool(db, pool_id, pool_data.Nombre, pool_data.Descripcion)
        return {"message": f"Pool {pool_id} actualizado."}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))
    except Exception as e:
        _handle_endpoint_errors("update_existing_pool", e, "Pools", pool_id)


@router.delete("/api/pools/{pool_id}", tags=["Pools"], status_code=status.HTTP_204_NO_CONTENT)
def delete_single_pool(pool_id: int, db: DatabaseConnector = Depends(get_db)):
    try:
        db_service.delete_pool(db, pool_id)
    except Exception as e:
        _handle_endpoint_errors("delete_single_pool", e, "Pools", pool_id)


@router.get("/api/pools/{pool_id}/asignaciones", tags=["Pools"])
def get_pool_assignments(pool_id: int, db: DatabaseConnector = Depends(get_db)):
    try:
        data = db_service.get_pool_assignments_and_available_resources(db, pool_id)
        return {"assigned": data["assigned"], "available": data["available"]}
    except Exception as e:
        _handle_endpoint_errors("get_pool_assignments", e, "Pools", pool_id)


@router.put("/api/pools/{pool_id}/asignaciones", tags=["Pools"])
def set_pool_assignments(pool_id: int, data: PoolAssignmentsRequest, db: DatabaseConnector = Depends(get_db)):
    try:
        db_service.assign_resources_to_pool(db, pool_id, data.robot_ids, data.equipo_ids)
        return {"message": f"Asignaciones para el Pool {pool_id} actualizadas."}
    except Exception as e:
        _handle_endpoint_errors("set_pool_assignments", e, "Pools", pool_id)


# ------------------------------------------------------------------
# ConfiguraciÃ³n del Sistema
# ------------------------------------------------------------------
@router.get("/api/config/preemption", tags=["Configuracion"])
def get_preemption_mode(db: DatabaseConnector = Depends(get_db)):
    try:
        val = db_service.get_system_config(db, "BALANCEO_PREEMPTION_MODE")
        is_enabled = (val or "").upper() == "TRUE"
        return {"enabled": is_enabled}
    except Exception as e:
        _handle_endpoint_errors("get_preemption_mode", e, "Configuracion")


@router.put("/api/config/preemption", tags=["Configuracion"])
def set_preemption_mode(enabled: bool = Body(..., embed=True), db: DatabaseConnector = Depends(get_db)):
    try:
        val = "TRUE" if enabled else "FALSE"
        db_service.set_system_config(db, "BALANCEO_PREEMPTION_MODE", val)
        return {"message": f"Modo Prioridad Estricta {'activado' if enabled else 'desactivado'}"}
    except Exception as e:
        _handle_endpoint_errors("set_preemption_mode", e, "Configuracion")


@router.get("/api/config/isolation", tags=["Configuracion"])
def get_isolation_mode(db: DatabaseConnector = Depends(get_db)):
    try:
        val = db_service.get_system_config(db, "BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO")
        is_enabled = (val or "TRUE").upper() == "TRUE"
        return {"enabled": is_enabled}
    except Exception as e:
        _handle_endpoint_errors("get_isolation_mode", e, "Configuracion")


@router.put("/api/config/isolation", tags=["Configuracion"])
def set_isolation_mode(enabled: bool = Body(..., embed=True), db: DatabaseConnector = Depends(get_db)):
    try:
        val = "TRUE" if enabled else "FALSE"
        db_service.set_system_config(db, "BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO", val)
        mode_text = "Aislamiento Estricto (Sin Desborde)" if enabled else "Desborde Permitido (Cross-Pool)"
        return {"message": f"Modo {mode_text} activado."}
    except Exception as e:
        _handle_endpoint_errors("set_isolation_mode", e, "Configuracion")


# ------------------------------------------------------------------
# Mapeos
# ------------------------------------------------------------------
@router.get("/api/mappings", tags=["Configuracion"], response_model=List[MapeoRobotResponse])
def get_mappings(db: DatabaseConnector = Depends(get_db)):
    try:
        return db_service.get_all_mappings(db)
    except Exception as e:
        _handle_endpoint_errors("get_mappings", e, "Mapeos")


@router.post("/api/mappings", tags=["Configuracion"])
def create_mapping_endpoint(mapping: MapeoRobotCreate, db: DatabaseConnector = Depends(get_db)):
    try:
        db_service.create_mapping(db, mapping.dict())
        return {"message": "Mapeo creado correctamente"}
    except Exception as e:
        _handle_endpoint_errors("create_mapping", e, "Mapeos")


@router.delete("/api/mappings/{mapeo_id}", tags=["Configuracion"])
def delete_mapping_endpoint(mapeo_id: int, db: DatabaseConnector = Depends(get_db)):
    try:
        db_service.delete_mapping(db, mapeo_id)
        return {"message": "Mapeo eliminado"}
    except Exception as e:
        _handle_endpoint_errors("delete_mapping", e, "Mapeos", mapeo_id)
