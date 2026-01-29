# web/backend/database.py
import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.config_manager import ConfigManager
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


def log_audit(
    db: DatabaseConnector,
    accion: str,
    entidad: str,
    entidad_id: str,
    detalle: str,
    host: str,
    usuario: str = "WebApp",
):
    """Registra una acción en la tabla de auditoría."""
    try:
        query = "EXEC dbo.RegistrarAuditoria @Accion=?, @Entidad=?, @EntidadId=?, @Detalle=?, @Host=?, @Usuario=?"
        params = (accion, entidad, entidad_id, detalle, host, usuario)
        db.ejecutar_consulta(query, params, es_select=False)
    except Exception as e:
        logger.error(f"Error al registrar auditoría: {e}", exc_info=True)


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
        # Ejecutar tareas en paralelo pero manejar excepciones individualmente
        results = await asyncio.gather(devices_task, users_task, return_exceptions=True)

        devices_api = results[0]
        users_api = results[1]

        # Verificar si devices falló (crítico)
        if isinstance(devices_api, Exception):
            raise devices_api

        # Verificar si users falló (no crítico, loguear warning)
        if isinstance(users_api, Exception):
            logger.warning(f"No se pudieron obtener usuarios de A360 (posible falta de permisos): {users_api}")
            users_api = []

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


def get_sync_status(db: DatabaseConnector) -> Dict:
    """
    Obtiene el estado de la última sincronización de robots/equipos.
    """
    # Por ahora retornamos None ya que no hay una columna de timestamp global
    # en las tablas de Robots/Equipos.
    return {"last_sync": None}


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
    """
    Obtiene lista de robots paginada usando SP.
    """
    try:
        # Construimos la llamada EXEC con parámetros nombrados para seguridad y claridad
        query = "EXEC dbo.ObtenerRobotsPaginado @Nombre=?, @Activo=?, @Online=?, @Programado=?, @Page=?, @Size=?, @SortBy=?, @SortDir=?"
        query_params = (name, active, online, programado, page, size, sort_by, sort_dir)

        robots_data = db.ejecutar_consulta(query, query_params, es_select=True)

        total_count = 0
        if robots_data:
            total_count = robots_data[0].get("TotalCount", 0)
            # Limpiamos la columna extra si no se quiere enviar al front (opcional)
            for r in robots_data:
                r.pop("TotalCount", None)

        return {"total_count": total_count, "page": page, "size": size, "robots": robots_data}

    except Exception as e:
        logger.error(f"Error en get_robots: {e}", exc_info=True)
        raise


def update_robot_status(db: DatabaseConnector, robot_id: int, field: str, value: bool) -> bool:
    """
    Actualiza el estado de un robot (Activo o EsOnline) usando SP.
    """
    try:
        query = "EXEC dbo.ActualizarRobotEstado @RobotId=?, @Campo=?, @Valor=?"
        params = (str(robot_id), field, value)
        rows = db.ejecutar_consulta(query, params, es_select=False)
        return rows > 0
    except ValueError as ve:
        # Relanzar errores de validación de negocio del SP
        raise ve
    except Exception as e:
        logger.error(f"Error en update_robot_status: {e}", exc_info=True)
        raise


def update_robot_details(db: DatabaseConnector, robot_id: int, robot_data: RobotUpdateRequest) -> int:
    """
    Actualiza los detalles de un robot usando SP.
    """
    query = "EXEC dbo.ActualizarRobotDetalle @RobotId=?, @Robot=?, @Descripcion=?, @MinEquipos=?, @MaxEquipos=?, @PrioridadBalanceo=?, @TicketsPorEquipoAdicional=?, @Parametros=?"
    params = (
        str(robot_id),
        robot_data.Robot,
        robot_data.Descripcion,
        robot_data.MinEquipos,
        robot_data.MaxEquipos,
        robot_data.PrioridadBalanceo,
        robot_data.TicketsPorEquipoAdicional,
        robot_data.Parametros,
    )
    return db.ejecutar_consulta(query, params, es_select=False)


