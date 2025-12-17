# sam/web/frontend/app.py
import asyncio
import uuid

# app.py - SECCIÓN DE IMPORTS
from reactpy import component, html, use_context, use_effect, use_location, use_state
from reactpy_router import browser_router, route

from sam.web.frontend.api.api_client import APIClient

# Componentes de páginas
from .features.components.equipo_list import EquiposControls, EquiposDashboard
from .features.components.mappings_page import MappingsPage

# Busca esta línea y agrega el nuevo componente:
from .features.components.pool_list import BalanceadorStrategyPanel, PoolsControls, PoolsDashboard
from .features.components.robot_list import RobotsControls, RobotsDashboard
from .features.components.schedule_list import SchedulesControls, SchedulesDashboard

# Modales
from .features.modals.equipos_modals import EquipoEditModal
from .features.modals.pool_modals import PoolAssignmentsModal, PoolEditModal
from .features.modals.robots_modals import AssignmentsModal, RobotEditModal, SchedulesModal
from .features.modals.schedule_modal import ScheduleEditModal, ScheduleEquiposModal

# Hooks
from .hooks.use_debounced_value_hook import use_debounced_value
from .hooks.use_equipos_hook import use_equipos
from .hooks.use_pools_hook import use_pools_management
from .hooks.use_robots_hook import use_robots
from .hooks.use_schedules_hook import use_schedules

# Layout
# Componentes compartidos
from .shared.common_components import ConfirmationModal, PageWithLayout
from .shared.notifications import NotificationContext, ToastContainer

# Contexto de la aplicación
from .state.app_context import AppProvider


