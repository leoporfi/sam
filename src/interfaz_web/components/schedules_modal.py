# interfaz_web/components/schedules_modal.py

import asyncio
from typing import Any, Callable, Dict, List, Set

import httpx
from reactpy import component, event, html, use_context, use_effect, use_state, use_memo, use_callback

from ..config.settings import Settings
from .notifications import NotificationContext

URL_BASE = Settings.API_BASE_URL

# Constantes para mejorar mantenibilidad
SCHEDULE_TYPES = ["Diaria", "Semanal", "Mensual", "Especifica"]
DEFAULT_FORM_STATE = {
    "ProgramacionId": None,
    "TipoProgramacion": "Diaria",
    "HoraInicio": "09:00",
    "Tolerancia": 60,
    "DiasSemana": "Lu,Ma,Mi,Ju,Vi",
    "DiaDelMes": 1,
    "FechaEspecifica": "",
    "Equipos": [],  # Siempre lista, nunca set
}

# Configuración HTTP reutilizable
HTTP_TIMEOUT = 30.0
HTTP_HEADERS = {"Content-Type": "application/json"}


@component
def DeleteButton(schedule_id: int, robot_id: int, on_delete_success: Callable):
    """Botón de borrado optimizado con mejor manejo de errores"""
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    is_deleting, set_is_deleting = use_state(False)

    # Definir la función async por separado
    async def delete_schedule(event):
        if is_deleting:
            return

        set_is_deleting(True)
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.delete(f"{URL_BASE}/api/robots/{robot_id}/programaciones/{schedule_id}", headers=HTTP_HEADERS)
                response.raise_for_status()

            show_notification("Programación eliminada.", "success")
            await on_delete_success()
        except httpx.HTTPError as e:
            show_notification(f"Error de conexión: {e}", "error")
        except Exception as e:
            show_notification(f"Error inesperado: {e}", "error")
        finally:
            set_is_deleting(False)

    # Usar use_callback con la función ya definida
    handle_click = use_callback(delete_schedule, [schedule_id, robot_id, is_deleting])

    return html.button(
        {"className": f"button is-danger is-light is-small {'is-loading' if is_deleting else ''}", "onClick": handle_click, "disabled": is_deleting},
        "Eliminar",
    )


@component
def TeamSelector(available_teams: List[Dict], selected_teams: List[int], on_change: Callable):
    """Componente separado para la selección de equipos"""

    # Asegurar que selected_teams es siempre una lista
    safe_selected_teams = list(selected_teams) if selected_teams else []

    # Memoizar conjuntos para evitar recálculos, pero convertir a lista al final
    selected_teams_set = use_memo(lambda: set(safe_selected_teams), [safe_selected_teams])
    all_available_ids_set = use_memo(lambda: {team["EquipoId"] for team in available_teams}, [available_teams])
    are_all_teams_selected = use_memo(
        lambda: all_available_ids_set and all_available_ids_set.issubset(selected_teams_set), [selected_teams_set, all_available_ids_set]
    )

    def handle_select_all_teams(event):
        is_checked = event["target"]["checked"]
        # Convertir siempre a lista antes de pasar al callback
        new_teams = list(all_available_ids_set) if is_checked else []
        on_change(new_teams)

    def handle_team_select(team_id, checked):
        # Trabajar con set para eficiencia pero convertir a lista al final
        current_teams = set(safe_selected_teams)
        if checked:
            current_teams.add(team_id)
        else:
            current_teams.discard(team_id)
        # Convertir a lista antes de pasar al callback
        on_change(list(current_teams))

    return html.div(
        {"className": "field mt-4"},
        html.label({"className": "label"}, "Asignar Equipos"),
        # Checkbox para seleccionar todos
        html.div(
            {"className": "field"},
            html.label(
                {"className": "checkbox is-small"},
                html.input({"type": "checkbox", "checked": are_all_teams_selected, "onChange": handle_select_all_teams}),
                " Seleccionar Todos / Deseleccionar Todos",
            ),
        ),
        # Lista de equipos con scroll
        html.div(
            {"className": "control"},
            html.div(
                {"className": "box", "style": {"maxHeight": "20vh", "overflowY": "auto"}},
                *[
                    html.div(
                        {"key": team["EquipoId"]},
                        html.label(
                            {"className": "checkbox"},
                            html.input(
                                {
                                    "type": "checkbox",
                                    "checked": team["EquipoId"] in selected_teams_set,
                                    "onChange": lambda e, tid=team["EquipoId"]: handle_team_select(tid, e["target"]["checked"]),
                                }
                            ),
                            f" {team['Equipo']}",
                        ),
                    )
                    for team in available_teams
                ],
            ),
        ),
    )


