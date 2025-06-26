# src/interfaz_web/components/robot_filters.py
from typing import Callable

from reactpy import component, html


@component
def RobotFilters(
    search_term: str,
    active_filter: str,
    online_filter: str,
    on_search_change: Callable,
    on_active_change: Callable,
    on_online_change: Callable,
):
    """Componente que encapsula la UI de los filtros."""
    return html.div(
        {"className": "flex flex-col sm:flex-row gap-4 mb-6"},
        # Barra de búsqueda
        html.div(
            {"className": "relative flex-grow"},
            html.input(
                {
                    "type": "search",
                    "className": "w-full pl-4 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500",
                    "placeholder": "Buscar robots por nombre...",
                    "value": search_term,
                    "onChange": lambda event: on_search_change(event["target"]["value"]),
                }
            ),
        ),
        # Filtros desplegables
        html.div(
            {"className": "flex gap-3"},
            html.select(
                {
                    "className": "border-gray-300 rounded-lg",
                    "value": active_filter,
                    "onChange": lambda event: on_active_change(event["target"]["value"]),
                },
                html.option({"value": "all"}, "Activo: Todos"),
                html.option({"value": "true"}, "Solo Activos"),
                html.option({"value": "false"}, "Solo Inactivos"),
            ),
            html.select(
                {
                    "className": "border-gray-300 rounded-lg",
                    "value": online_filter,
                    "onChange": lambda event: on_online_change(event["target"]["value"]),
                },
                html.option({"value": "all"}, "Online: Todos"),
                html.option({"value": "true"}, "Solo Online"),
                html.option({"value": "false"}, "Solo No Online"),
            ),
        ),
    )
