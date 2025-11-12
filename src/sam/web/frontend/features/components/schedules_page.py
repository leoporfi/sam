from reactpy import component, html, use_context, use_state

from ...hooks.use_equipos_hook import use_equipos
from ...hooks.use_robots_hook import use_robots
from ...hooks.use_schedules_hook import use_schedules
from ...shared.notifications import NotificationContext
from ..modals.schedule_edit_modal import ScheduleEditModal
from .schedules_components import SchedulesControls, SchedulesDashboard


@component
def SchedulesPage(theme_is_dark: bool, on_theme_toggle):
    # Hooks necesarios
    robots_state = use_robots()
    equipos_state = use_equipos()  # Necesario para PageWithLayout
    schedules_state = use_schedules()

    # Estado de los filtros
    search, set_search = use_state("")
    robot_id, set_robot_id = use_state(None)
    tipo, set_tipo = use_state(None)

    # Estado del modal
    modal_sid, set_modal_sid = use_state(None)
    modal_row, set_modal_row = use_state({})

    # Contexto para notificaciones
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    def set_robot_id_and_filter(r_id):
        set_robot_id(r_id)
        schedules_state["set_filters"]({"robot": r_id, "tipo": tipo, "activo": schedules_state["filters"]["activo"]})

    def set_tipo_and_filter(t):
        set_tipo(t)
        schedules_state["set_filters"]({"robot": robot_id, "tipo": t, "activo": schedules_state["filters"]["activo"]})

    def open_edit_modal(sid: int):
        row = next((s for s in schedules_state["schedules"] if s["ProgramacionId"] == sid), None)
        if row:
            set_modal_row(row)
            set_modal_sid(sid)
        else:
            show_notification("No se encontró la programación", "error")

    # Wrapper con header como las demás páginas
    return PageWithLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state=robots_state,
        equipos_state=equipos_state,
        children=html._(
            # Título dentro del contenido
            html.h2("Gestión de Programaciones"),
            # Controles
            SchedulesControls(
                search=search,
                on_search=set_search,
                robot_filter=robot_id,
                on_robot=set_robot_id_and_filter,
                tipo_filter=tipo,
                on_tipo=set_tipo_and_filter,
                on_new=lambda: show_notification("Función no implementada", "warning"),
                robots_list=robots_state["robots"],
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