# --- Componentes de Página (Lógica de cada ruta) ---
@component
def RobotsPage(theme_is_dark: bool, on_theme_toggle):
    """Lógica y UI para la página principal de Robots."""
    robots_state = use_robots()
    equipos_state = use_equipos()

    search_input, set_search_input = use_state(robots_state["filters"].get("name") or "")
    debounced_search = use_debounced_value(search_input, 300)

    @use_effect(dependencies=[debounced_search])
    def sync_search_with_filters():
        if debounced_search == robots_state["filters"].get("name"):
            return
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
        active_filter="all" if robots_state["filters"].get("active") is None else str(robots_state["filters"].get("active")).lower(),
        on_active_change=lambda value: robots_state["set_filters"](lambda prev: {**prev, "active": None if value == "all" else value == "true"}),
        online_filter="all" if robots_state["filters"].get("online") is None else str(robots_state["filters"].get("online")).lower(),
        on_online_change=lambda value: robots_state["set_filters"](lambda prev: {**prev, "online": None if value == "all" else value == "true"}),
        is_searching=is_searching,
        is_syncing_equipos=equipos_state.get("is_syncing", False),
        on_sync_equipos=equipos_state.get("trigger_sync"),
    )

    base_key = str(selected_robot.get("RobotId", uuid.uuid4())) if selected_robot and isinstance(selected_robot, dict) else str(uuid.uuid4())

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
                robot=selected_robot or {},
                is_open=modal_view == "edit",
                on_close=handle_modal_close,
                on_save_success=handle_save_and_refresh,
                key=f"{base_key}-edit",
            ),
            AssignmentsModal(
                robot=selected_robot or {},
                is_open=modal_view == "assign",
                on_close=handle_modal_close,
                on_save_success=handle_save_and_refresh,
                key=f"{base_key}-assign",
            ),
            SchedulesModal(
                robot=selected_robot or {},
                is_open=modal_view == "schedule",
                on_close=handle_modal_close,
                on_save_success=handle_save_and_refresh,
                key=f"{base_key}-schedule",
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
    filtered_pools = [pool for pool in pools_state["pools"] if not debounced_search or debounced_search.lower() in pool["Nombre"].lower()]

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

    base_key = str(modal_pool["PoolId"]) if modal_pool else str(uuid.uuid4())
    return PageWithLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state=robots_state,
        equipos_state=equipos_state,
        children=html._(
            page_controls,
            BalanceadorStrategyPanel(),
            PoolsDashboard(
                pools=filtered_pools,
                on_edit=handle_edit_click,
                on_assign=handle_assign_click,
                on_delete=handle_delete_click,
                loading=pools_state["loading"],
                error=pools_state["error"],
            ),
            PoolEditModal(
                pool=modal_pool or {},
                is_open=modal_view == "edit",
                on_close=handle_modal_close,
                on_save=handle_save_pool,
                key=f"{base_key}-edit",
            ),
            PoolAssignmentsModal(
                pool=modal_pool or {},
                is_open=modal_view == "assign",
                on_close=handle_modal_close,
                on_save_success=pools_state["refresh"],
                key=f"{base_key}-assign",
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

    is_modal_open, set_is_modal_open = use_state(False)
    # selected_equipo, set_selected_equipo = use_state(None) # Para futura edición

    def handle_create_click():
        """Abre el modal en modo creación."""
        # set_selected_equipo(None) # Asegura que no haya datos previos
        set_is_modal_open(True)

    def handle_modal_close():
        """Cierra el modal."""
        set_is_modal_open(False)
        # set_selected_equipo(None)

    async def handle_save_success():
        """Callback llamado por el modal tras guardar con éxito."""
        await equipos_state["refresh"]()

    search_input, set_search_input = use_state(equipos_state["filters"].get("name") or "")
    debounced_search = use_debounced_value(search_input, 300)

    @use_effect(dependencies=[debounced_search])
    def sync_search_with_filters():
        async def do_sync():
            await asyncio.sleep(0.05)
            if debounced_search == equipos_state["filters"].get("name"):
                return
            equipos_state["set_filters"](lambda prev: {**prev, "name": debounced_search or None})

        task = asyncio.create_task(do_sync())

        def cleanup():
            if not task.done():
                task.cancel()

        return cleanup

    is_searching = debounced_search != search_input

    page_controls = EquiposControls(
        search=search_input,
        on_search=set_search_input,
        is_searching=is_searching,
        active_filter="all" if equipos_state["filters"].get("active") is None else str(equipos_state["filters"].get("active")).lower(),
        on_active=lambda value: equipos_state["set_filters"](lambda prev: {**prev, "active": None if value == "all" else value == "true"}),
        balanceable_filter="all" if equipos_state["filters"].get("balanceable") is None else str(equipos_state["filters"].get("balanceable")).lower(),
        on_balanceable=lambda value: equipos_state["set_filters"](lambda prev: {**prev, "balanceable": None if value == "all" else value == "true"}),
        on_create_equipo=handle_create_click,
    )

    return PageWithLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state=robots_state,
        equipos_state=equipos_state,
        children=html._(
            page_controls,
            EquiposDashboard(equipos_state=equipos_state),
            EquipoEditModal(
                equipo=None,  # Pasar None para modo creación
                is_open=is_modal_open,
                on_close=handle_modal_close,
                on_save_success=handle_save_success,
            ),
        ),
    )


@component
def SchedulesPage(theme_is_dark: bool, on_theme_toggle):
    """Lógica y UI para la página de Programaciones con filtros en cascada."""
    # --- Hooks de estado ---
    robots_state = use_robots()
    equipos_state = use_equipos()
    schedules_state = use_schedules()

    # --- Estado de los filtros UI ---
    search_input, set_search_input = use_state("")
    debounced_search = use_debounced_value(search_input, delay=500)

    robot_filter, set_robot_filter = use_state(None)
    tipo_filter, set_tipo_filter = use_state(None)

    # --- Estado del Dropdown de Robots (Dinámico) ---
    dropdown_robots, set_dropdown_robots = use_state([])

    # --- Estado de Modales ---
    modal_sid, set_modal_sid = use_state(None)  # ID para Edición
    modal_row, set_modal_row = use_state({})  # Datos para Edición

    assign_equipos_sid, set_assign_equipos_sid = use_state(None)  # ID para Asignar Equipos

    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    # --- LÓGICA 1: Cargar robots dinámicamente según el Tipo (CASCADA) ---
    @use_effect(dependencies=[tipo_filter])
    def init_data_load():
        async def fetch_data():
            api = get_api_client()
            try:
                # Solicitamos programaciones filtradas por tipo para extraer los robots relevantes
                params = {"page": 1, "size": 300}
                if tipo_filter:
                    params["tipo"] = tipo_filter

                data = await api.get_schedules(params)
                items = data.get("items") or data.get("schedules", [])
                unique_robots = {}
                for s in items:
                    rid = s.get("RobotId")
                    rname = s.get("RobotNombre") or s.get("Robot", {}).get("Nombre")

                    if rid and rname and rid not in unique_robots:
                        unique_robots[rid] = {"RobotId": rid, "Robot": rname}

                sorted_robots = sorted(unique_robots.values(), key=lambda r: r["Robot"])
                set_dropdown_robots(sorted_robots)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"Error cargando filtro de robots: {e}")

        task = asyncio.create_task(fetch_data())
        return lambda: task.cancel()

    # --- LÓGICA 2: Sincronizar UI -> Hook de Datos (Filtros) ---

    # A) Búsqueda (con Debounce)
    @use_effect(dependencies=[debounced_search])
    def sync_search():
        schedules_state["set_filters"](lambda prev: {**prev, "search": debounced_search or None})

    # B) Filtro Robot
    @use_effect(dependencies=[robot_filter])
    def sync_robot():
        schedules_state["set_filters"](lambda prev: {**prev, "robot": robot_filter})

    # C) Filtro Tipo
    @use_effect(dependencies=[tipo_filter])
    def sync_tipo():
        # Al cambiar el tipo, actualizamos el filtro principal
        schedules_state["set_filters"](lambda prev: {**prev, "tipo": tipo_filter})

    # --- Handlers de Modales ---
    def open_edit_modal(sid: int):
        row = next((s for s in schedules_state["schedules"] if s["ProgramacionId"] == sid), None)
        if row:
            set_modal_row(row)
            set_modal_sid(sid)
        else:
            show_notification("No se encontró la programación", "error")

    def open_schedule_equipos_modal(schedule_data):
        sid = schedule_data.get("ProgramacionId")
        if sid:
            set_assign_equipos_sid(sid)
            set_modal_row(schedule_data)

    return PageWithLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state=robots_state,
        equipos_state=equipos_state,
        children=html._(
            SchedulesControls(
                search=search_input,
                on_search=set_search_input,
                robot_filter=robot_filter,
                on_robot=set_robot_filter,
                tipo_filter=tipo_filter,
                on_tipo=set_tipo_filter,
                on_new=lambda: show_notification("Función no implementada", "warning"),
                robots_list=dropdown_robots,
                is_searching=schedules_state["loading"],
            ),
            html.div(
                {"style": {"display": "block" if schedules_state["error"] else "none"}},
                html.article(
                    {"aria_invalid": "true", "style": {"color": "var(--pico-color-red-600)"}},
                    f"Error: {schedules_state['error']}",
                ),
            ),
            html.div(
                {"style": {"display": "block" if not schedules_state["loading"] and not schedules_state["error"] else "none"}},
                SchedulesDashboard(
                    schedules=schedules_state["schedules"],
                    on_toggle=schedules_state["toggle_active"],
                    on_edit=open_edit_modal,
                    on_assign_equipos=open_schedule_equipos_modal,
                    current_page=schedules_state["current_page"],
                    total_pages=schedules_state["total_pages"],
                    on_page_change=schedules_state["set_page"],
                    total_count=schedules_state["total_count"],
                    loading=schedules_state["loading"],
                    error=schedules_state["error"],
                ),
            ),
            # 1. Modal Editar Programación (Detalles)
            ScheduleEditModal(
                schedule_id=modal_sid,
                schedule=modal_row,
                is_open=modal_sid is not None,
                on_close=lambda: set_modal_sid(None),
                on_save=schedules_state["save_schedule"],
            ),
            # 2. Modal Asignar Equipos a Programación (NUEVO)
            ScheduleEquiposModal(
                schedule_id=assign_equipos_sid,
                schedule=modal_row,
                is_open=assign_equipos_sid is not None,
                on_close=lambda: set_assign_equipos_sid(None),
                on_save=schedules_state["save_schedule_equipos"],
            )
            if assign_equipos_sid is not None
            else None,
        ),
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
    """
    Componente raíz que provee los contextos (notificaciones y dependencias) y el enrutador.
    
    Aplica el patrón de Inyección de Dependencias desde el punto más alto (componente raíz),
    siguiendo la Guía General de SAM.
    """
    notifications, set_notifications = use_state([])
    is_dark, set_is_dark = use_state(True)
    script_to_run, set_script_to_run = use_state(html._())

    # Crear instancia única de APIClient para toda la aplicación
    # Esto permite inyección de dependencias y facilita testing
    api_client = APIClient(base_url="http://127.0.0.1:8000")

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

    # Contexto de notificaciones
    notification_context_value = {
        "notifications": notifications,
        "show_notification": show_notification,
        "dismiss_notification": dismiss_notification,
    }

    # Contexto de la aplicación (dependencias inyectadas)
    app_context_value = {
        "api_client": api_client,
    }

    return AppProvider(
        value=app_context_value,
        children=NotificationContext(
            html._(
                script_to_run,
                browser_router(
                    route("/", RobotsPage(theme_is_dark=is_dark, on_theme_toggle=set_is_dark)),
                    route("/equipos", EquiposPage(theme_is_dark=is_dark, on_theme_toggle=set_is_dark)),
                    route("/programaciones", SchedulesPage(theme_is_dark=is_dark, on_theme_toggle=set_is_dark)),
                    route("/pools", PoolsPage(theme_is_dark=is_dark, on_theme_toggle=set_is_dark)),
                    route("/mapeos", MappingsPage(theme_is_dark=is_dark, on_theme_toggle=set_is_dark)),
                    route("*", NotFoundPage(theme_is_dark=is_dark, on_theme_toggle=set_is_dark)),
                ),
                ToastContainer(),
            ),
            value=notification_context_value,
        ),
    )


@component
def TestLocation():
    location = use_location()
    return html.div(f"Current location: {location.pathname}")


# Agrégalo temporalmente en una ruta:
route("/test", TestLocation())

# --- Elementos del <head> ---
head = html.head(
    html.title("SAM"),
    html.meta({"charset": "utf-8"}),
    html.meta({"name": "viewport", "content": "width=device-width, initial-scale=1"}),
    html.link({"rel": "stylesheet", "href": "/static/css/pico.violet.min.css"}),
    html.link({"rel": "stylesheet", "href": "https://cdn.jsdelivr.net/npm/@picocss/pico@2.1.1/css/pico.colors.min.css"}),
    html.link({"rel": "stylesheet", "href": "/static/css/all.min.css"}),
    html.link({"rel": "stylesheet", "href": "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined"}),
    html.link({"rel": "stylesheet", "href": "/static/custom.css"}),
)
