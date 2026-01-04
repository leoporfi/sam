from typing import Callable, Dict, List, Optional

from reactpy import component, event, html, use_state

# Usamos el tipo ScheduleData de schemas para hint, aunque es un dict en runtime
from sam.web.backend.schemas import ScheduleData

from ...shared.common_components import LoadingSpinner, Pagination


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
):
    is_expanded, set_is_expanded = use_state(False)
    collapsible_panel_class = f"collapsible-panel {'is-expanded' if is_expanded else ''}"

    return html.div(
        {"class_name": "dashboard-controls"},
        html.div(
            {"class_name": "controls-header"},
            html.h2("Gestión de Programaciones"),
            html.button(
                {
                    "class_name": "mobile-controls-toggle outline secondary",
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
                    "class_name": "master-controls-grid",
                    "style": {"gridTemplateColumns": "5fr 2fr 2fr 1fr"},
                },
                html.input(
                    {
                        "type": "search",
                        "name": "search-schedule",
                        "placeholder": "Buscar robots por nombre...",
                        "value": search,
                        "on_change": lambda e: on_search(e["target"]["value"]),
                        "aria-busy": str(is_searching).lower(),
                    }
                ),
                html.select(
                    {
                        "name": "filter-activo",
                        "value": tipo_filter or "",
                        "on_change": lambda e: on_tipo(e["target"]["value"] or None),
                    },
                    html.option({"value": ""}, "Tipo: Todos"),
                    *[html.option({"value": t}, t) for t in ["Diaria", "Semanal", "Mensual", "Especifica"]],
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
                        "disabled": True,
                        "data-tooltip": "Próximamente",
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
    current_page: int,
    total_pages: int,
    on_page_change: Callable,
    total_count: int,
    loading: bool,
    error: str,
):
    """Componente principal que renderiza la tabla y paginación."""
    if loading:
        return LoadingSpinner()

    if error:
        return html.article(
            {"aria_invalid": "true", "style": {"color": "var(--pico-color-red-600)"}}, f"Error: {error}"
        )

    if not schedules:
        return html.article({"style": {"textAlign": "center", "padding": "2rem"}}, "No se encontraron programaciones.")

    return html._(
        Pagination(current_page, total_pages, len(schedules), total_count, on_page_change),
        html.div(
            {"className": "cards-container"},
            [
                ScheduleCard(
                    schedule=s,
                    on_toggle=on_toggle,
                    on_edit=on_edit,
                    on_assign_equipos=on_assign_equipos,
                    key=s["ProgramacionId"],  # Importante para el rendimiento de renderizado
                )
                for s in schedules
            ],
        ),
        html.div(
            {"className": "table-container"},
            SchedulesTable(schedules, on_toggle, on_edit, on_assign_equipos),
        ),
    )


def _format_schedule_details(s: ScheduleData) -> str:
    """Helper para formatear los detalles de la programación (días/fecha)"""
    t = s["TipoProgramacion"]
    if t == "Semanal":
        return s["DiasSemana"] or "-"
    if t == "Mensual":
        return f"Día {s['DiaDelMes']}" if s["DiaDelMes"] else "-"
    if t == "Especifica":
        return s["FechaEspecifica"] or "-"
    return "-"  # Diaria no tiene detalles específicos aparte de la hora


@component
def SchedulesTable(schedules: List[ScheduleData], on_toggle: Callable, on_edit: Callable, on_assign_equipos: Callable):
    headers = ["Robot", "Tipo", "Hora", "Días / Fecha", "Tol.", "Equipos", "Activo", "Acciones"]

    return html.article(
        html.table(
            html.thead(html.tr(*[html.th(h) for h in headers])),
            html.tbody(
                *[
                    html.tr(
                        {"key": s["ProgramacionId"]},
                        html.td(s["RobotNombre"]),
                        html.td(html.span({"class_name": "tag"}, s["TipoProgramacion"])),
                        html.td(html.strong(s["HoraInicio"] or "-")),
                        html.td(_format_schedule_details(s)),
                        html.td(f"{s['Tolerancia']} min"),
                        html.td(
                            {"style": {"fontSize": "0.9em", "maxWidth": "250px", "whiteSpace": "normal"}},
                            s["EquiposProgramados"] or "-",
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
                                        "data-tooltip": "Eliminar Programacion",
                                        "data-placement": "left",
                                        "class_name": "secondary",
                                        "disabled": True,
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
def ScheduleCard(schedule: ScheduleData, on_toggle: Callable, on_edit: Callable, on_assign_equipos: Callable):
    return html.article(
        {"class_name": "schedule-card"},
        html.header(
            html.div(
                {"style": {"display": "flex", "justifyContent": "space-between", "alignItems": "center"}},
                html.h5({"style": {"margin": 0}}, schedule["RobotNombre"]),
                html.span({"class_name": "tag"}, schedule["TipoProgramacion"]),
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
                html.strong(schedule["HoraInicio"] or "N/A"),
            ),
            html.p(
                html.i(
                    {
                        "class_name": "fa-regular fa-calendar",
                        "style": {"marginRight": "8px", "color": "var(--pico-muted-color)"},
                    }
                ),
                f"{_format_schedule_details(schedule)}",
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
            )
        ),
    )
