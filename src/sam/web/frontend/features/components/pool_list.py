# sam/web/frontend/features/components/pool_list.py
"""
Componentes para la gestión de pools.

Este módulo contiene los componentes para listar, mostrar y gestionar pools,
siguiendo el estándar de ReactPy de SAM.
"""

import asyncio
from typing import Callable, Dict, List

from reactpy import component, event, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client

from ...shared.async_content import AsyncContent, LoadingSpinner
from ...state.app_context import use_app_context
from ...shared.common_components import ConfirmationModal
from ...shared.styles import (
    BUTTON_PRIMARY,
    CARDS_CONTAINER_POOLS,
    COLLAPSIBLE_PANEL,
    COLLAPSIBLE_PANEL_EXPANDED,
    DASHBOARD_CONTROLS,
    MASTER_CONTROLS_GRID,
    MOBILE_CONTROLS_TOGGLE,
    POOL_CARD,
    POOL_CARD_BODY,
    POOL_CARD_FOOTER,
    POOL_CARD_HEADER,
    SEARCH_INPUT,
    TABLE_CONTAINER,
)


@component
def PoolsControls(
    search_term: str,
    on_search_change: Callable,
    is_searching: bool,
    on_create_pool: Callable,
):
    """Controles para el dashboard de Pools (título, buscador, botón)."""
    is_expanded, set_is_expanded = use_state(False)
    collapsible_panel_class = COLLAPSIBLE_PANEL_EXPANDED if is_expanded else COLLAPSIBLE_PANEL

    return html.div(
        {"class_name": DASHBOARD_CONTROLS},
        html.div(
            {"class_name": "controls-header"},
            html.h2("Gestión de Pools"),
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
                {"class_name": MASTER_CONTROLS_GRID, "style": {"gridTemplateColumns": "5fr 2fr"}},
                html.input(
                    {
                        "type": "search",
                        "name": "search-pool",
                        "placeholder": "Buscar pools por nombre...",
                        "value": search_term,
                        "on_change": lambda event: on_search_change(event["target"]["value"]),
                        "aria-busy": str(is_searching).lower(),
                        "class_name": SEARCH_INPUT,
                    }
                ),
                html.button(
                    {"on_click": on_create_pool, "type": "button", "class_name": BUTTON_PRIMARY},
                    html.i({"class_name": "fa-solid fa-plus"}),
                    " Pool",
                ),
            ),
        ),
    )


@component
def PoolsDashboard(
    pools: List[Dict], on_edit: Callable, on_assign: Callable, on_delete: Callable, loading: bool, error: str
):
    """Componente principal que renderiza la tabla/tarjetas."""
    pools_data = pools.get("pools", []) if isinstance(pools, dict) else pools

    # Usar AsyncContent para manejar estados de carga/error/vacío
    return AsyncContent(
        loading=loading and not pools_data,
        error=error,
        data=pools_data,
        empty_message="No se encontraron pools.",
        children=html._(
            html.div(
                {"class_name": CARDS_CONTAINER_POOLS},
                *[PoolCard(pool=p, on_edit=on_edit, on_assign=on_assign, on_delete=on_delete) for p in pools_data],
            ),
            html.div(
                {"class_name": TABLE_CONTAINER},
                PoolsTable(pools=pools, on_edit=on_edit, on_assign=on_assign, on_delete=on_delete),
            ),
        ),
    )


@component
def PoolsTable(pools: List[Dict], on_edit: Callable, on_assign: Callable, on_delete: Callable):
    """Tabla que muestra la lista de pools."""
    return html.article(
        html.table(
            html.thead(
                html.tr(
                    html.th("Nombre"),
                    html.th("Descripción"),
                    html.th("Robots"),
                    html.th("Equipos"),
                    html.th("Acciones"),
                )
            ),
            html.tbody(
                *[PoolRow(pool=p, on_edit=on_edit, on_assign=on_assign, on_delete=on_delete) for p in pools]
                if pools
                else [html.tr(html.td({"colSpan": 5, "style": {"text_align": "center"}}, "No se encontraron pools."))]
            ),
        )
    )


@component
def PoolRow(pool: Dict, on_edit: Callable, on_assign: Callable, on_delete: Callable):
    """Fila individual para la tabla de pools."""
    return html.tr(
        {"key": pool["PoolId"]},
        html.td(pool["Nombre"]),
        html.td(pool.get("Descripcion", "-")),
        html.td(str(pool.get("CantidadRobots", 0))),
        html.td(str(pool.get("CantidadEquipos", 0))),
        html.td(
            html.div(
                {"class_name": "grid"},
                html.a(
                    {
                        "href": "#",
                        "on_click": event(lambda e: on_edit(pool), prevent_default=True),
                        "data-tooltip": "Editar Pool",
                        "class_name": "secondary",
                    },
                    html.i({"class_name": "fa-solid fa-pencil"}),
                ),
                html.a(
                    {
                        "href": "#",
                        "on_click": event(lambda e: on_assign(pool), prevent_default=True),
                        "data-tooltip": "Asignar Recursos",
                        "class_name": "secondary",
                    },
                    html.i({"class_name": "fa-solid fa-link"}),
                ),
                html.a(
                    {
                        "href": "#",
                        "data-tooltip": "Eliminar Pool",
                        "data-placement": "left",
                        "class_name": "secondary",
                        "on_click": event(lambda e: on_delete(pool), prevent_default=True),
                    },
                    html.i({"class_name": "fa-solid fa-trash"}),
                ),
            )
        ),
    )


