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

    async def handle_submit_form_data(event): # Renamed
        # on_save is the prop, which will be trigger_robot_edit_confirmation
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
                html.button({"on_click": handle_submit_form_data, "class_name": "btn-accion"}, "Guardar Cambios"), # Updated on_click
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

    async def handle_submit_form_data(event): # Renamed
        # on_save is the prop, which will be trigger_robot_schedule_confirmation
        # It expects (robot, form_data)
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
                html.button({"on_click": handle_submit_form_data, "class_name": "btn-accion"}, "Guardar Programación"), # Updated on_click
                html.button({"on_click": on_cancel}, "Cancelar"),
            ),
        ),
    )

# --- Componente de Confirmación Genérico ---
@component
def ConfirmationModal(message, on_confirm, on_cancel):
    return html.div(
        {"class_name": "modal-overlay"},
        html.div(
            {"class_name": "modal-content confirmation-modal"},
            html.h2({"class_name": "modal-title"}, "Confirmación"),
            html.p({"class_name": "modal-message"}, message),
            html.div(
                {"class_name": "modal-actions"},
                html.button({
                    "on_click": lambda event: asyncio.ensure_future(on_confirm()) if asyncio.iscoroutinefunction(on_confirm) else on_confirm(),
                    "class_name": "btn-accion btn-confirm"
                }, "Confirmar"),
                html.button({
                    "on_click": on_cancel,
                    "class_name": "btn-accion-secundario btn-cancel"
                }, "Cancelar"),
            ),
        ),
    )

# --- Componente de Feedback Genérico ---
@component
def FeedbackModal(message, message_type, on_dismiss):
    modal_content_class = f"modal-content feedback-modal feedback-modal-{message_type}"
    title_text = "Éxito" if message_type == "success" else "Error"
    title_class = f"modal-title feedback-title-{message_type}"

    return html.div(
        {"class_name": "modal-overlay"},
        html.div(
            {"class_name": modal_content_class},
            html.h2({"class_name": title_class}, title_text),
            html.p({"class_name": "modal-message"}, message),
            html.div(
                {"class_name": "modal-actions"},
                html.button({
                    "on_click": on_dismiss,
                    "class_name": "btn-accion"
                }, "OK"),
            ),
        ),
    )

@component
def AssignmentForm(robots, available_teams, on_save, on_cancel):
    selected_robot_id, set_selected_robot_id = use_state("") # Store RobotId
    selected_team_ids, set_selected_team_ids = use_state([]) # Store list of EquipoId

    def handle_robot_change(event):
        set_selected_robot_id(event["target"]["value"])

    def handle_team_selection_change(team_id, event): # event is passed by on_change via partial
        # Debug print removed
        # is_checked determination removed

        if team_id in selected_team_ids:
            # Team is currently selected, so this action unchecks it
            set_selected_team_ids(lambda old_ids: [tid for tid in old_ids if tid != team_id])
        else:
            # Team is not currently selected, so this action checks it
            # Adding new items and then sorting is good for consistency.
            set_selected_team_ids(lambda old_ids: sorted(old_ids + [team_id]))

    async def handle_submit(event):
        # Basic validation: ensure a robot is selected and at least one team
        if not selected_robot_id:
            # In a real app, show a message in the form itself. For now, just log or prevent save.
            print("AssignmentForm Validation: Robot no seleccionado.")
            # Optionally, trigger a feedback modal directly from here or let on_save handle it.
            # For now, on_save will handle feedback for empty selections.
            pass # Fall through to on_save which should validate.
        if not selected_team_ids:
            print("AssignmentForm Validation: Ningún equipo seleccionado.")
            pass

        await on_save(selected_robot_id, selected_team_ids)

    robot_options = [html.option({"value": ""}, "Seleccione un robot")] + [
        html.option({"value": r["RobotId"]}, r["Robot"]) for r in robots
    ]

    team_checkboxes = []
    if not available_teams:
        team_checkboxes.append(html.p("No hay equipos disponibles para asignación."))
    else:
        for team in available_teams:
            team_id = team["EquipoId"]
            is_checked = team_id in selected_team_ids
            team_checkboxes.append(
                html.div({"key": f"team-{team_id}", "class_name": "checkbox-item"},
                    html.input({
                        "type": "checkbox",
                        "id": f"team-checkbox-{team_id}",
                        "checked": is_checked,
                        "on_change": partial(handle_team_selection_change, team_id)
                    }),
                    html.label({"for": f"team-checkbox-{team_id}"}, f" {team['Equipo']}")
                )
            )

    return html.div(
        {"class_name": "modal-overlay"},
        html.div(
            {"class_name": "modal-content assignment-form-modal"}, # New class for specific styling
            html.h2({"class_name": "modal-title"}, "Asignar Robot a Equipos"),
            html.div(
                {"class_name": "form-group"},
                html.label({"for": "robot_select_assignment"}, "Seleccionar Robot:"),
                html.select({
                    "id": "robot_select_assignment",
                    "value": selected_robot_id,
                    "on_change": handle_robot_change,
                    "class_name": "form-control" # General form control class
                }, robot_options)
            ),
            html.div(
                {"class_name": "form-group"},
                html.label("Seleccionar Equipos Disponibles (Licencia: ATTENDEDRUNTIME, Activo_SAM: 1, No asignados):"),
                html.div({
                    "class_name": "teams-checkbox-list", # For styling the scrollable area
                    "style": {"max_height": "250px", "overflow_y": "auto", "border": "1px solid #ced4da", "padding": "10px", "border_radius": "4px"}
                }, team_checkboxes)
            ),
            html.div(
                {"class_name": "modal-actions"},
                html.button({"on_click": handle_submit, "class_name": "btn-accion"}, "Guardar Asignaciones"),
                html.button({"on_click": on_cancel, "class_name": "btn-accion-secundario"}, "Cancelar"),
            ),
        )
    )

