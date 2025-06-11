# interfaz_web/service/main.py

import asyncio
from datetime import date
from functools import partial

import reactpy
from reactpy import component, html, use_effect, use_state

# Importar los módulos comunes de SAM
from common.database.sql_client import DatabaseConnector
from common.utils.config_manager import ConfigManager

# --- Conexión a la Base de Datos ---
try:
    cfg_sql_sam = ConfigManager.get_sql_server_config("SQL_SAM")
    db = DatabaseConnector(
        servidor=cfg_sql_sam["server"], base_datos=cfg_sql_sam["database"], usuario=cfg_sql_sam["uid"], contrasena=cfg_sql_sam["pwd"]
    )
    print("INFO: Conexión a la base de datos SAM establecida para la interfaz web.")
except Exception as e:
    db = None
    print(f"ERROR CRÍTICO: No se pudo conectar a la base de datos SAM: {e}")


# --- Componente del Formulario de Edición (Modal) ---
@component
def RobotEditForm(robot, on_save, on_cancel):
    form_data, set_form_data = use_state(robot)

    def handle_change(event):
        set_form_data(lambda old: {**old, event["target"]["name"]: event["target"]["value"]})

    async def handle_submit(event):
        await on_save(form_data)

    return html.div(
        {"class_name": "modal-overlay"},
        html.div(
            {"class_name": "modal-content"},
            html.h2(f"Editando Robot: {robot['Robot']}"),
            html.div(
                {"class_name": "form-group"},
                html.label("Prioridad Balanceo:"),
                html.input({"type": "number", "name": "PrioridadBalanceo", "value": form_data["PrioridadBalanceo"], "on_change": handle_change}),
            ),
            html.div(
                {"class_name": "form-group"},
                html.label("Min Equipos:"),
                html.input({"type": "number", "name": "MinEquipos", "value": form_data["MinEquipos"], "on_change": handle_change}),
            ),
            html.div(
                {"class_name": "form-group"},
                html.label("Max Equipos (-1 para ilimitado):"),
                html.input({"type": "number", "name": "MaxEquipos", "value": form_data["MaxEquipos"], "on_change": handle_change}),
            ),
            html.div(
                {"class_name": "form-group"},
                html.label("Tickets por Equipo Adicional:"),
                html.input(
                    {
                        "type": "number",
                        "name": "TicketsPorEquipoAdicional",
                        "value": form_data["TicketsPorEquipoAdicional"] or "",
                        "on_change": handle_change,
                    }
                ),
            ),
            html.div(
                {"class_name": "modal-actions"},
                html.button({"on_click": handle_submit, "class_name": "btn-accion"}, "Guardar Cambios"),
                html.button({"on_click": on_cancel}, "Cancelar"),
            ),
        ),
    )


# --- Componente para Crear Programaciones ---
@component
def ScheduleCreateForm(robot, equipos_disponibles, on_save, on_cancel):
    initial_form_data = {
        "tipo": "Diaria",
        "hora_inicio": "09:00:00",
        "equipo_id": equipos_disponibles[0]["EquipoId"] if equipos_disponibles else "",
        "dias_semana": "LU,MA,MI,JU,VI",
        "dia_mes": 1,
        "fecha_especifica": date.today().isoformat(),
    }
    form_data, set_form_data = use_state(initial_form_data)

    def handle_change(event):
        set_form_data(lambda old: {**old, event["target"]["name"]: event["target"]["value"]})

    async def handle_submit(event):
        await on_save(robot, form_data)

    dynamic_fields = []
    if form_data["tipo"] == "Semanal":
        dynamic_fields.append(
            html.div(
                {"class_name": "form-group", "key": "dias"},
                html.label("Días Semana (LU,MA,MI...):"),
                html.input({"type": "text", "name": "dias_semana", "value": form_data["dias_semana"], "on_change": handle_change}),
            )
        )
    elif form_data["tipo"] == "Mensual":
        dynamic_fields.append(
            html.div(
                {"class_name": "form-group", "key": "dia_mes"},
                html.label("Día del Mes:"),
                html.input({"type": "number", "name": "dia_mes", "value": form_data["dia_mes"], "on_change": handle_change}),
            )
        )
    elif form_data["tipo"] == "Especifica":
        dynamic_fields.append(
            html.div(
                {"class_name": "form-group", "key": "fecha"},
                html.label("Fecha Específica:"),
                html.input({"type": "date", "name": "fecha_especifica", "value": form_data["fecha_especifica"], "on_change": handle_change}),
            )
        )

    return html.div(
        {"class_name": "modal-overlay"},
        html.div(
            {"class_name": "modal-content"},
            html.h2(f"Programar Robot: {robot['Robot']}"),
            html.div(
                {"class_name": "form-group"},
                html.label("Tipo de Programación:"),
                html.select(
                    {"name": "tipo", "value": form_data["tipo"], "on_change": handle_change},
                    html.option({"value": "Diaria"}, "Diaria"),
                    html.option({"value": "Semanal"}, "Semanal"),
                    html.option({"value": "Mensual"}, "Mensual"),
                    html.option({"value": "Especifica"}, "Específica"),
                ),
            ),
            html.div(
                {"class_name": "form-group"},
                html.label("Equipo Exclusivo:"),
                html.select(
                    {"name": "equipo_id", "value": form_data["equipo_id"], "on_change": handle_change},
                    [html.option({"value": eq["EquipoId"]}, eq["Equipo"]) for eq in equipos_disponibles]
                    if equipos_disponibles
                    else html.option("No hay equipos disponibles"),
                ),
            ),
            html.div(
                {"class_name": "form-group"},
                html.label("Hora Inicio (HH:MM:SS):"),
                html.input({"type": "text", "name": "hora_inicio", "value": form_data["hora_inicio"], "on_change": handle_change}),
            ),
            *dynamic_fields,
            html.div(
                {"class_name": "modal-actions"},
                html.button({"on_click": handle_submit, "class_name": "btn-accion"}, "Guardar Programación"),
                html.button({"on_click": on_cancel}, "Cancelar"),
            ),
        ),
    )


