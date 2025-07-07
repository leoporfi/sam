# src/interfaz_web/components/robot_table.py
from typing import Callable, Dict, List

from reactpy import component, html

from ..schemas.robot_types import Robot
from .robot_row import RobotRow


@component
def RobotTable(robots: List[Robot], on_action: Callable, sort_by: str, sort_dir: str, on_sort: Callable):
    table_headers = [
        {"key": "Robot", "label": "Nombre"},
        {"key": "CantidadEquiposAsignados", "label": "Equipos"},
        {"key": "Activo", "label": "Activo"},
        {"key": "EsOnline", "label": "Online"},
        {"key": "TieneProgramacion", "label": "Tipo Ejecución"},
        {"key": "PrioridadBalanceo", "label": "Prioridad"},
        {"key": "TicketsPorEquipoAdicional", "label": "Tickets/Equipo"},
        {"key": "Acciones", "label": "Acciones", "sortable": False},
    ]

    def render_header(header_info: Dict):
        is_sortable = header_info.get("sortable", True)
        if not is_sortable:
            return html.th(header_info["label"])

        is_current_sort_col = sort_by == header_info["key"]
        icon = ""
        if is_current_sort_col:
            icon = " 🔼" if sort_dir == "asc" else " 🔽"

        return html.th({"style": {"cursor": "pointer"}, "onClick": lambda e: on_sort(header_info["key"])}, header_info["label"], html.span(icon))

    return html.div(
        {"className": "box"},
        html.table(
            {"className": "table is-bordered is-striped is-narrow is-hoverable is-fullwidth"},
            html.thead(html.tr(*[render_header(h) for h in table_headers])),
            html.tbody(
                *[RobotRow(robot=robot, on_action=on_action) for robot in robots]
                if robots
                else html.tr(html.td({"colSpan": len(table_headers), "className": "text-center p-8 text-gray-500"}, "No se encontraron robots.")),
            ),
        ),
    )