def create_robot(db: DatabaseConnector, robot_data: RobotCreateRequest) -> Dict:
    """
    Crea un nuevo robot usando SP.
    """
    query = "EXEC dbo.CrearRobot @RobotId=?, @Robot=?, @Descripcion=?, @MinEquipos=?, @MaxEquipos=?, @PrioridadBalanceo=?, @TicketsPorEquipoAdicional=?"
    params = (
        str(robot_data.RobotId),
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
        if "Violation of PRIMARY KEY constraint" in str(e) or "El RobotId ya existe" in str(e):
            raise ValueError(f"El RobotId {robot_data.RobotId} ya existe.")
        raise


# Asignaciones
def get_asignaciones_by_robot(db: DatabaseConnector, robot_id: int) -> List[Dict]:
    """Obtiene las asignaciones de un robot usando SP."""
    query = "EXEC dbo.ListarAsignacionesPorRobot @RobotId = ?"
    return db.ejecutar_consulta(query, (robot_id,), es_select=True)


def update_asignaciones_robot(
    db: DatabaseConnector, robot_id: int, assign_ids: List[int], unassign_ids: List[int]
) -> Dict:
    """
    Actualiza las asignaciones de un robot usando SP con TVPs.
    """
    try:
        # Preparar TVPs
        assign_tvp = [(eid,) for eid in assign_ids]
        unassign_tvp = [(eid,) for eid in unassign_ids]

        params = {
            "RobotId": str(robot_id),
            "AssignIds": assign_tvp,
            "UnassignIds": unassign_tvp,
            "AsignadoPor": "WebApp",
        }

        db.ejecutar_sp_con_tvp("dbo.ActualizarAsignacionesRobot", params)
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
    Obtiene los equipos disponibles para un robot usando SP.
    """
    query = "EXEC dbo.ListarEquiposDisponiblesParaRobot @RobotId = ?"
    return db.ejecutar_consulta(query, (str(robot_id),), es_select=True)


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
    robot_info = db.ejecutar_consulta("EXEC dbo.ObtenerRobotPorId @RobotId = ?", (str(data.RobotId),), es_select=True)
    if not robot_info:
        raise ValueError(f"No se encontró un robot con el ID {data.RobotId}")
    robot_str = robot_info[0]["Robot"]

    equipos_str = ""
    if data.Equipos:
        equipos_ids_tvp = [(eid,) for eid in data.Equipos]
        equipos_nombres_result = db.ejecutar_sp_con_tvp(
            "dbo.ObtenerNombresEquipos", {"EquiposIds": equipos_ids_tvp}, es_select=True
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
    """
    Cambia el estado activo de una programación usando SP.
    """
    query = "EXEC dbo.ActualizarEstadoProgramacion @ProgramacionId=?, @Activo=?"
    db.ejecutar_consulta(query, (schedule_id, activo), es_select=False)


def get_schedule_devices_data(db: DatabaseConnector, schedule_id: int) -> Dict[str, List[Dict]]:
    """
    Obtiene los equipos asignados a una programación específica y los disponibles.
    Usa SP dbo.ObtenerEquiposParaProgramacion.
    """
    try:
        # Usamos ejecutar_sp_multiple_result_sets que espera un dict de params
        params = {"ProgramacionId": schedule_id}
        result_sets = ejecutar_sp_multiple_result_sets(db, "dbo.ObtenerEquiposParaProgramacion", params)

        assigned = result_sets[0] if len(result_sets) > 0 else []
        available = result_sets[1] if len(result_sets) > 1 else []

        return {"assigned": assigned, "available": available}

    except Exception as e:
        logger.error(f"Error en get_schedule_devices_data: {e}", exc_info=True)
        raise


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
    Inserta un nuevo equipo manualmente en la base de datos usando SP.
    """
    logger.info(f"Intentando crear equipo manualmente: ID={equipo_data.EquipoId}, Nombre={equipo_data.Equipo}")
    try:
        query = "EXEC dbo.CrearEquipoManual @EquipoId=?, @Equipo=?, @UserId=?, @UserName=?, @Licencia=?"
        params = (
            equipo_data.EquipoId,
            equipo_data.Equipo,
            equipo_data.UserId,
            equipo_data.UserName,
            equipo_data.Licencia,
        )
        new_equipo_list = db.ejecutar_consulta(query, params, es_select=True)
        if not new_equipo_list:
            raise Exception("La inserción no devolvió el nuevo equipo.")
        logger.info(f"Equipo {equipo_data.EquipoId} creado exitosamente.")
        return new_equipo_list[0]
    except Exception as e:
        if "Violation of PRIMARY KEY constraint" in str(e) or "El EquipoId ya existe" in str(e):
            logger.warning(f"Intento de crear equipo duplicado: ID={equipo_data.EquipoId}")
            raise ValueError(f"Ya existe un equipo con el ID {equipo_data.EquipoId}.")
        elif "FOREIGN KEY constraint" in str(e):
            logger.warning(f"Error de FK al crear equipo {equipo_data.EquipoId}")
            raise ValueError("Error de referencia: Verifique si el PoolId (si aplica) existe.")
        else:
            logger.error(f"Error al crear equipo {equipo_data.EquipoId}: {e}", exc_info=True)
            raise


# Configuración


def get_system_config(db: DatabaseConnector, key: str) -> str:
    """Obtiene el valor de una configuración del sistema usando SP."""
    query = "EXEC dbo.ObtenerConfiguracion @Clave = ?"
    row = db.ejecutar_consulta(query, (key,), es_select=True)
    return row[0]["Valor"] if row else None


def set_system_config(db: DatabaseConnector, key: str, value: str):
    """Actualiza el valor de una configuración usando SP."""
    query = "EXEC dbo.ActualizarConfiguracion @Clave = ?, @Valor = ?"
    db.ejecutar_consulta(query, (key, str(value)), es_select=False)


def get_all_configs(db: DatabaseConnector) -> List[Dict]:
    """Obtiene todas las configuraciones del sistema usando SP."""
    query = "EXEC dbo.ListarConfiguraciones"
    return db.ejecutar_consulta(query, es_select=True)


# --- Gestión de Mapeos ---


def get_all_mappings(db: DatabaseConnector) -> List[Dict]:
    """Obtiene todos los mapeos usando SP."""
    return db.ejecutar_consulta("EXEC dbo.ListarMapeos", es_select=True)


def create_mapping(db: DatabaseConnector, data: dict):
    """Crea un nuevo mapeo usando SP."""
    query = "EXEC dbo.CrearMapeo @Proveedor=?, @NombreExterno=?, @RobotId=?, @Descripcion=?"
    db.ejecutar_consulta(
        query, (data["Proveedor"], data["NombreExterno"], data["RobotId"], data.get("Descripcion")), es_select=False
    )


def delete_mapping(db: DatabaseConnector, mapeo_id: int):
    """Elimina un mapeo usando SP."""
    db.ejecutar_consulta("EXEC dbo.EliminarMapeo @MapeoId = ?", (mapeo_id,), es_select=False)


# --- ANALÍTICA ---


def get_system_status(db: DatabaseConnector) -> Dict:
    """Obtiene el estado actual del sistema en tiempo real usando SP optimizado."""
    try:
        # Usamos ejecutar_sp_multiple_result_sets que espera un dict de params
        # Aunque no tenga params, pasamos dict vacío
        result_sets = ejecutar_sp_multiple_result_sets(db, "dbo.ObtenerEstadoSistema", {})

        if not result_sets:
            return {}

        row = result_sets[0][0] if result_sets[0] else {}

        return {
            "ejecuciones": {
                "TotalActivas": row.get("EjecucionesActivas", 0),
                "RobotsActivos": row.get("RobotsEjecutando", 0),
                "EquiposEjecutando": row.get("EquiposEjecutando", 0),
            },
            "programaciones": {
                "ProgramacionesActivas": row.get("ProgramacionesActivas", 0),
            },
            "robots": {
                "TotalRobots": row.get("TotalRobots", 0),
                "RobotsActivos": row.get("RobotsActivos", 0),
                "RobotsOnline": row.get("RobotsOnline", 0),
                "RobotsProgramados": row.get("RobotsProgramados", 0),
            },
            "equipos": {
                "TotalEquipos": row.get("TotalEquipos", 0),
                "EquiposActivos": row.get("EquiposActivos", 0),
                "EquiposBalanceables": row.get("EquiposBalanceables", 0),
                "EquiposViale": row.get("EquiposViale", 0),
                "EquiposVelez": row.get("EquiposVelez", 0),
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        logger.error(f"Error en get_system_status: {e}", exc_info=True)
        return {}


def ejecutar_sp_multiple_result_sets(db: DatabaseConnector, sp_name: str, params: Dict[str, Any]) -> List[List[Dict]]:
    """
    Ejecuta un stored procedure que retorna múltiples result sets.
    Retorna una lista de listas, donde cada lista interna es un result set.

    Nota: Los parámetros se pasan con nombres (@ParamName = ?) para mayor claridad.
    """
    import pyodbc

    try:
        with db.obtener_cursor() as cursor:
            # Construir la llamada al SP con parámetros nombrados
            param_placeholders = []
            param_values = []

            for key, value in params.items():
                # Solo incluir parámetros que no son None (el SP usa sus defaults)
                # Esto evita problemas de tipo cuando pyodbc intenta inferir el tipo de None
                if value is not None:
                    param_placeholders.append(f"@{key} = ?")
                    # Convertir booleanos a int para parámetros BIT de SQL Server
                    if isinstance(value, bool):
                        param_values.append(1 if value else 0)
                    else:
                        param_values.append(value)

            # Construir la llamada al SP
            if param_placeholders:
                # Usar EXEC en lugar de CALL para mejor compatibilidad con parámetros nombrados
                sp_call = f"EXEC {sp_name} {', '.join(param_placeholders)}"
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
    # El SP espera parámetros en este orden: @FechaInicio, @FechaFin, @RobotId, @IncluirDetalleHorario
    # Pasamos todos los parámetros, incluso None, para mantener el orden correcto
    params = {
        "FechaInicio": fecha_inicio,
        "FechaFin": fecha_fin,
        "RobotId": robot_id,
        "IncluirDetalleHorario": incluir_detalle_horario,
    }

    result_sets = ejecutar_sp_multiple_result_sets(db, "dbo.Analisis_Callbacks", params)

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

    result_sets = ejecutar_sp_multiple_result_sets(db, "dbo.Analisis_Balanceador", params)

    return {
        "metricas_generales": result_sets[0][0] if result_sets and len(result_sets) > 0 and result_sets[0] else {},
        "trazabilidad": result_sets[1] if len(result_sets) > 1 else [],
        "resumen_diario": result_sets[2] if len(result_sets) > 2 else [],
        "analisis_robots": result_sets[3] if len(result_sets) > 3 else [],
        "estado_actual": result_sets[4][0] if len(result_sets) > 4 and result_sets[4] else {},
        "thrashing_events": result_sets[5][0] if len(result_sets) > 5 and result_sets[5] else {},
    }


def get_tiempos_ejecucion_dashboard(
    db: DatabaseConnector,
    excluir_porcentaje_inferior: Optional[float] = None,
    excluir_porcentaje_superior: Optional[float] = None,
    incluir_solo_completadas: bool = True,
    meses_hacia_atras: Optional[int] = None,
) -> List[Dict]:
    """
    Obtiene el dashboard de análisis de tiempos de ejecución por robot.

    Considera:
    - FechaInicioReal (inicio real reportado por A360) cuando está disponible
    - Número de repeticiones del robot (extraído de Parametros JSON)
    - Datos históricos (Ejecuciones_Historico)
    - Calcula tiempo por repetición (tiempo total / número de repeticiones)
    - Calcula latencia (delay entre disparo e inicio real)

    Args:
        excluir_porcentaje_inferior: Percentil inferior a excluir (default: 0.15)
        excluir_porcentaje_superior: Percentil superior a excluir (default: 0.85)
        incluir_solo_completadas: Solo ejecuciones completadas (default: True)
        meses_hacia_atras: Meses hacia atrás para el análisis (default: 1)

    Returns:
        Lista de diccionarios con métricas por robot
    """
    params = {}
    if excluir_porcentaje_inferior is not None:
        params["ExcluirPorcentajeInferior"] = excluir_porcentaje_inferior
    if excluir_porcentaje_superior is not None:
        params["ExcluirPorcentajeSuperior"] = excluir_porcentaje_superior
    if incluir_solo_completadas is not None:
        params["IncluirSoloCompletadas"] = incluir_solo_completadas
    if meses_hacia_atras is not None:
        params["MesesHaciaAtras"] = meses_hacia_atras

    # Obtener valor por defecto de repeticiones desde configuración
    try:
        cfg_lanzador = ConfigManager.get_lanzador_config()
        default_repeticiones = int(cfg_lanzador.get("repeticiones", 1))
    except Exception:
        default_repeticiones = 1

    params["DefaultRepeticiones"] = default_repeticiones

    result_sets = ejecutar_sp_multiple_result_sets(db, "dbo.Analisis_TiemposEjecucion", params)

    # El SP retorna un solo result set
    return result_sets[0] if result_sets and len(result_sets) > 0 else []


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


def get_recent_executions(
    db: DatabaseConnector,
    limit: int = 50,
    umbral_fijo_minutos: int = 25,
    factor_umbral_dinamico: float = 1.5,
    piso_umbral_dinamico_minutos: int = 10,
    filtro_ejecuciones_cortas_minutos: int = 2,
    robot_name: Optional[str] = None,
    equipo_name: Optional[str] = None,
    grouped: bool = False,
) -> Dict[str, List[Dict]]:
    """
    Obtiene las ejecuciones recientes usando SP.
    Retorna dos listas: fallos y demoras/huérfanas.
    """
    try:
        params = {
            "Limit": limit,
            "UmbralFijoMinutos": umbral_fijo_minutos,
            "FactorUmbralDinamico": factor_umbral_dinamico,
            "PisoUmbralDinamicoMinutos": piso_umbral_dinamico_minutos,
            "FiltroEjecucionesCortasMinutos": filtro_ejecuciones_cortas_minutos,
            "DefaultRepeticiones": int(ConfigManager.get_lanzador_config().get("repeticiones", 1)),
        }

        # Agregar filtros opcionales solo si tienen valor
        if robot_name:
            params["RobotName"] = robot_name
        if equipo_name:
            params["EquipoName"] = equipo_name

        # El SP retorna DOS result sets:
        # 0: Fallos
        # 1: Demoras y Huérfanas
        result_sets = ejecutar_sp_multiple_result_sets(db, "dbo.ObtenerEjecucionesRecientes", params)

        fallos = result_sets[0] if result_sets and len(result_sets) > 0 else []
        demoras = result_sets[1] if result_sets and len(result_sets) > 1 else []

        if grouped and fallos:
            # Agrupar fallos por Robot, Equipo, Estado, MensajeError, Origen
            grupos = defaultdict(
                lambda: {
                    "Robot": "",
                    "Equipo": "",
                    "Estado": "",
                    "MensajeError": "",
                    "Origen": "",
                    "Cantidad": 0,
                    "TiempoTotal": 0.0,
                    "FechaInicio": None,
                    "FechaUltima": None,
                }
            )

            for f in fallos:
                key = (f.get("Robot"), f.get("Equipo"), f.get("Estado"), f.get("MensajeError"), f.get("Origen"))
                g = grupos[key]
                if g["Cantidad"] == 0:
                    g["Robot"] = f.get("Robot")
                    g["Equipo"] = f.get("Equipo")
                    g["Estado"] = f.get("Estado")
                    g["MensajeError"] = f.get("MensajeError")
                    g["Origen"] = f.get("Origen")
                    g["FechaInicio"] = f.get("FechaInicio")
                    g["FechaUltima"] = f.get("FechaInicio")
                else:
                    # Actualizar fechas
                    fi = f.get("FechaInicio")
                    if fi:
                        if not g["FechaInicio"] or fi < g["FechaInicio"]:
                            g["FechaInicio"] = fi
                        if not g["FechaUltima"] or fi > g["FechaUltima"]:
                            g["FechaUltima"] = fi

                g["Cantidad"] += 1
                g["TiempoTotal"] += f.get("TiempoTranscurridoMinutos") or 0.0

            # Calcular promedios y limpiar
            fallos_agrupados = []
            for g in grupos.values():
                g["TiempoPromedio"] = g["TiempoTotal"] / g["Cantidad"] if g["Cantidad"] > 0 else 0
                g.pop("TiempoTotal")
                fallos_agrupados.append(g)

            # Ordenar por cantidad descendente
            fallos_agrupados.sort(key=lambda x: x["Cantidad"], reverse=True)
            fallos = fallos_agrupados

        return {"fallos": fallos, "demoras": demoras}

    except Exception as e:
        logger.error(f"Error obteniendo ejecuciones recientes: {e}", exc_info=True)
        return {"fallos": [], "demoras": []}


def get_utilization_analysis(
    db: DatabaseConnector,
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
) -> List[Dict]:
    """
    Obtiene el análisis de utilización de recursos.
    Llama al SP dbo.AnalisisUtilizacionRecursos.
    """
    params = {}
    if fecha_inicio:
        params["FechaInicio"] = fecha_inicio
    if fecha_fin:
        params["FechaFin"] = fecha_fin

    # El SP retorna un solo result set
    result_sets = ejecutar_sp_multiple_result_sets(db, "dbo.Analisis_UtilizacionRecursos", params)
    return result_sets[0] if result_sets and len(result_sets) > 0 else []


def get_temporal_patterns(
    db: DatabaseConnector,
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
    robot_id: Optional[int] = None,
) -> List[Dict]:
    """
    Obtiene el análisis de patrones temporales (heatmap).
    Llama al SP dbo.AnalisisPatronesTemporales.
    """
    params = {}
    if fecha_inicio:
        params["FechaInicio"] = fecha_inicio
    if fecha_fin:
        params["FechaFin"] = fecha_fin
    if robot_id:
        params["RobotId"] = robot_id

    # El SP retorna un solo result set
    result_sets = ejecutar_sp_multiple_result_sets(db, "dbo.Analisis_PatronesTemporales", params)
    return result_sets[0] if result_sets and len(result_sets) > 0 else []


def get_success_analysis(
    db: DatabaseConnector,
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
    robot_id: Optional[int] = None,
) -> Dict[str, List[Dict]]:
    """
    Obtiene el análisis de tasas de éxito y errores.
    Llama al SP dbo.AnalisisTasasExito.
    Retorna un diccionario con 3 listas: "resumen_estados", "top_errores", "detalle_robots".
    """
    params = {}
    if fecha_inicio:
        params["FechaInicio"] = fecha_inicio
    if fecha_fin:
        params["FechaFin"] = fecha_fin
    if robot_id:
        params["RobotId"] = robot_id

    # El SP retorna 3 result sets
    result_sets = ejecutar_sp_multiple_result_sets(db, "dbo.Analisis_TasasExito", params)

    if not result_sets or len(result_sets) < 3:
        return {
            "resumen_global": {"TotalEjecuciones": 0, "TotalFallidas": 0},
            "resumen_estados": [],
            "top_errores": [],
            "detalle_robots": [],
        }

    resumen_estados = result_sets[0]
    total_ejecuciones = sum(item.get("Cantidad", 0) for item in resumen_estados)
    total_fallidas = sum(
        item.get("Cantidad", 0)
        for item in resumen_estados
        if item.get("Estado") in ("RUN_FAILED", "DEPLOY_FAILED", "RUN_ABORTED")
    )

    return {
        "resumen_global": {
            "TotalEjecuciones": total_ejecuciones,
            "TotalFallidas": total_fallidas,
        },
        "resumen_estados": resumen_estados,
        "top_errores": result_sets[1],
        "detalle_robots": result_sets[2],
    }


def obtener_info_ejecucion(db: DatabaseConnector, deployment_id: str) -> Optional[Dict]:
    """
    Obtiene información detallada de una ejecución por su DeploymentId.
    """
    query = """
        SELECT EjecucionId, DeploymentId, RobotId, EquipoId, UserId, Estado, Hora
        FROM dbo.Ejecuciones
        WHERE DeploymentId = ?
    """
    try:
        results = db.ejecutar_consulta(query, (deployment_id,), es_select=True)
        return results[0] if results else None
    except Exception as e:
        logger.error(f"Error obteniendo info de ejecución {deployment_id}: {e}")
        return None


def mover_ejecucion_a_historico(db: DatabaseConnector, deployment_id: str, estado_final: str, mensaje: str) -> bool:
    """
    Actualiza el estado de una ejecución y registra un mensaje de error/log.
    En SAM, el movimiento a la tabla histórica suele ser automático tras alcanzar un estado final.
    """
    query = """
        UPDATE dbo.Ejecuciones
        SET Estado = ?,
            FechaFin = GETDATE(),
            FechaActualizacion = GETDATE(),
            CallbackInfo = ?
        WHERE DeploymentId = ?
    """
    try:
        # Usamos CallbackInfo para guardar el mensaje si no hay una columna MensajeError explícita
        # o si queremos que el sistema lo trate como procesado por callback.
        db.ejecutar_consulta(query, (estado_final, mensaje, deployment_id), es_select=False)
        logger.info(f"Ejecución {deployment_id} actualizada a {estado_final} en BD local.")
        return True
    except Exception as e:
        logger.error(f"Error actualizando ejecución {deployment_id} en BD: {e}")
        return False
