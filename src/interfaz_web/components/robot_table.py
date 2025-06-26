# src/interfaz_web/components/robot_table.py
from typing import Callable, List

from reactpy import component, html

from ..schemas.robot_types import Robot
from .robot_row import RobotRow


@component
def RobotTable(robots: List[Robot], on_action: Callable):
    """El componente que renderiza la tabla completa."""

    table_headers = ["Nombre", "Equipos", "Activo", "Online", "Prioridad", "Tickets/Equipo", "Acciones"]

    return html.div(
        {"className": "overflow-x-auto bg-white rounded-lg shadow"},
        html.table(
            {"className": "min-w-full divide-y divide-gray-200"},
            html.thead(
                {"className": "bg-gray-50"},
                html.tr(
                    *[
                        html.th(
                            {
                                "scope": "col",
                                "className": f"px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider {'text-right' if h == 'Acciones' else ''}",
                            },
                            h,
                        )
                        for h in table_headers
                    ]
                ),
            ),
            html.tbody(
                {"className": "bg-white divide-y divide-gray-200"},
                *[RobotRow(robot=robot, on_action=on_action) for robot in robots]
                if robots
                else html.tr(html.td({"colSpan": len(table_headers), "className": "text-center p-8 text-gray-500"}, "No se encontraron robots.")),
            ),
        ),
    )
