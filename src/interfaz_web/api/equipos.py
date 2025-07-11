# src/interfaz_web/api/equipos.py
from fastapi import APIRouter, HTTPException, Depends
from ..dependencies import get_db_connector
from ..services import equipo_service
from common.database.sql_client import DatabaseConnector

router = APIRouter(
    prefix="/api/equipos",
    tags=["Equipos"]
)

@router.get("/disponibles/{robot_id}")
def get_available_teams(
    robot_id: int,
    db: DatabaseConnector = Depends(get_db_connector)
):
    """
    Obtiene la lista de equipos disponibles para ser asignados a un robot.
    """
    try:
        return equipo_service.get_available_teams_for_robot(db, robot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener equipos disponibles: {e}")
