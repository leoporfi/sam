# sam/web/frontend/features/components/schedule_list.py
"""
Componentes para la gestión de programaciones (schedules).

Este módulo contiene los componentes para listar, mostrar y gestionar programaciones,
siguiendo el estándar de ReactPy de SAM.
"""

from typing import Any, Callable, Dict, List, Optional

from reactpy import component, event, html, use_state

# Usamos el tipo ScheduleData de schemas para hint, aunque es un dict en runtime
from sam.web.backend.schemas import ScheduleData

from ...shared.async_content import AsyncContent
from ...shared.common_components import Pagination, SearchInput
from ...shared.formatters import format_equipos_list, format_schedule_details, format_time
from ...shared.styles import (
    CARDS_CONTAINER,
    COLLAPSIBLE_PANEL,
    COLLAPSIBLE_PANEL_EXPANDED,
    DASHBOARD_CONTROLS,
    MASTER_CONTROLS_GRID,
    MOBILE_CONTROLS_TOGGLE,
    SCHEDULE_CARD,
    SEARCH_INPUT,
    TABLE_CONTAINER,
    TAG,
)


def _to_bool(value: Any) -> bool:
    """Convierte un valor a booleano, manejando None, 0, 1, True, False, strings."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, str)):
        if isinstance(value, str) and value.isdigit():
            return bool(int(value))
        return bool(value)
    return bool(value)


# Tipos de programación disponibles (se usan en varios lugares)
SCHEDULE_TYPES = ["Diaria", "Semanal", "Mensual", "RangoMensual", "Especifica"]


@component
def SchedulesControls(
    search: str,
    on_search: Callable,
    robot_filter: Optional[int],
    on_robot: Callable,
    tipo_filter: Optional[str],
    on_tipo: Callable,
    on_new: Callable,
    robots_list: List[Dict],
    is_searching: bool,
    on_search_execute: Optional[Callable[[str], Any]] = None,
):
    is_expanded, set_is_expanded = use_state(False)
    collapsible_panel_class = COLLAPSIBLE_PANEL_EXPANDED if is_expanded else COLLAPSIBLE_PANEL

    # Valor controlado del select de Tipo:
    # - "ALL" representa "Tipo: Todos" (sin filtro)
    # - Cualquier otro valor debe ser uno de SCHEDULE_TYPES
    tipo_select_value = tipo_filter if tipo_filter in SCHEDULE_TYPES else "ALL"

    return html.div(
        {"class_name": DASHBOARD_CONTROLS},
        html.div(
            {"class_name": "controls-header"},
            html.h2("Gestión de Programaciones"),
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
                {
                    "class_name": MASTER_CONTROLS_GRID,
                    "style": {"gridTemplateColumns": "5fr 2fr 2fr 1fr"},
                },
                SearchInput(
                    placeholder="Buscar robots por nombre... (Presiona Enter)",
                    value=search,
                    on_execute=on_search_execute or (lambda v: on_search(v)),
                    class_name=SEARCH_INPUT,
                    name="search-schedule",
                    aria_busy=str(is_searching).lower(),
                ),
                html.select(
                    {
                        "name": "filter-tipo",
                        "value": tipo_select_value,
                        # Cuando el usuario selecciona "Tipo: Todos" (ALL),
                        # enviamos None al estado de filtros para que no aplique filtro de tipo.
                        "on_change": lambda e: on_tipo(e["target"]["value"] if e["target"]["value"] != "ALL" else None),
                    },
                    html.option({"value": "ALL"}, "Tipo: Todos"),
                    *[html.option({"value": t}, t) for t in SCHEDULE_TYPES],
                ),
                html.select(
                    {
                        "name": "filter-robot",
                        "value": str(robot_filter) if robot_filter else "",
                        "on_change": lambda e: on_robot(int(e["target"]["value"]) if e["target"]["value"] else None),
                    },
                    html.option({"value": ""}, "Robot: Todos"),
                    *[html.option({"value": str(r["RobotId"])}, r["Robot"]) for r in robots_list],
                ),
                html.button(
                    {
                        "on_click": on_new,
                        "data-tooltip": "Crear nueva programación",
                        # Añadimos estilo para centrar ícono
                        "style": {
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "gap": "0.5rem",
                        },
                    },
                    html.i({"class_name": "fa-solid fa-plus"}),
                    " Programación",
                ),
            ),
        ),
    )


@component
def SchedulesDashboard(
    schedules: List[ScheduleData],
    on_toggle: Callable,
    on_edit: Callable,
    on_assign_equipos: Callable,
    on_delete: Callable,
    current_page: int,
    total_pages: int,
    on_page_change: Callable,
    total_count: int,
    loading: bool,
    error: str,
):
    """Componente principal que renderiza la tabla y paginación."""
    pagination_component = (
        Pagination(current_page, total_pages, len(schedules), total_count, on_page_change) if total_pages > 1 else None
    )

    # Usar AsyncContent para manejar estados de carga/error/vacío
    return AsyncContent(
        loading=loading,
        error=error,
        data=schedules,
        empty_message="No se encontraron programaciones.",
        children=html._(
            pagination_component,
            html.div(
                {"class_name": CARDS_CONTAINER},
                [
                    ScheduleCard(
                        schedule=s,
                        on_toggle=on_toggle,
                        on_edit=on_edit,
                        on_assign_equipos=on_assign_equipos,
                        on_delete=on_delete,
                        key=str(s["ProgramacionId"]),  # Importante para el rendimiento de renderizado
                    )
                    for s in schedules
                ],
            ),
            html.div(
                {"class_name": TABLE_CONTAINER},
                SchedulesTable(schedules, on_toggle, on_edit, on_assign_equipos, on_delete),
            ),
        ),
    )


@component
def SchedulesTable(
    schedules: List[ScheduleData],
    on_toggle: Callable,
    on_edit: Callable,
    on_assign_equipos: Callable,
    on_delete: Callable,
):
    headers = ["Robot", "Tipo", "Hora", "Días / Fecha", "Tol.", "Equipos", "Activo", "Acciones"]

    return html.article(
        html.table(
            html.thead(html.tr(*[html.th(h) for h in headers])),
            html.tbody(
                *[
                    html.tr(
                        {"key": s["ProgramacionId"]},
                        html.td(s["RobotNombre"]),
                        html.td(
                            html.div(
                                {"style": {"display": "flex", "gap": "0.5rem", "flexWrap": "wrap"}},
                                html.span({"class_name": "tag"}, s["TipoProgramacion"]),
                                html.span(
                                    {
                                        "class_name": "tag",
                                        "style": {
                                            "backgroundColor": "var(--pico-primary-background)",
                                            "color": "var(--pico-primary-inverse)",
                                        },
                                    },
                                    "Cíclico",
                                )
                                if _to_bool(s.get("EsCiclico"))
                                else None,
                            )
                        ),
                        html.td(
                            html.strong(
                                f"{format_time(s['HoraInicio'])}"
                                + (
                                    f" - {format_time(s.get('HoraFin'))}"
                                    if _to_bool(s.get("EsCiclico")) and s.get("HoraFin")
                                    else ""
                                )
                            )
                        ),
                        html.td(format_schedule_details(s)),
                        html.td(f"{s['Tolerancia']} min"),
                        html.td(
                            {"style": {"fontSize": "0.9em", "maxWidth": "250px", "whiteSpace": "normal"}},
                            format_equipos_list(s.get("EquiposProgramados"), max_visible=10),
                        ),
                        html.td(
                            html.label(
                                html.input(
                                    {
                                        "title": "Activar/Desactivar",
                                        "type": "checkbox",
                                        "role": "switch",
                                        "checked": s["Activo"],
                                        "on_change": event(
                                            lambda e, sid=s["ProgramacionId"]: on_toggle(sid, e["target"]["checked"])
                                        ),
                                    }
                                ),
                            )
                        ),
                        html.td(
                            html.div(
                                {"class_name": "grid"},
                                html.a(
                                    {
                                        "href": "#",
                                        "on_click": event(
                                            lambda e, sid=s["ProgramacionId"]: on_edit(sid), prevent_default=True
                                        ),
                                        "data-tooltip": "Editar",
                                        "class_name": "secondary",
                                    },
                                    html.i({"class_name": "fa-solid fa-pencil"}),
                                ),
                                html.a(
                                    {
                                        "href": "#",
                                        "on_click": event(
                                            lambda e, sched=s: on_assign_equipos(sched),
                                            prevent_default=True,
                                        ),
                                        "data-tooltip": "Asignar Equipos",
                                        "class_name": "secondary",
                                    },
                                    html.i({"class_name": "fa-solid fa-computer"}),
                                ),
                                html.a(
                                    {
                                        "href": "#",
                                        "on_click": event(
                                            lambda e, sched=s: on_delete(sched),
                                            prevent_default=True,
                                        ),
                                        "data-tooltip": "Eliminar Programación",
                                        "data-placement": "left",
                                        "class_name": "secondary",
                                    },
                                    html.i({"class_name": "fa-solid fa-trash"}),
                                ),
                            ),
                        ),
                    )
                    for s in schedules
                ]
            ),
        )
    )


@component
def ScheduleCard(
    schedule: ScheduleData, on_toggle: Callable, on_edit: Callable, on_assign_equipos: Callable, on_delete: Callable
):
    return html.article(
        {"key": schedule["ProgramacionId"], "class_name": SCHEDULE_CARD},
        html.header(
            html.div(
                {"style": {"display": "flex", "justifyContent": "space-between", "alignItems": "center"}},
                html.h5({"style": {"margin": 0}}, schedule["RobotNombre"]),
                html.div(
                    {"style": {"display": "flex", "gap": "0.5rem", "alignItems": "center"}},
                    html.span({"class_name": TAG}, schedule["TipoProgramacion"]),
                    html.span(
                        {
                            "class_name": TAG,
                            "style": {
                                "backgroundColor": "var(--pico-primary-background)",
                                "color": "var(--pico-primary-inverse)",
                            },
                        },
                        "Cíclico",
                    )
                    if _to_bool(schedule.get("EsCiclico"))
                    else None,
                ),
            )
        ),
        html.div(
            html.p(
                html.i(
                    {
                        "class_name": "fa-regular fa-clock",
                        "style": {"marginRight": "8px", "color": "var(--pico-muted-color)"},
                    }
                ),
                html.strong(
                    f"{format_time(schedule['HoraInicio'])}"
                    + (
                        f" - {format_time(schedule.get('HoraFin'))}"
                        if _to_bool(schedule.get("EsCiclico")) and schedule.get("HoraFin")
                        else ""
                    )
                ),
            ),
            html.p(
                html.i(
                    {
                        "class_name": "fa-regular fa-calendar",
                        "style": {"marginRight": "8px", "color": "var(--pico-muted-color)"},
                    }
                ),
                f"{format_schedule_details(schedule)}",
            ),
            html.p(
                html.i(
                    {
                        "class_name": "fa-solid fa-desktop",
                        "style": {"marginRight": "8px", "color": "var(--pico-muted-color)"},
                    }
                ),
                f"{schedule['EquiposProgramados'] or '-'}",
            ),
            html.small({"style": {"color": "var(--pico-muted-color)"}}, f"Tolerancia: {schedule['Tolerancia']} min"),
        ),
        html.footer(
            html.div(
                {"class_name": "grid"},
                html.label(
                    {
                        "class_name": "toggle-switch",
                        "style": {"display": "flex", "alignItems": "center", "cursor": "pointer"},
                    },
                    html.input(
                        {
                            "type": "checkbox",
                            "role": "switch",
                            "checked": schedule["Activo"],
                            "on_click": event(
                                lambda e, sid=schedule["ProgramacionId"]: on_toggle(sid, e["target"]["checked"])
                            ),
                        }
                    ),
                    html.span({"style": {"marginLeft": "8px"}}, "Activa"),
                ),
                html.button(
                    {
                        "class_name": "outline secondary",
                        # Pasa un dict con la info del robot
                        "on_click": lambda e, s=schedule: on_assign_equipos(
                            {"RobotId": s["RobotId"], "Robot": s["RobotNombre"]}
                        ),
                        "aria-label": "Asignar Equipos",
                    },
                    html.i({"class_name": "fa-solid fa-computer"}),
                ),
                html.button(
                    {
                        "class_name": "outline secondary",
                        "on_click": lambda e, sid=schedule["ProgramacionId"]: on_edit(sid),
                    },
                    html.i({"class_name": "fa-solid fa-pencil"}),
                    " Editar",
                ),
                html.button(
                    {
                        "class_name": "outline secondary",
                        "on_click": lambda e, s=schedule: on_delete(s),
                    },
                    html.i({"class_name": "fa-solid fa-trash"}),
                    " Eliminar",
                ),
            )
        ),
    )
