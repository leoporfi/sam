# ARCHIVO: src/web/frontend/app.py
import uuid

from reactpy import component, html, use_effect, use_state
from reactpy_router import browser_router, link, route

from .features.equipos.equipos_components import EquiposControls, EquiposDashboard
from .features.modals.pool_modals import PoolAssignmentsModal, PoolEditModal
from .features.modals.robots_modals import AssignmentsModal, RobotEditModal, SchedulesModal
from .features.pools.pool_components import PoolsControls, PoolsDashboard
from .features.robots.robots_components import RobotsControls, RobotsDashboard
from .hooks.use_debounced_value_hook import use_debounced_value
from .hooks.use_equipos_hook import use_equipos
from .hooks.use_pools_hook import use_pools_management
from .hooks.use_robots_hook import use_robots
from .shared.common_components import ConfirmationModal, ThemeSwitcher
from .shared.notifications import NotificationContext, ToastContainer


# --- Header Component (dentro del router context) ---
@component
def HeaderNav(theme_is_dark: bool, on_theme_toggle, robots_state, equipos_state):
    """Header de navegación con botones de sincronización globales."""
    return html.header(
        {"class_name": "sticky-header"},
        html.div(
            {"class_name": "container"},
            html.nav(
                html.ul(
                    html.li(html.strong("SAM")),
                    html.li(link({"to": "/"}, "Robots")),
                    html.li(link({"to": "/equipos"}, "Equipos")),
                    html.li(link({"to": "/pools"}, "Pools")),
                ),
                html.ul(
                    html.li(
                        html.button(
                            {
                                "on_click": robots_state.get("trigger_sync"),
                                "disabled": robots_state.get("is_syncing", False),
                                "aria-busy": str(robots_state.get("is_syncing", False)).lower(),
                                "class_name": "pico-background-fuchsia-500",
                                "data-tooltip": "Sincronizar Robots",
                            },
                            html.i({"class_name": "fa-solid fa-robot"}),
                        )
                    ),
                    html.li(
                        html.button(
                            {
                                "on_click": equipos_state.get("trigger_sync"),
                                "disabled": equipos_state.get("is_syncing", False),
                                "aria-busy": str(equipos_state.get("is_syncing", False)).lower(),
                                "class_name": "pico-background-purple-500",
                                "data-tooltip": "Sincronizar Equipos",
                            },
                            html.i({"class_name": "fa-solid fa-desktop"}),
                        )
                    ),
                    html.li(ThemeSwitcher(is_dark=theme_is_dark, on_toggle=on_theme_toggle)),
                ),
            ),
        ),
    )


# --- Layout Wrapper para las páginas ---
@component
def PageWithLayout(theme_is_dark: bool, on_theme_toggle, robots_state, equipos_state, children):
    """Wrapper que incluye el header y la estructura principal en cada página."""
    return html._(
        HeaderNav(
            theme_is_dark=theme_is_dark,
            on_theme_toggle=on_theme_toggle,
            robots_state=robots_state,
            equipos_state=equipos_state,
        ),
        html.main({"class_name": "container"}, children),
    )


