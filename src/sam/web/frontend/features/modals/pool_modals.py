# sam/web/features/modals/pool_modals.py
import asyncio
from typing import Callable, Dict, List

from reactpy import component, event, html, use_context, use_effect, use_memo, use_state

from ...api.api_client import get_api_client
from ...shared.notifications import NotificationContext

DEFAULT_POOL_STATE = {"PoolId": None, "Nombre": "", "Descripcion": ""}


@component
def PoolEditModal(pool: Dict, is_open: bool, on_close: Callable, on_save: Callable):
    """Modal para crear o editar un Pool."""
    form_data, set_form_data = use_state(DEFAULT_POOL_STATE)
    is_loading, set_is_loading = use_state(False)
    notification_ctx = use_context(NotificationContext)
    is_edit_mode = pool and pool.get("PoolId") is not None

    @use_effect(dependencies=[pool])
    def sync_form_state():
        if pool is not None:
            set_form_data(pool if is_edit_mode else DEFAULT_POOL_STATE)
        else:
            set_form_data(DEFAULT_POOL_STATE)

    if pool is None:
        return None

    def handle_change(field, value):
        # Aplicar trim automático a campos de texto
        if isinstance(value, str):
            value = value.strip()
        set_form_data(lambda old: {**old, field: value})

    async def handle_submit(e):
        set_is_loading(True)
        try:
            await on_save(form_data)
            notification_ctx["show_notification"](
                f"Pool {'actualizado' if is_edit_mode else 'creado'} con éxito.", "success"
            )
            on_close()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            notification_ctx["show_notification"](str(e), "error")
        finally:
            if not asyncio.current_task().cancelled():
                set_is_loading(False)

    if not is_open:
        return None
    return html.dialog(
        {"open": True},
        html.article(
            html.header(
                html.button({"aria-label": "Close", "rel": "prev", "on_click": lambda e: on_close()}),
                html.h2("Editar Pool" if is_edit_mode else "Crear Nuevo Pool"),
            ),
            html.form(
                {"id": "pool-form", "onSubmit": event(handle_submit, prevent_default=True)},
                html.label(
                    "Nombre del Pool",
                    html.input(
                        {
                            "type": "text",
                            "name": "text-pool",
                            "value": form_data.get("Nombre", ""),
                            "on_change": lambda e: handle_change("Nombre", e["target"]["value"]),
                            "required": True,
                        }
                    ),
                ),
                html.label(
                    "Descripción",
                    html.textarea(
                        {
                            "value": form_data.get("Descripcion", ""),
                            "on_change": lambda e: handle_change("Descripcion", e["target"]["value"]),
                        }
                    ),
                ),
            ),
            html.footer(
                html.div(
                    {"class_name": "grid"},
                    html.button(
                        {
                            "type": "button",
                            "class_name": "secondary",
                            "on_click": lambda e: on_close(),
                            "disabled": is_loading,
                        },
                        "Cancelar",
                    ),
                    html.button({"type": "submit", "form": "pool-form", "aria-busy": is_loading}, "Guardar"),
                ),
            ),
        ),
    )


