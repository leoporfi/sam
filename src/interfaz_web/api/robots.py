# src/interfaz_web/api/robots.py
from typing import Dict, Optional, List
from fastapi import APIRouter, Body, Query, HTTPException, Depends

from ..dependencies import get_db_connector
from ..schemas.robot import RobotCreateRequest, RobotUpdateRequest
from ..services import robot_service
from common.database.sql_client import DatabaseConnector

router = APIRouter(
    prefix="/api/robots",
    tags=["Robots"]
)

@router.get("/")
def get_robots_with_assignments(
    db: DatabaseConnector = Depends(get_db_connector),
    name: Optional[str] = None,
    active: Optional[bool] = None,
    online: Optional[bool] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query("Robot"),
    sort_dir: Optional[str] = Query("asc"),
):
    try:
        return robot_service.get_robots(
            db=db,
            name=name,
            active=active,
            online=online,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener robots: {e}")

@router.patch("/{robot_id}")
def update_robot_status(
    robot_id: int, 
    updates: Dict[str, bool] = Body(...),
    db: DatabaseConnector = Depends(get_db_connector)
):
    try:
        field_to_update = next(iter(updates))
        if field_to_update not in ["Activo", "EsOnline"]:
            raise HTTPException(status_code=400, detail="Campo no válido para actualización parcial.")
        
        new_value = updates[field_to_update]
        
        success = robot_service.update_robot_status(db, robot_id, field_to_update, new_value)
        
        if success:
            return {"message": "Estado del robot actualizado con éxito."}
        else:
            raise HTTPException(status_code=404, detail="Robot no encontrado.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{robot_id}")
def update_robot_details(
    robot_id: int, 
    robot_data: RobotUpdateRequest,
    db: DatabaseConnector = Depends(get_db_connector)
):
    try:
        updated_count = robot_service.update_robot_details(db, robot_id, robot_data)
        if updated_count > 0:
            return {"message": f"Robot {robot_id} actualizado con éxito."}
        else:
            raise HTTPException(status_code=404, detail="Robot no encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", status_code=201)
def create_robot(
    robot_data: RobotCreateRequest,
    db: DatabaseConnector = Depends(get_db_connector)
):
    try:
        new_robot = robot_service.create_robot(db, robot_data)
        if not new_robot:
            raise HTTPException(status_code=500, detail="No se pudo crear el robot.")
        return new_robot
    except ValueError as e: # Captura el error específico del servicio
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado al crear el robot: {e}")
