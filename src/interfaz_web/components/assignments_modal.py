# src/interfaz_web/components/assignments_modal.py
import asyncio
from typing import Any, Callable, Dict, List

from reactpy import component, event, html, use_context, use_effect, use_state

from ..client.api_service import get_api_service
from .notifications import NotificationContext


# AssignmentsModal
@component
def AssignmentsModal(robot: Dict[str, Any] | None, on_close: Callable, on_save_success: Callable):
    # El estado se inicializa correctamente con listas
    assigned_teams, set_assigned_teams = use_state([])
    available_teams, set_available_teams = use_state([])
    to_unassign, set_to_unassign = use_state([])
    to_assign, set_to_assign = use_state([])
    is_loading, set_is_loading = use_state(False)

    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    api_service = get_api_service()

    @use_effect(dependencies=[robot])
    def fetch_data():
        async def get_data():
            if not robot:
                return
            set_is_loading(True)
            set_to_unassign([])
            set_to_assign([])
            try:
                assigned_res = await api_service.get_robot_assignments(robot["RobotId"])
                available_res = await api_service.get_available_teams(robot["RobotId"])
                set_assigned_teams(assigned_res)
                set_available_teams(available_res)
            except Exception as e:
                show_notification(f"Error al cargar datos: {e}", "error")
            finally:
                set_is_loading(False)

        asyncio.create_task(get_data())

    async def handle_save(event_data):
        set_is_loading(True)
        try:
            await api_service.update_robot_assignments(robot["RobotId"], to_assign, to_unassign)
            await on_save_success()
            show_notification("Se actualizó la asiganación correctamente", "success")
        except Exception as e:
            show_notification(f"Error al guardar: {e}", "error")
        finally:
            set_is_loading(False)

    if not robot:
        return None

    def get_estado(team: Dict) -> tuple[str, str]:
        if team.get("EsProgramado"):
            return ("Programado", "tag-programado")
        if team.get("Reservado"):
            return ("Reservado", "tag-reservado")
        return ("Dinámico", "tag-dinamico")

    return html.dialog(
        {"open": True},
        html.article(
            html.header(
                html.button({"aria-label": "Close", "rel": "prev", "onClick": event(on_close, prevent_default=True)}),
                html.h2("Asignación de Robots"),
                html.p(f"{robot.get('Robot', '')}"),
            ),
            html.div(
                {"className": "grid"},
                # Columna de Equipos Asignados
                html.div(
                    html.h5("Equipos Asignados"),
                    html.div(
                        {"style": {"maxHeight": "40vh", "overflow-y": "auto", "font-size": "0.90rem"}},
                        html.table(
                            html.thead(
                                html.tr(
                                    html.th(
                                        html.input(
                                            {
                                                "type": "checkbox",
                                                "onChange": lambda e: set_to_unassign(
                                                    list({team["EquipoId"] for team in assigned_teams}) if e["target"]["checked"] else []
                                                ),
                                            }
                                        )
                                    ),
                                    html.th("Nombre Equipo"),
                                    html.th("Estado"),
                                )
                            ),
                            html.tbody(
                                *[
                                    html.tr(
                                        {"key": team["EquipoId"]},
                                        html.td(
                                            html.input(
                                                {
                                                    "type": "checkbox",
                                                    "checked": team["EquipoId"] in to_unassign,
                                                    "onChange": lambda e, eid=team["EquipoId"]: set_to_unassign(
                                                        (to_unassign + [eid]) if e["target"]["checked"] else [i for i in to_unassign if i != eid]
                                                    ),
                                                }
                                            )
                                        ),
                                        html.td(team["Equipo"]),
                                        html.td(
                                            # Usamos un <span> para poder darle estilo si queremos
                                            html.span(
                                                {"className": f"tag {get_estado(team)[1]}"},
                                                get_estado(team)[0],  # Llamamos a la función para obtener el texto
                                            )
                                        ),
                                    )
                                    for team in assigned_teams
                                    if isinstance(team, dict)
                                ]
                            ),
                        ),
                    ),
                ),
                # Columna de Equipos Disponibles
                html.div(
                    html.h5("Equipos Disponibles"),
                    html.div(
                        {"style": {"maxHeight": "40vh", "overflow-y": "auto", "font-size": "0.90rem"}},
                        html.table(
                            html.thead(
                                html.tr(
                                    html.th(
                                        html.input(
                                            {
                                                "type": "checkbox",
                                                "onChange": lambda e: set_to_assign(
                                                    list({team["EquipoId"] for team in available_teams}) if e["target"]["checked"] else []
                                                ),
                                            }
                                        )
                                    ),
                                    html.th("Nombre Equipo"),
                                )
                            ),
                            html.tbody(
                                *[
                                    html.tr(
                                        {"key": team["EquipoId"]},
                                        html.td(
                                            html.input(
                                                {
                                                    "type": "checkbox",
                                                    "checked": team["EquipoId"] in to_assign,
                                                    "onChange": lambda e, eid=team["EquipoId"]: set_to_assign(
                                                        (to_assign + [eid]) if e["target"]["checked"] else [i for i in to_assign if i != eid]
                                                    ),
                                                }
                                            )
                                        ),
                                        html.td(team["Equipo"]),
                                    )
                                    for team in available_teams
                                    if isinstance(team, dict)
                                ]
                            ),
                        ),
                    ),
                ),
            ),
            html.footer(
                html.button({"className": "secondary", "onClick": on_close, "disabled": is_loading}, "Cancelar"),
                html.button({"aria-busy": str(is_loading).lower(), "onClick": handle_save, "disabled": is_loading}, "Guardar"),
            ),
        ),
    )
