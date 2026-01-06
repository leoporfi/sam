# sam/web/frontend/features/components/analytics/tasas_exito_dashboard.py

import asyncio
import logging
from datetime import datetime, timedelta

from reactpy import component, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client
from sam.web.frontend.shared.common_components import LoadingOverlay

from .chart_components import BarChart, PieChart

logger = logging.getLogger(__name__)


@component
def TasasExitoDashboard():
    """Dashboard de análisis de tasas de éxito y errores."""
    dashboard_data, set_dashboard_data = use_state(None)
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)
    fecha_inicio, set_fecha_inicio = use_state(None)
    fecha_fin, set_fecha_fin = use_state(None)
    robot_id, set_robot_id = use_state(None)

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
            if robot_id:
                params["robot_id"] = robot_id

            data = await api_client.get("/api/analytics/tasas-exito", params=params)
            set_dashboard_data(data)
        except Exception as e:
            set_error(str(e))
            logger.error(f"Error obteniendo dashboard de tasas de éxito: {e}")
        finally:
            set_loading(False)

    def handle_refresh(event=None):
        asyncio.create_task(fetch_dashboard())

    @use_effect(dependencies=[])
    def load_data():
        task = asyncio.create_task(fetch_dashboard())
        return lambda: task.cancel() if not task.done() else None

    # Calcular fechas por defecto (últimos 30 días)
    hoy = datetime.now()
    hace_30_dias = hoy - timedelta(days=30)
    fecha_inicio_default = fecha_inicio or hace_30_dias
    fecha_fin_default = fecha_fin or hoy

    if loading and not dashboard_data:
        return html.div({"class_name": "tasas-exito-dashboard loading"}, html.p("Cargando análisis de éxito..."))

    if error:
        return html.div(
            {"class_name": "tasas-exito-dashboard error", "style": {"color": "var(--pico-color-red-600)"}},
            html.h3("Error"),
            html.p(error),
            html.button({"on_click": handle_refresh}, "Reintentar"),
        )

    # Procesar datos para gráficos
    resumen_estados = dashboard_data.get("resumen_estados", []) if dashboard_data else []
    top_errores = dashboard_data.get("top_errores", []) if dashboard_data else []
    detalle_robots = dashboard_data.get("detalle_robots", []) if dashboard_data else []

    # Pie Chart: Estados
    pie_labels = [item["Estado"] for item in resumen_estados]
    pie_values = [item["Cantidad"] for item in resumen_estados]
    # Colores: FINISHED -> Verde, ERROR -> Rojo, FINISHED_NOT_OK -> Naranja, Otros -> Gris
    pie_colors = []
    for estado in pie_labels:
        if estado == "FINISHED":
            pie_colors.append("rgba(46, 204, 113, 0.7)")
        elif estado == "ERROR":
            pie_colors.append("rgba(231, 76, 60, 0.7)")
        elif estado == "FINISHED_NOT_OK":
            pie_colors.append("rgba(243, 156, 18, 0.7)")
        else:
            pie_colors.append("rgba(149, 165, 166, 0.7)")

    # Bar Chart: Top Errores (Tipos)
    bar_labels = [item["MensajeError"] for item in top_errores]  # MensajeError es alias de Estado en SP
    bar_values = [item["Cantidad"] for item in top_errores]

    return html.div(
        {"class_name": "tasas-exito-dashboard", "style": {"position": "relative"}},
        LoadingOverlay(is_loading=loading),
        html.header(
            {"class_name": "dashboard-header"},
            html.h2({"class_name": "dashboard-title"}, "Análisis de Tasas de Éxito y Errores"),
            html.button(
                {
                    "on_click": handle_refresh,
                    "class_name": "secondary dashboard-refresh-btn",
                    "title": "Actualizar",
                },
                html.i({"class_name": "fa-solid fa-rotate"}),
            ),
        ),
        html.p(
            {"class_name": "dashboard-description"},
            "Visualiza la proporción de ejecuciones exitosas vs. fallidas y los tipos de errores más frecuentes.",
        ),
        # Filtros
        html.div(
            {"class_name": "filters dashboard-filters"},
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
            html.button(
                {"on_click": handle_refresh, "type": "button"},
                html.i({"class_name": "fa-solid fa-filter"}),
                " Aplicar",
            ),
        ),
        # Gráficos
        html.div(
            {"class_name": "grid", "style": {"grid-template-columns": "1fr 1fr", "gap": "2rem"}},
            # Pie Chart
            html.div(
                {"class_name": "chart-container"},
                html.h3("Distribución de Estados"),
                PieChart(
                    chart_id="success-pie-chart",
                    title="Estados de Ejecución",
                    labels=pie_labels if pie_labels else ["Sin datos"],
                    datasets=[
                        {
                            "data": pie_values if pie_values else [0],
                            "backgroundColor": pie_colors if pie_colors else ["#ccc"],
                        }
                    ],
                    height="300px",
                )
                if pie_labels
                else html.p("No hay datos disponibles"),
            ),
            # Bar Chart (Top Errores)
            html.div(
                {"class_name": "chart-container"},
                html.h3("Top Tipos de Fallo"),
                BarChart(
                    chart_id="errors-bar-chart",
                    title="Cantidad",
                    labels=bar_labels if bar_labels else ["Sin datos"],
                    datasets=[
                        {
                            "label": "Cantidad",
                            "data": bar_values if bar_values else [0],
                            "backgroundColor": "rgba(231, 76, 60, 0.6)",
                        }
                    ],
                    height="300px",
                )
                if bar_labels
                else html.p("No hay errores registrados"),
            ),
        ),
        # Tabla Detalle por Robot
        html.div(
            {"class_name": "metrics-table", "style": {"margin-top": "2rem"}},
            html.h3("Detalle por Robot"),
            html.table(
                {"class_name": "dashboard-table"},
                html.thead(
                    html.tr(
                        html.th("Robot"),
                        html.th("Equipo"),
                        html.th("Total"),
                        html.th("Exitos"),
                        html.th("Errores"),
                        html.th("Tasa de Éxito"),
                    )
                ),
                html.tbody(
                    *[
                        html.tr(
                            html.td(item.get("Robot", "N/A")),
                            html.td(item.get("Equipo", "N/A")),
                            html.td(str(item.get("Total", 0))),
                            html.td(str(item.get("Exitos", 0))),
                            html.td(str(item.get("Errores", 0))),
                            html.td(
                                {
                                    "style": {
                                        "font-weight": "bold",
                                        "color": "var(--pico-color-green-600)"
                                        if float(item.get("TasaExito", 0)) > 90
                                        else "var(--pico-color-red-600)"
                                        if float(item.get("TasaExito", 0)) < 80
                                        else "var(--pico-color-orange-500)",
                                    }
                                },
                                f"{float(item.get('TasaExito', 0)):.2f}%",
                            ),
                        )
                        for item in detalle_robots
                    ]
                ),
            ),
        ),
    )
