# interfaz_web/components/assignments_modal.py

import asyncio
from typing import Any, Callable, Dict

import httpx
from reactpy import component, html, use_context, use_effect, use_state

from .notifications import NotificationContext
from .styles import BUTTON_STYLES


@component
def AssignmentsModal(robot: Dict[str, Any] | None, on_close: Callable, on_save_success: Callable):
    """
    Modal para gestionar las asignaciones de equipos de un robot.
    """
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]
    # Estados para las listas de equipos
    assigned_teams, set_assigned_teams = use_state([])
    available_teams, set_available_teams = use_state([])

    # Estados para las selecciones del usuario (usamos sets para eficiencia)
    to_unassign, set_to_unassign = use_state(set())
    to_assign, set_to_assign = use_state(set())

    # Estado para mensajes de error o carga
    # error, set_error = use_state("")
    is_loading, set_is_loading = use_state(False)

    @use_effect(dependencies=[robot])
    async def fetch_data():
        if not robot:
            return

        set_is_loading(True)
        # set_error("")
        set_to_unassign(set())
        set_to_assign(set())

        # Usamos asyncio.gather para ejecutar las tareas en paralelo
        try:
            async with httpx.AsyncClient() as client:
                # Primero creamos las dos tareas de petición
                assigned_task = client.get(f"http://127.0.0.1:8000/api/robots/{robot['RobotId']}/asignaciones")
                available_task = client.get(f"http://127.0.0.1:8000/api/equipos/disponibles/{robot['RobotId']}")
                # available_task = client.get("http://127.0.0.1:8000/api/equipos/disponibles")

                # Luego, asyncio.gather las ejecuta concurrentemente
                assigned_res, available_res = await asyncio.gather(assigned_task, available_task)

                assigned_res.raise_for_status()
                available_res.raise_for_status()
                set_assigned_teams(assigned_res.json())
                set_available_teams(available_res.json())
        except Exception as e:
            # Mostramos el error en la interfaz
            show_notification(f"Error al cargar datos: {e}.", "error")
            # set_error(f"Error al cargar datos: {e}")
            set_assigned_teams([])
            set_available_teams([])
        finally:
            set_is_loading(False)

    if not robot:
        return None

    def handle_unassign_toggle(equipo_id, checked):
        set_to_unassign(lambda old: old | {equipo_id} if checked else old - {equipo_id})

    def handle_assign_toggle(equipo_id, checked):
        set_to_assign(lambda old: old | {equipo_id} if checked else old - {equipo_id})

    # --- Lógica para guardar los cambios ---
    async def handle_save(event):
        # set_error("")
        set_is_loading(True)
        try:
            payload = {"assign_team_ids": list(to_assign), "unassign_team_ids": list(to_unassign)}
            async with httpx.AsyncClient() as client:
                res = await client.post(f"http://127.0.0.1:8000/api/robots/{robot['RobotId']}/asignaciones", json=payload, timeout=30)
                res.raise_for_status()
            await on_save_success()
            on_close(None)  # Pasamos None porque on_close ahora espera un argumento
        except Exception as e:
            show_notification(f"Error al guardar los cambios: {e}", "error")
            # set_error(f"Error al guardar los cambios: {e}")
        finally:
            set_is_loading(False)

    def handle_overlay_click(event):
        if event["target"] == event["currentTarget"]:
            on_close(event)

    # --- Creación de las filas de las tablas ---
    def get_status_tag(team):
        if team.get("Reservado"):
            return html.span({"className": "px-3 py-1 text-xs font-medium rounded-full bg-yellow-300 text-yellow-900"}, "Reservado")
        if team.get("EsProgramado"):
            return html.span({"className": "px-3 py-1 text-xs font-medium rounded-full bg-blue-300 text-blue-900"}, "Programado")
        return html.span({"className": "px-3 py-1 text-xs font-medium rounded-full bg-green-300 text-green-900"}, "Dinámico")

    assigned_rows = [
        html.tr(
            {"key": team["EquipoId"]},
            html.td({"className": "px-6 py-4 text-sm text-gray-900"}, team["Equipo"]),
            html.td({"className": "px-6 py-4 text-sm"}, get_status_tag(team)),
            html.td(
                {"className": "px-6 py-4 text-center"},
                html.input(
                    {
                        "type": "checkbox",
                        "className": "h-5 w-5 rounded bg-slate-700 border-slate-600 text-blue-500 focus:ring-blue-500",
                        "checked": team["EquipoId"] in to_unassign,
                        "onChange": lambda e, eid=team["EquipoId"]: handle_unassign_toggle(eid, e["target"]["checked"]),
                    }
                ),
            ),
        )
        for team in assigned_teams
    ]

    available_rows = [
        html.tr(
            {"key": team["EquipoId"]},
            html.td({"className": "px-6 py-4 text-sm text-gray-900"}, team["Equipo"]),
            html.td(
                {"className": "px-6 py-4 text-center"},
                html.input(
                    {
                        "type": "checkbox",
                        "className": "h-5 w-5 rounded bg-slate-700 border-slate-600 text-blue-500",
                        "checked": team["EquipoId"] in to_assign,
                        "onChange": lambda e, eid=team["EquipoId"]: handle_assign_toggle(eid, e["target"]["checked"]),
                    }
                ),
            ),
        )
        for team in available_teams
    ]

    # Estilos para las etiquetas de estado
    status_styles = {
        "Reservado": "px-3 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800",
        "Programado": "px-3 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800",
        "Dinámico": "px-3 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800",
    }

    def get_status_tag(team):
        status = "Dinámico"
        if team.get("Reservado"):
            status = "Reservado"
        elif team.get("EsProgramado"):
            status = "Programado"
        return html.span({"className": status_styles[status]}, status)

    # --- Renderizado final del Modal ---
    return html.div(
        {"className": "fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4", "onClick": handle_overlay_click},
        html.div(
            {
                "className": "w-full max-w-3xl max-h-[90vh] flex flex-col rounded-lg bg-white shadow-2xl text-gray-900",
                "onClick": lambda e: e.stop_propagation() if hasattr(e, "stop_propagation") else None,
            },
            html.div(
                {"className": "p-6 border-b border-gray-200"},
                html.h1({"className": "text-2xl font-bold"}, "Gestionar Asignaciones de Equipos"),
                html.p({"className": "text-sm text-gray-500"}, f"Robot: {robot['Robot']}"),
            ),
            html.div(
                {"className": "flex-grow overflow-y-auto p-6 space-y-8"},
                # Tabla 1: Equipos Asignados
                html.div(
                    html.h3({"className": "text-lg font-semibold mb-4"}, "Equipos Asignados Actualmente"),
                    html.div(
                        {"className": "overflow-hidden rounded-lg border border-gray-200"},
                        html.table(
                            {"className": "min-w-full divide-y divide-gray-200"},
                            html.thead(
                                {"className": "bg-gray-50"},
                                html.tr(
                                    html.th({"scope": "col", "className": "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"}, "Nombre Equipo"),
                                    html.th({"scope": "col", "className": "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"}, "Estado"),
                                    html.th({"scope": "col", "className": "px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase"}, "Desasignar"),
                                ),
                            ),
                            html.tbody(
                                {"className": "bg-white divide-y divide-gray-200"},
                                assigned_rows if assigned_rows else html.tr(html.td({"colSpan": 3, "className": "text-center p-4 text-gray-500"}, "No hay equipos asignados.")),
                            ),
                        ),
                    ),
                ),
                # Tabla 2: Equipos Disponibles
                # ... (La estructura de la segunda tabla sigue el mismo patrón de estilos claros)
                html.div(
                    html.h3({"className": "text-lg font-semibold mb-4"}, "Equipos Disponibles para Asignar"),
                    html.div(
                        {"className": "overflow-hidden rounded-lg border border-gray-200"},
                        html.table(
                            {"className": "min-w-full divide-y divide-gray-200"},
                            html.thead(
                                {"className": "bg-gray-50"},
                                html.tr(
                                    html.th({"scope": "col", "className": "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"}, "Nombre Equipo"),
                                    html.th({"scope": "col", "className": "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"}, "Estado"),
                                    html.th({"scope": "col", "className": "px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase"}, "Asignar"),
                                ),
                            ),
                            html.tbody(
                                {"className": "bg-white divide-y divide-gray-200"},
                                available_rows if available_rows else html.tr(html.td({"colSpan": 3, "className": "text-center p-4 text-gray-500"}, "No hay equipos disponibles.")),
                            ),
                        ),
                    ),
                ),
            ),
            html.div(
                {"className": "flex justify-end items-center gap-3 px-6 py-4 border-t border-gray-200"},
                html.button({"className": BUTTON_STYLES["secondary"], "onClick": on_close, "disabled": is_loading}, "Cancelar"),
                html.button({"className": BUTTON_STYLES["primary"], "onClick": handle_save, "disabled": is_loading}, "Aplicar Cambios")
            ),
        ),
    )
