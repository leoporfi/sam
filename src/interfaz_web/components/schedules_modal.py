# interfaz_web/components/schedules_modal.py

import asyncio
from typing import Any, Callable, Dict

import httpx
from reactpy import component, html, use_context, use_effect, use_state

from .notifications import NotificationContext
from .styles import BUTTON_STYLES

# Un diccionario con los valores por defecto para un nuevo formulario
DEFAULT_FORM_STATE = {
    "TipoProgramacion": "Diaria",
    "HoraInicio": "09:00",
    "Tolerancia": 60,
    "DiasSemana": "Lu,Ma,Mi,Ju,Vi",
    "DiaDelMes": 1,
    "FechaEspecifica": "",
    "Equipos": [],
}


@component
def DeleteButton(schedule_id: int, robot_id: int, on_delete_success: Callable):
    """
    Un botón que maneja la lógica asíncrona de borrado para una programación específica.
    """

    async def handle_click(event):
        try:
            # Aquí podríamos añadir una confirmación si quisiéramos
            async with httpx.AsyncClient() as client:
                await client.delete(f"http://127.0.0.1:8000/api/robots/{robot_id}/programaciones/{schedule_id}")
            # Notificamos al componente padre que el borrado fue exitoso
            await on_delete_success()
        except Exception as e:
            # Aquí podríamos pasar un error al componente padre para mostrarlo
            print(f"Error al eliminar la programación {schedule_id}: {e}")

    return html.button({"className": "font-medium text-red-500 hover:text-red-400", "onClick": handle_click}, "Eliminar")


