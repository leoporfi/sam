# sam/web/api.py
import logging
from typing import Dict, Optional

import pyodbc
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, Request, status

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.database import DatabaseConnector

# Importa los servicios desde el archivo local de base de datos
from . import database as db_service
from .dependencies import get_aa_client, get_db

# Importa los schemas desde el archivo local de schemas
from .schemas import (
    AssignmentUpdateRequest,
    EquipoStatusUpdate,
    PoolAssignmentsRequest,
    PoolCreate,
    PoolUpdate,
    RobotCreateRequest,
    RobotUpdateRequest,
    ScheduleData,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ------------------------------------------------------------------
# Generic helper – keeps all routes consistent
# ------------------------------------------------------------------
def _handle_endpoint_errors(func_name: str, e: Exception, resource: str, resource_id: Optional[int] = None):
    """
    Centralised error mapper for the whole router.
    Returns nothing – just raises the right HTTPException.
    """
    error_msg = str(e)

    # 404 – Not found
    if any(txt in error_msg.lower() for txt in ("no encontró", "no se encontró", "not found", "does not exist")):
        logger.warning("%s: %s %s no encontrado -> 404", func_name, resource, resource_id or "")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} no encontrado.")

    # 409 – Business-rule conflict
    if any(txt in error_msg.lower() for txt in ("no se puede", "cannot be", "conflicto")):
        logger.warning("%s: conflicto de negocio -> 409: %s", func_name, error_msg)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)

    # 400 – Bad request (validation, bad field, etc.)
    if isinstance(e, ValueError):
        logger.warning("%s: ValueError -> 400: %s", func_name, error_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # 500 – Internal server error (log full traceback)
    logger.error("%s: error inesperado -> 500: %s", func_name, error_msg, exc_info=True)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor.")


# Task Wrapper
async def run_robot_sync_task(db: DatabaseConnector, aa_client: AutomationAnywhereClient, app_state):
    """Wrapper para ejecutar y gestionar el estado de la tarea de sync de robots."""
    lock = app_state.sync_lock
    try:
        # Poner el estado en "running"
        async with lock:
            app_state.sync_status["robots"] = "running"

        # Ejecutar la tarea real (que tarda 36s)
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
    request: Request,  # <--- Inyectar Request
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
    request: Request,  # <--- Inyectar Request
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


# ------------------------------------------------------------------
# Robots
# ------------------------------------------------------------------
@router.get("/api/robots", tags=["Robots"])
def get_robots_with_assignments(
    db: DatabaseConnector = Depends(get_db),
    name: Optional[str] = None,
    active: Optional[bool] = None,
    online: Optional[bool] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query("Robot"),
    sort_dir: Optional[str] = Query("asc"),
):
    try:
        return db_service.get_robots(
            db=db, name=name, active=active, online=online, page=page, size=size, sort_by=sort_by, sort_dir=sort_dir
        )
    except Exception as e:
        _handle_endpoint_errors("get_robots_with_assignments", e, "Robots")


@router.patch("/api/robots/{robot_id}", tags=["Robots"])
def update_robot_status(robot_id: int, updates: Dict[str, bool] = Body(...), db: DatabaseConnector = Depends(get_db)):
    """Actualiza el estado de un robot"""
    field = next(iter(updates))
    if field not in {"Activo", "EsOnline"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campo no válido.")
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
# Schedules
# ------------------------------------------------------------------
@router.get("/api/schedules", tags=["Programaciones"])
def get_all_schedules(db: DatabaseConnector = Depends(get_db)):
    try:
        return db_service.get_all_schedules(db)
    except Exception as e:
        _handle_endpoint_errors("get_all_schedules", e, "Programaciones")


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
        _handle_endpoint_errors("delete_schedule", e, "Programación", programacion_id)


@router.post("/api/schedules", tags=["Programaciones"])
def create_schedule(data: ScheduleData, db: DatabaseConnector = Depends(get_db)):
    try:
        db_service.create_schedule(db, data)
        return {"message": "Programación creada."}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        _handle_endpoint_errors("create_schedule", e, "Programación")


@router.put("/api/schedules/{schedule_id}", tags=["Programaciones"])
def update_schedule(schedule_id: int, data: ScheduleData, db: DatabaseConnector = Depends(get_db)):
    try:
        db_service.update_schedule(db, schedule_id, data)
        return {"message": "Programación actualizada."}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        _handle_endpoint_errors("update_schedule", e, "Programación", schedule_id)


# ------------------------------------------------------------------
# Equipos
# ------------------------------------------------------------------
@router.get("/api/equipos/disponibles/{robot_id}", tags=["Equipos"])
def get_available_devices(robot_id: int, db: DatabaseConnector = Depends(get_db)):
    """
    Endpoint para obtener equipos disponibles. El robot_id se mantiene por
    compatibilidad con la ruta, pero la lógica de negocio (BR-05, BR-06)
    ya no lo requiere.
    """
    try:
        return db_service.get_available_devices_for_robot(db, robot_id)
    except Exception as e:
        _handle_endpoint_errors("get_available_devices", e, "Equipos", robot_id)


@router.get("/api/equipos", tags=["Equipos"])
def get_all_equipos(
    db: DatabaseConnector = Depends(get_db),
    name: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    balanceable: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
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


@router.patch("/api/equipos/{equipo_id}", tags=["Equipos"])
def update_equipo_status(equipo_id: int, update_data: EquipoStatusUpdate, db: DatabaseConnector = Depends(get_db)):
    """
    Actualiza el estado de un equipo (Activo_SAM o PermiteBalanceoDinamico).
    El SP valida: existe el equipo y que el valor sea distinto.
    """
    try:
        db_service.update_device_status(db, equipo_id, update_data.field, update_data.value)
        return {"message": "Estado del equipo actualizado con éxito."}

    except pyodbc.Error as db_error:
        _handle_endpoint_errors("update_equipo_status", db_error, "Equipo", equipo_id)

    except Exception as e:
        _handle_endpoint_errors("update_equipo_status", e, "Equipo", equipo_id)


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