@component
def ScheduleForm(form_data: Dict, available_teams: List[Dict], is_loading: bool, on_submit: Callable, on_cancel: Callable, on_change: Callable):
    """Componente separado para el formulario de programación"""

    tipo = form_data.get("TipoProgramacion")

    # Memoizar opciones del select para evitar recrear en cada render
    schedule_options = use_memo(
        lambda: [html.option({"value": schedule_type, "key": schedule_type}, schedule_type) for schedule_type in SCHEDULE_TYPES], []
    )

    def handle_form_change(field, value):
        on_change(field, value)

    def handle_team_change(teams):
        # Asegurar que teams es siempre una lista
        safe_teams = list(teams) if teams else []
        on_change("Equipos", safe_teams)

    return html.form(
        {"onSubmit": event(on_submit, prevent_default=True)},
        # Fila 1: Tipo, Hora, Tolerancia
        html.div(
            {"className": "columns"},
            html.div(
                {"className": "column is-one-third"},
                html.div(
                    {"className": "field"},
                    html.label({"className": "label"}, "Tipo de Programación"),
                    html.div(
                        {"className": "control"},
                        html.div(
                            {"className": "select is-fullwidth"},
                            html.select(
                                {"value": tipo, "onChange": lambda e: handle_form_change("TipoProgramacion", e["target"]["value"])}, *schedule_options
                            ),
                        ),
                    ),
                ),
            ),
            html.div(
                {"className": "column"},
                html.div(
                    {"className": "field"},
                    html.label({"className": "label"}, "Hora Inicio"),
                    html.div(
                        {"className": "control"},
                        html.input(
                            {
                                "type": "time",
                                "className": "input",
                                "value": form_data.get("HoraInicio"),
                                "onChange": lambda e: handle_form_change("HoraInicio", e["target"]["value"]),
                            }
                        ),
                    ),
                ),
            ),
            html.div(
                {"className": "column"},
                html.div(
                    {"className": "field"},
                    html.label({"className": "label"}, "Tolerancia (min)"),
                    html.div(
                        {"className": "control"},
                        html.input(
                            {
                                "type": "number",
                                "className": "input",
                                "value": form_data.get("Tolerancia"),
                                "onChange": lambda e: handle_form_change("Tolerancia", int(e["target"]["value"]) if e["target"]["value"] else 0),
                            }
                        ),
                    ),
                ),
            ),
        ),
        # Campos condicionales según el tipo
        ConditionalFields(tipo, form_data, handle_form_change),
        # Selección de equipos
        TeamSelector(available_teams, form_data.get("Equipos", []), handle_team_change),
        # Botones de acción
        html.div(
            {"className": "field is-grouped is-grouped-right mt-5"},
            html.div(
                {"className": "control"},
                html.button({"type": "button", "className": "button", "onClick": lambda e: on_cancel(), "disabled": is_loading}, "Cancelar"),
            ),
            html.div(
                {"className": "control"},
                html.button(
                    {"type": "submit", "className": f"button is-link {'is-loading' if is_loading else ''}", "disabled": is_loading}, "Guardar"
                ),
            ),
        ),
    )