@component
def SchedulesModal(robot: Dict[str, Any] | None, on_close: Callable, on_save_success: Callable):
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]
    view_mode, set_view_mode = use_state("list")
    schedules, set_schedules = use_state([])
    # error, set_error = use_state("")
    is_loading, set_is_loading = use_state(False)
    form_data, set_form_data = use_state(DEFAULT_FORM_STATE)
    available_teams, set_available_teams = use_state([])

    async def fetch_data():
        if not robot:
            return
        set_is_loading(True)

        try:
            async with httpx.AsyncClient() as client:
                schedules_task = client.get(f"http://127.0.0.1:8000/api/robots/{robot['RobotId']}/programaciones")
                teams_task = client.get(f"http://127.0.0.1:8000/api/equipos/disponibles/{robot['RobotId']}")
                schedules_res, teams_res = await asyncio.gather(schedules_task, teams_task)

                # Intentamos decodificar cada respuesta por separado para un mejor diagnóstico
                try:
                    schedules_res.raise_for_status()
                    set_schedules(schedules_res.json())
                except Exception as e_sched:
                    print(f"Error al procesar respuesta de programaciones. Texto recibido: '{schedules_res.text}'")
                    raise e_sched  # Relanzamos el error para que sea capturado por el bloque principal

                try:
                    teams_res.raise_for_status()
                    set_available_teams(teams_res.json())
                except Exception as e_teams:
                    print(f"Error al procesar respuesta de equipos. Texto recibido: '{teams_res.text}'")
                    raise e_teams
        except Exception as e:
            show_notification(f"Error al cargar datos: {e}", "error")
            # set_error(f"Error al cargar datos: {e}")
            set_schedules([])
            set_available_teams([])
        finally:
            set_is_loading(False)

    use_effect(fetch_data, [robot])

    def handle_new_schedule_click(event):
        set_form_data(DEFAULT_FORM_STATE)
        set_view_mode("form")

    # Código para la función handle_form_submit
    async def handle_form_submit(event):
        set_is_loading(True)
        payload = form_data.copy()
        payload["RobotId"] = robot["RobotId"]
        try:
            async with httpx.AsyncClient() as client:
                if "ProgramacionId" in payload and payload["ProgramacionId"]:
                    url = f"http://127.0.0.1:8000/api/programaciones/{payload['ProgramacionId']}"
                    await client.put(url, json=payload, timeout=30)
                else:
                    url = "http://127.0.0.1:8000/api/programaciones"
                    await client.post(url, json=payload, timeout=30)
            set_view_mode("list")
            await fetch_data()
        except Exception as e:
            show_notification(f"Error al guardar: {e}", "error")
        finally:
            set_is_loading(False)

    # Código para la función render_form
    def render_form():
        input_style = "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900 bg-white"

        def handle_team_select(team_id, checked):
            current_teams = set(form_data.get("Equipos", []))
            if checked:
                current_teams.add(team_id)
            else:
                current_teams.discard(team_id)
            handle_form_change("Equipos", list(current_teams))

        return html.form(
            {"className": "space-y-4", "onSubmit": handle_form_submit},
            html.div(
                html.label({"className": "block text-sm font-medium"}, "Tipo de Programación"),
                html.select(
                    {
                        "className": input_style,
                        "value": form_data.get("TipoProgramacion"),
                        "onChange": lambda e: handle_form_change("TipoProgramacion", e["target"]["value"]),
                    },
                    html.option("Diaria"),
                    html.option("Semanal"),
                    html.option("Mensual"),
                    html.option("Especifica"),
                ),
            ),
            html.div(
                {"className": "grid grid-cols-2 gap-4"},
                html.div(
                    html.label({"className": "block text-sm"}, "Hora Inicio"),
                    html.input(
                        {
                            "type": "time",
                            "className": input_style,
                            "value": form_data.get("HoraInicio"),
                            "onChange": lambda e: handle_form_change("HoraInicio", e["target"]["value"]),
                        }
                    ),
                ),
                html.div(
                    html.label({"className": "block text-sm"}, "Tolerancia (min)"),
                    html.input(
                        {
                            "type": "number",
                            "className": input_style,
                            "value": form_data.get("Tolerancia"),
                            "onChange": lambda e: handle_form_change("Tolerancia", e["target"]["value"]),
                        }
                    ),
                ),
            ),
            html.div(
                {"style": {"display": "block" if form_data.get("TipoProgramacion") == "Semanal" else "none"}},
                html.label({"className": "block text-sm"}, "Días (ej: Lu,Ma,Mi)"),
                html.input(
                    {
                        "type": "text",
                        "className": input_style,
                        "value": form_data.get("DiasSemana"),
                        "onChange": lambda e: handle_form_change("DiasSemana", e["target"]["value"]),
                    }
                ),
            ),
            html.div(
                {"style": {"display": "block" if form_data.get("TipoProgramacion") == "Mensual" else "none"}},
                html.label({"className": "block text-sm"}, "Día del Mes"),
                html.input(
                    {
                        "type": "number",
                        "min": 1,
                        "max": 31,
                        "className": input_style,
                        "value": form_data.get("DiaDelMes"),
                        "onChange": lambda e: handle_form_change("DiaDelMes", e["target"]["value"]),
                    }
                ),
            ),
            html.div(
                {"style": {"display": "block" if form_data.get("TipoProgramacion") == "Especifica" else "none"}},
                html.label({"className": "block text-sm"}, "Fecha Específica"),
                html.input(
                    {
                        "type": "date",
                        "className": input_style,
                        "value": form_data.get("FechaEspecifica"),
                        "onChange": lambda e: handle_form_change("FechaEspecifica", e["target"]["value"]),
                    }
                ),
            ),
            html.div(
                html.label({"className": "block text-sm font-medium"}, "Asignar Equipos"),
                html.div(
                    {"className": "mt-2 max-h-40 overflow-y-auto rounded-md border p-2 space-y-2"},
                    [
                        html.div(
                            {"key": team["EquipoId"]},
                            html.input(
                                {
                                    "type": "checkbox",
                                    "id": f"team-{team['EquipoId']}",
                                    "checked": team["EquipoId"] in form_data.get("Equipos", []),
                                    "onChange": lambda e, tid=team["EquipoId"]: handle_team_select(tid, e["target"]["checked"]),
                                }
                            ),
                            html.label({"htmlFor": f"team-{team['EquipoId']}", "className": "ml-2"}, team["Equipo"]),
                        )
                        for team in available_teams
                    ],
                ),
            ),
            html.div(
                {"className": "flex justify-end gap-3 pt-4"},
                html.button({"className": BUTTON_STYLES["secondary"], "onClick": lambda e: set_view_mode("list"), "disabled": is_loading}, "Cancelar"),
                html.button({"className": BUTTON_STYLES["primary"], "onClick": handle_form_submit, "disabled": is_loading}, "Guardar Cambios"),
            ),
        )

    # Código para la función render_list
    def render_list():
        schedule_rows = [
            html.tr(
                {"key": s["ProgramacionId"]},
                html.td({"className": "px-6 py-4"}, format_schedule_details(s)),
                html.td({"className": "px-6 py-4"}, s.get("EquiposAsignados", "Ninguno")),
                html.td(
                    {"className": "px-6 py-4 space-x-4"},
                    html.button({"className": "text-blue-400", "onClick": lambda e, sch=s: handle_edit_click(sch)}, "Editar"),
                    DeleteButton(schedule_id=s["ProgramacionId"], robot_id=robot["RobotId"], on_delete_success=fetch_data),
                ),
            )
            for s in schedules
        ]
        return html.table(
            {"className": "min-w-full divide-y divide-gray-700"},
            html.thead(
                html.tr(
                    html.th({"className": "px-6 py-3 text-left"}, "Detalles"),
                    html.th({"className": "px-6 py-3 text-left"}, "Equipos"),
                    html.th({"className": "px-6 py-3 text-left"}, "Acciones"),
                )
            ),
            html.tbody(schedule_rows if schedule_rows else html.tr(html.td({"colSpan": 3, "className": "text-center p-4"}, "No hay programaciones."))),
        )

    def handle_edit_click(schedule_to_edit):
        equipos_asignados_str = schedule_to_edit.get("EquiposAsignados", "") or ""
        equipos_ids = [team["EquipoId"] for team in available_teams if team["Equipo"] in equipos_asignados_str]
        set_form_data(
            {
                "ProgramacionId": schedule_to_edit.get("ProgramacionId"),
                "TipoProgramacion": schedule_to_edit.get("TipoProgramacion", "Diaria"),
                "HoraInicio": schedule_to_edit.get("HoraInicio", "09:00")[:5],
                "Tolerancia": schedule_to_edit.get("Tolerancia", 60),
                "DiasSemana": schedule_to_edit.get("DiasSemana", ""),
                "DiaDelMes": schedule_to_edit.get("DiaDelMes"),
                "FechaEspecifica": (schedule_to_edit.get("FechaEspecifica") or "")[:10],
                "Equipos": equipos_ids,
            }
        )
        set_view_mode("form")

    def handle_form_change(field, value):
        set_form_data(lambda old: {**old, field: value})

    if not robot:
        return None

    def format_schedule_details(schedule):
        details = f"Tipo: {schedule.get('TipoProgramacion', 'N/A')}, Hora: {schedule.get('HoraInicio', '')}"
        if schedule.get("TipoProgramacion") == "Semanal":
            details += f", Días: {schedule.get('DiasSemana', '')}"
        elif schedule.get("TipoProgramacion") == "Mensual":
            details += f", Día del Mes: {schedule.get('DiaDelMes', '')}"
        elif schedule.get("TipoProgramacion") == "Especifica":
            details += f", Fecha: {schedule.get('FechaEspecifica', '')}"
        return details

    # --- Creación de las Filas de la Tabla ---
    sschedule_rows = [
        html.tr(
            {"key": s["ProgramacionId"]},
            html.td({"className": "px-6 py-4 text-sm text-gray-900"}, format_schedule_details(s)),
            html.td({"className": "px-6 py-4 text-sm text-slate-300"}, s.get("EquiposAsignados", "Ninguno")),
            html.td(
                {"className": "px-6 py-4 text-sm space-x-4"},
                html.button(
                    {"className": "font-medium text-blue-500 hover:text-blue-400", "onClick": lambda event, schedule=s: handle_edit_click(schedule)},
                    "Editar",
                ),
                # --- CORRECCIÓN FINAL ---
                # Usamos el nuevo componente DeleteButton
                DeleteButton(schedule_id=s["ProgramacionId"], robot_id=robot["RobotId"], on_delete_success=fetch_data),
            ),
        )
        for s in schedules
    ]

    # El return final del componente SchedulesModal
    return html.div(
        {"className": "fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"},
        html.div(
            {"className": "w-full max-w-4xl max-h-[90vh] flex flex-col rounded-lg bg-white shadow-2xl text-gray-900"},
            html.div(
                {"className": "p-6 border-b border-gray-200 flex justify-between items-center"},
                html.div(
                    html.h1({"className": "text-2xl font-bold"}, "Gestionar Programaciones"),
                    html.p({"className": "text-slate-400 text-sm"}, f"Robot: {robot['Robot']}"),
                ),
                # El botón "Crear Nueva" ahora está conectado
                html.button({"className": "px-4 h-10 rounded-md bg-blue-600 text-white hover:bg-blue-700", "onClick": handle_new_schedule_click}, "Crear Nueva"),
            ),
            html.div(
                {"className": "flex-grow overflow-y-auto p-6"},
                # Llama a la función de renderizado correspondiente según el modo de vista
                render_list() if view_mode == "list" else render_form(),
            ),
            html.div(
                {"className": "flex justify-end items-center gap-3 px-6 py-4 border-t border-gray-200"},
                html.button({"className": "px-4 h-10 rounded-md bg-slate-700 text-white hover:bg-slate-600", "onClick": on_close}, "Cerrar"),
            ),
        ),
    )
