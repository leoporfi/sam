# sam/web/frontend/features/components/analytics/status_dashboard.py

import asyncio
import logging

from reactpy import component, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client

logger = logging.getLogger(__name__)


@component
def StatusDashboard():
    """Dashboard de estado actual del sistema."""
    status_data, set_status_data = use_state(None)
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)

    api_client = get_api_client()

    async def fetch_status():
        try:
            set_loading(True)
            set_error(None)
            data = await api_client.get("/api/analytics/status")
            set_status_data(data)
        except Exception as e:
            set_error(str(e))
            logger.error(f"Error obteniendo estado: {e}")
        finally:
            set_loading(False)

    @use_effect(dependencies=[])
    def load_data():
        # Crear tarea asíncrona para cargar datos
        task = asyncio.create_task(fetch_status())
        return lambda: task.cancel() if not task.done() else None

    if loading and not status_data:
        return html.div({"class_name": "status-dashboard loading"}, html.p("Cargando estado del sistema..."))

    if error:
        return html.div(
            {"class_name": "status-dashboard error", "style": {"color": "var(--pico-color-red-600)"}},
            html.h3("Error"),
            html.p(error),
            html.button({"on_click": lambda e: fetch_status()}, "Reintentar"),
        )

    if not status_data:
        return html.div({"class_name": "status-dashboard"}, html.p("No hay datos disponibles"))

    ejecuciones = status_data.get("ejecuciones", {})
    robots = status_data.get("robots", {})
    equipos = status_data.get("equipos", {})
    timestamp = status_data.get("timestamp", "N/A")

    return html.div(
        {"class_name": "status-dashboard"},
        html.header(
            html.h2("Estado Actual del Sistema"),
            html.button(
                {"on_click": lambda e: fetch_status(), "class_name": "secondary", "style": {"margin-left": "auto"}},
                "🔄 Actualizar",
            ),
        ),
        html.div(
            {
                "class_name": "status-cards",
                "style": {
                    "display": "grid",
                    "grid-template-columns": "repeat(auto-fit, minmax(250px, 1fr))",
                    "gap": "1rem",
                    "margin-top": "1rem",
                },
            },
            # Card Ejecuciones
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Ejecuciones Activas")),
                html.div(
                    {"class_name": "metric-value", "style": {"font-size": "2rem", "font-weight": "bold"}},
                    ejecuciones.get("TotalActivas", 0),
                ),
                html.div({"class_name": "metric-label"}, f"{ejecuciones.get('RobotsActivos', 0)} robots activos"),
                html.footer(
                    {"style": {"font-size": "0.8rem", "color": "var(--pico-muted-color)"}},
                    f"{ejecuciones.get('EquiposOcupados', 0)} equipos ocupados",
                ),
            ),
            # Card Robots
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Robots")),
                html.div(
                    {"class_name": "metric-value", "style": {"font-size": "2rem", "font-weight": "bold"}},
                    f"{robots.get('RobotsOnline', 0)} / {robots.get('TotalRobots', 0)}",
                ),
                html.div({"class_name": "metric-label"}, "Online / Total"),
                html.footer(
                    {"style": {"font-size": "0.8rem", "color": "var(--pico-muted-color)"}},
                    f"{robots.get('RobotsActivos', 0)} activos",
                ),
            ),
            # Card Equipos
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Equipos")),
                html.div(
                    {"class_name": "metric-value", "style": {"font-size": "2rem", "font-weight": "bold"}},
                    f"{equipos.get('EquiposActivos', 0)} / {equipos.get('TotalEquipos', 0)}",
                ),
                html.div({"class_name": "metric-label"}, "Activos / Total"),
                html.footer(
                    {"style": {"font-size": "0.8rem", "color": "var(--pico-muted-color)"}},
                    f"{equipos.get('EquiposBalanceables', 0)} balanceables",
                ),
            ),
        ),
        html.footer(
            {
                "class_name": "last-update",
                "style": {
                    "margin-top": "1rem",
                    "font-size": "0.9rem",
                    "color": "var(--pico-muted-color)",
                    "text-align": "center",
                },
            },
            f"Última actualización: {timestamp}",
        ),
    )