@component
def ConditionalFields(tipo: str, form_data: Dict, on_change: Callable):
    """Campos condicionales según el tipo de programación"""

    if tipo == "Semanal":
        return html.div(
            {"className": "field"},
            html.label({"className": "label"}, "Días (ej: Lu,Ma,Mi)"),
            html.div(
                {"className": "control"},
                html.input(
                    {
                        "type": "text",
                        "className": "input",
                        "value": form_data.get("DiasSemana", ""),
                        "onChange": lambda e: on_change("DiasSemana", e["target"]["value"]),
                    }
                ),
            ),
        )
    elif tipo == "Mensual":
        return html.div(
            {"className": "field"},
            html.label({"className": "label"}, "Día del Mes"),
            html.div(
                {"className": "control"},
                html.input(
                    {
                        "type": "number",
                        "min": 1,
                        "max": 31,
                        "className": "input",
                        "value": form_data.get("DiaDelMes", 1),
                        "onChange": lambda e: on_change("DiaDelMes", int(e["target"]["value"]) if e["target"]["value"] else 1),
                    }
                ),
            ),
        )
    elif tipo == "Especifica":
        return html.div(
            {"className": "field"},
            html.label({"className": "label"}, "Fecha Específica"),
            html.div(
                {"className": "control"},
                html.input(
                    {
                        "type": "date",
                        "className": "input",
                        "value": form_data.get("FechaEspecifica", ""),
                        "onChange": lambda e: on_change("FechaEspecifica", e["target"]["value"]),
                    }
                ),
            ),
        )

    return html.div()  # Elemento vacío para otros tipos


@component
def SchedulesList(schedules: List[Dict], robot_id: int, on_edit: Callable, on_delete_success: Callable):
    """Lista de programaciones optimizada"""

    def format_schedule_details(schedule):
        details = f"{schedule.get('TipoProgramacion', 'N/A')} a las {schedule.get('HoraInicio', '')}"
        if schedule.get("TipoProgramacion") == "Semanal":
            details += f" los días {schedule.get('DiasSemana', '')}"
        elif schedule.get("TipoProgramacion") == "Mensual":
            details += f" el día {schedule.get('DiaDelMes', '')} de cada mes"
        elif schedule.get("TipoProgramacion") == "Especifica":
            details += f" en la fecha {schedule.get('FechaEspecifica', '')}"
        return details

    # Memoizar las filas para evitar recálculos innecesarios
    rows = use_memo(
        lambda: [
            html.tr(
                {"key": s["ProgramacionId"]},
                html.td(format_schedule_details(s)),
                html.td(", ".join([team["Equipo"] for team in s.get("Equipos", [])]) or "Ninguno"),
                html.td(
                    {"className": "buttons are-small is-justify-content-flex-end"},
                    html.button({"className": "button is-light", "onClick": lambda e, sch=s: on_edit(sch)}, "Editar"),
                    DeleteButton(
                        schedule_id=s["ProgramacionId"],
                        robot_id=robot_id,
                        on_delete_success=on_delete_success,
                    ),
                ),
            )
            for s in schedules
        ],
        [schedules, robot_id],
    )

    return html.div(
        html.table(
            {"className": "table is-fullwidth is-hoverable is-striped"},
            html.thead(html.tr(html.th("Detalles"), html.th("Equipos"), html.th("Acciones"))),
            html.tbody(rows if rows else html.tr(html.td({"colSpan": 3, "className": "has-text-centered"}, "No hay programaciones."))),
        ),
    )


