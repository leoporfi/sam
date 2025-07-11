# interfaz_web/components/schedules_modal.py

import asyncio
from typing import Any, Callable, Dict, List, Set

import httpx
from reactpy import component, event, html, use_callback, use_context, use_effect, use_memo, use_state

from ..client.config.settings import Settings
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
        {"className": "secondary outline", "onClick": handle_click, "disabled": is_deleting, "aria-busy": is_deleting},
        "Eliminar",
    )


@component
def TeamSelector(available_teams: List[Dict], selected_teams: List[int], on_change: Callable):
    """Componente separado para la selección de equipos usando checkboxes"""

    # Asegurar que selected_teams es siempre una lista
    safe_selected_teams = list(selected_teams) if selected_teams else []

    # Memoizar conjuntos para evitar recálculos
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

    return html.fieldset(
        # Checkbox para seleccionar todos
        # html.legend("Asignar Equipos"),
        html.label(
            html.input({"type": "checkbox", "checked": are_all_teams_selected, "onChange": handle_select_all_teams}),
            "Asignar Equipos",
        ),
        # Lista de equipos con scroll
        html.div(
            {"style": {"maxHeight": "200px", "overflowY": "auto"}},
            *[
                html.label(
                    {"key": team["EquipoId"]},
                    html.input(
                        {
                            "type": "checkbox",
                            "checked": team["EquipoId"] in selected_teams_set,
                            "onChange": lambda e, tid=team["EquipoId"]: handle_team_select(tid, e["target"]["checked"]),
                        }
                    ),
                    team["Equipo"],
                )
                for team in available_teams
            ],
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

    return html._(
        html.form(
            {"onSubmit": event(on_submit, prevent_default=True)},
            # Fila 1: Tipo, Hora, Tolerancia
            html.label(
                "Tipo de Programación",
                html.select({"value": tipo, "onChange": lambda e: handle_form_change("TipoProgramacion", e["target"]["value"])}, *schedule_options),
            ),
            html.div(
                {"className": "grid"},
                html.label(
                    "Hora Inicio",
                    html.input(
                        {
                            "type": "time",
                            "value": form_data.get("HoraInicio"),
                            "onChange": lambda e: handle_form_change("HoraInicio", e["target"]["value"]),
                        }
                    ),
                ),
                html.label(
                    "Tolerancia (min)",
                    html.input(
                        {
                            "type": "number",
                            "min": "0",
                            "max": "60",
                            "value": form_data.get("Tolerancia"),
                            "onChange": lambda e: handle_form_change("Tolerancia", int(e["target"]["value"]) if e["target"]["value"] else 0),
                        }
                    ),
                ),
            ),
            # Campos condicionales según el tipo
            ConditionalFields(tipo, form_data, handle_form_change),
            # Selección de equipos
            TeamSelector(available_teams, form_data.get("Equipos", []), handle_team_change),
            # Botones de acción
            html.div(
                {"className": "grid"},
                html.button({"type": "button", "className": "secondary", "onClick": lambda e: on_cancel(), "disabled": is_loading}, "Cancelar"),
                html.button({"type": "submit", "disabled": is_loading, "aria-busy": is_loading}, "Guardar"),
            ),
        ),
    )


@component
def ConditionalFields(tipo: str, form_data: Dict, on_change: Callable):
    """Campos condicionales según el tipo de programación"""

    if tipo == "Semanal":
        return html.label(
            "Días (ej: Lu,Ma,Mi)",
            html.input(
                {
                    "type": "text",
                    "value": form_data.get("DiasSemana", ""),
                    "onChange": lambda e: on_change("DiasSemana", e["target"]["value"]),
                }
            ),
        )
    elif tipo == "Mensual":
        return html.label(
            "Día del Mes",
            html.input(
                {
                    "type": "number",
                    "min": 1,
                    "max": 31,
                    "value": form_data.get("DiaDelMes", 1),
                    "onChange": lambda e: on_change("DiaDelMes", int(e["target"]["value"]) if e["target"]["value"] else 1),
                }
            ),
        )
    elif tipo == "Especifica":
        return html.label(
            "Fecha Específica",
            html.input(
                {
                    "type": "date",
                    "value": form_data.get("FechaEspecifica", ""),
                    "onChange": lambda e: on_change("FechaEspecifica", e["target"]["value"]),
                }
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
                    html.div(
                        {"className": "grid"},
                        html.button({"className": "outline", "onClick": lambda e, sch=s: on_edit(sch)}, "Editar"),
                        DeleteButton(
                            schedule_id=s["ProgramacionId"],
                            robot_id=robot_id,
                            on_delete_success=on_delete_success,
                        ),
                    ),
                ),
            )
            for s in schedules
        ],
        [schedules, robot_id],
    )

    return html.div(
        html.table(
            html.thead(html.tr(html.th("Detalles"), html.th("Equipos"), html.th("Acciones"))),
            html.tbody(rows if rows else html.tr(html.td({"colSpan": 3}, "No hay programaciones."))),
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

    # Función para cargar datos
    def load_data():
        if not robot:
            return

        async def fetch():
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

        # Crear la tarea pero no retornarla
        task = asyncio.create_task(fetch())

        # Retornar función de limpieza
        def cleanup():
            if not task.done():
                task.cancel()

        return cleanup

    # Función optimizada para cargar datos
    fetch_data = use_callback(load_data, [robot])

    use_effect(fetch_data, [robot])

    # Definir la función async para submit por separado
    async def submit_form(event):
        set_is_loading(True)

        # Validar que haya al menos un equipo seleccionado
        equipos_list = list(form_data.get("Equipos", []))
        if not equipos_list:
            show_notification("Debe seleccionar al menos un equipo.", "error")
            set_is_loading(False)
            return

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
            "Equipos": equipos_list,  # Ya validado que no está vacío
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
                load_data()()  # Llamar la función directamente
                await on_save_success()

        except httpx.HTTPError as e:
            show_notification(f"Error de conexión: {e}", "error")
        except Exception as e:
            show_notification(f"Error inesperado: {e}", "error")
        finally:
            set_is_loading(False)

    # Manejadores de eventos optimizados
    handle_form_submit = use_callback(submit_form, [form_data, robot, on_save_success])

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

    return html.dialog(
        {"open": True, "style": {"width": "90vw", "maxWidth": "800px"}},  # Modal más ancho
        html.article(
            html.header(
                html.button({"aria-label": "Close", "rel": "prev", "onClick": event(on_close, prevent_default=True)}),
                html.h5(f"Programaciones del robot {robot.get('Robot', '')}"),
            ),
            # Contenido principal
            html.main(
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
            # El footer solo es visible en la vista de lista
            html.footer(
                html.div(
                    {"className": "grid"},
                    html.div(),  # Placeholder para alinear el botón a la derecha
                    html.button({"onClick": lambda e: handle_new_click()}, "Crear nueva programación"),
                )
            )
            if view_mode == "list"
            else None,
        ),
    )