# --- Componentes de Página (Lógica de cada ruta) ---
@component
def DashboardPage(theme_is_dark: bool, on_theme_toggle):
    """Lógica y UI para la página principal de Robots."""
    robots_state = use_robots()
    equipos_state = use_equipos()

    search_input, set_search_input = use_state(robots_state["filters"].get("name") or "")
    debounced_search = use_debounced_value(search_input, 300)

    @use_effect(dependencies=[debounced_search])
    def sync_search_with_filters():
        robots_state["set_filters"](lambda prev_filters: {**prev_filters, "name": debounced_search or None})

    is_searching = debounced_search != search_input
    selected_robot, set_selected_robot = use_state(None)
    modal_view, set_modal_view = use_state(None)

    def handle_modal_close(event=None):
        set_selected_robot(None)
        set_modal_view(None)

    async def handle_save_and_refresh():
        await robots_state["refresh"]()
        handle_modal_close()

    def handle_create_robot(event=None):
        set_selected_robot({})
        set_modal_view("edit")

    async def handle_robot_action(action: str, robot):
        if action in ["toggle_active", "toggle_online"]:
            status_key = "Activo" if action == "toggle_active" else "EsOnline"
            await robots_state["update_robot_status"](robot["RobotId"], {status_key: not robot[status_key]})
        else:
            set_selected_robot(robot)
            set_modal_view(action)

    page_controls = RobotsControls(
        is_syncing=robots_state["is_syncing"],
        on_sync=robots_state["trigger_sync"],
        on_create_robot=handle_create_robot,
        search_term=search_input,
        on_search_change=set_search_input,
        active_filter="all"
        if robots_state["filters"].get("active") is None
        else str(robots_state["filters"].get("active")).lower(),
        on_active_change=lambda value: robots_state["set_filters"](
            lambda prev: {**prev, "active": None if value == "all" else value == "true"}
        ),
        online_filter="all"
        if robots_state["filters"].get("online") is None
        else str(robots_state["filters"].get("online")).lower(),
        on_online_change=lambda value: robots_state["set_filters"](
            lambda prev: {**prev, "online": None if value == "all" else value == "true"}
        ),
        is_searching=is_searching,
        is_syncing_equipos=equipos_state.get("is_syncing", False),
        on_sync_equipos=equipos_state.get("trigger_sync"),
    )

    # FIX: Eliminamos la duplicación de robots_state
    return PageWithLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state=robots_state,
        equipos_state=equipos_state,
        children=html._(
            page_controls,
            RobotsDashboard(
                robots=robots_state["robots"],
                on_action=handle_robot_action,
                robots_state=robots_state,
                set_current_page=robots_state["set_current_page"],
            ),
            RobotEditModal(
                robot=selected_robot if modal_view == "edit" else None,
                on_close=handle_modal_close,
                on_save_success=handle_save_and_refresh,
            ),
            AssignmentsModal(
                robot=selected_robot if modal_view == "assign" else None,
                on_close=handle_modal_close,
                on_save_success=handle_save_and_refresh,
            ),
            SchedulesModal(
                robot=selected_robot if modal_view == "schedule" else None,
                on_close=handle_modal_close,
                on_save_success=handle_save_and_refresh,
            ),
        ),
    )


@component
def PoolsPage(theme_is_dark: bool, on_theme_toggle):
    """Lógica y UI para la página de Pools."""
    robots_state = use_robots()
    equipos_state = use_equipos()
    pools_state = use_pools_management()

    # Estados para búsqueda y modales
    search_input, set_search_input = use_state("")
    debounced_search = use_debounced_value(search_input, 300)
    modal_pool, set_modal_pool = use_state(None)
    modal_view, set_modal_view = use_state(None)
    pool_to_delete, set_pool_to_delete = use_state(None)

    # Filtrar pools por búsqueda
    filtered_pools = [
        pool
        for pool in pools_state["pools"]
        if not debounced_search or debounced_search.lower() in pool["Nombre"].lower()
    ]

    is_searching = debounced_search != search_input

    def handle_modal_close(event=None):
        set_modal_pool(None)
        set_modal_view(None)
        set_pool_to_delete(None)

    def handle_create_click(event=None):
        set_modal_pool({})
        set_modal_view("edit")

    def handle_edit_click(pool):
        set_modal_pool(pool)
        set_modal_view("edit")

    def handle_assign_click(pool):
        set_modal_pool(pool)
        set_modal_view("assign")

    def handle_delete_click(pool):
        set_pool_to_delete(pool)

    async def handle_confirm_delete():
        if pool_to_delete:
            await pools_state["remove_pool"](pool_to_delete["PoolId"])
            handle_modal_close()

    async def handle_save_pool(pool_data):
        if pool_data.get("PoolId"):
            await pools_state["edit_pool"](pool_data["PoolId"], pool_data)
        else:
            await pools_state["add_pool"](pool_data)
        handle_modal_close()

    page_controls = PoolsControls(
        search_term=search_input,
        on_search_change=set_search_input,
        is_searching=is_searching,
        on_create_pool=handle_create_click,
    )

    return PageWithLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state=robots_state,
        equipos_state=equipos_state,
        children=html._(
            page_controls,
            PoolsDashboard(
                pools=filtered_pools,
                on_edit=handle_edit_click,
                on_assign=handle_assign_click,
                on_delete=handle_delete_click,
                loading=pools_state["loading"],
                error=pools_state["error"],
            ),
            PoolEditModal(
                pool=modal_pool if modal_view == "edit" else None,
                on_close=handle_modal_close,
                on_save=handle_save_pool,
            ),
            PoolAssignmentsModal(
                pool=modal_pool if modal_view == "assign" else None,
                on_close=handle_modal_close,
                on_save_success=pools_state["refresh"],
            ),
            ConfirmationModal(
                is_open=bool(pool_to_delete),
                title="Confirmar Eliminación",
                message=f"¿Estás seguro de que quieres eliminar el pool '{pool_to_delete['Nombre'] if pool_to_delete else ''}'?",
                on_confirm=handle_confirm_delete,
                on_cancel=handle_modal_close,
            ),
        ),
    )


