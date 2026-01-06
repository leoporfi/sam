# sam/web/frontend/features/components/analytics/utilizacion_dashboard.py

import asyncio
import logging

from reactpy import component, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client
from sam.web.frontend.shared.common_components import LoadingOverlay
from sam.web.frontend.shared.formatters import format_minutes_to_hhmmss

from .chart_components import BarChart

logger = logging.getLogger(__name__)


@component
def UtilizationDashboard():
    """Dashboard de análisis de utilización de recursos."""
    dashboard_data, set_dashboard_data = use_state(None)
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)
    dias_hacia_atras, set_dias_hacia_atras = use_state(30)

    api_client = get_api_client()

    async def fetch_dashboard():
        try:
            set_loading(True)
            set_error(None)
            params = {
                "dias_hacia_atras": dias_hacia_atras,
            }

            data = await api_client.get("/api/analytics/utilizacion", params=params)
            set_dashboard_data(data)
        except Exception as e:
            set_error(str(e))
            logger.error(f"Error obteniendo dashboard de utilización: {e}")
        finally:
            set_loading(False)

    def handle_refresh(event=None):
        """Wrapper para manejar el click del botón de actualizar."""
        asyncio.create_task(fetch_dashboard())

    @use_effect(dependencies=[])
    def load_data():
        task = asyncio.create_task(fetch_dashboard())
        return lambda: task.cancel() if not task.done() else None

    if loading and not dashboard_data:
        return html.div({"class_name": "utilization-dashboard loading"}, html.p("Cargando análisis de utilización..."))

    if error:
        return html.div(
            {"class_name": "utilization-dashboard error", "style": {"color": "var(--pico-color-red-600)"}},
            html.h3("Error"),
            html.p(error),
            html.button({"on_click": handle_refresh}, "Reintentar"),
        )

    if not dashboard_data:
        return html.div({"class_name": "utilization-dashboard"}, html.p("No hay datos disponibles"))

    # Preparar datos para gráficos
    # Agrupar por Equipo o Robot? El SP devuelve pares Equipo-Robot.
    # Podríamos mostrar utilización por Equipo (sumando robots si aplica, o mostrando el max)
    # O por Robot.
    # Vamos a mostrar por Robot para empezar, concatenando Equipo si es relevante.

    labels = []
    utilization_values = []
    colors = []

    for item in dashboard_data:
        label = f"{item.get('Robot', 'N/A')} ({item.get('Equipo', 'N/A')})"
        utilization = float(item.get("PorcentajeUtilizacion", 0))

        labels.append(label[:40])  # Limitar longitud
        utilization_values.append(utilization)

        # Color basado en utilización (Rojo > 80%, Verde < 50%, Amarillo entre medio)
        if utilization > 80:
            colors.append("rgba(255, 99, 132, 0.6)")  # Rojo
        elif utilization > 50:
            colors.append("rgba(255, 205, 86, 0.6)")  # Amarillo
        else:
            colors.append("rgba(75, 192, 192, 0.6)")  # Verde

    return html.div(
        {"class_name": "utilization-dashboard", "style": {"position": "relative"}},
        LoadingOverlay(is_loading=loading),
        html.header(
            {
                "class_name": "dashboard-header",
            },
            html.h2({"class_name": "dashboard-title"}, "Análisis de Utilización de Recursos"),
            html.button(
                {
                    "on_click": handle_refresh,
                    "class_name": "secondary dashboard-refresh-btn",
                    "title": "Actualizar",
                    "aria-label": "Actualizar dashboard de utilización",
                },
                html.i({"class_name": "fa-solid fa-rotate"}),
            ),
        ),
        html.p(
            {
                "class_name": "dashboard-description",
            },
            "Analiza el porcentaje de tiempo que cada robot/equipo ha estado ocupado ejecutando tareas en el periodo seleccionado.",
        ),
        # Filtros
        html.div(
            {
                "class_name": "filters dashboard-filters",
            },
            html.div(
                html.label("Días hacia atrás:"),
                html.input(
                    {
                        "type": "number",
                        "min": "1",
                        "max": "365",
                        "value": dias_hacia_atras,
                        "on_change": lambda e: set_dias_hacia_atras(
                            int(e["target"]["value"]) if e["target"]["value"] else 30
                        ),
                    }
                ),
            ),
            html.button(
                {"on_click": handle_refresh, "type": "button"}, html.i({"class_name": "fa-solid fa-filter"}), " Aplicar"
            ),
        ),
        # Gráfico de Utilización
        html.div(
            {"class_name": "chart-container"},
            html.h3("Porcentaje de Utilización por Robot/Equipo"),
            BarChart(
                chart_id="utilization-chart",
                title="Utilización (%)",
                labels=labels if labels else ["Sin datos"],
                datasets=[
                    {
                        "label": "Utilización (%)",
                        "data": utilization_values if utilization_values else [0],
                        "backgroundColor": colors if colors else "rgba(75, 192, 192, 0.6)",
                    }
                ],
                height="400px",
            )
            if dashboard_data
            else html.p("No hay datos disponibles"),
        ),
        # Tabla de métricas detalladas
        html.div(
            {"class_name": "metrics-table"},
            html.h3("Detalle de Utilización"),
            html.table(
                {"class_name": "dashboard-table"},
                html.thead(
                    html.tr(
                        html.th("Equipo"),
                        html.th("Robot"),
                        html.th("Ejecuciones"),
                        html.th("Tiempo Ocupado (HH:MM:SS)"),
                        html.th("Tiempo Disponible (HH:MM:SS)"),
                        html.th("% Utilización"),
                    )
                ),
                html.tbody(
                    *[
                        html.tr(
                            html.td(item.get("Equipo", "N/A")),
                            html.td(item.get("Robot", "N/A")),
                            html.td(str(item.get("CantidadEjecuciones", 0))),
                            html.td(format_minutes_to_hhmmss(item.get("MinutosOcupados"))),
                            html.td(format_minutes_to_hhmmss(item.get("MinutosDisponibles"))),
                            html.td(
                                {
                                    "style": {
                                        "font-weight": "bold",
                                        "color": "var(--pico-color-red-600)"
                                        if float(item.get("PorcentajeUtilizacion", 0)) > 80
                                        else "inherit",
                                    }
                                },
                                f"{float(item.get('PorcentajeUtilizacion', 0)):.2f}%",
                            ),
                        )
                        for item in dashboard_data
                    ]
                ),
            ),
        ),
    )
