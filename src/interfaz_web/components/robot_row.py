# src/interfaz_web/components/robot_row.py
from typing import Callable

from reactpy import component, html

from ..schemas.robot_types import Robot
from .common.action_menu import ActionMenu


@component
def RobotRow(robot: Robot, on_action: Callable):
    """
    Renderiza una única fila para la tabla de robots, con manejadores de eventos
    asíncronos correctos.
    """
    # --- INICIO DE LA CORRECCIÓN ---

    # 1. Creamos funciones 'async def' con nombre para CADA acción.
    #    ReactPy sabe cómo manejar estas funciones cuando se le pasan a un 'onClick'.
    async def handle_edit(event=None):
        await on_action("edit", robot)

    async def handle_assign(event=None):
        await on_action("assign", robot)

    async def handle_schedule(event=None):
        await on_action("schedule", robot)

    async def handle_toggle_active(event=None):
        await on_action("toggle_active", robot)

    async def handle_toggle_online(event=None):
        await on_action("toggle_online", robot)

    # 2. Creamos la lista de acciones para el menú, pasando las NUEVAS funciones.
    actions = [
        {"label": "Editar Propiedades", "on_click": handle_edit},
        {"label": "Gestionar Asignaciones", "on_click": handle_assign},
        {"label": "Gestionar Programaciones", "on_click": handle_schedule},
    ]

    # --- FIN DE LA CORRECCIÓN ---

    return html.tr(
        {"key": robot["RobotId"]},
        html.td({"className": "px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"}, robot["Robot"]),
        html.td({"className": "px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center"}, robot.get("CantidadEquiposAsignados", 0)),
        html.td(
            {"className": "px-6 py-4 whitespace-nowrap text-sm"},
            html.label(
                {"className": "relative inline-flex items-center cursor-pointer"},
                html.input({"type": "checkbox", "className": "sr-only peer", "checked": robot["Activo"], "onChange": handle_toggle_active}),
                html.div(
                    {
                        "className": "w-11 h-6 bg-gray-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"
                    }
                ),
            ),
        ),
        html.td(
            {"className": "px-6 py-4 whitespace-nowrap text-sm"},
            html.label(
                {"className": "relative inline-flex items-center cursor-pointer"},
                html.input({"type": "checkbox", "className": "sr-only peer", "checked": robot["EsOnline"], "onChange": handle_toggle_online}),
                html.div(
                    {
                        "className": "w-11 h-6 bg-gray-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"
                    }
                ),
            ),
        ),
        html.td({"className": "px-6 py-4 whitespace-nowrap text-sm text-gray-500"}, str(robot["PrioridadBalanceo"])),
        html.td({"className": "px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center"}, str(robot.get("TicketsPorEquipoAdicional", "N/A"))),
        html.td({"className": "px-6 py-4 whitespace-nowrap text-sm font-medium text-right"}, ActionMenu(actions=actions)),
    )
