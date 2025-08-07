# src/sam_dashboard/frontend/features/modals/pool_modal_components.py

import asyncio
from typing import Any, Callable, Dict, List, Set

from reactpy import component, event, html, use_callback, use_context, use_effect, use_memo, use_state

from ...api_client import get_api_client
from ...shared.notifications import NotificationContext

DEFAULT_POOL_STATE = {"PoolId": None, "Nombre": "", "Descripcion": ""}


@component
def PoolEditModal(pool: Dict, on_close: Callable, on_save: Callable):
    """Modal para crear o editar un Pool."""
    form_data, set_form_data = use_state(DEFAULT_POOL_STATE)
    is_loading, set_is_loading = use_state(False)
    notification_ctx = use_context(NotificationContext)
    is_edit_mode = pool and pool.get("PoolId") is not None

    @use_effect(dependencies=[pool])
    def _populate_form():
        if pool is not None:
            set_form_data(pool if is_edit_mode else DEFAULT_POOL_STATE)

    if pool is None:
        return None

    def handle_change(field, value):
        set_form_data(lambda old: {**old, field: value})

    async def handle_submit(e):
        set_is_loading(True)
        try:
            await on_save(form_data)
            notification_ctx["show_notification"](f"Pool {'actualizado' if is_edit_mode else 'creado'} con éxito.", "success")
            on_close()
        except Exception as e:
            notification_ctx["show_notification"](str(e), "error")
        finally:
            set_is_loading(False)

    return html.dialog(
        {"open": True},
        html.article(
            html.header(
                html.button({"aria-label": "Close", "rel": "prev", "onClick": lambda e: on_close()}),
                html.h2("Editar Pool" if is_edit_mode else "Crear Nuevo Pool"),
            ),
            html.form(
                {"onSubmit": event(handle_submit, prevent_default=True)},
                html.label(
                    "Nombre del Pool",
                    html.input(
                        {
                            "type": "text",
                            "value": form_data.get("Nombre", ""),
                            "onChange": lambda e: handle_change("Nombre", e["target"]["value"]),
                            "required": True,
                        }
                    ),
                ),
                html.label(
                    "Descripción",
                    html.textarea(
                        {
                            "value": form_data.get("Descripcion", ""),
                            "onChange": lambda e: handle_change("Descripcion", e["target"]["value"]),
                        }
                    ),
                ),
                html.footer(
                    html.div(
                        {"className": "grid"},
                        html.button(
                            {"type": "button", "className": "secondary", "onClick": lambda e: on_close(), "disabled": is_loading}, "Cancelar"
                        ),
                        html.button({"type": "submit", "aria-busy": is_loading}, "Guardar"),
                    ),
                ),
            ),
        ),
    )


