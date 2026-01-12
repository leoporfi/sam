# sam/web/frontend/features/components/analytics/status_dashboard.py

import asyncio
import logging

from reactpy import component, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client

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
    critical_only, set_critical_only = use_state(True)

    api_client = get_api_client()

    async def fetch_status():
        try:
            set_loading(True)
            set_error(None)

            # 1. Fetch System Status
            data = await api_client.get("/api/analytics/status")
            set_status_data(data)

            # 2. Fetch Recent Executions
            # Pasamos el filtro critical_only
            exec_params = {"limit": 50, "critical_only": critical_only}
            exec_data = await api_client.get("/api/analytics/executions", params=exec_params)
            set_executions_data(exec_data)

        except Exception as e:
            set_error(str(e))
            logger.error(f"Error obteniendo estado: {e}")
        finally:
            set_loading(False)

    def handle_refresh(event=None):
        """Wrapper para manejar el click del botón de actualizar."""
        asyncio.create_task(fetch_status())

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
    @use_effect(dependencies=[critical_only])
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
        return html.div({"class_name": "status-dashboard loading"}, html.p("Cargando estado del sistema..."))

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

    return html.div(
        {"class_name": "status-dashboard"},
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
                    # Toggle Switch
                    html.label(
                        {
                            "style": {
                                "cursor": "pointer",
                                "display": "flex",
                                "align-items": "center",
                                "gap": "0.5rem",
                                "margin": "0",
                            }
                        },
                        html.input(
                            {
                                "type": "checkbox",
                                "role": "switch",
                                "checked": critical_only,
                                "on_change": lambda e: set_critical_only(e["target"]["checked"]),
                            }
                        ),
                        "Mostrar solo críticos",
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
                        html.th("Tiempo"),
                        html.th("Fecha Inicio"),
                        html.th("Mensaje"),
                        html.th("Origen"),
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
                                            if item.get("TipoCritico") == "Fallo"
                                            else "var(--pico-color-orange-500)"
                                            if item.get("TipoCritico") == "Demorada"
                                            else "var(--pico-color-yellow-500)"
                                            if item.get("TipoCritico") == "Huerfana"
                                            else "inherit",
                                            "font-weight": "bold" if item.get("TipoCritico") else "normal",
                                            "cursor": "help" if item.get("TipoCritico") else "default",
                                            "display": "flex",
                                            "align-items": "center",
                                            "gap": "0.5rem",
                                        },
                                    },
                                    html.i(
                                        {
                                            "class_name": "fa-solid fa-circle-xmark"
                                            if item.get("TipoCritico") == "Fallo"
                                            else "fa-solid fa-clock"
                                            if item.get("TipoCritico") == "Demorada"
                                            else "fa-solid fa-triangle-exclamation"
                                            if item.get("TipoCritico") == "Huerfana"
                                            else ""
                                        }
                                    )
                                    if item.get("TipoCritico")
                                    else "",
                                    item.get("Estado", "N/A"),
                                )
                            ),
                            html.td(format_duration(item.get("TiempoTranscurridoMinutos"))),
                            html.td(
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
                        )
                        for item in current_data
                    ]
                    if current_data
                    else [
                        html.tr(
                            html.td(
                                {"colspan": 7, "style": {"text-align": "center"}},
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
