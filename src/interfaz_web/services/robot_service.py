# src/interfaz_web/services/robot_service.py
from typing import Dict, List, Optional

from common.database.sql_client import DatabaseConnector

from ..schemas.robot import RobotCreateRequest, RobotUpdateRequest


def get_robots(
    db: DatabaseConnector,
    name: Optional[str] = None,
    active: Optional[bool] = None,
    online: Optional[bool] = None,
    page: int = 1,
    size: int = 20,
    sort_by: str = "Robot",
    sort_dir: str = "asc",
) -> Dict:
    sortable_columns = {
        "Robot": "r.Robot",
        "CantidadEquiposAsignados": "ISNULL(ea.Equipos, 0)",
        "Activo": "r.Activo",
        "EsOnline": "r.EsOnline",
        "TieneProgramacion": "(CASE WHEN EXISTS (SELECT 1 FROM dbo.Programaciones p WHERE p.RobotId = r.RobotId AND p.Activo = 1) THEN 1 ELSE 0 END)",
        "PrioridadBalanceo": "r.PrioridadBalanceo",
        "TicketsPorEquipoAdicional": "r.TicketsPorEquipoAdicional",
    }
    order_by_column = sortable_columns.get(sort_by, "r.Robot")
    order_by_direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

    select_from_clause = "FROM dbo.Robots r LEFT JOIN dbo.EquiposAsignados ea ON r.Robot = ea.Robot"
    conditions: List[str] = []
    params: List[any] = []

    if name:
        conditions.append("r.Robot LIKE ?")
        params.append(f"%{name}%")
    if active is not None:
        conditions.append("r.Activo = ?")
        params.append(active)
    if online is not None:
        conditions.append("r.EsOnline = ?")
        params.append(online)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    count_query = f"SELECT COUNT(*) as total_count {select_from_clause} {where_clause}"
    total_count_result = db.ejecutar_consulta(count_query, tuple(params), es_select=True)
    total_count = total_count_result[0]["total_count"] if total_count_result else 0

    offset = (page - 1) * size
    main_query = f"""
        SELECT
            r.RobotId, r.Robot, r.Descripcion, r.MinEquipos, r.MaxEquipos,
            r.EsOnline, r.Activo, r.PrioridadBalanceo,
            r.TicketsPorEquipoAdicional, 
            ISNULL(ea.Equipos, 0) as CantidadEquiposAsignados,
            CAST(CASE WHEN EXISTS (SELECT 1 FROM dbo.Programaciones p WHERE p.RobotId = r.RobotId AND p.Activo = 1) 
                 THEN 1 ELSE 0 END AS BIT) AS TieneProgramacion
        {select_from_clause}
        {where_clause}
        ORDER BY {order_by_column} {order_by_direction}
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    pagination_params = params + [offset, size]
    robots_data = db.ejecutar_consulta(main_query, tuple(pagination_params), es_select=True)

    return {"total_count": total_count, "page": page, "size": size, "robots": robots_data}

def update_robot_status(db: DatabaseConnector, robot_id: int, field: str, value: bool) -> bool:
    query = f"UPDATE dbo.Robots SET {field} = ? WHERE RobotId = ?"
    params = (value, robot_id)
    rows_affected = db.ejecutar_consulta(query, params, es_select=False)
    return rows_affected > 0

def update_robot_details(db: DatabaseConnector, robot_id: int, robot_data: RobotUpdateRequest) -> int:
    query = """
        UPDATE dbo.Robots SET
            Robot = ?, Descripcion = ?, MinEquipos = ?, MaxEquipos = ?,
            PrioridadBalanceo = ?, TicketsPorEquipoAdicional = ?
        WHERE RobotId = ?
    """
    params = (
        robot_data.Robot,
        robot_data.Descripcion,
        robot_data.MinEquipos,
        robot_data.MaxEquipos,
        robot_data.PrioridadBalanceo,
        robot_data.TicketsPorEquipoAdicional,
        robot_id,
    )
    return db.ejecutar_consulta(query, params, es_select=False)

def create_robot(db: DatabaseConnector, robot_data: RobotCreateRequest) -> Dict:
    query = """
        INSERT INTO dbo.Robots (RobotId, Robot, Descripcion, MinEquipos, MaxEquipos, PrioridadBalanceo, TicketsPorEquipoAdicional)
        OUTPUT INSERTED.*
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    params = (
        robot_data.RobotId,
        robot_data.Robot,
        robot_data.Descripcion,
        robot_data.MinEquipos,
        robot_data.MaxEquipos,
        robot_data.PrioridadBalanceo,
        robot_data.TicketsPorEquipoAdicional,
    )
    try:
        new_robot = db.ejecutar_consulta(query, params, es_select=True)
        if not new_robot:
            return None
        return new_robot[0]
    except Exception as e:
        if "Violation of PRIMARY KEY constraint" in str(e):
            raise ValueError(f"El RobotId {robot_data.RobotId} ya existe.")
        raise