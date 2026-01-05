# web/backend/database.py
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pyodbc

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.database import DatabaseConnector
from sam.common.sincronizador_comun import SincronizadorComun

from .schemas import (
    EquipoCreateRequest,
    RobotCreateRequest,
    RobotUpdateRequest,
    ScheduleData,
    ScheduleEditData,
)

logger = logging.getLogger(__name__)


# Sincronización con A360
async def sync_with_a360(db: DatabaseConnector, aa_client: AutomationAnywhereClient) -> Dict:
    """
    Orquesta la sincronización de las tablas Robots y Equipos con A360.
    """
    logger.info("Iniciando la sincronización con A360 desde el servicio WEB...")
    try:
        # El cliente aa_client ya viene creado e inyectado
        sincronizador = SincronizadorComun(db_connector=db, aa_client=aa_client)
        # SincronizadorComun suele tener lógica mixta, así que lo invocamos directo si es async,
        # pero si sincronizar_entidades fuera bloqueante, habría que envolverlo.
        # Asumiendo que es async nativo:
        summary = await sincronizador.sincronizar_entidades()
        logger.info(f"Sincronización completada: {summary}")
        return summary
    except Exception as e:
        logger.critical(f"Error fatal durante la sincronización web: {type(e).__name__} - {e}", exc_info=True)
        raise


async def sync_robots_only(db: DatabaseConnector, aa_client: AutomationAnywhereClient) -> Dict:
    """
    Sincroniza únicamente la tabla Robots con A360.
    """
    logger.info("Iniciando sincronización de robots desde A360...")
    try:
        # El cliente aa_client ya viene creado e inyectado
        robots_api = await aa_client.obtener_robots()
        logger.info(f"Datos recibidos de A360: {len(robots_api)} robots.")

        # Mover la escritura a DB a un hilo aparte para NO bloquear el loop
        await asyncio.to_thread(db.merge_robots, robots_api)

        logger.info(f"Sincronización de robots completada. {len(robots_api)} robots procesados.")
        return {"robots_sincronizados": len(robots_api)}
    except Exception as e:
        logger.critical(f"Error durante sincronización de robots: {type(e).__name__} - {e}", exc_info=True)
        raise


async def sync_equipos_only(db: DatabaseConnector, aa_client: AutomationAnywhereClient) -> Dict:
    """
    Sincroniza únicamente la tabla Equipos con A360.
    """
    logger.info("Iniciando sincronización de equipos desde A360...")
    try:
        # El cliente aa_client ya viene creado e inyectado
        sincronizador = SincronizadorComun(db_connector=db, aa_client=aa_client)

        devices_task = aa_client.obtener_devices()
        users_task = aa_client.obtener_usuarios_detallados()
        devices_api, users_api = await asyncio.gather(devices_task, users_task)

        logger.info(f"Datos recibidos de A360: {len(devices_api)} dispositivos, {len(users_api)} usuarios.")

        # Procesamiento en CPU (podría bloquear un poco, pero es rápido)
        equipos_finales = sincronizador._procesar_y_mapear_equipos(devices_api, users_api)

        # DB Write en hilo aparte
        await asyncio.to_thread(db.merge_equipos, equipos_finales)

        logger.info(f"Sincronización de equipos completada. {len(equipos_finales)} equipos procesados.")
        return {"equipos_sincronizados": len(equipos_finales)}
    except Exception as e:
        logger.critical(f"Error durante sincronización de equipos: {type(e).__name__} - {e}", exc_info=True)
        raise


