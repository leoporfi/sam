# src/interfaz_web/services/equipo_service.py
from typing import Dict, List

from common.database.sql_client import DatabaseConnector


def get_available_teams_for_robot(db: DatabaseConnector, robot_id: int) -> List[Dict]:
    """
    Obtiene equipos que no están asignados al robot especificado.
    """
    query = """
        SELECT EquipoId, Equipo FROM dbo.Equipos
        WHERE Activo_SAM = 1 AND PermiteBalanceoDinamico = 1
        AND EquipoId NOT IN (
            SELECT EquipoId FROM dbo.Asignaciones WHERE RobotId = ?
        )
    """
    return db.ejecutar_consulta(query, (robot_id,), es_select=True)
