# web/frontend/features/equipos/equipos_components.py
from typing import Callable, Dict, List

from reactpy import component, event, html, use_state

from sam.web.backend.schemas import Equipo

from ...shared.common_components import LoadingSpinner, Pagination


@component
def EquiposControls(
    search_term: str,
    on_search_change: Callable,
    active_filter: str,
    on_active_change: Callable,
    balanceable_filter: str,
    on_balanceable_change: Callable,
    is_searching: bool,
):
    """Controles para el dashboard de Equipos (título, filtros)."""
    is_expanded, set_is_expanded = use_state(False)
    collapsible_panel_class = f"collapsible-panel {'is-expanded' if is_expanded else ''}"

    return html.div(
        {"class_name": "dashboard-controls"},
        html.div(
            {"class_name": "controls-header"},
            html.h2("Gestión de Equipos"),
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
                {"class_name": "master-controls-grid", "style": {"gridTemplateColumns": "5fr 2fr 2fr 2fr"}},
                html.input(
                    {
                        "type": "search",
                        "name": "search-device",
                        "placeholder": "Buscar equipos por nombre...",
                        "value": search_term,
                        "on_change": lambda event: on_search_change(event["target"]["value"]),
                        "aria-busy": str(is_searching).lower(),
                    }
                ),
                html.select(
                    {
                        "name": "filter-activo",
                        "value": active_filter,
                        "on_change": lambda e: on_active_change(e["target"]["value"]),
                    },
                    html.option({"value": "all"}, "Activo: Todos"),
                    html.option({"value": "true"}, "Solo Activos"),
                    html.option({"value": "false"}, "Solo Inactivos"),
                ),
                html.select(
                    {
                        "name": "filter-balanceable",
                        "value": balanceable_filter,
                        "on_change": lambda e: on_balanceable_change(e["target"]["value"]),
                    },
                    html.option({"value": "all"}, "Balanceo: Todos"),
                    html.option({"value": "true"}, "Permite Balanceo"),
                    html.option({"value": "false"}, "No Permite Balanceo"),
                ),
                html.button(
                    html.i({"class_name": "fa-solid fa-plus"}),
                    " Agregar Equipo",
                ),
            ),
        ),
    )


@component
def EquiposDashboard(equipos_state: Dict):
    """Componente principal que renderiza la tabla/tarjetas y la paginación de equipos."""
    if equipos_state["error"]:
        return html.article({"aria_invalid": "true"}, f"Error al cargar datos: {equipos_state['error']}")
    if equipos_state["loading"] and not equipos_state["equipos"]:
        return LoadingSpinner()

    pagination_component = (
        Pagination(
            current_page=equipos_state["current_page"],
            total_pages=equipos_state["total_pages"],
            total_items=equipos_state["total_count"],
            items_per_page=equipos_state["page_size"],
            on_page_change=equipos_state["set_current_page"],
        )
        if equipos_state["total_pages"] > 1
        else None
    )

    return html._(
        html.div(
            {"class_name": "cards-container"},
            *[
                EquipoCard(equipo=equipo, on_action=equipos_state["update_equipo_status"])
                for equipo in equipos_state["equipos"]
            ],
        ),
        html.div(
            {"class_name": "table-container"},
            EquiposTable(
                equipos=equipos_state["equipos"],
                on_action=equipos_state["update_equipo_status"],
                sort_by=equipos_state["sort_by"],
                sort_dir=equipos_state["sort_dir"],
                on_sort=equipos_state["handle_sort"],
            ),
        ),
        pagination_component,
    )


@component
def EquiposTable(equipos: List[Equipo], on_action: Callable, sort_by: str, sort_dir: str, on_sort: Callable):
    headers = [
        {"key": "Equipo", "label": "Equipo"},
        {"key": "Licencia", "label": "Licencia"},
        {"key": "Activo_SAM", "label": "Activo SAM"},
        {"key": "PermiteBalanceoDinamico", "label": "Permite Balanceo"},
        {"key": "RobotAsignado", "label": "Robot Asignado"},
        {"key": "Pool", "label": "Pool"},
    ]

    def render_header(h_info: Dict):
        sort_indicator = ""
        if sort_by == h_info["key"]:
            sort_indicator = " ▲" if sort_dir == "asc" else " ▼"
        return html.th(
            {"scope": "col"},
            html.a(
                {"href": "#", "on_click": event(lambda e: on_sort(h_info["key"]), prevent_default=True)},
                h_info["label"],
                sort_indicator,
            ),
        )

    return html.article(
        html.table(
            html.thead(html.tr(*[render_header(h) for h in headers])),
            html.tbody(
                *[EquipoRow(equipo=equipo, on_action=on_action) for equipo in equipos]
                if len(equipos)
                else [
                    html.tr(
                        html.td(
                            {"colSpan": len(headers), "style": {"text_align": "center"}}, "No se encontraron equipos."
                        )
                    ),
                ]
            ),
        )
    )