# Robots
def get_robots(
    db: DatabaseConnector,
    name: Optional[str] = None,
    active: Optional[bool] = None,
    online: Optional[bool] = None,
    programado: Optional[bool] = None,
    page: int = 1,
    size: int = 100,
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
    if programado is not None:
        # Programado = True  -> robots que tienen al menos una programación activa
        # Programado = False -> robots sin programaciones activas
        if programado:
            conditions.append(
                "EXISTS (SELECT 1 FROM dbo.Programaciones p WHERE p.RobotId = r.RobotId AND p.Activo = 1)"
            )
        else:
            conditions.append(
                "NOT EXISTS (SELECT 1 FROM dbo.Programaciones p WHERE p.RobotId = r.RobotId AND p.Activo = 1)"
            )

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    count_query = f"SELECT COUNT(*) as total_count {select_from_clause} {where_clause}"
    total_count_result = db.ejecutar_consulta(count_query, tuple(params), es_select=True)
    total_count = total_count_result[0]["total_count"] if total_count_result else 0

    offset = (page - 1) * size
    main_query = f"""
        SELECT
            r.RobotId, r.Robot, r.Descripcion, r.MinEquipos, r.MaxEquipos,
            r.EsOnline, r.Activo, r.PrioridadBalanceo,
            r.TicketsPorEquipoAdicional, r.Parametros,
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
    if field == "EsOnline" and value is True:
        # Verificar si el robot tiene programaciones activas
        check_query = """
            SELECT COUNT(*) AS ProgramCount
            FROM dbo.Programaciones
            WHERE RobotId = ? AND Activo = 1
        """
        result = db.ejecutar_consulta(check_query, (robot_id,), es_select=True)
        if result and result[0]["ProgramCount"] > 0:
            # Si tiene programaciones, lanzar un error en lugar de actualizar
            raise ValueError("No se puede marcar como 'Online' un robot que tiene programaciones activas.")

    query = f"UPDATE dbo.Robots SET {field} = ? WHERE RobotId = ?"
    params = (value, robot_id)
    rows_affected = db.ejecutar_consulta(query, params, es_select=False)
    return rows_affected > 0


def update_robot_details(db: DatabaseConnector, robot_id: int, robot_data: RobotUpdateRequest) -> int:
    query = """
        UPDATE dbo.Robots SET
            Robot = ?, Descripcion = ?, MinEquipos = ?, MaxEquipos = ?,
            PrioridadBalanceo = ?, TicketsPorEquipoAdicional = ?, Parametros = ?
        WHERE RobotId = ?
    """
    params = (
        robot_data.Robot,
        robot_data.Descripcion,
        robot_data.MinEquipos,
        robot_data.MaxEquipos,
        robot_data.PrioridadBalanceo,
        robot_data.TicketsPorEquipoAdicional,
        robot_data.Parametros,
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


# Asignaciones
def get_asignaciones_by_robot(db: DatabaseConnector, robot_id: int) -> List[Dict]:
    query = """
        SELECT A.RobotId, A.EquipoId, A.Equipo, A.EsProgramado, A.Reservado
        FROM dbo.AsignacionesView AS A
        WHERE A.RobotId = ?
    """
    return db.ejecutar_consulta(query, (robot_id,), es_select=True)


def update_asignaciones_robot(
    db: DatabaseConnector, robot_id: int, assign_ids: List[int], unassign_ids: List[int]
) -> Dict:
    robot_info = db.ejecutar_consulta("SELECT EsOnline FROM dbo.Robots WHERE RobotId = ?", (robot_id,), es_select=True)
    if not robot_info:
        raise ValueError("Robot no encontrado")

    try:
        with db.obtener_cursor() as cursor:
            # 1. Desasignar equipos
            if unassign_ids:
                unassign_placeholders = ",".join("?" for _ in unassign_ids)
                unassign_query = (
                    f"DELETE FROM dbo.Asignaciones WHERE RobotId = ? AND EquipoId IN ({unassign_placeholders})"
                )
                cursor.execute(unassign_query, robot_id, *unassign_ids)

            # 2. Asignar nuevos equipos
            if assign_ids:
                assign_query = """
                    INSERT INTO dbo.Asignaciones (RobotId, EquipoId, EsProgramado, Reservado, AsignadoPor)
                    VALUES (?, ?, 0, 1, 'WebApp')
                """
                assign_params = [(robot_id, equipo_id) for equipo_id in assign_ids]
                cursor.executemany(assign_query, assign_params)

            cursor.commit()
            return {"message": "Asignaciones actualizadas correctamente."}
    except Exception as e:
        logger.error(f"Error al actualizar asignaciones para el robot {robot_id}: {e}", exc_info=True)
        raise


# Se actualiza para implementar la Regla 3 Corregida.
def get_available_devices_for_robot(db: DatabaseConnector, robot_id: int) -> List[Dict]:
    """
    Obtiene equipos disponibles para programar para un robot específico.

    MEJORA: En lugar de múltiples NOT EXISTS, delegamos la lógica compleja
    a un Stored Procedure que encapsula las reglas de negocio.

    Un equipo está disponible si:
    1. Está Activo_SAM = 1
    2. Tiene licencia 'ATTENDEDRUNTIME' o 'RUNTIME' (BR-05)
    3. NO está 'Reservado = 1' manualmente (BR-03)
    4. NO está asignado dinámicamente (EsProgramado = 0 Y Reservado = 0)
    5. NO está ya asignado (de cualquier forma) A ESTE MISMO robot
    6. SÍ PUEDE estar asignado programáticamente (EsProgramado = 1) a OTRO robot
    """
    try:
        # OPCIÓN 1: Usar Stored Procedure (RECOMENDADO)
        query = "EXEC dbo.ObtenerEquiposDisponiblesParaRobot @RobotId = ?"
        return db.ejecutar_consulta(query, (robot_id,), es_select=True)

    except Exception as e:
        logger.error(f"Error al obtener equipos disponibles para robot {robot_id}: {e}", exc_info=True)
        # OPCIÓN 2: Fallback a query inline si el SP no existe aún
        return get_available_devices_for_robot_inline(db, robot_id)


def get_available_devices_for_robot_inline(db: DatabaseConnector, robot_id: int) -> List[Dict]:
    """
    Implementación inline como fallback o para desarrollo.
    Esta query es equivalente pero más legible que la versión con NOT EXISTS anidados.
    Incluye información sobre si el equipo está programado en otro robot.
    """
    query = """
        WITH EquiposReservados AS (
            -- Equipos reservados manualmente o asignados dinámicamente por CUALQUIER robot
            SELECT DISTINCT EquipoId
            FROM dbo.Asignaciones
            WHERE Reservado = 1
               OR (EsProgramado = 0 AND Reservado = 0)
        ),
        EquiposYaAsignados AS (
            -- Equipos ya asignados (de cualquier forma) A ESTE robot específico
            SELECT DISTINCT EquipoId
            FROM dbo.Asignaciones
            WHERE RobotId = ?
        ),
        EquiposProgramadosEnOtrosRobots AS (
            -- Equipos programados en otros robots (no en este)
            SELECT DISTINCT EquipoId, CAST(1 AS BIT) AS EsProgramado
            FROM dbo.Asignaciones
            WHERE EsProgramado = 1
              AND RobotId != ?
        )
        SELECT
            E.EquipoId,
            E.Equipo,
            ISNULL(P.EsProgramado, CAST(0 AS BIT)) AS EsProgramado,
            CAST(0 AS BIT) AS Reservado
        FROM dbo.Equipos E
        LEFT JOIN EquiposProgramadosEnOtrosRobots P ON E.EquipoId = P.EquipoId
        WHERE E.Activo_SAM = 1
          AND E.Licencia IN ('ATTENDEDRUNTIME', 'RUNTIME')
          AND E.EquipoId NOT IN (SELECT EquipoId FROM EquiposReservados)
          AND E.EquipoId NOT IN (SELECT EquipoId FROM EquiposYaAsignados)
        ORDER BY E.Equipo
    """
    return db.ejecutar_consulta(query, (robot_id, robot_id), es_select=True)


def get_devices(
    db: DatabaseConnector,
    name: Optional[str] = None,
    active: Optional[bool] = None,
    balanceable: Optional[bool] = None,
    page: int = 1,
    size: int = 100,
    sort_by: str = "Equipo",
    sort_dir: str = "asc",
) -> Dict:
    params = (name, active, balanceable, page, size, sort_by, sort_dir)

    try:
        with db.obtener_cursor() as cursor:
            # El SP devuelve dos result sets: primero el conteo, luego los datos.
            cursor.execute("{CALL dbo.ListarEquipos(?, ?, ?, ?, ?, ?, ?)}", params)

            total_count_result = cursor.fetchone()
            total_count = total_count_result[0] if total_count_result else 0

            cursor.nextset()

            columns = [column[0] for column in cursor.description]
            equipos_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return {"total_count": total_count, "page": page, "size": size, "equipos": equipos_data}
    except Exception as e:
        logger.error(f"Error en get_equipos: {e}", exc_info=True)
        raise


def update_device_status(db: DatabaseConnector, equipo_id: int, field: str, value: bool) -> bool:
    query = "{CALL dbo.ActualizarEstadoEquipo(?, ?, ?)}"
    params = (equipo_id, field, value)
    # El SP no devuelve filas, pero sí un recuento de filas afectadas.
    rows_affected = db.ejecutar_consulta(query, params, es_select=False)
    return rows_affected > 0


# Programaciones
def get_all_schedules(db: DatabaseConnector) -> List[Dict]:
    query = "EXEC dbo.ListarProgramaciones"
    schedules = db.ejecutar_consulta(query, es_select=True)
    for schedule in schedules:
        equipos_str = schedule.pop("EquiposProgramados", "")
        schedule["Equipos"] = [{"Equipo": name.strip()} for name in equipos_str.split(",")] if equipos_str else []
    return schedules


def get_robot_schedules(db: DatabaseConnector, robot_id: int) -> List[Dict]:
    query = "EXEC dbo.ListarProgramacionesPorRobot @RobotId = ?"
    schedules = db.ejecutar_consulta(query, (robot_id,), es_select=True)
    for schedule in schedules:
        equipos_str = schedule.pop("EquiposProgramados", "")
        schedule["Equipos"] = [{"Equipo": name.strip()} for name in equipos_str.split(",")] if equipos_str else []
    return schedules


def delete_schedule(db: DatabaseConnector, programacion_id: int, robot_id: int):
    # RFR-25: Se utiliza el Stored Procedure para una eliminación segura.
    query = "EXEC dbo.EliminarProgramacionCompleta @ProgramacionId = ?, @RobotId = ?"
    db.ejecutar_consulta(query, (programacion_id, robot_id), es_select=False)


def create_schedule(db: DatabaseConnector, data: ScheduleData):
    robot_nombre_result = db.ejecutar_consulta(
        "SELECT Robot FROM dbo.Robots WHERE RobotId = ?", (data.RobotId,), es_select=True
    )
    if not robot_nombre_result:
        raise ValueError(f"No se encontró un robot con el ID {data.RobotId}")
    robot_str = robot_nombre_result[0]["Robot"]

    equipos_str = ""
    if data.Equipos:
        placeholders = ",".join("?" for _ in data.Equipos)
        # Usamos NVARCHAR(MAX) para evitar el límite de 8000 bytes de STRING_AGG
        equipos_nombres_result = db.ejecutar_consulta(
            f"SELECT STRING_AGG(CAST(Equipo AS NVARCHAR(MAX)), ',') AS Nombres FROM dbo.Equipos WHERE EquipoId IN ({placeholders})",
            tuple(data.Equipos),
            es_select=True,
        )
        if equipos_nombres_result and equipos_nombres_result[0]["Nombres"]:
            equipos_str = equipos_nombres_result[0]["Nombres"]

    # Mapear PrimerosDiasMes a DiaInicioMes=1, DiaFinMes=N
    dia_inicio = data.DiaInicioMes
    dia_fin = data.DiaFinMes
    if data.PrimerosDiasMes:
        dia_inicio = 1
        dia_fin = data.PrimerosDiasMes

    # Usar sintaxis EXEC con parámetros nombrados (más explícito y compatible)
    # El orden de los parámetros debe coincidir exactamente con el SP
    query = "EXEC dbo.CrearProgramacion @Robot=?, @Equipos=?, @TipoProgramacion=?, @HoraInicio=?, @Tolerancia=?, @DiasSemana=?, @DiaDelMes=?, @FechaEspecifica=?, @DiaInicioMes=?, @DiaFinMes=?, @UltimosDiasMes=?, @UsuarioCrea=?, @EsCiclico=?, @HoraFin=?, @FechaInicioVentana=?, @FechaFinVentana=?, @IntervaloEntreEjecuciones=?"
    params = (
        robot_str,
        equipos_str,
        data.TipoProgramacion,
        data.HoraInicio,
        data.Tolerancia,
        data.DiasSemana,
        data.DiaDelMes,
        data.FechaEspecifica,
        dia_inicio,
        dia_fin,
        data.UltimosDiasMes,
        "WebApp_Creation",  # @UsuarioCrea
        data.EsCiclico if data.EsCiclico is not None else False,
        data.HoraFin,
        data.FechaInicioVentana,
        data.FechaFinVentana,
        data.IntervaloEntreEjecuciones,
    )
    db.ejecutar_consulta(query, params, es_select=False)


def update_schedule(db: DatabaseConnector, schedule_id: int, data: ScheduleData):
    """
    Función COMPLEJA usada por el MODAL DE ROBOTS.
    Llama a 'ActualizarProgramacionCompleta' con Equipos.
    """
    if data.TipoProgramacion == "Semanal" and not data.DiasSemana:
        raise ValueError("Para programación Semanal, se requieren DiasSemana.")
    if data.TipoProgramacion == "Mensual" and not data.DiaDelMes:
        raise ValueError("Para programación Mensual, se requiere DiaDelMes.")
    if data.TipoProgramacion == "Especifica" and not data.FechaEspecifica:
        raise ValueError("Para programación Específica, se requiere FechaEspecifica.")

    equipos_str = ""
    if data.Equipos:
        placeholders = ",".join("?" for _ in data.Equipos)
        # Usamos NVARCHAR(MAX) para evitar el límite de 8000 bytes de STRING_AGG
        equipos_nombres_result = db.ejecutar_consulta(
            f"SELECT STRING_AGG(CAST(Equipo AS NVARCHAR(MAX)), ',') AS Nombres FROM dbo.Equipos WHERE EquipoId IN ({placeholders})",
            tuple(data.Equipos),
            es_select=True,
        )
        if equipos_nombres_result and equipos_nombres_result[0]["Nombres"]:
            equipos_str = equipos_nombres_result[0]["Nombres"]

    # Mapear PrimerosDiasMes a DiaInicioMes=1, DiaFinMes=N
    dia_inicio = data.DiaInicioMes
    dia_fin = data.DiaFinMes
    if data.PrimerosDiasMes:
        dia_inicio = 1
        dia_fin = data.PrimerosDiasMes

    query = """
        EXEC dbo.ActualizarProgramacionCompleta
            @ProgramacionId=?,
            @RobotId=?,
            @TipoProgramacion=?,
            @HoraInicio=?,
            @DiaSemana=?,
            @DiaDelMes=?,
            @FechaEspecifica=?,
            @Tolerancia=?,
            @Equipos=?,
            @UsuarioModifica=?,
            @DiaInicioMes=?,
            @DiaFinMes=?,
            @UltimosDiasMes=?,
            @EsCiclico=?,
            @HoraFin=?,
            @FechaInicioVentana=?,
            @FechaFinVentana=?,
            @IntervaloEntreEjecuciones=?
    """
    params = (
        schedule_id,
        data.RobotId,
        data.TipoProgramacion,
        data.HoraInicio,
        data.DiasSemana or None,
        data.DiaDelMes or None,
        data.FechaEspecifica or None,
        data.Tolerancia,
        equipos_str,
        "WebApp_Update",  # Usuario que modifica
        dia_inicio,
        dia_fin,
        data.UltimosDiasMes,
        data.EsCiclico if data.EsCiclico is not None else None,
        data.HoraFin,
        data.FechaInicioVentana,
        data.FechaFinVentana,
        data.IntervaloEntreEjecuciones,
    )
    db.ejecutar_consulta(query, params, es_select=False)


def update_schedule_simple(db: DatabaseConnector, schedule_id: int, data: ScheduleEditData):
    """
    Función SIMPLE usada por la PÁGINA DE PROGRAMACIONES.
    Llama a 'ActualizarProgramacionSimple'.
    """
    # (Validación...)
    if data.TipoProgramacion == "Semanal" and not data.DiasSemana:
        raise ValueError("Para programación Semanal, se requieren DiasSemana.")
    if data.TipoProgramacion == "Mensual" and not data.DiaDelMes:
        raise ValueError("Para programación Mensual, se requiere DiaDelMes.")
    if data.TipoProgramacion == "Especifica" and not data.FechaEspecifica:
        raise ValueError("Para programación Específica, se requiere FechaEspecifica.")

    # Mapear PrimerosDiasMes a DiaInicioMes=1, DiaFinMes=N
    dia_inicio = data.DiaInicioMes
    dia_fin = data.DiaFinMes
    if data.PrimerosDiasMes:
        dia_inicio = 1
        dia_fin = data.PrimerosDiasMes

    sql = """
        EXEC dbo.ActualizarProgramacionSimple
            @ProgramacionId=?,
            @TipoProgramacion=?,
            @HoraInicio=?,
            @DiasSemana=?,
            @DiaDelMes=?,
            @FechaEspecifica=?,
            @Tolerancia=?,
            @Activo=?,
            @DiaInicioMes=?,
            @DiaFinMes=?,
            @UltimosDiasMes=?,
            @EsCiclico=?,
            @HoraFin=?,
            @FechaInicioVentana=?,
            @FechaFinVentana=?,
            @IntervaloEntreEjecuciones=?
    """
    # Convertir time/date a formato compatible con SQL Server
    # pyodbc maneja automáticamente objetos time y date, pero para ser explícitos:
    hora_fin_val = data.HoraFin if data.HoraFin else None
    fecha_inicio_val = data.FechaInicioVentana if data.FechaInicioVentana else None
    fecha_fin_val = data.FechaFinVentana if data.FechaFinVentana else None

    params = (
        schedule_id,
        data.TipoProgramacion,
        data.HoraInicio,  # time object, pyodbc lo convierte automáticamente
        data.DiasSemana or None,
        data.DiaDelMes or None,
        data.FechaEspecifica or None,  # date object, pyodbc lo convierte automáticamente
        data.Tolerancia,
        data.Activo,
        dia_inicio,
        dia_fin,
        data.UltimosDiasMes,
        data.EsCiclico if data.EsCiclico is not None else None,
        hora_fin_val,  # time object
        fecha_inicio_val,  # date object
        fecha_fin_val,  # date object
        data.IntervaloEntreEjecuciones,
    )
    db.ejecutar_consulta(sql, params, es_select=False)


def get_schedules_paginated(
    db: DatabaseConnector,
    robot_id: Optional[int],
    tipo: Optional[str],
    activo: Optional[bool],
    search: Optional[str],
    page: int,
    size: int,
) -> dict:
    """
    Llama al SP dbo.ListarProgramacionesPaginadas (versión de 1 resultset)
    """
    offset = (page - 1) * size
    params = (robot_id, tipo, activo, search, size, offset)

    try:
        sql = "EXEC dbo.ListarProgramacionesPaginadas ?, ?, ?, ?, ?, ?"
        results = db.ejecutar_consulta(sql, params, es_select=True)

        total = 0
        schedules = []

        if results:
            total = results[0].get("TotalRows", 0)
            schedules = results
            for s in schedules:
                s.pop("TotalRows", None)

        return {"schedules": schedules, "total_count": total}
    except Exception as e:
        logger.error(f"Error al obtener programaciones paginadas: {e}", exc_info=True)
        raise


def toggle_schedule_active(db: DatabaseConnector, schedule_id: int, activo: bool):
    sql = "UPDATE dbo.Programaciones SET Activo=? WHERE ProgramacionId=?"
    db.ejecutar_consulta(sql, (activo, schedule_id), es_select=False)


def get_schedule_devices_data(db: DatabaseConnector, schedule_id: int) -> Dict[str, List[Dict]]:
    """
    Obtiene los equipos asignados a una programación específica y los disponibles.
    Incluye información sobre si los equipos están programados en otras programaciones.
    """
    # 1. Obtener los asignados a ESTA programación
    query_assigned = """
        SELECT e.EquipoId AS ID, e.Equipo AS Nombre, e.Licencia,
               CAST(1 AS BIT) AS EsProgramado, CAST(0 AS BIT) AS Reservado
        FROM Equipos e
        INNER JOIN Asignaciones a ON e.EquipoId = a.EquipoId
        WHERE a.ProgramacionId = ?
    """
    assigned = db.ejecutar_consulta(query_assigned, (schedule_id,), es_select=True)

    # 2. Obtener equipos disponibles (que estén activos en SAM)
    # Excluimos:
    # - Los que ya están asignados a esta programación
    # - Los que están reservados manualmente (Reservado = 1)
    # - Los que están asignados dinámicamente (EsProgramado = 0 AND Reservado = 0)
    # Incluimos información sobre si están programados en otras programaciones
    assigned_ids = [item["ID"] for item in assigned]

    # Si hay asignados, construimos los placeholders (?,?,?)
    if assigned_ids:
        placeholders = ",".join("?" * len(assigned_ids))
        query_available = f"""
            WITH EquiposReservadosODinamicos AS (
                -- Equipos reservados manualmente o asignados dinámicamente
                SELECT DISTINCT EquipoId
                FROM dbo.Asignaciones
                WHERE Reservado = 1
                   OR (EsProgramado = 0 AND Reservado = 0)
            ),
            EquiposProgramadosEnOtrasProgramaciones AS (
                -- Equipos programados en otras programaciones (no en esta)
                SELECT DISTINCT EquipoId, CAST(1 AS BIT) AS EsProgramado
                FROM dbo.Asignaciones
                WHERE EsProgramado = 1
                  AND ProgramacionId != ?
            )
            SELECT
                e.EquipoId AS ID,
                e.Equipo AS Nombre,
                e.Licencia,
                ISNULL(P.EsProgramado, CAST(0 AS BIT)) AS EsProgramado,
                CAST(0 AS BIT) AS Reservado
            FROM Equipos e
            LEFT JOIN EquiposProgramadosEnOtrasProgramaciones P ON e.EquipoId = P.EquipoId
            WHERE e.Activo_SAM = 1
              AND e.EquipoId NOT IN ({placeholders})
              AND e.EquipoId NOT IN (SELECT EquipoId FROM EquiposReservadosODinamicos)
            ORDER BY e.Equipo ASC
        """
        params = tuple([schedule_id] + list(assigned_ids))
    else:
        # Si no hay nadie asignado, traemos todos los activos (excluyendo reservados/dinámicos)
        query_available = """
            WITH EquiposReservadosODinamicos AS (
                -- Equipos reservados manualmente o asignados dinámicamente
                SELECT DISTINCT EquipoId
                FROM dbo.Asignaciones
                WHERE Reservado = 1
                   OR (EsProgramado = 0 AND Reservado = 0)
            ),
            EquiposProgramadosEnOtrasProgramaciones AS (
                -- Equipos programados en otras programaciones (no en esta)
                SELECT DISTINCT EquipoId, CAST(1 AS BIT) AS EsProgramado
                FROM dbo.Asignaciones
                WHERE EsProgramado = 1
                  AND ProgramacionId != ?
            )
            SELECT
                e.EquipoId AS ID,
                e.Equipo AS Nombre,
                e.Licencia,
                ISNULL(P.EsProgramado, CAST(0 AS BIT)) AS EsProgramado,
                CAST(0 AS BIT) AS Reservado
            FROM Equipos e
            LEFT JOIN EquiposProgramadosEnOtrasProgramaciones P ON e.EquipoId = P.EquipoId
            WHERE e.Activo_SAM = 1
              AND e.EquipoId NOT IN (SELECT EquipoId FROM EquiposReservadosODinamicos)
            ORDER BY e.Equipo ASC
        """
        params = (schedule_id,)

    available = db.ejecutar_consulta(query_available, params, es_select=True)

    return {"assigned": assigned, "available": available}


def update_schedule_devices_db(db: DatabaseConnector, schedule_id: int, equipo_ids: List[int]):
    """
    Actualiza las asignaciones usando el Stored Procedure 'ActualizarEquiposProgramacion'.
    Requiere que el SP exista en la base de datos.
    """
    try:
        # 1. Preparamos la lista para el TVP (Table-Valued Parameter)
        # Tu tipo 'dbo.IdListType' espera una columna [ID], así que pasamos tuplas de un elemento: (id,)
        devices_tvp = [(eid,) for eid in equipo_ids]

        # 2. Preparamos los parámetros del SP
        params = {
            "ProgramacionId": schedule_id,
            "EquiposIds": devices_tvp,  # Esto se mapea automáticamente al tipo TVP en SQL
        }

        # 3. Ejecutamos el SP usando el método especializado de tu conector
        db.ejecutar_sp_con_tvp("dbo.ActualizarEquiposProgramacion", params)

        # Nota: ejecutar_sp_con_tvp ya maneja el commit internamente.

    except Exception as e:
        # Capturamos cualquier error de SQL (ej. ID inválido) y lo relanzamos limpio
        raise Exception(f"Error al ejecutar SP ActualizarEquiposProgramacion: {e}")


# Pool
def get_pools(db: DatabaseConnector) -> List[Dict]:
    sql = "EXEC dbo.ListarPools"
    try:
        return db.ejecutar_consulta(sql, es_select=True)
    except Exception:
        raise


def create_pool(db: DatabaseConnector, nombre: str, descripcion: Optional[str]) -> Dict:
    sql = "EXEC dbo.CrearPool @Nombre = ?, @Descripcion = ?"
    params = (nombre, descripcion)
    try:
        new_pool_list = db.ejecutar_consulta(sql, params, es_select=True)
        if not new_pool_list:
            raise Exception("El Stored Procedure no devolvió el nuevo pool.")
        new_pool = new_pool_list[0]
        new_pool["CantidadRobots"] = 0
        new_pool["CantidadEquipos"] = 0
        return new_pool
    except Exception:
        raise


def update_pool(db: DatabaseConnector, pool_id: int, nombre: str, descripcion: Optional[str]):
    sql = "EXEC dbo.ActualizarPool @PoolId = ?, @Nombre = ?, @Descripcion = ?"
    params = (pool_id, nombre, descripcion)
    try:
        db.ejecutar_consulta(sql, params, es_select=False)
    except Exception as e:
        raise e


def delete_pool(db: DatabaseConnector, pool_id: int):
    sql = "EXEC dbo.EliminarPool @PoolId = ?"
    try:
        db.ejecutar_consulta(sql, (pool_id,), es_select=False)
    except Exception as e:
        raise e


def get_pool_assignments_and_available_resources(db: DatabaseConnector, pool_id: int) -> Dict:
    sql = "EXEC dbo.ObtenerRecursosParaPool @PoolId = ?"
    params = (pool_id,)
    assigned, available = [], []
    try:
        with db.obtener_cursor() as cursor:
            cursor.execute(sql, params)
            columns = [column[0] for column in cursor.description]
            for row in cursor.fetchall():
                assigned.append(dict(zip(columns, row)))
            if cursor.nextset():
                columns = [column[0] for column in cursor.description]
                for row in cursor.fetchall():
                    available.append(dict(zip(columns, row)))
        return {"assigned": assigned, "available": available}
    except Exception as e:
        raise e


def assign_resources_to_pool(db: DatabaseConnector, pool_id: int, robot_ids: List[int], equipo_ids: List[int]) -> None:
    robots_tvp = [(r,) for r in robot_ids]
    equipos_tvp = [(e,) for e in equipo_ids]

    db.ejecutar_sp_con_tvp(
        "dbo.AsignarRecursosAPool",
        {
            "PoolId": pool_id,
            "RobotIds": robots_tvp,
            "EquipoIds": equipos_tvp,
        },
    )


# Equipos
def create_equipo(db: DatabaseConnector, equipo_data: EquipoCreateRequest) -> Dict:
    """
    Inserta un nuevo equipo manualmente en la base de datos.
    NOTA: Esto asume que no existe un SP CrearEquipo. Usa INSERT directo.
    """
    logger.info(f"Intentando crear equipo manualmente: ID={equipo_data.EquipoId}, Nombre={equipo_data.Equipo}")
    # Usamos valores por defecto consistentes con la tabla
    # Activo_SAM = 1 (True)
    # PermiteBalanceoDinamico = 0 (False)
    query = """
        INSERT INTO dbo.Equipos (
            EquipoId, Equipo, UserId, UserName, Licencia,
            Activo_SAM, PermiteBalanceoDinamico
        )
        OUTPUT INSERTED.EquipoId, INSERTED.Equipo, INSERTED.UserName, INSERTED.Licencia,
               INSERTED.Activo_SAM, INSERTED.PermiteBalanceoDinamico
               , 'N/A' AS RobotAsignado, 'N/A' AS Pool
        VALUES (?, ?, ?, ?, ?, 1, 0);
    """
    params = (
        equipo_data.EquipoId,
        str(equipo_data.Equipo).upper(),
        equipo_data.UserId,
        equipo_data.UserName,
        equipo_data.Licencia,
    )
    try:
        new_equipo_list = db.ejecutar_consulta(query, params, es_select=True)
        if not new_equipo_list:
            raise Exception("La inserción no devolvió el nuevo equipo.")
        logger.info(f"Equipo {equipo_data.EquipoId} creado exitosamente.")
        return new_equipo_list[0]
    except pyodbc.IntegrityError as e:  # type: ignore  # noqa: F821
        # Captura error de clave duplicada
        if "Violation of PRIMARY KEY constraint" in str(e) or "duplicate key" in str(e).lower():
            logger.warning(f"Intento de crear equipo duplicado: ID={equipo_data.EquipoId}")
            raise ValueError(f"Ya existe un equipo con el ID {equipo_data.EquipoId}.")
        elif "FOREIGN KEY constraint" in str(e):
            logger.warning(f"Error de FK al crear equipo {equipo_data.EquipoId}")
            raise ValueError("Error de referencia: Verifique si el PoolId (si aplica) existe.")
        else:
            logger.error(f"Error de integridad no manejado al crear equipo: {e}", exc_info=True)
            raise
    except Exception as e:
        logger.error(f"Error inesperado al crear equipo {equipo_data.EquipoId}: {e}", exc_info=True)
        raise


# Configuración


def get_system_config(db: DatabaseConnector, key: str) -> str:
    """Obtiene el valor de una configuración del sistema."""
    query = "SELECT Valor FROM dbo.ConfiguracionSistema WHERE Clave = ?"
    row = db.ejecutar_consulta(query, (key,), es_select=True)
    return row[0]["Valor"] if row else None


def set_system_config(db: DatabaseConnector, key: str, value: str):
    """Actualiza el valor de una configuración."""
    query = """
        UPDATE dbo.ConfiguracionSistema
        SET Valor = ?, FechaActualizacion = GETDATE()
        WHERE Clave = ?
    """
    db.ejecutar_consulta(query, (str(value), key), es_select=False)


# --- Gestión de Mapeos ---


def get_all_mappings(db: DatabaseConnector) -> List[Dict]:
    """Obtiene todos los mapeos con el nombre del robot interno asociado."""
    query = """
        SELECT m.*, r.Robot as RobotNombre
        FROM dbo.MapeoRobots m
        LEFT JOIN dbo.Robots r ON m.RobotId = r.RobotId
        ORDER BY m.Proveedor, m.NombreExterno
    """
    return db.ejecutar_consulta(query, es_select=True)


def create_mapping(db: DatabaseConnector, data: dict):
    query = """
        INSERT INTO dbo.MapeoRobots (Proveedor, NombreExterno, RobotId, Descripcion)
        VALUES (?, ?, ?, ?)
    """
    db.ejecutar_consulta(
        query, (data["Proveedor"], data["NombreExterno"], data["RobotId"], data.get("Descripcion")), es_select=False
    )


def delete_mapping(db: DatabaseConnector, mapeo_id: int):
    db.ejecutar_consulta("DELETE FROM dbo.MapeoRobots WHERE MapeoId = ?", (mapeo_id,), es_select=False)


# --- ANALÍTICA ---


def get_system_status(db: DatabaseConnector) -> Dict:
    """Obtiene el estado actual del sistema en tiempo real."""
    result = {}

    # Estado del balanceador
    query_balanceador = "SELECT * FROM dbo.EstadoBalanceadorTiempoReal"
    estado_balanceador = db.ejecutar_consulta(query_balanceador, es_select=True)
    result["balanceador"] = estado_balanceador[0] if estado_balanceador else {}

    # Ejecuciones activas
    query_ejecuciones = """
        SELECT
            COUNT(*) AS TotalActivas,
            COUNT(DISTINCT RobotId) AS RobotsActivos,
            COUNT(DISTINCT EquipoId) AS EquiposOcupados
        FROM dbo.EjecucionesActivas
    """
    ejecuciones = db.ejecutar_consulta(query_ejecuciones, es_select=True)
    result["ejecuciones"] = ejecuciones[0] if ejecuciones else {}

    # Robots - con distinción de programados
    # Usamos subconsultas para evitar el error de agregación sobre EXISTS
    query_robots = """
        SELECT
            COUNT(*) AS TotalRobots,
            SUM(CASE WHEN Activo = 1 THEN 1 ELSE 0 END) AS RobotsActivos,
            SUM(CASE WHEN EsOnline = 1 THEN 1 ELSE 0 END) AS RobotsOnline,
            SUM(CASE WHEN EsOnline = 0 THEN 1 ELSE 0 END) AS RobotsOffline,
            (
                SELECT COUNT(DISTINCT p.RobotId)
                FROM dbo.Programaciones p
                WHERE p.Activo = 1
            ) AS RobotsProgramados,
            SUM(CASE WHEN Activo = 1 AND EsOnline = 1 THEN 1 ELSE 0 END) AS RobotsActivosOnline,
            (
                SELECT COUNT(DISTINCT r2.RobotId)
                FROM dbo.Robots r2
                WHERE r2.Activo = 1
                    AND r2.EsOnline = 0
                    AND EXISTS (
                        SELECT 1 FROM dbo.Programaciones p2
                        WHERE p2.RobotId = r2.RobotId AND p2.Activo = 1
                    )
            ) AS RobotsActivosProgramados
        FROM dbo.Robots r
    """
    robots = db.ejecutar_consulta(query_robots, es_select=True)
    result["robots"] = robots[0] if robots else {}

    # Equipos
    query_equipos = """
        SELECT
            COUNT(*) AS TotalEquipos,
            SUM(CASE WHEN Activo_SAM = 1 THEN 1 ELSE 0 END) AS EquiposActivos,
            SUM(CASE WHEN PermiteBalanceoDinamico = 1 THEN 1 ELSE 0 END) AS EquiposBalanceables
        FROM dbo.Equipos
    """
    equipos = db.ejecutar_consulta(query_equipos, es_select=True)
    result["equipos"] = equipos[0] if equipos else {}

    return result


def ejecutar_sp_multiple_result_sets(db: DatabaseConnector, sp_name: str, params: Dict[str, Any]) -> List[List[Dict]]:
    """
    Ejecuta un stored procedure que retorna múltiples result sets.
    Retorna una lista de listas, donde cada lista interna es un result set.

    Nota: Los parámetros se pasan con nombres (@ParamName = ?) para mayor claridad.
    """
    try:
        with db.obtener_cursor() as cursor:
            # Construir la llamada al SP con parámetros nombrados
            param_placeholders = []
            param_values = []

            for key, value in params.items():
                # Solo incluir parámetros que no son None (el SP usa sus defaults)
                if value is not None:
                    param_placeholders.append(f"@{key} = ?")
                    # Convertir booleanos a int para parámetros BIT de SQL Server
                    if isinstance(value, bool):
                        param_values.append(1 if value else 0)
                    else:
                        param_values.append(value)

            # Si no hay parámetros, llamar sin ellos
            if param_placeholders:
                sp_call = f"{{CALL {sp_name}({', '.join(param_placeholders)})}}"
                cursor.execute(sp_call, *param_values)
            else:
                sp_call = f"{{CALL {sp_name}}}"
                cursor.execute(sp_call)

            # Recoger todos los result sets
            result_sets = []
            while True:
                try:
                    if cursor.description:
                        columns = [column[0] for column in cursor.description]
                        rows = cursor.fetchall()
                        result_set = [dict(zip(columns, row)) for row in rows]
                        result_sets.append(result_set)
                    else:
                        # Result set sin columnas (puede ser un mensaje o resultado vacío)
                        result_sets.append([])

                    # Intentar obtener el siguiente result set
                    if not cursor.nextset():
                        break
                except (pyodbc.ProgrammingError, AttributeError):
                    # No hay más result sets o cursor no tiene nextset
                    break

            return result_sets
    except Exception as e:
        logger.error(f"Error ejecutando SP {sp_name}: {e}", exc_info=True)
        raise


def get_callbacks_dashboard(
    db: DatabaseConnector,
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
    robot_id: Optional[int] = None,
    incluir_detalle_horario: bool = True,
) -> Dict:
    """Obtiene el dashboard de análisis de callbacks."""
    # El SP espera parámetros nombrados, todos opcionales
    # Pasamos todos los parámetros, incluso si son None (el SP maneja los defaults)
    params = {
        "FechaInicio": fecha_inicio,
        "FechaFin": fecha_fin,
        "RobotId": robot_id,
        "IncluirDetalleHorario": incluir_detalle_horario,  # Se convertirá a BIT en ejecutar_sp_multiple_result_sets
    }

    result_sets = ejecutar_sp_multiple_result_sets(db, "dbo.ObtenerDashboardCallbacks", params)

    return {
        "metricas_generales": result_sets[0][0] if result_sets and len(result_sets) > 0 and result_sets[0] else {},
        "rendimiento_distribucion": result_sets[1] if len(result_sets) > 1 else [],
        "analisis_por_robot": result_sets[2] if len(result_sets) > 2 else [],
        "tendencia_diaria": result_sets[3] if len(result_sets) > 3 else [],
        "patron_horario": result_sets[4] if len(result_sets) > 4 and incluir_detalle_horario else [],
        "casos_problematicos": result_sets[5] if len(result_sets) > 5 else [],
    }


def get_balanceador_dashboard(
    db: DatabaseConnector,
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
    pool_id: Optional[int] = None,
) -> Dict:
    """Obtiene el dashboard de análisis del balanceador."""
    params = {}
    if fecha_inicio:
        params["FechaInicio"] = fecha_inicio
    if fecha_fin:
        params["FechaFin"] = fecha_fin
    if pool_id:
        params["PoolId"] = pool_id

    result_sets = ejecutar_sp_multiple_result_sets(db, "dbo.ObtenerDashboardBalanceador", params)

    return {
        "metricas_generales": result_sets[0][0] if result_sets and len(result_sets) > 0 and result_sets[0] else {},
        "trazabilidad": result_sets[1] if len(result_sets) > 1 else [],
        "resumen_diario": result_sets[2] if len(result_sets) > 2 else [],
        "analisis_robots": result_sets[3] if len(result_sets) > 3 else [],
        "estado_actual": result_sets[4][0] if len(result_sets) > 4 and result_sets[4] else {},
        "thrashing_events": result_sets[5][0] if len(result_sets) > 5 and result_sets[5] else {},
    }


# --- LÓGICA CORE DE RESOLUCIÓN ---


def resolver_robot_id(db: DatabaseConnector, nombre_externo: str, proveedor: str = "A360") -> Optional[int]:
    """
    Lógica de Resolución Inteligente:
    1. Busca coincidencia exacta en la tabla Robots (nombre interno == nombre externo).
    2. Si falla, busca en la tabla MapeoRobots usando el proveedor.
    3. Retorna RobotId o None.
    """
    # 1. Intento Directo
    row = db.ejecutar_consulta("SELECT RobotId FROM dbo.Robots WHERE Robot = ?", (nombre_externo,), es_select=True)
    if row:
        return row[0]["RobotId"]

    # 2. Intento por Mapeo
    row_map = db.ejecutar_consulta(
        "SELECT RobotId FROM dbo.MapeoRobots WHERE NombreExterno = ? AND Proveedor = ?",
        (nombre_externo, proveedor),
        es_select=True,
    )
    if row_map:
        return row_map[0]["RobotId"]

    return None