@component
def PoolAssignmentsModal(pool: Dict, on_close: Callable, on_save_success: Callable):
    """Modal rediseñado para asignar recursos a un pool en cajas separadas."""
    api_client = get_api_client()
    notification_ctx = use_context(NotificationContext)
    is_loading, set_is_loading = use_state(True)

    available_robots, set_available_robots = use_state([])
    assigned_robots, set_assigned_robots = use_state([])
    available_equipos, set_available_equipos = use_state([])
    assigned_equipos, set_assigned_equipos = use_state([])

    selected_avail_robots, set_selected_avail_robots = use_state(set())
    selected_asgn_robots, set_selected_asgn_robots = use_state(set())
    selected_avail_equipos, set_selected_avail_equipos = use_state(set())
    selected_asgn_equipos, set_selected_asgn_equipos = use_state(set())

    @use_effect(dependencies=[pool])
    def _load_data():
        if not pool or not pool.get("PoolId"):
            return

        async def _fetch():
            set_is_loading(True)
            try:
                data = await api_client.get_pool_assignments(pool["PoolId"])
                set_available_robots([r for r in data.get("available", []) if r["Tipo"] == "Robot"])
                set_assigned_robots([r for r in data.get("assigned", []) if r["Tipo"] == "Robot"])
                set_available_equipos([e for e in data.get("available", []) if e["Tipo"] == "Equipo"])
                set_assigned_equipos([e for e in data.get("assigned", []) if e["Tipo"] == "Equipo"])
            except Exception as e:
                notification_ctx["show_notification"](f"Error al cargar: {e}", "error")
            finally:
                set_is_loading(False)

        asyncio.create_task(_fetch())

    if not pool:
        return None

    async def handle_save(e):
        set_is_loading(True)
        try:
            robot_ids = [r["ID"] for r in assigned_robots]
            team_ids = [eq["ID"] for eq in assigned_equipos]
            await api_client.update_pool_assignments(pool["PoolId"], robot_ids, team_ids)
            await on_save_success()
            notification_ctx["show_notification"]("Asignaciones guardadas.", "success")
            on_close()
        except Exception as e:
            notification_ctx["show_notification"](f"Error al guardar: {e}", "error")
        finally:
            set_is_loading(False)

    return html.dialog(
        {"open": True, "style": {"maxWidth": "90vw", "width": "1200px"}},
        html.article(
            {"aria-busy": is_loading},
            html.header(
                html.button({"aria-label": "Close", "rel": "prev", "onClick": lambda e: on_close()}),
                html.h3(f"Asignar Recursos a: {pool.get('Nombre')}"),
            ),
            html.h5("Asignación de Robots"),
            AssignmentBox(
                available_items=available_robots,
                set_available_items=set_available_robots,
                assigned_items=assigned_robots,
                set_assigned_items=set_assigned_robots,
                selected_available_ids=selected_avail_robots,
                set_selected_available_ids=set_selected_avail_robots,
                selected_assigned_ids=selected_asgn_robots,
                set_selected_assigned_ids=set_selected_asgn_robots,
            ),
            html.hr(),
            html.h5("Asignación de Equipos"),
            AssignmentBox(
                available_items=available_equipos,
                set_available_items=set_available_equipos,
                assigned_items=assigned_equipos,
                set_assigned_items=set_assigned_equipos,
                selected_available_ids=selected_avail_equipos,
                set_selected_available_ids=set_selected_avail_equipos,
                selected_assigned_ids=selected_asgn_equipos,
                set_selected_assigned_ids=set_selected_asgn_equipos,
            ),
            html.footer(
                html.div(
                    {"className": "grid"},
                    html.button({"className": "secondary", "onClick": lambda e: on_close()}, "Cancelar"),
                    html.button({"onClick": handle_save}, "Guardar Cambios"),
                )
            ),
        ),
    )


@component
def AssignmentBox(
    available_items,
    set_available_items,
    assigned_items,
    set_assigned_items,
    selected_available_ids,
    set_selected_available_ids,
    selected_assigned_ids,
    set_selected_assigned_ids,
):
    """Componente genérico para una fila de asignación (disponibles -> flechas -> asignados)."""

    def move_to_assigned(e):
        to_move = {item["ID"] for item in available_items if item["ID"] in selected_available_ids}
        set_assigned_items(assigned_items + [item for item in available_items if item["ID"] in to_move])
        set_available_items([item for item in available_items if item["ID"] not in to_move])
        set_selected_available_ids(set())

    def move_to_available(e):
        to_move = {item["ID"] for item in assigned_items if item["ID"] in selected_assigned_ids}
        set_available_items(available_items + [item for item in assigned_items if item["ID"] in to_move])
        set_assigned_items([item for item in assigned_items if item["ID"] not in to_move])
        set_selected_assigned_ids(set())

    return html.div(
        {"className": "grid", "style": {"gridTemplateColumns": "5fr 1fr 5fr", "alignItems": "center", "gap": "1rem"}},
        ResourceListBox("Disponibles", available_items, selected_available_ids, set_selected_available_ids),
        html.div(
            {"style": {"display": "flex", "flexDirection": "column", "gap": "1rem"}},
            html.button({"onClick": move_to_assigned, "disabled": not selected_available_ids}, "➡️"),
            html.button({"onClick": move_to_available, "disabled": not selected_assigned_ids}, "⬅️"),
        ),
        ResourceListBox("Asignados", assigned_items, selected_assigned_ids, set_selected_assigned_ids),
    )


@component
def ResourceListBox(title, items, selected_ids, set_selected_ids):
    """Componente que renderiza una caja con una lista de recursos seleccionables."""

    def handle_selection(item_id):
        new_selection = selected_ids.copy()
        if item_id in new_selection:
            new_selection.remove(item_id)
        else:
            new_selection.add(item_id)
        set_selected_ids(new_selection)

    return html.div(
        html.p(html.strong(title)),
        html.div(
            {"style": {"height": "20vh", "overflowY": "auto", "border": "1px solid var(--contrast-border)", "padding": "0.5rem"}},
            *[
                html.label(
                    {"key": item["ID"]},
                    html.input(
                        {
                            "type": "checkbox",
                            "checked": item["ID"] in selected_ids,
                            "onChange": lambda e, i_id=item["ID"]: handle_selection(i_id),
                        }
                    ),
                    item["Nombre"],
                )
                for item in sorted(items, key=lambda x: x["Nombre"])
            ],
        ),
    )
