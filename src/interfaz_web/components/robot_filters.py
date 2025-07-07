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
        {"className": "field is-grouped mb-5"},  # 'field is-grouped' para agrupar controles
        html.p(
            {"className": "control is-expanded"},
            html.input(
                {
                    "type": "search",
                    "className": "input",  # Clase 'input' de Bulma
                    "placeholder": "Buscar robots por nombre...",
                    "value": search_term,
                    "onChange": lambda event: on_search_change(event["target"]["value"]),
                }
            ),
        ),
        html.p(
            {"className": "control"},
            html.div(
                {"className": "select"},  # Wrapper 'select' de Bulma
                html.select(
                    {
                        "value": active_filter,
                        "onChange": lambda event: on_active_change(event["target"]["value"]),
                    },
                    html.option({"value": "all"}, "Activo: Todos"),
                    html.option({"value": "true"}, "Solo Activos"),
                    html.option({"value": "false"}, "Solo Inactivos"),
                ),
            ),
        ),
        html.p(
            {"className": "control"},
            html.div(
                {"className": "select"},  # Wrapper 'select' de Bulma
                html.select(
                    {
                        "value": online_filter,
                        "onChange": lambda event: on_online_change(event["target"]["value"]),
                    },
                    html.option({"value": "all"}, "Online: Todos"),
                    html.option({"value": "true"}, "Solo Online"),
                    html.option({"value": "false"}, "Solo No Online"),
                ),
            ),
        ),
    )
