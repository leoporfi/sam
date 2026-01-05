# sam/web/frontend/features/components/analytics/balanceador_dashboard.py

import asyncio
import logging
from datetime import datetime, timedelta

from reactpy import component, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client

from .chart_components import BarChart

logger = logging.getLogger(__name__)


@component
def BalanceadorDashboard():
    """Dashboard de análisis del balanceador."""
    dashboard_data, set_dashboard_data = use_state(None)
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)
    fecha_inicio, set_fecha_inicio = use_state(None)
    fecha_fin, set_fecha_fin = use_state(None)

    api_client = get_api_client()

    async def fetch_dashboard():
        try:
            set_loading(True)
            set_error(None)
            params = {}
            if fecha_inicio:
                params["fecha_inicio"] = fecha_inicio.isoformat()
            if fecha_fin:
                params["fecha_fin"] = fecha_fin.isoformat()

            data = await api_client.get("/api/analytics/balanceador", params=params)
            set_dashboard_data(data)
        except Exception as e:
            set_error(str(e))
            logger.error(f"Error obteniendo dashboard de balanceador: {e}")
        finally:
            set_loading(False)

    def handle_refresh(event=None):
        """Wrapper para manejar el click del botón de actualizar."""
        asyncio.create_task(fetch_dashboard())

    @use_effect(dependencies=[fecha_inicio, fecha_fin])
    def load_data():
        task = asyncio.create_task(fetch_dashboard())
        return lambda: task.cancel() if not task.done() else None

    if loading and not dashboard_data:
        return html.div({"class_name": "balanceador-dashboard loading"}, html.p("Cargando dashboard..."))

    if error:
        return html.div(
            {"class_name": "balanceador-dashboard error", "style": {"color": "var(--pico-color-red-600)"}},
            html.h3("Error"),
            html.p(error),
            html.button({"on_click": handle_refresh}, "Reintentar"),
        )

    if not dashboard_data:
        return html.div({"class_name": "balanceador-dashboard"}, html.p("No hay datos disponibles"))

    metricas = dashboard_data.get("metricas_generales", {})
    resumen_diario = dashboard_data.get("resumen_diario", [])
    analisis_robots = dashboard_data.get("analisis_robots", [])
    estado_actual = dashboard_data.get("estado_actual", {})

    # Preparar datos para gráfico de resumen diario
    resumen_labels = []
    resumen_asignaciones = []
    resumen_desasignaciones = []

    if resumen_diario:
        for item in resumen_diario:
            fecha_str = item.get("Fecha", "")
            if fecha_str:
                try:
                    fecha_obj = datetime.fromisoformat(fecha_str) if isinstance(fecha_str, str) else fecha_str
                    resumen_labels.append(
                        fecha_obj.strftime("%d/%m") if hasattr(fecha_obj, "strftime") else str(fecha_str)[:10]
                    )
                except (ValueError, AttributeError):
                    resumen_labels.append(str(fecha_str)[:10])
            else:
                resumen_labels.append("N/A")

            resumen_asignaciones.append(item.get("Asignaciones", 0))
            resumen_desasignaciones.append(item.get("Desasignaciones", 0))

    # Preparar datos para gráfico de análisis por robot (top 10)
    robots_labels = []
    robots_acciones = []

    if analisis_robots:
        top_robots = sorted(analisis_robots, key=lambda x: x.get("TotalAcciones", 0), reverse=True)[:10]
        for robot in top_robots:
            robots_labels.append(robot.get("RobotNombre", "N/A")[:20])  # Limitar longitud
            robots_acciones.append(robot.get("TotalAcciones", 0))

    # Calcular fechas por defecto (últimos 30 días)
    hoy = datetime.now()
    hace_30_dias = hoy - timedelta(days=30)
    fecha_inicio_default = fecha_inicio or hace_30_dias
    fecha_fin_default = fecha_fin or hoy

    return html.div(
        {"class_name": "balanceador-dashboard"},
        html.header(
            html.h2("Dashboard de Balanceador"),
            html.button(
                {"on_click": handle_refresh, "class_name": "secondary", "style": {"margin-left": "auto"}},
                "🔄 Actualizar",
            ),
        ),
        # Filtros de fecha
        html.div(
            {
                "class_name": "filters",
                "style": {
                    "display": "grid",
                    "grid-template-columns": "1fr 1fr auto",
                    "gap": "1rem",
                    "margin": "1rem 0",
                    "align-items": "end",
                },
            },
            html.div(
                html.label("Fecha Inicio:"),
                html.input(
                    {
                        "type": "datetime-local",
                        "value": fecha_inicio_default.strftime("%Y-%m-%dT%H:%M") if fecha_inicio_default else "",
                        "on_change": lambda e: set_fecha_inicio(
                            datetime.fromisoformat(e["target"]["value"].replace("T", " "))
                            if e["target"]["value"]
                            else None
                        ),
                    }
                ),
            ),
            html.div(
                html.label("Fecha Fin:"),
                html.input(
                    {
                        "type": "datetime-local",
                        "value": fecha_fin_default.strftime("%Y-%m-%dT%H:%M") if fecha_fin_default else "",
                        "on_change": lambda e: set_fecha_fin(
                            datetime.fromisoformat(e["target"]["value"].replace("T", " "))
                            if e["target"]["value"]
                            else None
                        ),
                    }
                ),
            ),
            html.button({"on_click": handle_refresh, "type": "button"}, "Aplicar Filtros"),
        ),
        # Métricas principales
        html.div(
            {
                "class_name": "metrics-grid",
                "style": {
                    "display": "grid",
                    "grid-template-columns": "repeat(auto-fit, minmax(250px, 1fr))",
                    "gap": "1rem",
                    "margin-top": "1rem",
                },
            },
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Total Acciones")),
                html.div(
                    {"class_name": "metric-value", "style": {"font-size": "2rem", "font-weight": "bold"}},
                    metricas.get("TotalAcciones", 0),
                ),
                html.div(
                    {"class_name": "metric-label"},
                    f"{metricas.get('AsignacionesReales', 0)} asignaciones / {metricas.get('DesasignacionesReales', 0)} desasignaciones",
                ),
            ),
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Robots Afectados")),
                html.div(
                    {"class_name": "metric-value", "style": {"font-size": "2rem", "font-weight": "bold"}},
                    metricas.get("RobotsAfectados", 0),
                ),
                html.div(
                    {"class_name": "metric-label"},
                    f"Promedio tickets: {metricas.get('PromedioTicketsPendientes', 0):.1f}",
                ),
            ),
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Movimiento Neto")),
                html.div(
                    {"class_name": "metric-value", "style": {"font-size": "2rem", "font-weight": "bold"}},
                    f"{metricas.get('PromedioMovimientoNeto', 0):.1f}",
                ),
                html.div(
                    {"class_name": "metric-label"},
                    "Promedio de cambio de equipos",
                ),
            ),
        ),
        # Estado actual
        html.div(
            {"class_name": "estado-actual", "style": {"margin-top": "2rem"}},
            html.h3("Estado Actual del Sistema"),
            html.div(
                {
                    "style": {
                        "display": "grid",
                        "grid-template-columns": "repeat(auto-fit, minmax(200px, 1fr))",
                        "gap": "1rem",
                    }
                },
                html.article(
                    {"class_name": "card"},
                    html.header(html.h4("Robots Activos")),
                    html.div(
                        {"style": {"font-size": "1.5rem", "font-weight": "bold"}}, estado_actual.get("RobotsActivos", 0)
                    ),
                ),
                html.article(
                    {"class_name": "card"},
                    html.header(html.h4("Robots Online")),
                    html.div(
                        {"style": {"font-size": "1.5rem", "font-weight": "bold"}}, estado_actual.get("RobotsOnline", 0)
                    ),
                ),
                html.article(
                    {"class_name": "card"},
                    html.header(html.h4("Equipos Activos")),
                    html.div(
                        {"style": {"font-size": "1.5rem", "font-weight": "bold"}},
                        estado_actual.get("EquiposActivos", 0),
                    ),
                ),
                html.article(
                    {"class_name": "card"},
                    html.header(html.h4("Ejecuciones Activas")),
                    html.div(
                        {"style": {"font-size": "1.5rem", "font-weight": "bold"}},
                        estado_actual.get("EjecucionesActivas", 0),
                    ),
                ),
            ),
        ),
        # Gráfico de resumen diario
        html.div(
            {"class_name": "chart-container", "style": {"margin-top": "2rem"}},
            html.h3("Resumen Diario de Acciones"),
            BarChart(
                chart_id="balanceador-resumen-chart",
                title="Asignaciones vs Desasignaciones por Día",
                labels=resumen_labels if resumen_labels else ["Sin datos"],
                datasets=[
                    {
                        "label": "Asignaciones",
                        "data": resumen_asignaciones if resumen_asignaciones else [0],
                        "backgroundColor": "rgba(75, 192, 192, 0.6)",
                    },
                    {
                        "label": "Desasignaciones",
                        "data": resumen_desasignaciones if resumen_desasignaciones else [0],
                        "backgroundColor": "rgba(255, 99, 132, 0.6)",
                    },
                ],
                height="300px",
            )
            if resumen_diario
            else html.p("No hay datos de resumen diario disponibles"),
        ),
        # Gráfico de análisis por robot
        html.div(
            {"class_name": "chart-container", "style": {"margin-top": "2rem"}},
            html.h3("Top 10 Robots por Actividad"),
            BarChart(
                chart_id="balanceador-robots-chart",
                title="Total de Acciones por Robot",
                labels=robots_labels if robots_labels else ["Sin datos"],
                datasets=[
                    {
                        "label": "Total Acciones",
                        "data": robots_acciones if robots_acciones else [0],
                        "backgroundColor": "rgba(54, 162, 235, 0.6)",
                    }
                ],
                height="300px",
            )
            if analisis_robots
            else html.p("No hay datos de análisis por robot disponibles"),
        ),
        # Tabla de análisis por robot
        html.div(
            {"class_name": "analisis-robots", "style": {"margin-top": "2rem"}},
            html.h3("Análisis por Robot"),
            html.table(
                {"role": "table"},
                html.thead(
                    html.tr(
                        html.th("Robot"),
                        html.th("Total Acciones"),
                        html.th("Asignaciones"),
                        html.th("Desasignaciones"),
                        html.th("Promedio Equipos"),
                        html.th("Promedio Tickets"),
                    )
                ),
                html.tbody(
                    *[
                        html.tr(
                            html.td(robot.get("RobotNombre", "")),
                            html.td(robot.get("TotalAcciones", 0)),
                            html.td(robot.get("Asignaciones", 0)),
                            html.td(robot.get("Desasignaciones", 0)),
                            html.td(f"{robot.get('PromedioEquiposDespues', 0):.1f}"),
                            html.td(f"{robot.get('PromedioTickets', 0):.1f}"),
                        )
                        for robot in analisis_robots[:10]
                    ]
                    if analisis_robots
                    else [html.tr(html.td({"colspan": 6}, "No hay datos disponibles"))]
                ),
            ),
        ),
    )
