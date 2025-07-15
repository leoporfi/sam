# src/interfaz_web/api/programaciones.py
from fastapi import APIRouter, Depends, HTTPException

from common.database.sql_client import DatabaseConnector

from ..dependencies import get_db_connector
from ..schemas.programacion import ScheduleData
from ..services import programacion_service

router = APIRouter(tags=["Programaciones"])


@router.get("/api/robots/{robot_id}/programaciones")
def get_robot_schedules(robot_id: int, db: DatabaseConnector = Depends(get_db_connector)):
    try:
        return programacion_service.get_schedules_for_robot(db, robot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener programaciones: {e}")


@router.delete("/api/robots/{robot_id}/programaciones/{programacion_id}", status_code=204)
def delete_schedule(robot_id: int, programacion_id: int, db: DatabaseConnector = Depends(get_db_connector)):
    try:
        programacion_service.delete_schedule_full(db, programacion_id, robot_id)
        # No se devuelve contenido en un 204
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar la programación: {e}")


@router.post("/api/programaciones")
def create_schedule(data: ScheduleData, db: DatabaseConnector = Depends(get_db_connector)):
    try:
        programacion_service.create_new_schedule(db, data)
        return {"message": "Programación creada con éxito."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear la programación: {e}")


@router.put("/api/programaciones/{programacion_id}")
def update_schedule(programacion_id: int, data: ScheduleData, db: DatabaseConnector = Depends(get_db_connector)):
    try:
        programacion_service.update_existing_schedule(db, programacion_id, data)
        return {"message": "Programación actualizada con éxito"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar la programación: {e}")
