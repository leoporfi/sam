# sam/web/frontend/features/components/equipo_list.py
"""
Componentes para la gestión de equipos.

Este módulo contiene los componentes para listar, mostrar y gestionar equipos,
siguiendo el estándar de ReactPy de SAM.
"""

from typing import Callable, Dict, List

from reactpy import component, event, html, use_state

from sam.web.backend.schemas import Equipo

from ...shared.async_content import AsyncContent
from ...shared.common_components import Pagination
from ...shared.styles import (
    BUTTON_PRIMARY,
    CARDS_CONTAINER,
    COLLAPSIBLE_PANEL,
    COLLAPSIBLE_PANEL_EXPANDED,
    DASHBOARD_CONTROLS,
    MASTER_CONTROLS_GRID,
    MOBILE_CONTROLS_TOGGLE,
    ROBOT_CARD,
    ROBOT_CARD_BODY,
    ROBOT_CARD_HEADER,
    SEARCH_INPUT,
    TABLE_CONTAINER,
    TAG,
    TAG_SECONDARY,
)


@component
def EquiposControls(
    search: str,
    on_search: Callable,
    on_search_execute: Callable,
    active_filter: str,
    on_active: Callable,
    balanceable_filter: str,
    on_balanceable: Callable,
    on_create_equipo: Callable,
):
    """Controles para el dashboard de Equipos (título, filtros)."""
    is_expanded, set_is_expanded = use_state(False)
    collapsible_panel_class = COLLAPSIBLE_PANEL_EXPANDED if is_expanded else COLLAPSIBLE_PANEL

    return html.div(
        {"class_name": DASHBOARD_CONTROLS},
        html.div(
            {"class_name": "controls-header"},
            html.h2("Gestión de Equipos"),
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
                        "name": "search-device",
                        "placeholder": "Buscar equipos por nombre... (Presiona Enter)",
                        "value": search,
                        "on_change": lambda event: on_search(event["target"]["value"]),
                        "on_key_down": lambda event: on_search_execute() if event.get("key") == "Enter" else None,
                        "class_name": SEARCH_INPUT,
                    }
                ),
                html.select(
                    {
                        "name": "filter-activo",
                        "value": active_filter,
                        "on_change": lambda e: on_active(e["target"]["value"]),
                    },
                    html.option({"value": "all"}, "Activo: Todos"),
                    html.option({"value": "true"}, "Solo Activos"),
                    html.option({"value": "false"}, "Solo Inactivos"),
                ),
                html.select(
                    {
                        "name": "filter-balanceable",
                        "value": balanceable_filter,
                        "on_change": lambda e: on_balanceable(e["target"]["value"]),
                    },
                    html.option({"value": "all"}, "Balanceo: Todos"),
                    html.option({"value": "true"}, "Permite Balanceo"),
                    html.option({"value": "false"}, "No Permite Balanceo"),
                ),
                html.button(
                    {"on_click": lambda e: on_create_equipo(), "type": "button", "class_name": BUTTON_PRIMARY},
                    html.i({"class_name": "fa-solid fa-plus"}),
                    " Equipo",
                ),
            ),
        ),
    )


@component
def EquiposDashboard(equipos_state: Dict):
    """Componente principal que renderiza la tabla/tarjetas y la paginación de equipos."""
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

    # Usar AsyncContent para manejar estados de carga/error/vacío
    return AsyncContent(
        loading=equipos_state["loading"] and not equipos_state["equipos"],
        error=equipos_state["error"],
        data=equipos_state["equipos"],
        empty_message="No se encontraron equipos.",
        children=html._(
            pagination_component,
            html.div(
                {"class_name": CARDS_CONTAINER},
                *[
                    EquipoCard(equipo=equipo, on_action=equipos_state["update_equipo_status"])
                    for equipo in equipos_state["equipos"]
                ],
            ),
            html.div(
                {"class_name": TABLE_CONTAINER},
                EquiposTable(
                    equipos=equipos_state["equipos"],
                    on_action=equipos_state["update_equipo_status"],
                    sort_by=equipos_state["sort_by"],
                    sort_dir=equipos_state["sort_dir"],
                    on_sort=equipos_state["handle_sort"],
                ),
            ),
        ),
    )


