# src/interfaz_web/services/programacion_service.py
from typing import Dict, List

from common.database.sql_client import DatabaseConnector

from ..schemas.programacion import ScheduleData


def get_schedules_for_robot(db: DatabaseConnector, robot_id: int) -> List[Dict]:
    query_schedules = "SELECT * FROM dbo.Programaciones WHERE RobotId = ? ORDER BY HoraInicio"
    schedules = db.ejecutar_consulta(query_schedules, (robot_id,), es_select=True)

    if not schedules:
        return []

    schedule_ids = [s["ProgramacionId"] for s in schedules]
    placeholders = ",".join("?" for _ in schedule_ids)

    query_teams = f"""
        SELECT a.ProgramacionId, e.EquipoId, e.Equipo
        FROM dbo.Asignaciones a
        JOIN dbo.Equipos e ON a.EquipoId = e.EquipoId
        WHERE a.ProgramacionId IN ({placeholders}) AND a.EsProgramado = 1
    """
    team_assignments = db.ejecutar_consulta(query_teams, tuple(schedule_ids), es_select=True)

    teams_map = {}
    for assignment in team_assignments:
        pid = assignment["ProgramacionId"]
        if pid not in teams_map:
            teams_map[pid] = []
        teams_map[pid].append({"EquipoId": assignment["EquipoId"], "Equipo": assignment["Equipo"]})

    for schedule in schedules:
        schedule["Equipos"] = teams_map.get(schedule["ProgramacionId"], [])

    return schedules

def delete_schedule_full(db: DatabaseConnector, programacion_id: int, robot_id: int):
    query = "EXEC dbo.EliminarProgramacionCompleta @ProgramacionId = ?, @RobotId = ?"
    db.ejecutar_consulta(query, (programacion_id, robot_id), es_select=False)

def create_new_schedule(db: DatabaseConnector, data: ScheduleData):
    equipos_nombres_result = db.ejecutar_consulta(
        f"SELECT STRING_AGG(Equipo, ',') AS Nombres FROM dbo.Equipos WHERE EquipoId IN ({','.join('?' for _ in data.Equipos)})",
        tuple(data.Equipos),
        es_select=True,
    )
    equipos_str = equipos_nombres_result[0]["Nombres"] if equipos_nombres_result and equipos_nombres_result[0]["Nombres"] else ""

    robot_nombre_result = db.ejecutar_consulta("SELECT Robot FROM dbo.Robots WHERE RobotId = ?", (data.RobotId,), es_select=True)
    robot_str = robot_nombre_result[0]["Robot"] if robot_nombre_result else ""

    sp_map = {
        "Diaria": ("dbo.CargarProgramacionDiaria", ["@Robot", "@Equipos", "@HoraInicio", "@Tolerancia"]),
        "Semanal": ("dbo.CargarProgramacionSemanal", ["@Robot", "@Equipos", "@DiasSemana", "@HoraInicio", "@Tolerancia"]),
        "Mensual": ("dbo.CargarProgramacionMensual", ["@Robot", "@Equipos", "@DiaDelMes", "@HoraInicio", "@Tolerancia"]),
        "Especifica": ("dbo.CargarProgramacionEspecifica", ["@Robot", "@Equipos", "@FechaEspecifica", "@HoraInicio", "@Tolerancia"]),
    }
    if data.TipoProgramacion not in sp_map:
        raise ValueError("Tipo de programación no válido")

    sp_name, sp_param_names = sp_map[data.TipoProgramacion]
    params_dict = {
        "@Robot": robot_str,
        "@Equipos": equipos_str,
        "@HoraInicio": data.HoraInicio,
        "@Tolerancia": data.Tolerancia,
        "@DiasSemana": data.DiasSemana,
        "@DiaDelMes": data.DiaDelMes,
        "@FechaEspecifica": data.FechaEspecifica,
    }

    params_tuple = tuple(params_dict[p] for p in sp_param_names)
    placeholders = ", ".join("?" for _ in params_tuple)
    query = f"EXEC {sp_name} {placeholders}"

    db.ejecutar_consulta(query, params_tuple, es_select=False)

def update_existing_schedule(db: DatabaseConnector, programacion_id: int, data: ScheduleData):
    equipos_str = ""
    if data.Equipos:
        placeholders = ",".join("?" for _ in data.Equipos)
        equipos_nombres_result = db.ejecutar_consulta(
            f"SELECT STRING_AGG(Equipo, ',') AS Nombres FROM dbo.Equipos WHERE EquipoId IN ({placeholders})",
            tuple(data.Equipos),
            es_select=True,
        )
        equipos_str = equipos_nombres_result[0]["Nombres"] if equipos_nombres_result and equipos_nombres_result[0]["Nombres"] else ""

    query = "EXEC dbo.ActualizarProgramacionCompleta ?, ?, ?, ?, ?, ?, ?, ?, ?"
    params = (
        programacion_id,
        data.RobotId,
        data.TipoProgramacion,
        data.HoraInicio,
        data.DiasSemana,
        data.DiaDelMes,
        data.FechaEspecifica,
        data.Tolerancia,
        equipos_str,
    )
    db.ejecutar_consulta(query, params, es_select=False)
