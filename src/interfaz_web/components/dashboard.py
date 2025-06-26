# src/interfaz_web/components/dashboard.py

from reactpy import component, html, use_callback, use_effect, use_state

from ..hooks.use_debounced_value import use_debounced_value
from ..hooks.use_robots import use_robots
from ..schemas.robot_types import RobotFilters
from .assignments_modal import AssignmentsModal
from .common.loading_spinner import LoadingSpinner
from .common.pagination import Pagination
from .robot_filters import RobotFilters as RobotFiltersComponent
from .robot_modal import RobotEditModal
from .robot_table import RobotTable
from .schedules_modal import SchedulesModal


@component
def RobotDashboard():
    # =================================================================
    # 1. OBTENER ESTADO Y FUNCIONES DEL HOOK
    # Toda la lógica de datos ahora vive en el hook 'use_robots'.
    # =================================================================
    robots_state = use_robots()

    # Desempaquetamos para un uso más fácil
    robots = robots_state["robots"]
    loading = robots_state["loading"]
    error = robots_state["error"]
    filters = robots_state["filters"]
    set_filters = robots_state["set_filters"]
    refresh_robots = robots_state["refresh"]
    update_robot_status = robots_state["update_robot_status"]
    # 2. EXTRAEMOS LAS VARIABLES Y FUNCIONES DE PAGINACIÓN DEL HOOK
    current_page = robots_state["current_page"]
    set_current_page = robots_state["set_current_page"]
    total_pages = robots_state["total_pages"]

    # =================================================================
    # 2. GESTIÓN DEL ESTADO LOCAL DE LA UI
    # El dashboard solo maneja el estado 'en vivo' de los inputs.
    # =================================================================
    search_term, set_search_term = use_state(filters.get("name") or "")

    # Usamos nuestro hook para que la búsqueda no se dispare con cada letra
    debounced_search = use_debounced_value(search_term, 300)

    # =================================================================
    # 3. EFECTO PARA SINCRONIZAR LA BÚSQUEDA
    # Este efecto se ejecuta solo cuando el usuario deja de teclear.
    # =================================================================
    @use_effect(dependencies=[debounced_search])
    def sync_search_with_hook():
        # Le decimos al hook que el filtro 'name' ha cambiado.
        set_filters(lambda prev_filters: {**prev_filters, "name": debounced_search or None})

    # =================================================================
    # 4. MANEJADORES DE EVENTOS
    # Funciones que se ejecutarán por acciones del usuario.
    # =================================================================

    def handle_active_filter_change(value):
        active_value = None if value == "all" else value == "true"
        set_filters(lambda prev_filters: {**prev_filters, "active": active_value})

    def handle_online_filter_change(value):
        online_value = None if value == "all" else value == "true"
        set_filters(lambda prev_filters: {**prev_filters, "online": online_value})

    # --- Lógica de Modales (se mantiene igual) ---
    selected_robot, set_selected_robot = use_state(None)
    modal_view, set_modal_view = use_state(None)

    def handle_modal_close(event=None):
        set_selected_robot(None)
        set_modal_view(None)

    async def handle_save_and_refresh():
        await refresh_robots()
        handle_modal_close()

    def handle_create_robot(event=None):
        set_selected_robot({})
        set_modal_view("edit")

    @use_callback
    async def handle_robot_action(action: str, robot):
        if action in ["toggle_active", "toggle_online"]:
            status_key = "Activo" if action == "toggle_active" else "EsOnline"
            await update_robot_status(robot["RobotId"], {status_key: not robot[status_key]})
        elif action == "edit":
            set_selected_robot(robot)
            set_modal_view("edit")
        elif action == "assign":
            set_selected_robot(robot)
            set_modal_view("assign")
        elif action == "schedule":
            set_selected_robot(robot)
            set_modal_view("schedule")

    # =================================================================
    # 5. LÓGICA DE RENDERIZADO
    # =================================================================

    # Decide qué mostrar: el spinner, un error, o la tabla.
    if error:
        content = html.div({"className": "text-red-500 p-4 bg-red-50 rounded-lg"}, f"Error al cargar: {error}")
    elif loading and not robots:
        content = LoadingSpinner()
    else:
        content = RobotTable(robots=robots, on_action=handle_robot_action)

    return html.div(
        {"className": "p-8 space-y-6"},
        # Cabecera con título y botón de Añadir
        html.div(
            {"className": "flex flex-wrap items-center justify-between gap-4"},
            html.h1({"className": "text-3xl font-bold text-gray-900"}, "Gestión de Robots"),
            html.button(
                {
                    "className": "bg-blue-600 text-white hover:bg-blue-700 flex items-center justify-center gap-2 rounded-lg h-10 px-5 text-sm font-medium shadow-sm",
                    "onClick": handle_create_robot,
                },
                html.span({"className": "text-lg"}, "+"),
                html.span({"className": "truncate"}, "Añadir Robot"),
            ),
        ),
        # Componente de Filtros
        RobotFiltersComponent(
            search_term=search_term,
            active_filter="all" if filters.get("active") is None else str(filters.get("active")).lower(),
            online_filter="all" if filters.get("online") is None else str(filters.get("online")).lower(),
            on_search_change=set_search_term,
            on_active_change=handle_active_filter_change,
            on_online_change=handle_online_filter_change,
        ),
        # Contenido principal (Tabla, Spinner, o Error)
        # content,
        html.div(
            {"className": "space-y-4"},
            content,
            # 3. AÑADIMOS EL COMPONENTE DE PAGINACIÓN CONDICIONALMENTE
            # Solo se muestra si hay más de una página
            Pagination(current_page=current_page, total_pages=total_pages, on_page_change=set_current_page) if total_pages > 1 else None,
        ),
        # Modales (solo se renderizan si son necesarios)
        RobotEditModal(robot=selected_robot if modal_view == "edit" else None, on_close=handle_modal_close, on_save_success=handle_save_and_refresh),
        AssignmentsModal(robot=selected_robot if modal_view == "assign" else None, on_close=handle_modal_close, on_save_success=handle_save_and_refresh),
        SchedulesModal(robot=selected_robot if modal_view == "schedule" else None, on_close=handle_modal_close, on_save_success=handle_save_and_refresh),
    )
