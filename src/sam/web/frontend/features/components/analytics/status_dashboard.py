# sam/web/frontend/features/components/analytics/status_dashboard.py

import asyncio
import logging

from reactpy import component, html, use_context, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client
from sam.web.frontend.shared.async_content import SkeletonCardGrid, SkeletonTable
from sam.web.frontend.shared.notifications import NotificationContext

logger = logging.getLogger(__name__)


@component
def StatusDashboard(scroll_to=None):
    """Dashboard de estado actual del sistema."""
    status_data, set_status_data = use_state(None)
    executions_data, set_executions_data = use_state({"fallos": [], "demoras": []})
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)

    # Estado para tabs
    active_tab, set_active_tab = use_state("fallos")

    # Nuevo estado para el filtro
    grouped_view, set_grouped_view = use_state(False)

    # Estados para filtros (valores en inputs)
    filter_robot, set_filter_robot = use_state("")
    filter_equipo, set_filter_equipo = use_state("")
    filter_limit, set_filter_limit = use_state("100")

    # Estados para filtros aplicados (valores que se envían al backend)
    applied_robot, set_applied_robot = use_state("")
    applied_equipo, set_applied_equipo = use_state("")
    applied_limit, set_applied_limit = use_state(100)

    # Estado para el proceso de destrabar
    unlocking_id, set_unlocking_id = use_state(None)

    # Estado para el modal de confirmación
    show_confirm_modal, set_show_confirm_modal = use_state(False)
    pending_unlock_id, set_pending_unlock_id = use_state(None)

    # Obtener contexto de notificaciones
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"] if notification_ctx else None

    api_client = get_api_client()

    async def fetch_status():
        try:
            set_loading(True)
            set_error(None)

            # 1. Fetch System Status
            data = await api_client.get("/api/analytics/status")
            set_status_data(data)

            # 2. Fetch Recent Executions
            # Pasamos los filtros aplicados
            exec_params = {"limit": applied_limit}

            # Agregar filtros opcionales solo si tienen valor
            if applied_robot:
                exec_params["robot_name"] = applied_robot
            if applied_equipo:
                exec_params["equipo_name"] = applied_equipo

            # Solo agrupar si estamos en la pestaña de fallos
            if active_tab == "fallos" and grouped_view:
                exec_params["grouped"] = True

            exec_data = await api_client.get("/api/analytics/executions", params=exec_params)
            set_executions_data(exec_data)
            set_loading(False)
        except asyncio.CancelledError:
            # Silenciar errores de cancelación y NO actualizar estado
            pass
        except Exception as e:
            set_error(str(e))
            logger.error(f"Error obteniendo estado: {e}")
            set_loading(False)

    def handle_refresh(event=None):
        """Wrapper para manejar el click del botón de actualizar."""
        asyncio.create_task(fetch_status())

    def handle_apply_filters(event=None):
        """Aplica los filtros y refresca los datos."""
        # Convertir limit a int, con valor por defecto si es inválido
        try:
            limit_value = int(filter_limit) if filter_limit else 100
            if limit_value <= 0:
                limit_value = 100
        except ValueError:
            limit_value = 100

        # Actualizar los filtros aplicados
        set_applied_robot(filter_robot.strip())
        set_applied_equipo(filter_equipo.strip())
        set_applied_limit(limit_value)

        # Refrescar datos con los nuevos filtros
        asyncio.create_task(fetch_status())

    def request_unlock_confirmation(deployment_id):
        """Abre el modal de confirmación para destrabar."""
        set_pending_unlock_id(deployment_id)
        set_show_confirm_modal(True)

    def cancel_unlock():
        """Cierra el modal de confirmación."""
        set_show_confirm_modal(False)
        set_pending_unlock_id(None)

    async def confirm_unlock():
        """Ejecuta la acción de destrabar después de la confirmación."""
        if pending_unlock_id:
            set_show_confirm_modal(False)
            await handle_unlock(pending_unlock_id)
            set_pending_unlock_id(None)

    async def handle_unlock(deployment_id):
        """Solicita al backend destrabar una ejecución."""
        if not deployment_id:
            return

        set_unlocking_id(deployment_id)

        try:
            logger.info(f"Solicitando destrabar ejecución: {deployment_id}")
            res = await api_client.post(f"/api/executions/{deployment_id}/unlock", data={})

            if res.get("success"):
                if show_notification:
                    show_notification(res.get("message", "Ejecución destrabada correctamente."), "success")
                # Refrescar datos después de un pequeño delay
                await asyncio.sleep(1.5)
                await fetch_status()
            else:
                if show_notification:
                    show_notification(res.get("message", "Error al destrabar ejecución."), "error")

        except Exception as e:
            logger.error(f"Error al destrabar ejecución {deployment_id}: {e}")
            if show_notification:
                show_notification(f"Error: {str(e)}", "error")
        finally:
            set_unlocking_id(None)

    def format_duration(minutes):
        """Formatea minutos a 'dd hh:mm:ss' o 'hh:mm:ss'."""
        if minutes is None:
            return "-"

        total_seconds = int(minutes * 60)
        days = total_seconds // 86400
        remaining_seconds = total_seconds % 86400
        hours = remaining_seconds // 3600
        remaining_seconds %= 3600
        mins = remaining_seconds // 60
        secs = remaining_seconds % 60

        if days > 0:
            return f"{days}d {hours:02}:{mins:02}:{secs:02}"
        return f"{hours:02}:{mins:02}:{secs:02}"

    # Efecto para cargar datos al inicio y cuando cambia el filtro
    @use_effect(dependencies=[grouped_view, active_tab])
    def load_data():
        # Crear tarea asíncrona para cargar datos
        task = asyncio.create_task(fetch_status())

        # Configurar actualización automática cada 30 segundos
        async def periodic_update():
            while True:
                await asyncio.sleep(30)
                await fetch_status()

        update_task = asyncio.create_task(periodic_update())

        def cleanup():
            if not task.done():
                task.cancel()
            if not update_task.done():
                update_task.cancel()

        return cleanup

    if loading and not status_data:
        return html.div(
            {"class_name": "status-dashboard"},
            html.header(
                {"class_name": "dashboard-header"},
                html.h2({"class_name": "dashboard-title"}, "Estado Actual del Sistema"),
            ),
            SkeletonCardGrid(count=4),
            html.div({"style": {"margin-top": "2rem"}}, SkeletonTable(rows=5, cols=7)),
        )

    if error:
        return html.div(
            {"class_name": "status-dashboard error", "style": {"color": "var(--pico-color-red-600)"}},
            html.h3("Error"),
            html.p(error),
            html.button({"on_click": handle_refresh}, "Reintentar"),
        )

    if not status_data:
        return html.div({"class_name": "status-dashboard"}, html.p("No hay datos disponibles"))

    ejecuciones = status_data.get("ejecuciones", {})
    robots = status_data.get("robots", {})
    equipos = status_data.get("equipos", {})
    programaciones = status_data.get("programaciones", {})
    timestamp = status_data.get("timestamp", "N/A")

    # Procesar datos para tabs
    fallos = executions_data.get("fallos", [])
    demoras_raw = executions_data.get("demoras", [])
    demoras = [x for x in demoras_raw if x.get("TipoCritico") == "Demorada"]
    huerfanas = [x for x in demoras_raw if x.get("TipoCritico") == "Huerfana"]

    # Seleccionar datos según tab activo
    current_data = []
    if active_tab == "fallos":
        current_data = fallos
    elif active_tab == "demoras":
        current_data = demoras
    elif active_tab == "huerfanas":
        current_data = huerfanas

    def handle_key_down(event):
        """Dispara la búsqueda al presionar Enter."""
        if event["key"] == "Enter":
            handle_apply_filters()

    return html.div(
        {"class_name": "status-dashboard"},
        # --- MODAL DE CONFIRMACIÓN ---
        html.dialog(
            {"open": show_confirm_modal},
            html.article(
                html.header(
                    html.button({"aria-label": "Close", "class_name": "close", "on_click": lambda e: cancel_unlock()}),
                    html.h3("⚠️ Confirmar Acción Manual"),
                ),
                html.p(
                    "Estás a punto de destrabar manualmente esta ejecución. ",
                    html.strong("Esta acción NO detiene el proceso en Automation Anywhere."),
                ),
                html.p("Solo se actualizará el estado en la base de datos local para liberar el equipo y el robot."),
                html.div(
                    {
                        "class_name": "alert alert-warning",
                        "style": {
                            "background-color": "#fff3cd",
                            "color": "#856404",
                            "padding": "1rem",
                            "border-radius": "0.5rem",
                            "margin-bottom": "1rem",
                        },
                    },
                    html.strong("IMPORTANTE: "),
                    "Antes de continuar, verifica manualmente en la Control Room de Automation Anywhere que la ejecución se haya detenido o completado.",
                ),
                html.footer(
                    html.button(
                        {
                            "class_name": "secondary",
                            "on_click": lambda e: cancel_unlock(),
                            "style": {"margin-right": "1rem"},
                        },
                        "Cancelar",
                    ),
                    html.button(
                        {
                            "on_click": lambda e: asyncio.create_task(confirm_unlock()),
                        },
                        "Confirmar y Destrabar",
                    ),
                ),
            ),
        )
        if show_confirm_modal
        else "",
        html.header(
            {
                "class_name": "dashboard-header",
            },
            html.h2({"class_name": "dashboard-title"}, "Estado Actual del Sistema"),
        ),
        html.p(
            {
                "class_name": "dashboard-description",
            },
            "Vista en tiempo real del estado operativo de SAM. Muestra ejecuciones activas, estado de robots (online/offline/programados) y disponibilidad de equipos. Se actualiza automáticamente cada 30 segundos.",
        ),
        html.p(
            {
                "class_name": "dashboard-alert dashboard-alert-yellow",
            },
            "ℹ️ Estado operativo: Muestra ejecuciones en curso y alertas críticas recientes. Incluye datos de la tabla actual y del histórico reciente para asegurar visibilidad de fallos.",
        ),
        html.div(
            {
                "class_name": "status-cards dashboard-grid",
            },
            # Card Ejecuciones Activas
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Ejecuciones Activas")),
                html.p(
                    {"class_name": "metric-description"},
                    "Ejecuciones en curso en este momento",
                ),
                html.div(
                    {"class_name": "metric-value"},
                    ejecuciones.get("TotalActivas", 0),
                ),
                html.div({"class_name": "metric-label"}, "Ejecuciones en curso"),
                html.footer(
                    {"class_name": "metric-footer"},
                    f"{ejecuciones.get('RobotsActivos', 0)} robots activos • {ejecuciones.get('EquiposEjecutando', 0)} equipos ocupados",
                ),
            ),
            # Card Robots
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Robots")),
                html.p(
                    {"class_name": "metric-description"},
                    "Estado de robots: cíclicos y programados",
                ),
                html.div(
                    {"class_name": "metric-value"},
                    f"{robots.get('RobotsActivos', 0)} / {robots.get('TotalRobots', 0)}",
                ),
                html.div({"class_name": "metric-label"}, "Activos / Total"),
                html.div(
                    {
                        "style": {
                            "display": "grid",
                            "grid-template-columns": "1fr 1fr",
                            "gap": "0.5rem",
                            "margin-top": "0.5rem",
                            "font-size": "0.9rem",
                        }
                    },
                    html.div(
                        {"class_name": "text-green"},
                        f"🟢 {robots.get('RobotsOnline', 0)} cíclicos",
                    ),
                    html.div(
                        {"class_name": "text-blue"},
                        f"📅 {robots.get('RobotsProgramados', 0)} programados",
                    ),
                ),
            ),
            # Card Equipos
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Equipos")),
                html.p(
                    {"class_name": "metric-description"},
                    "Equipos disponibles y configuración de balanceo dinámico",
                ),
                html.div(
                    {"class_name": "metric-value"},
                    f"{equipos.get('EquiposActivos', 0)} / {equipos.get('TotalEquipos', 0)}",
                ),
                html.div({"class_name": "metric-label"}, "Activos / Total"),
                html.footer(
                    {
                        "class_name": "metric-footer",
                        "style": {"display": "flex", "flex-direction": "column", "gap": "0.2rem"},
                    },
                    html.div(f"{equipos.get('EquiposBalanceables', 0)} balanceables"),
                    html.div(
                        {
                            "style": {
                                "display": "flex",
                                "gap": "0.8rem",
                                "font-size": "0.8rem",
                                "margin-top": "0.3rem",
                                "border-top": "1px solid var(--pico-muted-border-color)",
                                "padding-top": "0.3rem",
                            }
                        },
                        html.span(f"📍 VIALE: {equipos.get('EquiposViale', 0)}"),
                        html.span(f"📍 VELEZ: {equipos.get('EquiposVelez', 0)}"),
                    ),
                ),
            ),
            # Card Programaciones
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Programaciones")),
                html.p(
                    {"class_name": "metric-description"},
                    "Programaciones activas en el sistema",
                ),
                html.div(
                    {"class_name": "metric-value"},
                    programaciones.get("ProgramacionesActivas", 0),
                ),
                html.div({"class_name": "metric-label"}, "Programaciones activas"),
            ),
        ),
        # --- TABLA DE EJECUCIONES RECIENTES (CON TABS) ---
        html.div(
            {
                "class_name": "recent-executions-section",
                "style": {"margin-top": "2rem"},
                "id": "recent-executions",
            },
            html.div(
                {
                    "style": {
                        "display": "flex",
                        "justify-content": "space-between",
                        "align-items": "center",
                        "margin-bottom": "1rem",
                    }
                },
                html.h3({"style": {"margin": "0"}}, "Estado de Ejecuciones Recientes"),
                html.div(
                    {"style": {"display": "flex", "align-items": "center", "gap": "1rem"}},
                    # Toggle Agrupado (Solo para fallos)
                    html.label(
                        {
                            "style": {
                                "cursor": "pointer",
                                "display": "flex",
                                "align-items": "center",
                                "gap": "0.5rem",
                                "margin": "0",
                                "opacity": "1" if active_tab == "fallos" else "0.5",
                                "pointer-events": "auto" if active_tab == "fallos" else "none",
                            }
                        },
                        html.input(
                            {
                                "type": "checkbox",
                                "role": "switch",
                                "checked": grouped_view,
                                "on_change": lambda e: set_grouped_view(e["target"]["checked"]),
                                "disabled": active_tab != "fallos",
                            }
                        ),
                        "Vista agrupada",
                    ),
                    # Refresh Button
                    html.button(
                        {
                            "on_click": handle_refresh,
                            "class_name": "secondary outline",
                            "title": "Actualizar",
                            "style": {"padding": "0.4rem", "border": "none"},
                        },
                        html.i({"class_name": "fa-solid fa-rotate"}),
                    ),
                ),
            ),
            # --- FILTROS ---
            html.div(
                {
                    "class_name": "filters dashboard-filters",
                    "style": {"margin-bottom": "1rem"},
                },
                html.div(
                    {
                        "style": {
                            "display": "grid",
                            "grid-template-columns": "1fr 1fr 1fr auto",
                            "gap": "1rem",
                            "align-items": "end",
                        }
                    },
                    # Filtro Robot
                    html.div(
                        html.label(
                            {"for": "filter-robot"},
                            "Robot:",
                        ),
                        html.input(
                            {
                                "id": "filter-robot",
                                "type": "text",
                                "placeholder": "Nombre del robot...",
                                "value": filter_robot,
                                "on_change": lambda e: set_filter_robot(e["target"]["value"]),
                                "on_key_down": handle_key_down,
                            }
                        ),
                    ),
                    # Filtro Equipo
                    html.div(
                        html.label(
                            {"for": "filter-equipo"},
                            "Equipo:",
                        ),
                        html.input(
                            {
                                "id": "filter-equipo",
                                "type": "text",
                                "placeholder": "Nombre del equipo...",
                                "value": filter_equipo,
                                "on_change": lambda e: set_filter_equipo(e["target"]["value"]),
                                "on_key_down": handle_key_down,
                            }
                        ),
                    ),
                    # Filtro Limit
                    html.div(
                        html.label(
                            {"for": "filter-limit"},
                            "Límite:",
                        ),
                        html.input(
                            {
                                "id": "filter-limit",
                                "type": "number",
                                "placeholder": "100",
                                "value": filter_limit,
                                "min": "1",
                                "max": "500",
                                "on_change": lambda e: set_filter_limit(e["target"]["value"]),
                                "on_key_down": handle_key_down,
                            }
                        ),
                    ),
                    # Botón Aplicar
                    html.button(
                        {
                            "on_click": handle_apply_filters,
                            "type": "button",
                            "title": "Aplicar filtros y actualizar",
                        },
                        html.i({"class_name": "fa-solid fa-filter"}),
                        " Aplicar",
                    ),
                ),
            ),
            # TABS NAVIGATION
            html.div(
                {
                    "class_name": "tabs-nav",
                    "style": {
                        "display": "flex",
                        "gap": "1rem",
                        "margin-bottom": "1rem",
                        "border-bottom": "1px solid var(--pico-muted-border-color)",
                    },
                },
                # Tab Fallos
                html.button(
                    {
                        "class_name": f"tab-button {'active' if active_tab == 'fallos' else ''}",
                        "on_click": lambda e: set_active_tab("fallos"),
                        "style": {
                            "background": "transparent",
                            "border": "none",
                            "border-bottom": "3px solid var(--pico-color-red-600)"
                            if active_tab == "fallos"
                            else "3px solid transparent",
                            "color": "var(--pico-color-red-600)"
                            if active_tab == "fallos"
                            else "var(--pico-muted-color)",
                            "font-weight": "bold",
                            "padding": "0.5rem 1rem",
                            "cursor": "pointer",
                            "display": "flex",
                            "align-items": "center",
                            "gap": "0.5rem",
                        },
                    },
                    "Fallos",
                    html.span(
                        {
                            "style": {
                                "background-color": "var(--pico-color-red-600)",
                                "color": "white",
                                "padding": "0.1rem 0.4rem",
                                "border-radius": "10px",
                                "font-size": "0.75rem",
                            }
                        },
                        str(len(fallos)),
                    )
                    if len(fallos) > 0
                    else "",
                ),
                # Tab Demoras
                html.button(
                    {
                        "class_name": f"tab-button {'active' if active_tab == 'demoras' else ''}",
                        "on_click": lambda e: set_active_tab("demoras"),
                        "style": {
                            "background": "transparent",
                            "border": "none",
                            "border-bottom": "3px solid var(--pico-color-orange-500)"
                            if active_tab == "demoras"
                            else "3px solid transparent",
                            "color": "var(--pico-color-orange-500)"
                            if active_tab == "demoras"
                            else "var(--pico-muted-color)",
                            "font-weight": "bold",
                            "padding": "0.5rem 1rem",
                            "cursor": "pointer",
                            "display": "flex",
                            "align-items": "center",
                            "gap": "0.5rem",
                        },
                    },
                    "Demoras",
                    html.span(
                        {
                            "style": {
                                "background-color": "var(--pico-color-orange-500)",
                                "color": "white",
                                "padding": "0.1rem 0.4rem",
                                "border-radius": "10px",
                                "font-size": "0.75rem",
                            }
                        },
                        str(len(demoras)),
                    )
                    if len(demoras) > 0
                    else "",
                ),
                # Tab Huérfanas
                html.button(
                    {
                        "class_name": f"tab-button {'active' if active_tab == 'huerfanas' else ''}",
                        "on_click": lambda e: set_active_tab("huerfanas"),
                        "style": {
                            "background": "transparent",
                            "border": "none",
                            "border-bottom": "3px solid var(--pico-color-yellow-500)"
                            if active_tab == "huerfanas"
                            else "3px solid transparent",
                            "color": "var(--pico-color-yellow-500)"
                            if active_tab == "huerfanas"
                            else "var(--pico-muted-color)",
                            "font-weight": "bold",
                            "padding": "0.5rem 1rem",
                            "cursor": "pointer",
                            "display": "flex",
                            "align-items": "center",
                            "gap": "0.5rem",
                        },
                    },
                    "Huérfanas",
                    html.span(
                        {
                            "style": {
                                "background-color": "var(--pico-color-yellow-500)",
                                "color": "black",
                                "padding": "0.1rem 0.4rem",
                                "border-radius": "10px",
                                "font-size": "0.75rem",
                            }
                        },
                        str(len(huerfanas)),
                    )
                    if len(huerfanas) > 0
                    else "",
                ),
            ),
            # TABLE
            html.table(
                {"class_name": "dashboard-table striped"},
                html.thead(
                    html.tr(
                        html.th("Robot"),
                        html.th("Equipo"),
                        html.th("Estado"),
                        html.th("Cant.") if active_tab == "fallos" and grouped_view else html.th("Tiempo"),
                        html.th("Prom.") if active_tab == "fallos" and grouped_view else "",
                        html.th("Fecha Inicio - Última")
                        if active_tab == "fallos" and grouped_view
                        else html.th("Fecha Inicio"),
                        html.th("Mensaje"),
                        html.th("Origen"),
                        html.th("Acción") if active_tab == "demoras" else "",
                    )
                ),
                html.tbody(
                    *[
                        html.tr(
                            html.td(item.get("Robot", "N/A")),
                            html.td(
                                html.div(
                                    {"style": {"display": "flex", "align-items": "center", "gap": "0.5rem"}},
                                    html.a(
                                        {
                                            "href": f"appurl://{item.get('Equipo', '')}",
                                            "title": f"Conectar a {item.get('Equipo', '')}",
                                            "style": {"color": "var(--pico-primary)", "text-decoration": "none"},
                                        },
                                        html.i({"class_name": "fa-solid fa-desktop"}),
                                    ),
                                    html.span(item.get("Equipo", "N/A")) if item.get("Equipo") else "",
                                )
                            ),
                            html.td(
                                html.span(
                                    {
                                        "data-tooltip": f"Umbral: {item.get('UmbralUtilizadoMinutos', 0):.1f} min ({item.get('TipoUmbral', 'Fijo')})"
                                        if item.get("TipoCritico")
                                        else None,
                                        "style": {
                                            "color": "var(--pico-color-red-600)"
                                            if (
                                                item.get("TipoCritico") == "Fallo"
                                                or (active_tab == "fallos" and grouped_view)
                                            )
                                            else "var(--pico-color-orange-500)"
                                            if item.get("TipoCritico") == "Demorada"
                                            else "var(--pico-color-yellow-500)"
                                            if item.get("TipoCritico") == "Huerfana"
                                            else "inherit",
                                            "font-weight": "bold"
                                            if (item.get("TipoCritico") or (active_tab == "fallos" and grouped_view))
                                            else "normal",
                                            "cursor": "help" if item.get("TipoCritico") else "default",
                                            "display": "flex",
                                            "align-items": "center",
                                            "gap": "0.5rem",
                                        },
                                    },
                                    html.i(
                                        {
                                            "class_name": "fa-solid fa-circle-xmark"
                                            if (
                                                item.get("TipoCritico") == "Fallo"
                                                or (active_tab == "fallos" and grouped_view)
                                            )
                                            else "fa-solid fa-clock"
                                            if item.get("TipoCritico") == "Demorada"
                                            else "fa-solid fa-triangle-exclamation"
                                            if item.get("TipoCritico") == "Huerfana"
                                            else ""
                                        }
                                    )
                                    if (item.get("TipoCritico") or (active_tab == "fallos" and grouped_view))
                                    else "",
                                    item.get("Estado", "N/A"),
                                )
                            ),
                            # Cantidad (solo agrupado)
                            html.td(
                                html.span(
                                    {
                                        "class_name": "badge",
                                        "style": {
                                            "background-color": "var(--pico-color-red-600)",
                                            "color": "white",
                                            "padding": "0.1rem 0.4rem",
                                            "border-radius": "4px",
                                        },
                                    },
                                    str(item.get("Cantidad", 1)),
                                )
                            )
                            if active_tab == "fallos" and grouped_view
                            else html.td(format_duration(item.get("TiempoTranscurridoMinutos"))),
                            # Promedio (solo agrupado)
                            *(
                                [html.td(format_duration(item.get("TiempoPromedio")))]
                                if active_tab == "fallos" and grouped_view
                                else []
                            ),
                            # Fechas
                            html.td(
                                html.div(
                                    {"style": {"font-size": "0.85rem"}},
                                    html.div(str(item.get("FechaInicio", "")).replace("T", " ")[:16]),
                                    html.div(
                                        {
                                            "style": {
                                                "color": "var(--pico-muted-color)",
                                                "border-top": "1px solid #eee",
                                                "margin-top": "2px",
                                            }
                                        },
                                        str(item.get("FechaUltima", "")).replace("T", " ")[:16],
                                    )
                                    if item.get("FechaUltima")
                                    else "",
                                )
                            )
                            if active_tab == "fallos" and grouped_view
                            else html.td(
                                str(item.get("FechaInicio", "")).replace("T", " ")[:19]
                                if item.get("FechaInicio")
                                else "N/A"
                            ),
                            html.td(
                                {
                                    "style": {
                                        "max-width": "300px",
                                        "overflow": "hidden",
                                        "text-overflow": "ellipsis",
                                        "white-space": "nowrap",
                                    }
                                },
                                item.get("MensajeError") or "-",
                            ),
                            html.td(
                                html.span(
                                    {
                                        "class_name": "badge",
                                        "style": {
                                            "background-color": "var(--pico-color-blue-600)"
                                            if item.get("Origen") == "Activa"
                                            else "var(--pico-color-grey-600)",
                                            "color": "white",
                                            "padding": "0.2rem 0.5rem",
                                            "border-radius": "4px",
                                            "font-size": "0.8rem",
                                        },
                                    },
                                    item.get("Origen", "N/A"),
                                )
                            ),
                            html.td(
                                html.button(
                                    {
                                        "class_name": "outline secondary",
                                        "style": {
                                            "padding": "0.2rem 0.5rem",
                                            "font-size": "0.75rem",
                                            "margin": "0",
                                            "border-color": "var(--pico-color-orange-500)",
                                            "color": "var(--pico-color-orange-500)",
                                        },
                                        "on_click": lambda e,
                                        d=(item.get("DeploymentId") or item.get("Id")): request_unlock_confirmation(d),
                                        "disabled": unlocking_id == (item.get("DeploymentId") or item.get("Id")),
                                    },
                                    html.i(
                                        {"class_name": "fa-solid fa-hand-sparkles", "style": {"margin-right": "5px"}}
                                    )
                                    if unlocking_id != (item.get("DeploymentId") or item.get("Id"))
                                    else html.i({"class_name": "fa-solid fa-spinner fa-spin"}),
                                    " Destrabar"
                                    if unlocking_id != (item.get("DeploymentId") or item.get("Id"))
                                    else " Procesando...",
                                )
                                if active_tab == "demoras"
                                else ""
                            ),
                        )
                        for item in current_data
                    ]
                    if current_data
                    else [
                        html.tr(
                            html.td(
                                {"colspan": 8, "style": {"text-align": "center"}},
                                "No hay items en esta categoría.",
                            )
                        )
                    ]
                ),
            ),
        ),
        html.footer(
            {
                "class_name": "last-update",
            },
            f"Última actualización: {timestamp}",
        ),
        # Script para auto-scroll si se solicita
        html.script(
            f"""
            setTimeout(function() {{
                var el = document.getElementById('{scroll_to}');
                if(el) {{
                    el.scrollIntoView({{behavior: 'smooth', block: 'start'}});
                }}
            }}, 500);
            """
        )
        if scroll_to
        else "",
    )