@component
def SchedulesModal(robot: Dict[str, Any] | None, on_close: Callable, on_save_success: Callable):
    """Componente principal del modal optimizado"""

    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    # Estados del componente
    view_mode, set_view_mode = use_state("list")
    schedules, set_schedules = use_state([])
    available_teams, set_available_teams = use_state([])
    form_data, set_form_data = use_state(DEFAULT_FORM_STATE)
    is_loading, set_is_loading = use_state(False)

    # Definir la función async por separado
    async def load_data():
        if not robot:
            return

        set_is_loading(True)
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                # Usar asyncio.gather para peticiones paralelas
                schedules_task = client.get(f"{URL_BASE}/api/robots/{robot['RobotId']}/programaciones", headers=HTTP_HEADERS)
                teams_task = client.get(f"{URL_BASE}/api/equipos/disponibles/{robot['RobotId']}", headers=HTTP_HEADERS)

                schedules_res, teams_res = await asyncio.gather(schedules_task, teams_task)
                schedules_res.raise_for_status()
                teams_res.raise_for_status()

                set_schedules(schedules_res.json())
                set_available_teams(teams_res.json())

        except httpx.HTTPError as e:
            show_notification(f"Error de conexión: {e}", "error")
            set_schedules([])
            set_available_teams([])
        except Exception as e:
            show_notification(f"Error inesperado: {e}", "error")
            set_schedules([])
            set_available_teams([])
        finally:
            set_is_loading(False)

    # Función optimizada para cargar datos
    fetch_data = use_callback(load_data, [robot])

    use_effect(fetch_data, [robot])

    # Definir la función async para submit por separado
    async def submit_form(event):
        set_is_loading(True)
        # Crear payload asegurando que todos los valores sean serializables
        payload = {
            "ProgramacionId": form_data.get("ProgramacionId"),
            "RobotId": robot["RobotId"],
            "TipoProgramacion": form_data.get("TipoProgramacion"),
            "HoraInicio": form_data.get("HoraInicio"),
            "Tolerancia": form_data.get("Tolerancia"),
            "DiasSemana": form_data.get("DiasSemana"),
            "DiaDelMes": form_data.get("DiaDelMes"),
            "FechaEspecifica": form_data.get("FechaEspecifica"),
            "Equipos": list(form_data.get("Equipos", [])),  # Asegurar que es lista
        }

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                if payload.get("ProgramacionId"):
                    url = f"{URL_BASE}/api/programaciones/{payload['ProgramacionId']}"
                    response = await client.put(url, json=payload, headers=HTTP_HEADERS)
                    message = "Programación actualizada con éxito."
                else:
                    url = f"{URL_BASE}/api/programaciones"
                    response = await client.post(url, json=payload, headers=HTTP_HEADERS)
                    message = "Programación creada con éxito."

                response.raise_for_status()
                show_notification(message, "success")

                set_view_mode("list")
                await fetch_data()
                await on_save_success()

        except httpx.HTTPError as e:
            show_notification(f"Error de conexión: {e}", "error")
        except Exception as e:
            show_notification(f"Error inesperado: {e}", "error")
        finally:
            set_is_loading(False)

    # Manejadores de eventos optimizados
    handle_form_submit = use_callback(submit_form, [form_data, robot, fetch_data, on_save_success])

    def handle_edit_click(schedule_to_edit):
        # Asegurar que equipos_ids es siempre una lista
        equipos_ids = [team["EquipoId"] for team in schedule_to_edit.get("Equipos", [])]

        form_state = {
            "ProgramacionId": schedule_to_edit.get("ProgramacionId"),
            "TipoProgramacion": schedule_to_edit.get("TipoProgramacion", "Diaria"),
            "HoraInicio": (schedule_to_edit.get("HoraInicio") or "09:00")[:5],
            "Tolerancia": schedule_to_edit.get("Tolerancia", 60),
            "DiasSemana": schedule_to_edit.get("DiasSemana", ""),
            "DiaDelMes": schedule_to_edit.get("DiaDelMes", 1),
            "FechaEspecifica": (schedule_to_edit.get("FechaEspecifica") or "")[:10],
            "Equipos": equipos_ids,  # Ya es lista
        }
        set_form_data(form_state)
        set_view_mode("form")

    def handle_form_change(field, value):
        # Asegurar que el valor es serializable
        if field == "Equipos":
            value = list(value) if value else []
        set_form_data(lambda old: {**old, field: value})

    def handle_new_click():
        set_form_data(DEFAULT_FORM_STATE.copy())
        set_view_mode("form")

    def handle_cancel():
        set_view_mode("list")

    if not robot:
        return None

    return html.div(
        {"className": "modal is-active"},
        html.div({"className": "modal-background", "onClick": on_close}),
        html.div(
            {"className": "modal-card", "style": {"width": "70%", "maxWidth": "960px"}},
            html.header(
                {"className": "modal-card-head"},
                html.div(
                    {"className": "level is-mobile", "style": {"width": "100%"}},
                    html.div({"className": "level-left"}, html.p({"className": "modal-card-title"}, "Gestionar Programaciones")),
                    html.div(
                        {"className": "level-right"},
                        html.button(
                            {"className": "button is-link", "onClick": lambda e: handle_new_click()},
                            html.span({"className": "icon"}, html.i({"className": "fas fa-plus"})),
                            html.span("Nueva Programación"),
                        )
                        if view_mode == "list"
                        else None,
                    ),
                ),
            ),
            html.section(
                {"className": "modal-card-body"},
                SchedulesList(schedules=schedules, robot_id=robot["RobotId"], on_edit=handle_edit_click, on_delete_success=on_save_success)
                if view_mode == "list"
                else ScheduleForm(
                    form_data=form_data,
                    available_teams=available_teams,
                    is_loading=is_loading,
                    on_submit=handle_form_submit,
                    on_cancel=handle_cancel,
                    on_change=handle_form_change,
                ),
            ),
            html.footer(
                {"className": "modal-card-foot is-justify-content-flex-end"},
                html.button({"className": "button", "onClick": on_close}, "Cerrar"),
            ),
        ),
    )


