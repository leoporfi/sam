# Agrega estas importaciones al inicio del archivo database.py
import asyncio
import logging
from typing import Dict, List, Optional

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.database import DatabaseConnector
from sam.common.sincronizador_comun import SincronizadorComun

from .schemas import EquipoCreateRequest, RobotCreateRequest, RobotUpdateRequest, ScheduleData

logger = logging.getLogger(__name__)


# Sincronización con A360
async def sync_with_a360(db: DatabaseConnector, aa_client: AutomationAnywhereClient) -> Dict:
    """
    Orquesta la sincronización de las tablas Robots y Equipos con A360
    utilizando el nuevo componente centralizado.
    """
    logger.info("Iniciando la sincronización con A360 desde el servicio WEB...")
    try:
        # El cliente aa_client ya viene creado e inyectado
        sincronizador = SincronizadorComun(db_connector=db, aa_client=aa_client)
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

        db.merge_robots(robots_api)

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

        equipos_finales = sincronizador._procesar_y_mapear_equipos(devices_api, users_api)
        db.merge_equipos(equipos_finales)

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
        )
        SELECT E.EquipoId, E.Equipo
        FROM dbo.Equipos E
        WHERE E.Activo_SAM = 1
          AND E.Licencia IN ('ATTENDEDRUNTIME', 'RUNTIME')
          AND E.EquipoId NOT IN (SELECT EquipoId FROM EquiposReservados)
          AND E.EquipoId NOT IN (SELECT EquipoId FROM EquiposYaAsignados)
        ORDER BY E.Equipo
    """
    return db.ejecutar_consulta(query, (robot_id,), es_select=True)


def get_devices(
    db: DatabaseConnector,
    name: Optional[str] = None,
    active: Optional[bool] = None,
    balanceable: Optional[bool] = None,
    page: int = 1,
    size: int = 20,
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
    # RFR-25: Se implementa la función para llamar al SP unificado.
    robot_nombre_result = db.ejecutar_consulta(
        "SELECT Robot FROM dbo.Robots WHERE RobotId = ?", (data.RobotId,), es_select=True
    )
    if not robot_nombre_result:
        raise ValueError(f"No se encontró un robot con el ID {data.RobotId}")
    robot_str = robot_nombre_result[0]["Robot"]

    equipos_str = ""
    if data.Equipos:
        placeholders = ",".join("?" for _ in data.Equipos)
        equipos_nombres_result = db.ejecutar_consulta(
            f"SELECT STRING_AGG(Equipo, ',') AS Nombres FROM dbo.Equipos WHERE EquipoId IN ({placeholders})",
            tuple(data.Equipos),
            es_select=True,
        )
        if equipos_nombres_result and equipos_nombres_result[0]["Nombres"]:
            equipos_str = equipos_nombres_result[0]["Nombres"]

    query = "EXEC dbo.CrearProgramacion @Robot=?, @Equipos=?, @TipoProgramacion=?, @HoraInicio=?, @Tolerancia=?, @DiasSemana=?, @DiaDelMes=?, @FechaEspecifica=?"
    params = (
        robot_str,
        equipos_str,
        data.TipoProgramacion,
        data.HoraInicio,
        data.Tolerancia,
        data.DiasSemana,
        data.DiaDelMes,
        data.FechaEspecifica,
    )
    db.ejecutar_consulta(query, params, es_select=False)


def update_schedule(db: DatabaseConnector, schedule_id: int, data: ScheduleData):
    # RFR-25: Se implementa la función para llamar al SP de actualización.
    equipos_str = ""
    if data.Equipos:
        placeholders = ",".join("?" for _ in data.Equipos)
        equipos_nombres_result = db.ejecutar_consulta(
            f"SELECT STRING_AGG(Equipo, ',') AS Nombres FROM dbo.Equipos WHERE EquipoId IN ({placeholders})",
            tuple(data.Equipos),
            es_select=True,
        )
        if equipos_nombres_result and equipos_nombres_result[0]["Nombres"]:
            equipos_str = equipos_nombres_result[0]["Nombres"]

    query = "EXEC dbo.ActualizarProgramacionCompleta @ProgramacionId=?, @RobotId=?, @TipoProgramacion=?, @HoraInicio=?, @DiaSemana=?, @DiaDelMes=?, @FechaEspecifica=?, @Tolerancia=?, @Equipos=?"
    params = (
        schedule_id,
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
    except pyodbc.IntegrityError as e:
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
