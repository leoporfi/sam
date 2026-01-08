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
    executions_data, set_executions_data = use_state([])
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)

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

    return html.div(
        {"class_name": "status-dashboard"},
        html.header(
            {
                "class_name": "dashboard-header",
            },
            html.h2({"class_name": "dashboard-title"}, "Estado Actual del Sistema"),
            html.div(
                {"class_name": "header-actions", "style": {"display": "flex", "gap": "1rem", "align-items": "center"}},
                # Toggle Switch
                html.label(
                    {"style": {"cursor": "pointer", "display": "flex", "align-items": "center", "gap": "0.5rem"}},
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
                html.button(
                    {
                        "on_click": handle_refresh,
                        "class_name": "secondary dashboard-refresh-btn",
                        "title": "Actualizar",
                        "aria-label": "Actualizar estado del sistema",
                    },
                    html.i({"class_name": "fa-solid fa-rotate"}),
                ),
            ),
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
            "ℹ️ Datos en tiempo real: Solo muestra ejecuciones activas de la tabla actual. Los datos históricos no se incluyen en este dashboard.",
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
                    {"class_name": "metric-footer"},
                    f"{equipos.get('EquiposBalanceables', 0)} balanceables",
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
        # --- TABLA DE EJECUCIONES RECIENTES ---
        html.div(
            {
                "class_name": "recent-executions-section",
                "style": {"margin-top": "2rem"},
                "id": "recent-executions",  # ID para anclaje
            },
            html.h3("Estado de Ejecuciones Recientes"),
            html.table(
                {"class_name": "dashboard-table striped"},
                html.thead(
                    html.tr(
                        html.th("Robot"),
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
                                html.span(
                                    {
                                        "data-tooltip": f"Umbral: {item.get('UmbralUtilizadoMinutos', 0):.1f} min ({item.get('TipoUmbral', 'Fijo')})"
                                        if item.get("TipoCritico")
                                        else None,
                                        "style": {
                                            "color": "var(--pico-color-red-500)"
                                            if item.get("TipoCritico") == "Fallo"
                                            else "var(--pico-color-yellow-500)"
                                            if item.get("TipoCritico") in ["Demorada", "Huerfana"]
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
                            html.td(
                                f"{item.get('TiempoTranscurridoMinutos', 0)} min"
                                if item.get("TiempoTranscurridoMinutos") is not None
                                else "-"
                            ),
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
                        for item in executions_data
                    ]
                    if executions_data
                    else [
                        html.tr(
                            html.td(
                                {"colspan": 6, "style": {"text-align": "center"}},
                                "No hay ejecuciones recientes para mostrar.",
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