"""VERSION ANTERIOR"""
# # interfaz_web/components/schedules_modal.py

# import asyncio
# from typing import Any, Callable, Dict

# import httpx
# from reactpy import component, event, html, use_context, use_effect, use_state

# from ..config.settings import Settings
# from .notifications import NotificationContext

# URL_BASE = Settings.API_BASE_URL


# @component
# def DeleteButton(schedule_id: int, robot_id: int, on_delete_success: Callable):
#     """
#     Botón de borrado autocontenido que maneja su lógica de clic
#     y notifica al componente padre tras el éxito.
#     """
#     notification_ctx = use_context(NotificationContext)
#     show_notification = notification_ctx["show_notification"]

#     async def handle_click(event):
#         try:
#             # Aquí se podría añadir un diálogo de confirmación
#             async with httpx.AsyncClient() as client:
#                 await client.delete(f"{URL_BASE}/api/robots/{robot_id}/programaciones/{schedule_id}")
#             show_notification("Programación eliminada.", "success")

#             # Llamamos a la función que nos pasó el padre para refrescar toda la UI
#             await on_delete_success()

#         except Exception as e:
#             show_notification(f"Error al eliminar: {e}", "error")

#     return html.button({"className": "button is-danger is-light is-small", "onClick": handle_click}, "Eliminar")


# # Valores por defecto para un nuevo formulario de programación
# DEFAULT_FORM_STATE = {
#     "ProgramacionId": None,
#     "TipoProgramacion": "Diaria",
#     "HoraInicio": "09:00",
#     "Tolerancia": 60,
#     "DiasSemana": "Lu,Ma,Mi,Ju,Vi",
#     "DiaDelMes": 1,
#     "FechaEspecifica": "",
#     "Equipos": [],
# }


# @component
# def SchedulesModal(robot: Dict[str, Any] | None, on_close: Callable, on_save_success: Callable):
#     notification_ctx = use_context(NotificationContext)
#     show_notification = notification_ctx["show_notification"]

#     # --- Estados del componente ---
#     view_mode, set_view_mode = use_state("list")  # 'list' o 'form'
#     schedules, set_schedules = use_state([])
#     available_teams, set_available_teams = use_state([])
#     form_data, set_form_data = use_state(DEFAULT_FORM_STATE)
#     is_loading, set_is_loading = use_state(False)

#     # --- Lógica de Datos ---
#     async def fetch_data():
#         if not robot:
#             return
#         set_is_loading(True)
#         try:
#             async with httpx.AsyncClient() as client:
#                 # Usamos el puerto 8080 donde corre uvicorn
#                 schedules_task = client.get(f"{URL_BASE}/api/robots/{robot['RobotId']}/programaciones")
#                 teams_task = client.get(f"{URL_BASE}/api/equipos/disponibles/{robot['RobotId']}")
#                 schedules_res, teams_res = await asyncio.gather(schedules_task, teams_task)
#                 schedules_res.raise_for_status()
#                 teams_res.raise_for_status()
#                 set_schedules(schedules_res.json())
#                 set_available_teams(teams_res.json())
#         except Exception as e:
#             show_notification(f"Error al cargar datos de programaciones: {e}", "error")
#             set_schedules([])
#             set_available_teams([])
#         finally:
#             set_is_loading(False)