@component
def EquiposTable(equipos: List[Equipo], on_action: Callable, sort_by: str, sort_dir: str, on_sort: Callable):
    headers = [
        {"key": "Equipo", "label": "Equipo"},
        {"key": "Licencia", "label": "Licencia"},
        {"key": "Activo_SAM", "label": "Activo SAM"},
        {"key": "PermiteBalanceoDinamico", "label": "Permite Balanceo"},
        {"key": "RobotAsignado", "label": "Robot Asignado"},
        {"key": "EsProgramado", "label": "Tipo Asig."},
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


def get_tipo_asignacion(equipo: Dict) -> tuple[str, str, str]:
    """
    Determina el tipo de asignación de un equipo para la tabla/tarjeta principal.

    Args:
        equipo: Diccionario con información del equipo de la vista principal

    Returns:
        tuple[str, str, str]: (texto_estado, clase_css, tooltip)

    Estados posibles:
        - 'N/A': Equipo sin asignación
        - 'Programado': Asignado vía programación (EsProgramado=1)
        - 'Reservado': Reservado manualmente (Reservado=1) - NOTA: Requiere que el SP devuelva este campo
        - 'Dinámico': Asignado por balanceador (ni programado ni reservado)

    NOTA: Actualmente el SP ListarEquipos no devuelve el campo 'Reservado'.
          Cuando se agregue, actualizar esta función para detectar correctamente el estado Reservado.
    """
    robot_asignado = equipo.get("RobotAsignado")

    # Si no tiene robot asignado
    if not robot_asignado or robot_asignado == "N/A":
        return ("N/A", TAG_SECONDARY, "Sin asignación")

    # Orden de prioridad (consistente con los modales)
    if equipo.get("EsProgramado"):
        return (
            "Programado",
            "tag-programado",
            f"Asignado vía programación a {robot_asignado}",
        )

    # NOTA: Cuando el SP ListarEquipos devuelva 'Reservado', agregar esta verificación:
    # if equipo.get("Reservado"):
    #     return (
    #         "Reservado",
    #         "tag-reservado",
    #         f"Reservado manualmente para {robot_asignado}",
    #     )

    # Si tiene robot pero no es programado (y no tenemos info de Reservado) → Dinámico
    return (
        "Dinámico",
        "tag-dinamico",
        f"Asignado dinámicamente a {robot_asignado} por el balanceador",
    )


@component
def EquipoRow(equipo: Equipo, on_action: Callable):
    """
    Fila de la tabla de equipos.
    Siguiendo el mismo patrón que RobotRow: funciones async separadas para cada acción.
    """
    # Desactivar el switch de balanceo SOLO si el equipo tiene una asignación PROGRAMADA
    is_programado = equipo.get("EsProgramado", False)
    balanceo_disabled = is_programado
    balanceo_title = (
        "No se puede balancear un equipo con asignación programada."
        if is_programado
        else "Activar/Desactivar Balanceo Dinámico"
    )

    async def handle_toggle_activo(event):
        await on_action(equipo["EquipoId"], "Activo_SAM", not equipo["Activo_SAM"])

    async def handle_toggle_balanceo(event):
        # Evitar acción si está desactivado
        if balanceo_disabled:
            return
        await on_action(equipo["EquipoId"], "PermiteBalanceoDinamico", not equipo["PermiteBalanceoDinamico"])

    return html.tr(
        {"key": equipo["EquipoId"]},
        html.td({"title": equipo["UserName"]}, equipo["Equipo"]),
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
                        "disabled": balanceo_disabled,
                        "title": balanceo_title,
                    }
                )
            )
        ),
        html.td(
            html.span(
                {"class_name": TAG_SECONDARY if equipo.get("RobotAsignado") == "N/A" else TAG},
                equipo.get("RobotAsignado", "N/A"),
            )
        ),
        # --- Mostrar el estado de la asignación ---
        html.td(
            (
                html.span(
                    {
                        "class_name": get_tipo_asignacion(equipo)[1],
                        "title": get_tipo_asignacion(equipo)[2],
                    },
                    get_tipo_asignacion(equipo)[0],
                )
                if equipo.get("RobotAsignado") not in [None, "N/A"]
                else get_tipo_asignacion(equipo)[0]
            )
        ),
        html.td(
            html.span({"class_name": TAG_SECONDARY if equipo.get("Pool") == "N/A" else TAG}, equipo.get("Pool", "N/A"))
        ),
    )


@component
def EquipoCard(equipo: Equipo, on_action: Callable):
    """
    Tarjeta de equipo para vista móvil.
    Siguiendo el mismo patrón que RobotCard: funciones async separadas para cada acción.
    """
    is_programado = equipo.get("EsProgramado", False)  # Nuevo campo del SP
    balanceo_disabled = is_programado
    balanceo_title = (
        "No se puede balancear un equipo con asignación programada."
        if is_programado
        else "Activar/Desactivar Balanceo Dinámico"
    )

    async def handle_toggle_activo(event):
        await on_action(equipo["EquipoId"], "Activo_SAM", not equipo["Activo_SAM"])

    async def handle_toggle_balanceo(event):
        if balanceo_disabled:
            return
        await on_action(equipo["EquipoId"], "PermiteBalanceoDinamico", not equipo["PermiteBalanceoDinamico"])

    return html.article(
        {"key": equipo["EquipoId"], "class_name": ROBOT_CARD},
        html.div({"class_name": ROBOT_CARD_HEADER}, html.h5(equipo["Equipo"])),
        html.div(
            {"class_name": ROBOT_CARD_BODY},
            html.p(f"Licencia: {equipo.get('Licencia', 'N/A')}"),
            html.p(
                "Robot: ",
                html.span(
                    {"class_name": TAG_SECONDARY if equipo.get("RobotAsignado") == "N/A" else TAG},
                    equipo.get("RobotAsignado", "N/A"),
                ),
            ),
            html.p(
                "Tipo Asig.: ",
                (
                    html.span(
                        {
                            "class_name": get_tipo_asignacion(equipo)[1],
                            "title": get_tipo_asignacion(equipo)[2],
                        },
                        get_tipo_asignacion(equipo)[0],
                    )
                    if equipo.get("RobotAsignado") not in [None, "N/A"]
                    else get_tipo_asignacion(equipo)[0]
                ),
            ),
            html.p(
                "Pool: ",
                html.span(
                    {"class_name": TAG_SECONDARY if equipo.get("Pool") == "N/A" else TAG}, equipo.get("Pool", "N/A")
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
                            "disabled": balanceo_disabled,
                            "title": balanceo_title,
                        }
                    ),
                    "Balanceo",
                ),
            ),
        ),
    )
