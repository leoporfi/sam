import asyncio  # <--- AÑADIDO

from reactpy import component, html, use_context, use_effect, use_state

from sam.web.frontend.hooks.use_debounced_value_hook import use_debounced_value

from ...api.api_client import get_api_client
from ...hooks.use_equipos_hook import use_equipos
from ...hooks.use_robots_hook import use_robots
from ...hooks.use_schedules_hook import use_schedules
from ...shared.notifications import NotificationContext
from ..modals.schedule_edit_modal import ScheduleEditModal
from .schedules_components import SchedulesControls, SchedulesDashboard


@component
def SchedulesPage(theme_is_dark: bool, on_theme_toggle):
    # --- Hooks de estado ---
    robots_state = use_robots()  # Se mantiene para el PageWithLayout
    equipos_state = use_equipos()
    schedules_state = use_schedules()

    # --- Estado de los filtros ---
    search, set_search = use_state("")
    robot_id, set_robot_id = use_state(None)
    tipo, set_tipo = use_state(None)
    debounced_search = use_debounced_value(search, delay=500)

    # --- NUEVO ESTADO: Lista de robots para el dropdown ---
    dropdown_robots, set_dropdown_robots = use_state([])  # <--- AÑADIDO

    # --- Estado del modal ---
    modal_sid, set_modal_sid = use_state(None)
    modal_row, set_modal_row = use_state({})

    # --- Contexto de notificaciones ---
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    # --- EFECTO 1: Cargar la lista de robots para el dropdown ---
    # Este efecto se ejecuta UNA VEZ al cargar la página
    @use_effect(dependencies=[])  # <--- AÑADIDO (COMPLETAMENTE NUEVO)
    def load_all_robots_for_dropdown():
        api = get_api_client()

        async def fetch():
            try:
                # Pedimos los primeros 100 robots (máximo de tu API) sin filtros
                params = {"page": 1, "size": 100, "active": None}
                data = await api.get_robots(params)
                set_dropdown_robots(data.get("robots", []))
            except Exception as e:
                print(f"Error al cargar la lista de robots para el filtro: {e}")
                show_notification("Error al cargar filtros de robots", "error")

        task = asyncio.create_task(fetch())
        return lambda: task.cancel()

    # --- EFECTO 2: Aplicar filtros a la tabla de programaciones ---
    # Este es el efecto que TÚ preguntaste. ¡DEBE QUEDARSE!
    # Se ejecuta CADA VEZ que uno de sus 'dependencies' cambia.
    @use_effect(dependencies=[debounced_search, robot_id, tipo])
    def apply_filters():
        schedules_state["set_filters"](
            {
                "robot": robot_id,
                "tipo": tipo,
                "activo": schedules_state["filters"]["activo"],  # Preservar filtro 'activo'
                "search": debounced_search if debounced_search else None,
            }
        )

    # --- Manejadores de eventos (simplificados) ---
    def set_robot_id_and_filter(r_id):
        set_robot_id(r_id)  # <-- Solo actualiza el estado local

    def set_tipo_and_filter(t):
        set_tipo(t)  # <-- Solo actualiza el estado local

    def open_edit_modal(sid: int):
        row = next((s for s in schedules_state["schedules"] if s["ProgramacionId"] == sid), None)
        if row:
            set_modal_row(row)
            set_modal_sid(sid)
        else:
            show_notification("No se encontró la programación", "error")

    # --- Renderizado del componente ---
    return PageWithLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state=robots_state,
        equipos_state=equipos_state,
        children=html._(
            html.h2("Gestión de Programaciones"),
            SchedulesControls(
                search=search,
                on_search=set_search,
                robot_filter=robot_id,
                on_robot=set_robot_id_and_filter,
                tipo_filter=tipo,
                on_tipo=set_tipo_and_filter,
                on_new=lambda: show_notification("Función no implementada", "warning"),
                robots_list=dropdown_robots,  # <--- MODIFICADO
                is_searching=schedules_state["loading"],
            ),
            # Estado de carga
            html.div(
                {"style": {"display": "block" if schedules_state["loading"] else "none"}},
                html.div({"style": {"textAlign": "center", "padding": "2rem"}}, "Cargando programaciones..."),
            ),
            # Mensaje de error
            html.div(
                {"style": {"display": "block" if schedules_state["error"] else "none"}},
                html.article(
                    {"aria_invalid": "true", "style": {"color": "var(--pico-color-red-600)"}},
                    f"Error: {schedules_state['error']}",
                ),
            ),
            # Dashboard (solo si no hay carga ni error)
            html.div(
                {
                    "style": {
                        "display": "block"
                        if not schedules_state["loading"] and not schedules_state["error"]
                        else "none"
                    }
                },
                SchedulesDashboard(
                    schedules=schedules_state["schedules"],
                    on_toggle=schedules_state["toggle_active"],
                    on_edit=open_edit_modal,
                    page=schedules_state["current_page"],
                    total_pages=schedules_state["total_pages"],
                    on_page=schedules_state["set_page"],
                    total_count=schedules_state["total_count"],
                ),
            ),
            # Modal
            ScheduleEditModal(
                schedule_id=modal_sid,
                schedule=modal_row,
                is_open=modal_sid is not None,
                on_close=lambda: set_modal_sid(None),
                on_save=schedules_state["save_schedule"],
            ),
        ),
    )


from ...shared.common_components import PageWithLayout