#     use_effect(fetch_data, [robot])

#     # --- Manejadores de Eventos ---
#     async def handle_form_submit(event):
#         set_is_loading(True)
#         payload = form_data.copy()
#         payload["RobotId"] = robot["RobotId"]
#         try:
#             async with httpx.AsyncClient() as client:
#                 if "ProgramacionId" in payload and payload["ProgramacionId"]:
#                     url = f"{URL_BASE}/api/programaciones/{payload['ProgramacionId']}"
#                     await client.put(url, json=payload, timeout=30)
#                     show_notification("Programación actualizada con éxito.", "success")
#                 else:
#                     url = f"{URL_BASE}/api/programaciones"
#                     await client.post(url, json=payload, timeout=30)
#                     show_notification("Programación creada con éxito.", "success")
#             set_view_mode("list")
#             await fetch_data()
#             await on_save_success()
#         except Exception as e:
#             show_notification(f"Error al guardar: {e}", "error")
#         finally:
#             set_is_loading(False)

#     def handle_edit_click(schedule_to_edit):
#         equipos_ids = [team["EquipoId"] for team in schedule_to_edit.get("Equipos", [])]

#         form_state = {
#             "ProgramacionId": schedule_to_edit.get("ProgramacionId"),
#             "TipoProgramacion": schedule_to_edit.get("TipoProgramacion", "Diaria"),
#             "HoraInicio": (schedule_to_edit.get("HoraInicio") or "09:00")[:5],
#             "Tolerancia": schedule_to_edit.get("Tolerancia", 60),
#             "DiasSemana": schedule_to_edit.get("DiasSemana", ""),
#             "DiaDelMes": schedule_to_edit.get("DiaDelMes"),
#             "FechaEspecifica": (schedule_to_edit.get("FechaEspecifica") or "")[:10],
#             "Equipos": equipos_ids,
#         }
#         set_form_data(form_state)
#         set_view_mode("form")

#     def handle_form_change(field, value):
#         set_form_data(lambda old: {**old, field: value})

#     def handle_team_select(team_id, checked):
#         current_teams = set(form_data.get("Equipos", []))
#         if checked:
#             current_teams.add(team_id)
#         else:
#             current_teams.discard(team_id)
#         handle_form_change("Equipos", list(current_teams))

#     def handle_new_click():
#         set_form_data(DEFAULT_FORM_STATE)
#         set_view_mode("form")

#     # --- Funciones de Renderizado ---
#     def render_list():
#         rows = [
#             html.tr(
#                 {"key": s["ProgramacionId"]},
#                 html.td(format_schedule_details(s)),
#                 html.td(", ".join([team["Equipo"] for team in s.get("Equipos", [])]) or "Ninguno"),
#                 html.td(
#                     {"className": "buttons are-small is-justify-content-flex-end"},
#                     html.button({"className": "button is-light", "onClick": lambda e, sch=s: handle_edit_click(sch)}, "Editar"),
#                     DeleteButton(
#                         schedule_id=s["ProgramacionId"],
#                         robot_id=robot["RobotId"],
#                         on_delete_success=on_save_success,  # Pasamos la función de refresco del padre
#                     ),
#                 ),
#             )
#             for s in schedules
#         ]
#         return html.div(
#             html.table(
#                 {"className": "table is-fullwidth is-hoverable is-striped"},
#                 html.thead(html.tr(html.th("Detalles"), html.th("Equipos"), html.th("Acciones"))),
#                 html.tbody(rows if rows else html.tr(html.td({"colSpan": 3, "className": "has-text-centered"}, "No hay programaciones."))),
#             ),
#         )

#     def render_form():
#         tipo = form_data.get("TipoProgramacion")

