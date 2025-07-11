# src/interfaz_web/components/robot_table.py
from typing import Callable, Dict, List

from reactpy import component, event, html

from ..client.schemas.robot_types import Robot
from .robot_row import RobotRow


@component
def RobotTable(robots: List[Robot], on_action: Callable, sort_by: str, sort_dir: str, on_sort: Callable):
    table_headers = [
        {"key": "Robot", "label": "Robot"},
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

        sort_indicator = ""
        is_current_sort_col = sort_by == header_info["key"]
        if is_current_sort_col:
            sort_indicator = " ▲" if sort_dir == "asc" else " ▼"

        return html.th(
            {"scope": "col"},
            html.a(
                {"href": "#", "onClick": event(lambda e: on_sort(header_info["key"]), prevent_default=True)},
                header_info["label"],
                sort_indicator,
            ),
        )

    return html.article(
        html.div(
            {"className": "table-container"},  # Para que la tabla sea responsive en pantallas pequeñas
            html.table(
                {"className": "striped"},
                html.thead(html.tr(*[render_header(h) for h in table_headers])),
                html.tbody(
                    *[RobotRow(robot=robot, on_action=on_action) for robot in robots]
                    if robots
                    else html.tr(html.td({"colSpan": len(table_headers), "className": "text-center p-8"}, "No se encontraron robots.")),
                ),
            ),
        ),
    )