# --- Componente Principal de la Aplicación ---
@component
def App():
    robots, set_robots = use_state([])
    robot_en_edicion, set_robot_en_edicion = use_state(None)
    robot_para_programar, set_robot_para_programar = use_state(None)
    equipos_disponibles, set_equipos_disponibles = use_state([])

    # State for Search
    search_term, set_search_term = use_state("")

    # State for Filters
    activo_filter, set_activo_filter = use_state("all") # "all", "true", "false"
    online_filter, set_online_filter = use_state("all") # "all", "true", "false"

    # State for Confirmation Modal
    show_confirmation, set_show_confirmation = use_state(False)
    confirmation_message, set_confirmation_message = use_state("")
    # Store a factory/getter for the coroutine func: lambda that returns the actual coroutine or None
    on_confirm_action_callback, set_on_confirm_action_callback = use_state(lambda: (lambda: None))

    # State for Feedback Modal
    show_feedback, set_show_feedback = use_state(False)
    feedback_message, set_feedback_message = use_state("")
    feedback_type, set_feedback_type = use_state("success")

    # State for new Assignment Form (to be created)
    show_assignment_form, set_show_assignment_form = use_state(False)
    available_teams_for_assignment, set_available_teams_for_assignment = use_state([])


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
        await fetch_robots() # This will also re-trigger filtering

    async def trigger_robot_edit_confirmation(form_data_from_edit_form):
        set_confirmation_message("¿Está seguro de que desea guardar los cambios en el robot?")
        async def actual_db_action():
            await handle_save_robot_action(form_data_from_edit_form)
        # Store a lambda that returns the actual coroutine function
        # The outer lambda `lambda _: ...` is to prevent ReactPy from calling our inner lambda with the previous state.
        set_on_confirm_action_callback(lambda _: (lambda: actual_db_action))
        set_show_confirmation(True)

    async def execute_confirmed_action():
        set_show_confirmation(False)
        # Call the stored lambda, which returns the actual_db_action
        action_to_run_factory = on_confirm_action_callback()
        if action_to_run_factory:
            # Now call the actual_db_action (which is a coroutine function) and await it
            await action_to_run_factory()
        # The outer lambda `lambda _: ...` is to prevent ReactPy from calling our inner lambda with the previous state.
        set_on_confirm_action_callback(lambda _: (lambda: (lambda: None))) # Reset

    async def handle_save_robot_action(updated_robot_data):
        if not db:
            set_feedback_message("Error: No se pudo conectar a la base de datos.")
            set_feedback_type("error")
            set_show_feedback(True)
            return

        try:
            query = "UPDATE dbo.Robots SET PrioridadBalanceo = ?, MinEquipos = ?, MaxEquipos = ?, TicketsPorEquipoAdicional = ? WHERE RobotId = ?"
            params = (
                updated_robot_data["PrioridadBalanceo"],
                updated_robot_data["MinEquipos"],
                updated_robot_data["MaxEquipos"],
                updated_robot_data.get("TicketsPorEquipoAdicional") or None,
                updated_robot_data["RobotId"],
            )
            db.ejecutar_consulta(query, params)

            set_feedback_message("Robot actualizado exitosamente.")
            set_feedback_type("success")
            set_show_feedback(True) # Show success feedback

            set_robot_en_edicion(None)
            await fetch_robots()
        except Exception as e:
            print(f"Error al actualizar robot: {e}") # Log for server
            set_feedback_message(f"Error al actualizar robot: {str(e)}")
            set_feedback_type("error")
            set_show_feedback(True) # Show error feedback

    async def trigger_robot_schedule_confirmation(robot_arg, form_data_arg):
        set_confirmation_message("¿Está seguro de que desea programar este robot?")
        async def actual_db_action():
            await handle_save_schedule_action(robot_arg, form_data_arg)
        set_on_confirm_action_callback(lambda _: (lambda: actual_db_action))
        set_show_confirmation(True)

    async def handle_save_schedule_action(robot, schedule_form_data):
        if not db:
            set_feedback_message("Error: No se pudo conectar a la base de datos.")
            set_feedback_type("error")
            set_show_feedback(True)
            return

        equipo_id_seleccionado = int(schedule_form_data["equipo_id"])
        equipo_seleccionado_obj = next((eq for eq in equipos_disponibles if eq["EquipoId"] == equipo_id_seleccionado), None)
        if not equipo_seleccionado_obj:
            print("Error: Equipo seleccionado no encontrado.")
            # Set feedback: "Equipo no encontrado"
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

            set_feedback_message("Robot programado exitosamente.")
            set_feedback_type("success")
            set_show_feedback(True)
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"UI Error: Falló la transacción de programación. Se revirtieron los cambios. Error: {e}")
            set_feedback_message(f"Error al programar robot: {str(e)}")
            set_feedback_type("error")
            set_show_feedback(True)
            # Removed raise e
        finally:
            if conn:
                conn.close()
            set_robot_para_programar(None)
            await fetch_robots()

    async def handle_save_assignments_action(robot_id, team_ids_list):
        if not robot_id or not team_ids_list:
            set_feedback_message("Error: Debe seleccionar un robot y al menos un equipo.")
            set_feedback_type("error")
            set_show_feedback(True)
            return

        if not db:
            set_feedback_message("Error: No se pudo conectar a la base de datos.")
            set_feedback_type("error")
            set_show_feedback(True)
            return

        all_successful = True
        errors_encountered = []

        for team_id in team_ids_list:
            try:
                # Corrected query to include Reservado and AsignadoPor
                query = "INSERT INTO dbo.Asignaciones (RobotId, EquipoId, Reservado, FechaAsignacion, AsignadoPor) VALUES (?, ?, ?, GETDATE(), ?)"
                # Parameters now include 1 for Reservado and "WEB" for AsignadoPor
                db.ejecutar_consulta(query, (int(robot_id), int(team_id), 1, "WEB"))
            except Exception as e:
                all_successful = False
                error_detail = f"Error al asignar equipo ID {team_id}: {str(e)}"
                print(error_detail)
                errors_encountered.append(error_detail)

        if all_successful:
            set_feedback_message(f"{len(team_ids_list)} equipo(s) asignado(s) exitosamente.")
            set_feedback_type("success")
        else:
            error_summary = "; ".join(errors_encountered)
            set_feedback_message(f"Algunas asignaciones fallaron. Detalles: {error_summary}")
            set_feedback_type("error")

        set_show_feedback(True)
        set_show_assignment_form(False)
        await fetch_available_teams()

    async def trigger_assignment_confirmation(robot_id, team_ids_list):
        if not robot_id or not team_ids_list:
            set_feedback_message("Debe seleccionar un robot y al menos un equipo antes de guardar.")
            set_feedback_type("error")
            set_show_feedback(True)
            return

        robot_name = next((r['Robot'] for r in robots if str(r['RobotId']) == str(robot_id)), "Robot Desconocido")
        confirmation_msg = f"¿Está seguro de que desea asignar {len(team_ids_list)} equipo(s) al robot '{robot_name}'?"

        set_confirmation_message(confirmation_msg)
        async def actual_db_action():
            await handle_save_assignments_action(robot_id, team_ids_list)
        set_on_confirm_action_callback(lambda _: (lambda: actual_db_action))
        set_show_confirmation(True)

    async def fetch_available_teams():
        if not db:
            print("Error: Database connection not available for fetching available teams.")
            set_available_teams_for_assignment([])
            return

        query = """
            SELECT E.EquipoId, E.Equipo
            FROM dbo.Equipos E
            WHERE E.Licencia = 'ATTENDEDRUNTIME'
              AND E.Activo_SAM = 1
              AND NOT EXISTS (
                  SELECT 1
                  FROM dbo.Asignaciones A
                  WHERE A.EquipoId = E.EquipoId
              )
            ORDER BY E.Equipo;
        """
        try:
            teams_data = db.ejecutar_consulta(query, es_select=True)
            set_available_teams_for_assignment(teams_data or [])
        except Exception as e:
            print(f"Error fetching available teams: {e}")
            set_available_teams_for_assignment([])
            set_feedback_message(f"Error al cargar equipos disponibles: {str(e)}")
            set_feedback_type("error")
            set_show_feedback(True)

    async def handle_open_assignment_form(event=None):
        await fetch_available_teams()
        set_show_assignment_form(True)

    async def handle_open_schedule_form(robot_para_agendar, event=None):
        if not db: return
        # This query for schedule form might be different, it fetches teams not reserved or programmed
        query = "SELECT EquipoId, Equipo FROM dbo.Equipos WHERE Activo_SAM = 1 AND EquipoId NOT IN (SELECT EquipoId FROM dbo.Asignaciones WHERE Reservado = 1 OR EsProgramado = 1)"
        equipos = db.ejecutar_consulta(query, es_select=True)
        set_equipos_disponibles(equipos or []) # This is for the ScheduleCreateForm's specific needs
        set_robot_para_programar(robot_para_agendar)

    if not db:
        return html.div(html.h1("Error de Conexión"), html.p("No se pudo establecer la conexión con la base de datos SAM."))

    # Filtering Logic
    current_filter_stage = list(robots) # Start with a copy

    if search_term:
        current_filter_stage = [r for r in current_filter_stage if search_term.lower() in r['Robot'].lower()]

    if activo_filter == "true":
        current_filter_stage = [r for r in current_filter_stage if r['Activo'] is True or r['Activo'] == 1]
    elif activo_filter == "false":
        current_filter_stage = [r for r in current_filter_stage if r['Activo'] is False or r['Activo'] == 0]

    if online_filter == "true":
        current_filter_stage = [r for r in current_filter_stage if r['EsOnline'] is True or r['EsOnline'] == 1]
    elif online_filter == "false":
        current_filter_stage = [r for r in current_filter_stage if r['EsOnline'] is False or r['EsOnline'] == 0]

    filtered_robots = current_filter_stage

    table_rows = []
    for robot_data in filtered_robots: # Renamed robot to robot_data to avoid conflict with robot_para_programar
        table_rows.append(
            html.tr(
                {"key": robot_data["RobotId"]},
                html.td(robot_data["Robot"]),
                html.td(
                    html.button(
                        {
                            "on_click": partial(handle_toggle, robot_data["RobotId"], "Activo"),
                            "class_name": f"btn-{'activo' if robot_data['Activo'] else 'inactivo'}",
                        },
                        "Sí" if robot_data["Activo"] else "No",
                    )
                ),
                html.td(
                    html.button(
                        {
                            "on_click": partial(handle_toggle, robot_data["RobotId"], "EsOnline"),
                            "class_name": f"btn-{'activo' if robot_data['EsOnline'] else 'inactivo'}",
                        },
                        "Sí" if robot_data["EsOnline"] else "No",
                    )
                ),
                html.td(robot_data["PrioridadBalanceo"]),
                html.td(
                    html.button({"on_click": partial(handle_open_schedule_form, robot_data), "class_name": "btn-accion"}, "Programar"),
                    html.button({"on_click": lambda event, r=robot_data: set_robot_en_edicion(r), "class_name": "btn-accion-secundario"}, "Editar"),
                ),
            )
        )

    app_children = [
        html.link({"rel": "stylesheet", "href": "/static/style.css"}),
        html.h1("Panel de Mantenimiento SAM - Gestión de Robots"),
        html.div({"class_name": "filter-controls"},
            html.input({
                "type": "text",
                "placeholder": "Buscar robot...",
                "value": search_term,
                "on_change": lambda event: set_search_term(event["target"]["value"]),
                "class_name": "search-input"
            }),
            html.div({"class_name": "filter-group"},
                html.label({"for": "activo_filter_select"}, "Activo: "),
                html.select({
                    "id": "activo_filter_select",
                    "value": activo_filter,
                    "on_change": lambda event: set_activo_filter(event["target"]["value"]),
                    "class_name": "filter-select"
                },
                    html.option({"value": "all"}, "Todos"),
                    html.option({"value": "true"}, "Sí"),
                    html.option({"value": "false"}, "No")
                )
            ),
            html.div({"class_name": "filter-group"},
                html.label({"for": "online_filter_select"}, "Online: "),
                html.select({
                    "id": "online_filter_select",
                    "value": online_filter,
                    "on_change": lambda event: set_online_filter(event["target"]["value"]),
                    "class_name": "filter-select"
                },
                    html.option({"value": "all"}, "Todos"),
                    html.option({"value": "true"}, "Sí"),
                    html.option({"value": "false"}, "No")
                )
            )
        ),
        html.div({"class_name": "action-buttons-bar", "style": {"margin_bottom": "20px", "display": "flex", "gap": "10px"}},
            html.button({"on_click": fetch_robots, "class_name": "btn-accion"}, "Refrescar Datos"),
            html.button({
                "on_click": handle_open_assignment_form, # Changed
                "class_name": "btn-accion-secundario"
            }, "Asignar Robot a Equipos")
        ),
        html.table(
            {"class_name": "sam-table"},
            html.thead(html.tr(html.th("Robot"), html.th("Activo"), html.th("Es Online"), html.th("Prioridad"), html.th("Acciones"))),
            html.tbody(table_rows if filtered_robots else html.tr(html.td({"colSpan": 5}, "No hay robots para mostrar."))),
        ),
    ]

    if robot_en_edicion:
        app_children.append(RobotEditForm(
            robot=robot_en_edicion,
            on_save=trigger_robot_edit_confirmation,
            on_cancel=lambda event: set_robot_en_edicion(None)
        ))

    if robot_para_programar:
        app_children.append(ScheduleCreateForm(
            robot=robot_para_programar,
            equipos_disponibles=equipos_disponibles,
            on_save=trigger_robot_schedule_confirmation,
            on_cancel=lambda event: set_robot_para_programar(None),
        ))

    if show_assignment_form:
        app_children.append(AssignmentForm(
            robots=robots,
            available_teams=available_teams_for_assignment,
            on_save=trigger_assignment_confirmation,
            on_cancel=lambda event: set_show_assignment_form(False)
        ))

    if show_confirmation:
        app_children.append(ConfirmationModal(
            message=confirmation_message,
            on_confirm=execute_confirmed_action,
            on_cancel=lambda event: set_show_confirmation(False)
        ))

    if show_feedback:
        app_children.append(FeedbackModal(
            message=feedback_message,
            message_type=feedback_type,
            on_dismiss=lambda event: set_show_feedback(False)
        ))

    return html.div({"class_name": "container"}, *app_children)

```
