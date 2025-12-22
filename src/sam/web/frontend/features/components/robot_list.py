# sam/web/frontend/features/components/robot_list.py
"""
Componentes para la gestión de robots.

Este módulo contiene los componentes para listar, mostrar y gestionar robots,
siguiendo el estándar de ReactPy de SAM.
"""

from typing import Callable, Dict, List

from reactpy import component, event, html, use_state

from sam.web.backend.schemas import Robot

from ...shared.async_content import AsyncContent
from ...shared.common_components import Pagination
from ...shared.styles import (
    BUTTON_PRIMARY,
    CARDS_CONTAINER_ROBOTS,
    COLLAPSIBLE_PANEL,
    COLLAPSIBLE_PANEL_EXPANDED,
    DASHBOARD_CONTROLS,
    MASTER_CONTROLS_GRID,
    MOBILE_CONTROLS_TOGGLE,
    ROBOT_CARD,
    ROBOT_CARD_BODY,
    ROBOT_CARD_FOOTER,
    ROBOT_CARD_HEADER,
    SEARCH_INPUT,
    STATUS_EJECUCION_DEMANDA,
    STATUS_EJECUCION_PROGRAMADO,
    TABLE_CONTAINER,
)


@component
def RobotsControls(
    is_syncing: bool,
    on_sync: Callable,
    on_create_robot: Callable,
    search_term: str,
    on_search_change: Callable,
    active_filter: str,
    on_active_change: Callable,
    online_filter: str,
    on_online_change: Callable,
    is_searching: bool,
    # Nuevos parámetros para sincronización de equipos
    is_syncing_equipos: bool = False,
    on_sync_equipos: Callable = None,
):
    """Controles para el dashboard de Robots (título, botones, filtros)."""
    is_expanded, set_is_expanded = use_state(False)

    collapsible_panel_class = COLLAPSIBLE_PANEL_EXPANDED if is_expanded else COLLAPSIBLE_PANEL

    return html.div(
        {"class_name": DASHBOARD_CONTROLS},
        html.div(
            {"class_name": "controls-header"},
            html.h2("Gestión de Robots"),
            html.button(
                {
                    "class_name": MOBILE_CONTROLS_TOGGLE,
                    "on_click": lambda e: set_is_expanded(not is_expanded),
                },
                html.i({"class_name": f"fa-solid fa-chevron-{'up' if is_expanded else 'down'}"}),
                " Controles",
            ),
        ),
        html.div(
            {"class_name": collapsible_panel_class},
            html.div(
                {"class_name": MASTER_CONTROLS_GRID, "style": {"gridTemplateColumns": "5fr 2fr 2fr 1fr"}},
                html.input(
                    {
                        "type": "search",
                        "name": "search-robot",
                        "placeholder": "Buscar robots por nombre...",
                        "value": search_term,
                        "on_change": lambda event: on_search_change(event["target"]["value"].strip()),
                        "aria-busy": str(is_searching).lower(),
                        "class_name": SEARCH_INPUT,
                    }
                ),
                html.select(
                    {
                        "name": "filter-activo",
                        "value": active_filter,
                        "on_change": lambda event: on_active_change(event["target"]["value"]),
                    },
                    html.option({"value": "all"}, "Activo: Todos"),
                    html.option({"value": "true"}, "Solo Activos"),
                    html.option({"value": "false"}, "Solo Inactivos"),
                ),
                html.select(
                    {
                        "name": "filter-online",
                        "value": online_filter,
                        "on_change": lambda event: on_online_change(event["target"]["value"]),
                    },
                    html.option({"value": "all"}, "Online: Todos"),
                    html.option({"value": "true"}, "Solo Online"),
                    html.option({"value": "false"}, "Solo Programados"),
                ),
                html.button(
                    {"on_click": on_create_robot, "type": "button", "class_name": BUTTON_PRIMARY},
                    html.i({"class_name": "fa-solid fa-plus"}),
                    " Robot",
                ),
            ),
        ),
    )


@component
def RobotsDashboard(robots: List[Robot], on_action: Callable, robots_state: Dict, set_current_page: Callable):
    """Componente principal que renderiza la tabla/tarjetas y la paginación."""
    loading = robots_state["loading"]
    error = robots_state["error"]
    current_page = robots_state["current_page"]
    total_pages = robots_state["total_pages"]
    total_count = robots_state["total_count"]
    page_size = robots_state["page_size"]

    pagination_component = (
        Pagination(
            current_page=current_page,
            total_pages=total_pages,
            total_items=total_count,
            items_per_page=page_size,
            on_page_change=set_current_page,
        )
        if total_pages > 1
        else None
    )

    # Usar AsyncContent para manejar estados de carga/error/vacío
    return AsyncContent(
        loading=loading and not robots,
        error=error,
        data=robots,
        empty_message="No se encontraron robots.",
        children=html._(
            pagination_component,
            html.div(
                {"class_name": CARDS_CONTAINER_ROBOTS},
                *[RobotCard(robot=robot, on_action=on_action) for robot in robots],
            ),
            html.div(
                {"class_name": TABLE_CONTAINER},
                RobotTable(
                    robots=robots,
                    on_action=on_action,
                    sort_by=robots_state["sort_by"],
                    sort_dir=robots_state["sort_dir"],
                    on_sort=robots_state["handle_sort"],
                ),
            ),
        ),
    )


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
                {"href": "#", "on_click": event(lambda e: on_sort(header_info["key"]), prevent_default=True)},
                header_info["label"],
                sort_indicator,
            ),
        )

    return html.article(
        html.table(
            html.thead(html.tr(*[render_header(h) for h in table_headers])),
            html.tbody(
                *[RobotRow(robot=robot, on_action=on_action) for robot in robots]
                if robots
                else [
                    html.tr(
                        html.td(
                            {"colSpan": len(table_headers), "style": {"text_align": "center"}},
                            "No se encontraron robots.",
                        )
                    )
                ]
            ),
        )
    )