#         # --- NUEVA LÓGICA PARA EL CHECKBOX "SELECCIONAR TODOS" ---
#         selected_teams_set = set(form_data.get("Equipos", []))
#         all_available_ids_set = {team["EquipoId"] for team in available_teams}
#         are_all_teams_selected = all_available_ids_set and all_available_ids_set.issubset(selected_teams_set)

#         def handle_select_all_teams(event):
#             is_checked = event["target"]["checked"]
#             if is_checked:
#                 handle_form_change("Equipos", list(all_available_ids_set))
#             else:
#                 handle_form_change("Equipos", [])

#         return html.form(
#             {"onSubmit": event(handle_form_submit, prevent_default=True)},
#             # Fila 1: Tipo, Hora, Tolerancia
#             html.div(
#                 {"className": "columns"},
#                 html.div(
#                     {"className": "column is-one-third"},
#                     html.div(
#                         {"className": "field"},
#                         html.label({"className": "label"}, "Tipo de Programación"),
#                         html.div(
#                             {"className": "control"},
#                             html.div(
#                                 {"className": "select is-fullwidth"},
#                                 html.select(
#                                     {"value": tipo, "onChange": lambda e: handle_form_change("TipoProgramacion", e["target"]["value"])},
#                                     html.option("Diaria"),
#                                     html.option("Semanal"),
#                                     html.option("Mensual"),
#                                     html.option("Especifica"),
#                                 ),
#                             ),
#                         ),
#                     ),
#                 ),
#                 html.div(
#                     {"className": "column"},
#                     html.div(
#                         {"className": "field"},
#                         html.label({"className": "label"}, "Hora Inicio"),
#                         html.div(
#                             {"className": "control"},
#                             html.input(
#                                 {
#                                     "type": "time",
#                                     "className": "input",
#                                     "value": form_data.get("HoraInicio"),
#                                     "onChange": lambda e: handle_form_change("HoraInicio", e["target"]["value"]),
#                                 },
#                             ),
#                         ),
#                     ),
#                 ),
#                 html.div(
#                     {"className": "column"},
#                     html.div(
#                         {"className": "field"},
#                         html.label({"className": "label"}, "Tolerancia (min)"),
#                         html.div(
#                             {"className": "control"},
#                             html.input(
#                                 {
#                                     "type": "number",
#                                     "className": "input",
#                                     "value": form_data.get("Tolerancia"),
#                                     "onChange": lambda e: handle_form_change("Tolerancia", e["target"]["value"]),
#                                 },
#                             ),
#                         ),
#                     ),
#                 ),
#             ),
#             # Fila 2: Campos Condicionales
#             html.div(
#                 {"style": {"display": "block" if tipo == "Semanal" else "none"}},
#                 html.div(
#                     {"className": "field"},
#                     html.label({"className": "label"}, "Días (ej: Lu,Ma,Mi)"),
#                     html.div(
#                         {"className": "control"},
#                         html.input(
#                             {
#                                 "type": "text",
#                                 "className": "input",
#                                 "value": form_data.get("DiasSemana"),
#                                 "onChange": lambda e: handle_form_change("DiasSemana", e["target"]["value"]),
#                             },
#                         ),
#                     ),
#                 ),
#             ),
#             html.div(
#                 {"style": {"display": "block" if tipo == "Mensual" else "none"}},
#                 html.div(
#                     {"className": "field"},
#                     html.label({"className": "label"}, "Día del Mes"),
#                     html.div(
#                         {"className": "control"},
#                         html.input(
#                             {
#                                 "type": "number",
#                                 "min": 1,
#                                 "max": 31,
#                                 "className": "input",
#                                 "value": form_data.get("DiaDelMes"),
#                                 "onChange": lambda e: handle_form_change("DiaDelMes", e["target"]["value"]),
#                             },
#                         ),
#                     ),
#                 ),
#             ),
#             html.div(
#                 {"style": {"display": "block" if tipo == "Especifica" else "none"}},
#                 html.div(
#                     {"className": "field"},
#                     html.label({"className": "label"}, "Fecha Específica"),
#                     html.div(
#                         {"className": "control"},
#                         html.input(
#                             {
#                                 "type": "date",
#                                 "className": "input",
#                                 "value": form_data.get("FechaEspecifica"),
#                                 "onChange": lambda e: handle_form_change("FechaEspecifica", e["target"]["value"]),
#                             },
#                         ),
#                     ),
#                 ),
#             ),
#             # Fila 3: Selección de Equipos
#             html.div(
#                 {"className": "field mt-4"},
#                 html.label({"className": "label"}, "Asignar Equipos"),
#                 # Checkbox para seleccionar todos
#                 html.div(
#                     {"className": "field"},
#                     html.label(
#                         {"className": "checkbox is-small"},
#                         html.input({"type": "checkbox", "checked": are_all_teams_selected, "onChange": handle_select_all_teams}),
#                         " Seleccionar Todos / Deseleccionar Todos",
#                     ),
#                 ),
#                 # Lista de equipos con scroll
#                 html.div(
#                     {"className": "control"},
#                     html.div(
#                         {"className": "box", "style": {"maxHeight": "20vh", "overflowY": "auto"}},
#                         *[
#                             html.div(
#                                 {"key": team["EquipoId"]},
#                                 html.label(
#                                     {"className": "checkbox"},
#                                     html.input(
#                                         {
#                                             "type": "checkbox",
#                                             "checked": team["EquipoId"] in selected_teams_set,
#                                             "onChange": lambda e, tid=team["EquipoId"]: handle_team_select(tid, e["target"]["checked"]),
#                                         }
#                                     ),
#                                     f" {team['Equipo']}",
#                                 ),
#                             )
#                             for team in available_teams
#                         ],
#                     ),
#                 ),
#             ),
#             # Fila 4: Botones de Acción
#             html.div(
#                 {"className": "field is-grouped is-grouped-right mt-5"},
#                 html.div(
#                     {"className": "control"},
#                     html.button(
#                         {"type": "button", "className": "button", "onClick": lambda e: set_view_mode("list"), "disabled": is_loading}, "Cancelar"
#                     ),
#                 ),
#                 html.div(
#                     {"className": "control"},
#                     html.button(
#                         {"type": "submit", "className": f"button is-link {'is-loading' if is_loading else ''}", "disabled": is_loading}, "Guardar"
#                     ),
#                 ),
#             ),
#         )