@component
def EquiposPage(theme_is_dark: bool, on_theme_toggle):
    """Lógica y UI para la nueva página de Equipos."""
    robots_state = use_robots()
    equipos_state = use_equipos()
    search_input, set_search_input = use_state(equipos_state["filters"].get("name") or "")
    debounced_search = use_debounced_value(search_input, 300)

    @use_effect(dependencies=[debounced_search])
    def sync_search_with_filters():
        equipos_state["set_filters"](lambda prev_filters: {**prev_filters, "name": debounced_search or None})

    is_searching = debounced_search != search_input

    page_controls = EquiposControls(
        search_term=search_input,
        on_search_change=set_search_input,
        is_searching=is_searching,
        active_filter="all"
        if equipos_state["filters"].get("active") is None
        else str(equipos_state["filters"].get("active")).lower(),
        on_active_change=lambda value: equipos_state["set_filters"](
            lambda prev: {**prev, "active": None if value == "all" else value == "true"}
        ),
        balanceable_filter="all"
        if equipos_state["filters"].get("balanceable") is None
        else str(equipos_state["filters"].get("balanceable")).lower(),
        on_balanceable_change=lambda value: equipos_state["set_filters"](
            lambda prev: {**prev, "balanceable": None if value == "all" else value == "true"}
        ),
    )

    return PageWithLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state=robots_state,
        equipos_state=equipos_state,
        children=html._(page_controls, EquiposDashboard(equipos_state=equipos_state)),
    )


@component
def NotFoundPage(theme_is_dark: bool, on_theme_toggle):
    """Página para rutas no encontradas."""
    robots_state = use_robots()
    equipos_state = use_equipos()

    return PageWithLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state=robots_state,
        equipos_state=equipos_state,
        children=html.article(
            html.header(html.h1("Página no encontrada")),
            html.p("La página que buscas no existe."),
        ),
    )


# --- Estructura Principal de la App ---
@component
def App():
    """Componente raíz que provee el contexto y el enrutador."""
    notifications, set_notifications = use_state([])
    is_dark, set_is_dark = use_state(True)
    script_to_run, set_script_to_run = use_state(html._())

    @use_effect(dependencies=[is_dark])
    def apply_theme():
        theme = "dark" if is_dark else "light"
        key = f"theme-script-{uuid.uuid4()}"
        js_code = f"document.documentElement.setAttribute('data-theme', '{theme}')"
        set_script_to_run(html.script({"key": key}, js_code))

    def show_notification(message, style="success"):
        new_id = str(uuid.uuid4())
        set_notifications(lambda old: old + [{"id": new_id, "message": message, "style": style}])

    def dismiss_notification(notification_id):
        set_notifications(lambda old: [n for n in old if n["id"] != notification_id])

    context_value = {
        "notifications": notifications,
        "show_notification": show_notification,
        "dismiss_notification": dismiss_notification,
    }

    return NotificationContext(
        html._(
            script_to_run,
            browser_router(
                route("/", DashboardPage(theme_is_dark=is_dark, on_theme_toggle=set_is_dark)),
                route("/pools", PoolsPage(theme_is_dark=is_dark, on_theme_toggle=set_is_dark)),
                route("/equipos", EquiposPage(theme_is_dark=is_dark, on_theme_toggle=set_is_dark)),
                route("*", NotFoundPage(theme_is_dark=is_dark, on_theme_toggle=set_is_dark)),
            ),
            ToastContainer(),
        ),
        value=context_value,
    )


# --- Elementos del <head> ---
head = html.head(
    html.title("SAM"),
    html.meta({"charset": "utf-8"}),
    html.meta({"name": "viewport", "content": "width=device-width, initial-scale=1"}),
    html.link({"rel": "stylesheet", "href": "/static/css/pico.violet.min.css"}),
    html.link(
        {"rel": "stylesheet", "href": "https://cdn.jsdelivr.net/npm/@picocss/pico@2.1.1/css/pico.colors.min.css"}
    ),
    html.link({"rel": "stylesheet", "href": "/static/css/all.min.css"}),
    html.link({"rel": "stylesheet", "href": "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined"}),
    html.link({"rel": "stylesheet", "href": "/static/custom.css"}),
)
