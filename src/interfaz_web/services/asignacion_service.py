# src/interfaz_web/services/asignacion_service.py
from typing import Dict, List

from common.database.sql_client import DatabaseConnector


def get_asignaciones_by_robot(db: DatabaseConnector, robot_id: int) -> List[Dict]:
    query = """
        SELECT A.RobotId, A.EquipoId, A.Equipo, A.EsProgramado, A.Reservado
        FROM dbo.AsignacionesView AS A
        WHERE A.RobotId = ?
    """
    return db.ejecutar_consulta(query, (robot_id,), es_select=True)

def update_asignaciones_robot(db: DatabaseConnector, robot_id: int, assign_ids: List[int], unassign_ids: List[int]) -> Dict:
    robot_info = db.ejecutar_consulta("SELECT EsOnline FROM dbo.Robots WHERE RobotId = ?", (robot_id,), es_select=True)
    if not robot_info:
        raise ValueError("Robot no encontrado")

    return db.actualizar_asignaciones_robot(robot_id, assign_ids, unassign_ids)
