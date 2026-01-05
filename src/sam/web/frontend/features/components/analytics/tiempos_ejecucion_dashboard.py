# sam/web/frontend/features/components/analytics/tiempos_ejecucion_dashboard.py

import asyncio
import logging

from reactpy import component, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client

from .chart_components import BarChart

logger = logging.getLogger(__name__)


@component
def TiemposEjecucionDashboard():
    """Dashboard de análisis de tiempos de ejecución por robot."""
    dashboard_data, set_dashboard_data = use_state(None)
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)
    meses_hacia_atras, set_meses_hacia_atras = use_state(1)
    incluir_solo_completadas, set_incluir_solo_completadas = use_state(True)

    api_client = get_api_client()

    async def fetch_dashboard():
        try:
            set_loading(True)
            set_error(None)
            params = {
                "meses_hacia_atras": meses_hacia_atras,
                "incluir_solo_completadas": incluir_solo_completadas,
            }

            data = await api_client.get("/api/analytics/tiempos-ejecucion", params=params)
            set_dashboard_data(data)
        except Exception as e:
            set_error(str(e))
            logger.error(f"Error obteniendo dashboard de tiempos de ejecución: {e}")
        finally:
            set_loading(False)

    def handle_refresh(event=None):
        """Wrapper para manejar el click del botón de actualizar."""
        asyncio.create_task(fetch_dashboard())

    @use_effect(dependencies=[meses_hacia_atras, incluir_solo_completadas])
    def load_data():
        task = asyncio.create_task(fetch_dashboard())
        return lambda: task.cancel() if not task.done() else None

    if loading and not dashboard_data:
        return html.div(
            {"class_name": "tiempos-ejecucion-dashboard loading"}, html.p("Cargando análisis de tiempos...")
        )

    if error:
        return html.div(
            {"class_name": "tiempos-ejecucion-dashboard error", "style": {"color": "var(--pico-color-red-600)"}},
            html.h3("Error"),
            html.p(error),
            html.button({"on_click": handle_refresh}, "Reintentar"),
        )

    if not dashboard_data:
        return html.div({"class_name": "tiempos-ejecucion-dashboard"}, html.p("No hay datos disponibles"))

    # Preparar datos para gráficos
    robots_labels = []
    tiempos_por_repeticion = []
    tiempos_totales = []
    repeticiones_promedio = []
    latencias = []

    for item in dashboard_data:
        robots_labels.append(item.get("RobotNombre", "N/A")[:30])  # Limitar longitud
        tiempos_por_repeticion.append(item.get("TiempoPromedioPorRepeticionMinutos", 0))
        tiempos_totales.append(item.get("TiempoPromedioTotalMinutos", 0))
        repeticiones_promedio.append(item.get("PromedioRepeticiones", 1))
        latencias.append(item.get("LatenciaPromedioMinutos", 0) if item.get("LatenciaPromedioMinutos") else 0)

    return html.div(
        {"class_name": "tiempos-ejecucion-dashboard"},
        html.header(
            {
                "style": {
                    "display": "flex",
                    "align-items": "baseline",
                    "gap": "0.75rem",
                    "flex-wrap": "wrap",
                }
            },
            html.h2({"style": {"margin": "0", "flex": "1"}}, "Análisis de Tiempos de Ejecución"),
            html.button(
                {
                    "on_click": handle_refresh,
                    "class_name": "secondary",
                    "style": {
                        "padding": "0.375rem 0.5rem",
                        "min-width": "auto",
                        "font-size": "0.9rem",
                        "line-height": "1",
                        "display": "flex",
                        "align-items": "center",
                        "justify-content": "center",
                    },
                    "title": "Actualizar",
                    "aria-label": "Actualizar dashboard de tiempos de ejecución",
                },
                html.i({"class_name": "fa-solid fa-rotate"}),
            ),
        ),
        html.p(
            {
                "style": {
                    "color": "var(--pico-muted-color)",
                    "margin-bottom": "1rem",
                    "font-size": "0.95rem",
                }
            },
            "Analiza los tiempos de ejecución de robots considerando el número de repeticiones. Muestra tiempo por repetición (tiempo total dividido por número de repeticiones), latencia de inicio (delay entre disparo e inicio real), y métricas estadísticas excluyendo extremos.",
        ),
        html.p(
            {
                "style": {
                    "color": "var(--pico-color-blue-600)",
                    "margin-bottom": "1rem",
                    "font-size": "0.85rem",
                    "padding": "0.5rem",
                    "background-color": "var(--pico-color-blue-50)",
                    "border-left": "3px solid var(--pico-color-blue-500)",
                    "border-radius": "4px",
                }
            },
            "ℹ️ Métricas importantes: El tiempo por repetición es el tiempo real de procesamiento de un ticket. La latencia muestra el delay entre que SAM dispara el robot y A360 realmente lo inicia. Los datos incluyen ejecuciones actuales e históricas.",
        ),
        # Filtros
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
                html.label("Meses hacia atrás:"),
                html.input(
                    {
                        "type": "number",
                        "min": "1",
                        "max": "12",
                        "value": meses_hacia_atras,
                        "on_change": lambda e: set_meses_hacia_atras(
                            int(e["target"]["value"]) if e["target"]["value"] else 1
                        ),
                    }
                ),
            ),
            html.div(
                html.label(
                    html.input(
                        {
                            "type": "checkbox",
                            "checked": incluir_solo_completadas,
                            "on_change": lambda e: set_incluir_solo_completadas(e["target"]["checked"]),
                            "style": {"margin-right": "0.5rem"},
                        }
                    ),
                    "Solo ejecuciones completadas",
                )
            ),
            html.button(
                {"on_click": handle_refresh, "type": "button"}, html.i({"class_name": "fa-solid fa-filter"}), " Aplicar"
            ),
        ),
        # Gráfico de tiempo por repetición
        html.div(
            {"class_name": "chart-container", "style": {"margin-top": "2rem"}},
            html.h3("Tiempo Promedio por Repetición por Robot"),
            BarChart(
                chart_id="tiempos-repeticion-chart",
                title="Tiempo Promedio por Repetición (minutos)",
                labels=robots_labels if robots_labels else ["Sin datos"],
                datasets=[
                    {
                        "label": "Tiempo por Repetición (min)",
                        "data": tiempos_por_repeticion if tiempos_por_repeticion else [0],
                        "backgroundColor": "rgba(75, 192, 192, 0.6)",
                    }
                ],
                height="400px",
            )
            if dashboard_data
            else html.p("No hay datos disponibles"),
        ),
        # Gráfico de latencia
        html.div(
            {"class_name": "chart-container", "style": {"margin-top": "2rem"}},
            html.h3("Latencia Promedio de Inicio por Robot"),
            html.p(
                {"style": {"font-size": "0.85rem", "color": "var(--pico-muted-color)", "margin-bottom": "0.5rem"}},
                "Delay entre que SAM dispara el robot y A360 realmente lo inicia (actualizado por Conciliador)",
            ),
            BarChart(
                chart_id="latencia-chart",
                title="Latencia Promedio (minutos)",
                labels=robots_labels if robots_labels else ["Sin datos"],
                datasets=[
                    {
                        "label": "Latencia (min)",
                        "data": latencias if latencias else [0],
                        "backgroundColor": "rgba(255, 99, 132, 0.6)",
                    }
                ],
                height="300px",
            )
            if dashboard_data and any(lat > 0 for lat in latencias)
            else html.p("No hay datos de latencia disponibles (FechaInicioReal no actualizado por Conciliador)"),
        ),
        # Tabla de métricas detalladas
        html.div(
            {"class_name": "metrics-table", "style": {"margin-top": "2rem"}},
            html.h3("Métricas Detalladas por Robot"),
            html.table(
                {"style": {"width": "100%", "font-size": "0.9rem"}},
                html.thead(
                    html.tr(
                        html.th("Robot"),
                        html.th("Ejecuciones"),
                        html.th("Tiempo/Rep (min)"),
                        html.th("Tiempo Total (min)"),
                        html.th("Repeticiones"),
                        html.th("Latencia (min)"),
                        html.th("Desv. Est. (seg)"),
                    )
                ),
                html.tbody(
                    *[
                        html.tr(
                            html.td(item.get("RobotNombre", "N/A")),
                            html.td(str(item.get("EjecucionesAnalizadas", 0))),
                            html.td(f"{item.get('TiempoPromedioPorRepeticionMinutos', 0):.2f}"),
                            html.td(f"{item.get('TiempoPromedioTotalMinutos', 0):.2f}"),
                            html.td(f"{item.get('PromedioRepeticiones', 1):.1f}"),
                            html.td(
                                f"{item.get('LatenciaPromedioMinutos', 0):.2f}"
                                if item.get("LatenciaPromedioMinutos")
                                else "N/A"
                            ),
                            html.td(f"{item.get('DesviacionEstandarSegundos', 0):.1f}"),
                        )
                        for item in dashboard_data[:20]  # Top 20
                    ]
                ),
            ),
        ),
    )