#     def format_schedule_details(schedule):
#         details = f"{schedule.get('TipoProgramacion', 'N/A')} a las {schedule.get('HoraInicio', '')}"
#         if schedule.get("TipoProgramacion") == "Semanal":
#             details += f" los días {schedule.get('DiasSemana', '')}"
#         elif schedule.get("TipoProgramacion") == "Mensual":
#             details += f" el día {schedule.get('DiaDelMes', '')} de cada mes"
#         elif schedule.get("TipoProgramacion") == "Especifica":
#             details += f" en la fecha {schedule.get('FechaEspecifica', '')}"
#         return details

#     if not robot:
#         return None

#     return html.div(
#         {"className": "modal is-active"},
#         html.div({"className": "modal-background", "onClick": on_close}),
#         html.div(
#             {"className": "modal-card", "style": {"width": "70%", "maxWidth": "960px"}},
#             html.header(
#                 {"className": "modal-card-head"},
#                 html.div(
#                     {"className": "level is-mobile", "style": {"width": "100%"}},
#                     html.div({"className": "level-left"}, html.p({"className": "modal-card-title"}, "Gestionar Programaciones")),
#                     html.div(
#                         {"className": "level-right"},
#                         html.button(
#                             {"className": "button is-link", "onClick": lambda e: handle_new_click()},
#                             html.span({"className": "icon"}, html.i({"className": "fas fa-plus"})),
#                             html.span("Nueva Programación"),
#                         )
#                         if view_mode == "list"
#                         else None,
#                     ),
#                 ),
#                 # html.button({"className": "delete", "aria-label": "close", "onClick": on_close}),
#             ),
#             html.section({"className": "modal-card-body"}, render_list() if view_mode == "list" else render_form()),
#             html.footer(
#                 {"className": "modal-card-foot is-justify-content-flex-end"},
#                 html.button({"className": "button", "onClick": on_close}, "Cerrar"),
#             ),
#         ),
#     )