@component
def EquipoRow(equipo: Equipo, on_action: Callable):
    """
    Fila de la tabla de equipos.
    Siguiendo el mismo patrón que RobotRow: funciones async separadas para cada acción.
    """

    async def handle_toggle_activo(event):
        await on_action(equipo["EquipoId"], "Activo_SAM", not equipo["Activo_SAM"])

    async def handle_toggle_balanceo(event):
        await on_action(equipo["EquipoId"], "PermiteBalanceoDinamico", not equipo["PermiteBalanceoDinamico"])

    return html.tr(
        {"key": equipo["EquipoId"]},
        html.td(equipo["Equipo"]),
        html.td(equipo.get("Licencia") or "N/A"),
        html.td(
            html.label(
                html.input(
                    {
                        "type": "checkbox",
                        "name": f"checkbox-activo-{equipo['EquipoId']}",
                        "role": "switch",
                        "checked": equipo["Activo_SAM"],
                        "on_change": event(handle_toggle_activo),
                    }
                )
            )
        ),
        html.td(
            html.label(
                html.input(
                    {
                        "type": "checkbox",
                        "name": f"checkbox-dinamico-{equipo['EquipoId']}",
                        "role": "switch",
                        "checked": equipo["PermiteBalanceoDinamico"],
                        "on_change": event(handle_toggle_balanceo),
                    }
                )
            )
        ),
        html.td(
            html.span(
                {"class_name": "tag secondary" if equipo.get("RobotAsignado") == "N/A" else "tag"},
                equipo.get("RobotAsignado", "N/A"),
            )
        ),
        html.td(
            html.span(
                {"class_name": "tag secondary" if equipo.get("Pool") == "N/A" else "tag"}, equipo.get("Pool", "N/A")
            )
        ),
    )


@component
def EquipoCard(equipo: Equipo, on_action: Callable):
    """
    Tarjeta de equipo para vista móvil.
    Siguiendo el mismo patrón que RobotCard: funciones async separadas para cada acción.
    """

    async def handle_toggle_activo(event):
        await on_action(equipo["EquipoId"], "Activo_SAM", not equipo["Activo_SAM"])

    async def handle_toggle_balanceo(event):
        await on_action(equipo["EquipoId"], "PermiteBalanceoDinamico", not equipo["PermiteBalanceoDinamico"])

    return html.article(
        {"key": equipo["EquipoId"], "class_name": "robot-card"},
        html.div({"class_name": "robot-card-header"}, html.h5(equipo["Equipo"])),
        html.div(
            {"class_name": "robot-card-body"},
            html.p(f"Licencia: {equipo.get('Licencia', 'N/A')}"),
            html.p(
                "Robot: ",
                html.span(
                    {"class_name": "tag secondary" if equipo.get("RobotAsignado") == "N/A" else "tag"},
                    equipo.get("RobotAsignado", "N/A"),
                ),
            ),
            html.p(
                "Pool: ",
                html.span(
                    {"class_name": "tag secondary" if equipo.get("Pool") == "N/A" else "tag"}, equipo.get("Pool", "N/A")
                ),
            ),
            html.div(
                {"class_name": "grid"},
                html.label(
                    html.input(
                        {
                            "type": "checkbox",
                            "name": f"checkbox-activo-{equipo['EquipoId']}",
                            "role": "switch",
                            "checked": equipo["Activo_SAM"],
                            "on_change": event(handle_toggle_activo),
                        }
                    ),
                    "Activo SAM",
                ),
                html.label(
                    html.input(
                        {
                            "type": "checkbox",
                            "name": f"checkbox-dinamico-{equipo['EquipoId']}",
                            "role": "switch",
                            "checked": equipo["PermiteBalanceoDinamico"],
                            "on_change": event(handle_toggle_balanceo),
                        }
                    ),
                    "Balanceo",
                ),
            ),
        ),
    )
