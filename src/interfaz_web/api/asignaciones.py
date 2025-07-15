# src/interfaz_web/api/asignaciones.py
from fastapi import APIRouter, Depends, HTTPException

from common.database.sql_client import DatabaseConnector

from ..dependencies import get_db_connector
from ..schemas.asignacion import AssignmentUpdateRequest
from ..services import asignacion_service

router = APIRouter(prefix="/api/robots/{robot_id}/asignaciones", tags=["Asignaciones"])


@router.get("/")
def get_robot_asignaciones(robot_id: int, db: DatabaseConnector = Depends(get_db_connector)):
    try:
        return asignacion_service.get_asignaciones_by_robot(db, robot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener asignaciones: {e}")


@router.post("/")
def update_robot_asignaciones(robot_id: int, update_data: AssignmentUpdateRequest, db: DatabaseConnector = Depends(get_db_connector)):
    try:
        result = asignacion_service.update_asignaciones_robot(db, robot_id, update_data.assign_team_ids, update_data.unassign_team_ids)
        return result
    except ValueError as e:  # Para errores controlados como "Robot no encontrado"
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar asignaciones: {e}")