# --- Componente Principal de la Aplicación ---
@component
def App():
    robots, set_robots = use_state([])
    robot_en_edicion, set_robot_en_edicion = use_state(None)
    robot_para_programar, set_robot_para_programar = use_state(None)
    equipos_disponibles, set_equipos_disponibles = use_state([])
    search_term, set_search_term = use_state("")

    async def fetch_robots(event=None):
        if not db:
            return
        query = "SELECT RobotId, Robot, Activo, EsOnline, PrioridadBalanceo, MinEquipos, MaxEquipos, TicketsPorEquipoAdicional FROM dbo.Robots ORDER BY Robot"
        data = db.ejecutar_consulta(query, es_select=True)
        set_robots(data or [])

    use_effect(fetch_robots, [])

    async def handle_toggle(robot_id, field_to_toggle, event=None):
        if not db:
            return
        robot_actual = next((r for r in robots if r["RobotId"] == robot_id), None)
        if not robot_actual:
            return
        nuevo_estado = not robot_actual[field_to_toggle]
        query = f"UPDATE dbo.Robots SET {field_to_toggle} = ? WHERE RobotId = ?"
        db.ejecutar_consulta(query, (nuevo_estado, robot_id))
        await fetch_robots()

    async def handle_save_robot(updated_robot_data, event=None):
        if not db:
            return
        query = "UPDATE dbo.Robots SET PrioridadBalanceo = ?, MinEquipos = ?, MaxEquipos = ?, TicketsPorEquipoAdicional = ? WHERE RobotId = ?"
        params = (
            updated_robot_data["PrioridadBalanceo"],
            updated_robot_data["MinEquipos"],
            updated_robot_data["MaxEquipos"],
            updated_robot_data.get("TicketsPorEquipoAdicional") or None,
            updated_robot_data["RobotId"],
        )
        db.ejecutar_consulta(query, params)
        set_robot_en_edicion(None)
        await fetch_robots()

    async def handle_open_schedule_form(robot_para_agendar, event=None):
        if not db:
            return
        query = "SELECT EquipoId, Equipo FROM dbo.Equipos WHERE Activo_SAM = 1 AND EquipoId NOT IN (SELECT EquipoId FROM dbo.Asignaciones WHERE Reservado = 1 OR EsProgramado = 1)"
        equipos = db.ejecutar_consulta(query, es_select=True)
        set_equipos_disponibles(equipos or [])
        set_robot_para_programar(robot_para_agendar)

    async def handle_save_schedule(robot, schedule_form_data, event=None):
        if not db:
            return
        equipo_id_seleccionado = int(schedule_form_data["equipo_id"])
        equipo_seleccionado_obj = next((eq for eq in equipos_disponibles if eq["EquipoId"] == equipo_id_seleccionado), None)
        if not equipo_seleccionado_obj:
            return
        nombre_del_equipo_seleccionado = equipo_seleccionado_obj["Equipo"]
        conn = None
        try:
            conn = db.conectar_base_datos()
            cursor = conn.cursor()
            sp_name = f"dbo.CargarProgramacion{schedule_form_data['tipo']}"
            params = {"@Robot": robot["Robot"], "@Equipos": nombre_del_equipo_seleccionado}
            if schedule_form_data["tipo"] == "Diaria":
                params["@HorasInicio"] = schedule_form_data["hora_inicio"]
            elif schedule_form_data["tipo"] == "Semanal":
                params["@DiasSemana"] = schedule_form_data["dias_semana"]
                params["@HorasInicio"] = schedule_form_data["hora_inicio"]
            elif schedule_form_data["tipo"] == "Mensual":
                params["@DiaDelMes"] = schedule_form_data["dia_mes"]
                params["@HoraInicio"] = schedule_form_data["hora_inicio"]
            elif schedule_form_data["tipo"] == "Especifica":
                params["@FechasEspecificas"] = schedule_form_data["fecha_especifica"]
                params["@HorasInicio"] = schedule_form_data["hora_inicio"]
            param_placeholders = ", ".join([f"{k} = ?" for k in params])
            query_sp = f"EXEC {sp_name} {param_placeholders}"
            cursor.execute(query_sp, tuple(params.values()))
            cursor.execute("UPDATE dbo.Robots SET EsOnline = 0 WHERE RobotId = ?", (robot["RobotId"],))
            cursor.execute("UPDATE dbo.Equipos SET PermiteBalanceoDinamico = 0 WHERE EquipoId = ?", (equipo_id_seleccionado,))
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"UI Error: Falló la transacción de programación. Se revirtieron los cambios. Error: {e}")
        finally:
            if conn:
                conn.close()
            set_robot_para_programar(None)
            await fetch_robots()

    if not db:
        return html.div(html.h1("Error de Conexión"), html.p("No se pudo establecer la conexión con la base de datos SAM."))

    # Filtrar robots basado en el término de búsqueda
    if search_term:
        filtered_robots = [r for r in robots if search_term.lower() in r['Robot'].lower()]
    else:
        filtered_robots = robots

    table_rows = []
    for robot in filtered_robots:
        table_rows.append(
            html.tr(
                {"key": robot["RobotId"]},
                html.td(robot["Robot"]),
                html.td(
                    html.button(
                        {
                            "on_click": partial(handle_toggle, robot["RobotId"], "Activo"),
                            "class_name": f"btn-{'activo' if robot['Activo'] else 'inactivo'}",
                        },
                        "Sí" if robot["Activo"] else "No",
                    )
                ),
                html.td(
                    html.button(
                        {
                            "on_click": partial(handle_toggle, robot["RobotId"], "EsOnline"),
                            "class_name": f"btn-{'activo' if robot['EsOnline'] else 'inactivo'}",
                        },
                        "Sí" if robot["EsOnline"] else "No",
                    )
                ),
                html.td(robot["PrioridadBalanceo"]),
                html.td(
                    html.button({"on_click": partial(handle_open_schedule_form, robot), "class_name": "btn-accion"}, "Programar"),
                    # <<< --- INICIO DE LA CORRECCIÓN --- >>>
                    # Usamos lambda para llamar a la función de estado con un solo argumento.
                    html.button({"on_click": lambda event, r=robot: set_robot_en_edicion(r), "class_name": "btn-accion-secundario"}, "Editar"),
                    # <<< --- FIN DE LA CORRECCIÓN --- >>>
                ),
            )
        )

    return html.div(
        {"class_name": "container"},
        html.link({"rel": "stylesheet", "href": "/static/style.css"}),
        html.h1("Panel de Mantenimiento SAM - Gestión de Robots"),
        html.input({
            "type": "text",
            "placeholder": "Buscar robot...",
            "value": search_term,
            "on_change": lambda event: set_search_term(event["target"]["value"]),
            "class_name": "search-input"
        }),
        html.button({"on_click": fetch_robots}, "Refrescar Datos"),
        html.table(
            {"class_name": "sam-table"},
            html.thead(html.tr(html.th("Robot"), html.th("Activo"), html.th("Es Online"), html.th("Prioridad"), html.th("Acciones"))),
            html.tbody(table_rows),
        ),
        # <<< --- INICIO DE LA CORRECCIÓN --- >>>
        # Aquí también usamos lambda para los botones de "Cancelar" de los modales.
        robot_en_edicion and RobotEditForm(robot=robot_en_edicion, on_save=handle_save_robot, on_cancel=lambda event: set_robot_en_edicion(None)),
        robot_para_programar
        and ScheduleCreateForm(
            robot=robot_para_programar,
            equipos_disponibles=equipos_disponibles,
            on_save=handle_save_schedule,
            on_cancel=lambda event: set_robot_para_programar(None),
        ),
        # <<< --- FIN DE LA CORRECCIÓN --- >>>
    )