@component
def PoolCard(pool: Dict, on_edit: Callable, on_assign: Callable, on_delete: Callable):
    """Tarjeta individual para la vista móvil de pools."""
    return html.article(
        {"key": pool["PoolId"], "class_name": POOL_CARD},
        html.div(
            {"class_name": POOL_CARD_HEADER},
            html.h5(pool["Nombre"]),
            html.small(pool.get("Descripcion", "")),
        ),
        html.div(
            {"class_name": POOL_CARD_BODY},
            html.div(
                {"class_name": "resource-counts"},
                html.span(html.i({"class_name": "fa-solid fa-robot"}), f" {pool.get('CantidadRobots', 0)} Robots"),
                html.span(html.i({"class_name": "fa-solid fa-computer"}), f" {pool.get('CantidadEquipos', 0)} Equipos"),
            ),
        ),
        html.footer(
            {"class_name": POOL_CARD_FOOTER},
            html.button({"class_name": "outline secondary", "on_click": lambda e: on_edit(pool)}, "Editar"),
            html.button({"class_name": "outline secondary", "on_click": lambda e: on_assign(pool)}, "Asignar"),
            html.button({"class_name": "outline secondary", "on_click": lambda e: on_delete(pool)}, "Eliminar"),
        ),
    )


@component
def BalanceadorStrategyPanel():
    """Panel para configurar estrategias globales con confirmación."""
    # Estados de configuración
    preemption_enabled, set_preemption_enabled = use_state(False)
    isolation_enabled, set_isolation_enabled = use_state(True)
    is_loading, set_is_loading = use_state(True)

    # Estados para el modal de confirmación
    confirm_open, set_confirm_open = use_state(False)
    pending_change, set_pending_change = use_state(None)  # Dict con 'type' y 'value'

    # Obtener api_client del contexto
    try:
        app_context = use_app_context()
        api_client = app_context.get("api_client") or get_api_client()
    except Exception:
        api_client = get_api_client()

    # Cargar estado inicial
    @use_effect(dependencies=[])
    def init_data_load():
        async def fetch_data():
            try:
                p_data = await api_client.get_preemption_mode()
                i_data = await api_client.get_isolation_mode()
                set_preemption_enabled(p_data.get("enabled", False))
                set_isolation_enabled(i_data.get("enabled", True))
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"Error cargando configuración: {e}")
            finally:
                if not asyncio.current_task().cancelled():
                    set_is_loading(False)

        task = asyncio.create_task(fetch_data())
        return lambda: task.cancel()

    # Prepara el cambio pero pide confirmación
    def request_change(setting_type, new_value):
        set_pending_change({"type": setting_type, "value": new_value})
        set_confirm_open(True)

    # Ejecuta el cambio tras confirmar
    async def execute_change():
        if not pending_change:
            return

        setting = pending_change["type"]
        val = pending_change["value"]

        try:
            if setting == "preemption":
                await api_client.set_preemption_mode(val)
                set_preemption_enabled(val)
            elif setting == "isolation":
                await api_client.set_isolation_mode(val)
                set_isolation_enabled(val)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Error guardando configuración: {e}")
        finally:
            if not asyncio.current_task().cancelled():
                set_confirm_open(False)
                set_pending_change(None)

    def get_confirm_message():
        if not pending_change:
            return ""
        val = pending_change["value"]
        if pending_change["type"] == "preemption":
            return (
                "activar el Modo Prioridad Estricta. Esto podría detener robots en ejecución."
                if val
                else "desactivar la Prioridad Estricta."
            )
        else:
            return (
                "activar el Aislamiento Estricto. Los robots NO podrán usar equipos de otros pools."
                if val
                else "permitir el Desborde. Los robots podrán usar equipos libres de otros pools."
            )

    if is_loading:
        return html.div({"style": {"padding": "1rem"}}, LoadingSpinner())

    return html.article(
        {"class_name": "card", "style": {"marginBottom": "2rem"}},
        html.header(
            html.h4(
                html.i({"class_name": "fa-solid fa-sliders", "style": {"marginRight": "10px"}}),
                "Estrategia Global de Balanceo",
            )
        ),
        html.div(
            {"class_name": "grid"},
            # Opción 1: Prioridad Estricta (Preemption)
            html.div(
                html.label(
                    html.input(
                        {
                            "type": "checkbox",
                            "role": "switch",
                            "checked": preemption_enabled,
                            "on_change": lambda e: request_change("preemption", e["target"]["checked"]),
                        }
                    ),
                    html.strong("Prioridad Estricta (Preemption)"),
                ),
                html.small(
                    {"style": {"display": "block", "marginTop": "0.5rem", "color": "var(--pico-muted-color)"}},
                    "Permite detener robots de baja prioridad para liberar recursos inmediatamente.",
                ),
            ),
            # Opción 2: Aislamiento Estricto (Pool Isolation)
            html.div(
                html.label(
                    html.input(
                        {
                            "type": "checkbox",
                            "role": "switch",
                            "checked": isolation_enabled,
                            "on_change": lambda e: request_change("isolation", e["target"]["checked"]),
                        }
                    ),
                    html.strong("Aislamiento de Pool Estricto"),
                ),
                html.small(
                    {"style": {"display": "block", "marginTop": "0.5rem", "color": "var(--pico-muted-color)"}},
                    "Si está activo, impide que los robots tomen equipos prestados de otros pools (Desborde).",
                ),
            ),
        ),
        # Modal de Confirmación
        ConfirmationModal(
            is_open=confirm_open,
            title="Confirmar Cambio de Estrategia",
            message=f"¿Estás seguro de que deseas {get_confirm_message()}",
            on_confirm=execute_change,
            on_cancel=lambda: set_confirm_open(False),
        ),
    )
