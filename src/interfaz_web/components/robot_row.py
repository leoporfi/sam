# src/interfaz_web/components/robot_row.py
from typing import Callable

from reactpy import component, event, html

from ..client.schemas.robot_types import Robot


@component
def RobotRow(robot: Robot, on_action: Callable):
    """
    Renderiza una única fila para la tabla de robots con manejadores de eventos asíncronos corregidos.
    """

    async def handle_action(action_name: str, event_data=None):
        """Maneja las acciones del robot de forma asíncrona"""
        await on_action(action_name, robot)

    # Funciones auxiliares para los manejadores de eventos
    async def handle_edit(event_data):
        await handle_action("edit")

    async def handle_assign(event_data):
        await handle_action("assign")

    async def handle_schedule(event_data):
        await handle_action("schedule")

    async def handle_toggle_active(event_data):
        await handle_action("toggle_active")

    async def handle_toggle_online(event_data):
        await handle_action("toggle_online")

    # Definición de acciones para el menú
    actions = [
        {"label": "Editar", "on_click": handle_edit},
        {"label": "Asignar", "on_click": handle_assign},
        {"label": "Programar", "on_click": handle_schedule},
    ]

    return html.tr(
        {"key": robot["RobotId"]},
        html.td(robot["Robot"]),
        html.td(robot.get("CantidadEquiposAsignados", 0)),
        html.td(
            html.fieldset(
                html.label(
                    html.input(
                        {
                            "type": "checkbox",
                            "role": "switch",
                            "checked": robot["Activo"],
                            "onChange": handle_toggle_active,
                        }
                    )
                )
            )
        ),
        html.td(
            html.fieldset(
                html.label(
                    html.input(
                        {
                            "type": "checkbox",
                            "role": "switch",
                            "checked": robot["EsOnline"],
                            "onChange": handle_toggle_online,
                        }
                    )
                )
            )
        ),
        html.td("Programado" if robot.get("TieneProgramacion") else "A Demanda"),
        html.td(str(robot["PrioridadBalanceo"])),
        html.td(str(robot.get("TicketsPorEquipoAdicional", "N/A"))),
        # html.td(ActionMenu(actions=actions)),
        html.td(
            # Usamos un div con la clase grid para alinear los íconos horizontalmente
            html.div(
                {"className": "grid"},
                # Botón/Icono para Editar
                html.a(
                    {
                        "href": "#",
                        "onClick": event(handle_edit, prevent_default=True),
                        "data-tooltip": "Editar Robot",  # Tooltip de Pico.css
                        "className": "secondary",
                    },
                    html.i({"className": "fa-solid fa-pencil"}),
                ),
                # Botón/Icono para Asignar
                html.a(
                    {
                        "href": "#",
                        "onClick": event(handle_assign, prevent_default=True),
                        "data-tooltip": "Asignar Equipos",  # Tooltip de Pico.css
                        "className": "secondary",
                    },
                    html.i({"className": "fa-solid fa-users"}),
                ),
                # Botón/Icono para Programar
                html.a(
                    {
                        "href": "#",
                        "onClick": event(handle_schedule, prevent_default=True),
                        "data-tooltip": "Programar Tareas",
                        "data-placement": "left",  # Tooltip de Pico.css
                        "className": "secondary",
                    },
                    html.i({"className": "fa-solid fa-clock"}),
                ),
            )
        ),
    )