@component
def PoolAssignmentsModal(pool: Dict, is_open: bool, on_close: Callable, on_save_success: Callable):
    """Modal para asignar recursos (Robots y Equipos) a un pool."""
    # Obtener api_client del contexto
    try:
        from ...state.app_context import use_app_context

        app_context = use_app_context()
        api_client = app_context.get("api_client") or get_api_client()
    except Exception:
        api_client = get_api_client()
    notification_ctx = use_context(NotificationContext)
    is_loading, set_is_loading = use_state(True)
    active_tab, set_active_tab = use_state("robots")  # Nuevo estado para las solapas

    available_robots, set_available_robots = use_state([])
    assigned_robots, set_assigned_robots = use_state([])
    available_equipos, set_available_equipos = use_state([])
    assigned_equipos, set_assigned_equipos = use_state([])

    selected_avail_robots, set_selected_avail_robots = use_state([])
    selected_asgn_robots, set_selected_asgn_robots = use_state([])
    selected_avail_equipos, set_selected_avail_equipos = use_state([])
    selected_asgn_equipos, set_selected_asgn_equipos = use_state([])

    @use_effect(dependencies=[pool])
    def init_data_load():
        if not pool or not pool.get("PoolId"):
            return

        async def fetch_data():
            set_is_loading(True)
            try:
                data = await api_client.get_pool_assignments(pool["PoolId"])
                set_available_robots([r for r in data.get("available", []) if r["Tipo"] == "Robot"])
                set_assigned_robots([r for r in data.get("assigned", []) if r["Tipo"] == "Robot"])
                set_available_equipos([e for e in data.get("available", []) if e["Tipo"] == "Equipo"])
                set_assigned_equipos([e for e in data.get("assigned", []) if e["Tipo"] == "Equipo"])
            except asyncio.CancelledError:
                raise
            except Exception as e:
                notification_ctx["show_notification"](f"Error al cargar asignaciones: {e}", "error")
            finally:
                if not asyncio.current_task().cancelled():
                    set_is_loading(False)

        if pool and pool.get("PoolId"):
            task = asyncio.create_task(fetch_data())
            return lambda: task.cancel()

    async def handle_save(e):
        set_is_loading(True)
        try:
            robot_ids = [r["ID"] for r in assigned_robots]
            team_ids = [eq["ID"] for eq in assigned_equipos]
            await api_client.update_pool_assignments(pool["PoolId"], robot_ids, team_ids)
            await on_save_success()
            notification_ctx["show_notification"]("Asignaciones guardadas con éxito.", "success")
            on_close()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            notification_ctx["show_notification"](f"Error al guardar asignaciones: {e}", "error")
        finally:
            if not asyncio.current_task().cancelled():
                set_is_loading(False)

    if not is_open or not pool:
        return html.dialog({"open": False, "style": {"display": "none"}})

    return html.dialog(
        {
            "open": True,
        },
        html.article(
            {"aria-busy": str(is_loading).lower(), "style": {"maxWidth": "90vw", "width": "900px"}},
            html.header(
                html.button({"aria-label": "Close", "rel": "prev", "on_click": lambda e: on_close()}),
                html.h3(f"Asignar Recursos a: {pool.get('Nombre')}"),
            ),
            # Solapas de navegación
            html.div(
                {"class_name": "tabs-container"},
                html.button(
                    {
                        "class_name": "tab-button" + (" active" if active_tab == "robots" else ""),
                        "on_click": lambda e: set_active_tab("robots"),
                    },
                    html.i({"class_name": "fa-solid fa-robot"}),
                    " Robots",
                ),
                html.button(
                    {
                        "class_name": "tab-button" + (" active" if active_tab == "equipos" else ""),
                        "on_click": lambda e: set_active_tab("equipos"),
                    },
                    html.i({"class_name": "fa-solid fa-computer"}),
                    " Equipos",
                ),
            ),
            # Contenido de las solapas
            html.div(
                {"class_name": "tab-content"},
                AssignmentBox(
                    available_items=available_robots,
                    set_available_items=set_available_robots,
                    assigned_items=assigned_robots,
                    set_assigned_items=set_assigned_robots,
                    selected_available_ids=selected_avail_robots,
                    set_selected_available_ids=set_selected_avail_robots,
                    selected_assigned_ids=selected_asgn_robots,
                    set_selected_assigned_ids=set_selected_asgn_robots,
                )
                if active_tab == "robots"
                else AssignmentBox(
                    available_items=available_equipos,
                    set_available_items=set_available_equipos,
                    assigned_items=assigned_equipos,
                    set_assigned_items=set_assigned_equipos,
                    selected_available_ids=selected_avail_equipos,
                    set_selected_available_ids=set_selected_avail_equipos,
                    selected_assigned_ids=selected_asgn_equipos,
                    set_selected_assigned_ids=set_selected_asgn_equipos,
                ),
            ),
            html.footer(
                html.div(
                    {"class_name": "grid"},
                    html.button({"class_name": "secondary", "on_click": lambda e: on_close()}, "Cancelar"),
                    html.button({"on_click": handle_save}, "Guardar"),
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
    """Componente reutilizable para la UI de asignación (disponibles <-> asignados)."""

    def move_items(source, set_source, dest, set_dest, selected_ids, set_selected_ids):
        items_to_move_ids = {item["ID"] for item in source if item["ID"] in selected_ids}
        set_dest(dest + [item for item in source if item["ID"] in items_to_move_ids])
        set_source([item for item in source if item["ID"] not in items_to_move_ids])
        set_selected_ids([])

    return html.div(
        {"class_name": "grid", "style": {"gridTemplateColumns": "5fr 1fr 5fr", "alignItems": "center", "gap": "1rem"}},
        ResourceListBox("Disponibles", available_items, selected_available_ids, set_selected_available_ids),
        html.div(
            {"style": {"display": "flex", "flexDirection": "column", "gap": "1rem"}},
            html.button(
                {
                    "on_click": lambda e: move_items(
                        available_items,
                        set_available_items,
                        assigned_items,
                        set_assigned_items,
                        selected_available_ids,
                        set_selected_available_ids,
                    ),
                    "disabled": not selected_available_ids,
                    "data-tooltip": "Asignar seleccionados",
                },
                html.i({"class_name": "fa-solid fa-arrow-right"}),
            ),
            html.button(
                {
                    "on_click": lambda e: move_items(
                        assigned_items,
                        set_assigned_items,
                        available_items,
                        set_available_items,
                        selected_assigned_ids,
                        set_selected_assigned_ids,
                    ),
                    "disabled": not selected_assigned_ids,
                    "data-tooltip": "Desasignar seleccionados",
                },
                html.i({"class_name": "fa-solid fa-arrow-left"}),
            ),
        ),
        ResourceListBox("Asignados", assigned_items, selected_assigned_ids, set_selected_assigned_ids),
    )


@component
def ResourceListBox(title: str, items: List[Dict], selected_ids: List[int], set_selected_ids: Callable):
    """Renderiza una lista de equipos seleccionables con búsqueda."""
    search, set_search = use_state("")
    sorted_items = use_memo(lambda: sorted(items, key=lambda x: x.get("Nombre", "").lower()), [items])
    filtered_items = use_memo(
        lambda: [item for item in sorted_items if search.lower() in item["Nombre"].lower()],
        [sorted_items, search],
    )

    selected_ids_set = use_memo(lambda: set(selected_ids), [selected_ids])
    all_filtered_ids = use_memo(lambda: [item["ID"] for item in filtered_items], [filtered_items])
    are_all_selected = len(selected_ids) > 0 and all(item_id in selected_ids_set for item_id in all_filtered_ids)

    def handle_selection(item_id):
        current_selection = list(selected_ids)
        if item_id in current_selection:
            current_selection.remove(item_id)
        else:
            current_selection.append(item_id)
        set_selected_ids(current_selection)

    def handle_select_all(event):
        if event["target"]["checked"]:
            set_selected_ids(all_filtered_ids)
        else:
            set_selected_ids([])

    return html.div(
        {"class_name": "device-list-section"},
        html.div(
            {"class_name": "device-list-header"},
            html.h5(title),
            html.input(
                {
                    "type": "search",
                    "name": f"search-{title.lower()}",
                    "placeholder": "Filtrar...",
                    "value": search,
                    "on_change": lambda e: set_search(e["target"]["value"]),
                }
            ),
        ),
        html.div(
            {"class_name": "device-list-table compact-assignment-table"},
            html.table(
                {"role": "grid"},
                html.thead(
                    html.tr(
                        html.th(
                            {"scope": "col", "style": {"width": "40px"}},
                            html.input(
                                {
                                    "type": "checkbox",
                                    "checked": are_all_selected,
                                    "on_change": handle_select_all,
                                }
                            ),
                        ),
                        html.th({"scope": "col"}, "Nombre"),
                    )
                ),
                html.tbody(
                    *[
                        html.tr(
                            {"key": item["ID"]},
                            html.td(
                                html.input(
                                    {
                                        "type": "checkbox",
                                        "checked": item["ID"] in selected_ids_set,
                                        "on_change": lambda e, i_id=item["ID"]: handle_selection(i_id),
                                    }
                                )
                            ),
                            html.td(item["Nombre"]),
                        )
                        for item in filtered_items
                    ]
                    if filtered_items
                    else [
                        html.tr(
                            html.td(
                                {"colSpan": 2, "style": {"text_align": "center"}},
                                "No se encontraron recursos.",
                            )
                        )
                    ]
                ),
            ),
        ),
    )