@component
def RobotRow(robot: Robot, on_action: Callable):
    async def handle_toggle_active(event):
        await on_action("toggle_active", robot)

    async def handle_toggle_online(event):
        try:
            await on_action("toggle_online", robot)
        except Exception as e:
            print(f"Error toggling online status: {e}")

    async def handle_edit(event):
        await on_action("edit", robot)

    async def handle_assign(event):
        await on_action("assign", robot)

    async def handle_schedule(event):
        await on_action("schedule", robot)

    is_programado = robot.get("TieneProgramacion", False)
    tipo_ejecucion_text = "Programado" if is_programado else "A Demanda"
    tipo_ejecucion_class = STATUS_EJECUCION_PROGRAMADO if is_programado else STATUS_EJECUCION_DEMANDA

    return html.tr(
        {"key": robot["RobotId"]},
        html.td({"title": robot["Descripcion"]}, robot["Robot"]),
        html.td(robot.get("CantidadEquiposAsignados", 0)),
        html.td(
            html.label(
                html.input(
                    {
                        "type": "checkbox",
                        "name": "checkbox-activo",
                        "role": "switch",
                        "checked": robot["Activo"],
                        "on_change": event(handle_toggle_active),
                    }
                )
            )
        ),
        html.td(
            html.label(
                html.input(
                    {
                        "type": "checkbox",
                        "name": "checkbox-EsOnline",
                        "role": "switch",
                        "checked": robot["EsOnline"],
                        "on_change": event(handle_toggle_online),
                        "disabled": is_programado,  # Deshabilitar si está programado
                        "title": "No se puede marcar como Online si tiene programaciones"
                        if is_programado
                        else "Marcar como Online/Offline",
                        "aria-label": f"Marcar Online/Offline robot {robot['Robot']}",
                    }
                )
            )
        ),
        html.td(html.span({"class_name": tipo_ejecucion_class}, tipo_ejecucion_text)),
        html.td(str(robot["PrioridadBalanceo"])),
        html.td(str(robot.get("TicketsPorEquipoAdicional", "N/A"))),
        html.td(
            html.div(
                {"class_name": "grid"},
                html.a(
                    {
                        "href": "#",
                        "on_click": event(handle_edit, prevent_default=True),
                        "data-tooltip": "Editar Robot",
                        "class_name": "secondary",
                    },
                    html.i({"class_name": "fa-solid fa-pencil"}),
                ),
                html.a(
                    {
                        "href": "#",
                        "on_click": event(handle_assign, prevent_default=True),
                        "data-tooltip": "Asignar Equipos",
                        "class_name": "secondary",
                    },
                    html.i({"class_name": "fa-solid fa-computer"}),
                ),
                html.a(
                    {
                        "href": "#",
                        "on_click": event(handle_schedule, prevent_default=True),
                        "data-tooltip": "Programar Robots",
                        "data-placement": "left",
                        "class_name": "secondary",
                    },
                    html.i({"class_name": "fa-solid fa-clock"}),
                ),
            )
        ),
    )


@component
def RobotCard(robot: Robot, on_action: Callable):
    async def handle_toggle_active(event):
        await on_action("toggle_active", robot)

    async def handle_toggle_online(event):
        try:
            await on_action("toggle_online", robot)
        except Exception as e:
            print(f"Error toggling online status: {e}")

    async def handle_edit(event):
        await on_action("edit", robot)

    async def handle_assign(event):
        await on_action("assign", robot)

    async def handle_schedule(event):
        await on_action("schedule", robot)

    is_programado = robot.get("TieneProgramacion", False)
    tipo_ejecucion_text = "Programado" if is_programado else "A Demanda"
    tipo_ejecucion_class = STATUS_EJECUCION_PROGRAMADO if is_programado else STATUS_EJECUCION_DEMANDA

    return html.article(
        {"key": robot["RobotId"], "class_name": ROBOT_CARD},
        html.div(
            {"class_name": ROBOT_CARD_HEADER},
            html.h5(robot["Robot"]),
        ),
        html.div(
            {"class_name": ROBOT_CARD_BODY},
            html.div(
                {"class_name": "grid"},
                html.label(
                    html.input(
                        {
                            "type": "checkbox",
                            "name": "checkbox-activo",
                            "role": "switch",
                            "checked": robot["Activo"],
                            "on_change": event(handle_toggle_active),
                        }
                    ),
                    "Activo",
                ),
                html.label(
                    html.input(
                        {
                            "type": "checkbox",
                            "name": "checkbox-Esonline",
                            "role": "switch",
                            "checked": robot["EsOnline"],
                            "on_change": event(handle_toggle_online),
                        }
                    ),
                    "Online",
                ),
            ),
            html.p(f"Equipos: {robot.get('CantidadEquiposAsignados', 0)}"),
            html.p("Ejecución: ", html.span({"class_name": tipo_ejecucion_class}, tipo_ejecucion_text)),
        ),
        html.footer(
            {"class_name": ROBOT_CARD_FOOTER},
            html.button({"class_name": "outline secondary", "on_click": event(handle_edit)}, "Editar"),
            html.button({"class_name": "outline secondary", "on_click": event(handle_assign)}, "Asignar"),
            html.button({"class_name": "outline secondary", "on_click": event(handle_schedule)}, "Programar"),
        ),
    )
