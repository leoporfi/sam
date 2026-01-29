# sam/web/frontend/features/components/analytics/tiempos_ejecucion_dashboard.py


import asyncio
import logging

from reactpy import component, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client
from sam.web.frontend.shared.async_content import SkeletonTable
from sam.web.frontend.shared.common_components import LoadingOverlay
from sam.web.frontend.shared.formatters import format_minutes_to_hhmmss

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
    # Estado para Top N
    top_n, set_top_n = use_state(20)
    # Estado para Ordenamiento
    sort_by, set_sort_by = use_state("tiempo_desc")  # tiempo_desc, latencia_desc

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
            set_loading(False)
        except asyncio.CancelledError:
            # Silenciar errores de cancelación y NO actualizar estado
            pass
        except Exception as e:
            set_error(str(e))
            logger.error(f"Error obteniendo dashboard de tiempos de ejecución: {e}")
            set_loading(False)

    def handle_refresh(event=None):
        """Wrapper para manejar el click del botón de actualizar."""
        asyncio.create_task(fetch_dashboard())

    @use_effect(dependencies=[])
    def load_data():
        task = asyncio.create_task(fetch_dashboard())
        return lambda: task.cancel() if not task.done() else None

    if loading and not dashboard_data:
        return html.div(
            {"class_name": "tiempos-ejecucion-dashboard"},
            html.header(
                {"class_name": "dashboard-header"},
                html.h2({"class_name": "dashboard-title"}, "Análisis de Tiempos de Ejecución"),
            ),
            SkeletonTable(rows=10, cols=7),
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

    # Ordenar datos según criterio
    if sort_by == "tiempo_desc":
        dashboard_data.sort(key=lambda x: float(x.get("TiempoPromedioPorRepeticionMinutos", 0) or 0), reverse=True)
    elif sort_by == "latencia_desc":
        dashboard_data.sort(key=lambda x: float(x.get("LatenciaPromedioMinutos", 0) or 0), reverse=True)

    # Aplicar Top N a los datos
    filtered_data = dashboard_data[:top_n]

    # Preparar datos para gráficos
    robots_labels = []
    tiempos_por_repeticion = []
    tiempos_totales = []
    repeticiones_promedio = []
    latencias = []

    for item in filtered_data:
        robots_labels.append(item.get("RobotNombre", "N/A")[:30])  # Limitar longitud
        tiempos_por_repeticion.append(item.get("TiempoPromedioPorRepeticionMinutos", 0))
        tiempos_totales.append(item.get("TiempoPromedioTotalMinutos", 0))
        repeticiones_promedio.append(item.get("PromedioRepeticiones", 1))
        latencias.append(item.get("LatenciaPromedioMinutos", 0) if item.get("LatenciaPromedioMinutos") else 0)

    return html.div(
        {"class_name": "tiempos-ejecucion-dashboard", "style": {"position": "relative"}},
        LoadingOverlay(is_loading=loading),
        html.header(
            {
                "class_name": "dashboard-header",
            },
            html.h2({"class_name": "dashboard-title"}, "Análisis de Tiempos de Ejecución"),
            html.button(
                {
                    "on_click": handle_refresh,
                    "class_name": "secondary dashboard-refresh-btn",
                    "title": "Actualizar",
                    "aria-label": "Actualizar dashboard de tiempos de ejecución",
                },
                html.i({"class_name": "fa-solid fa-rotate"}),
            ),
        ),
        html.p(
            {
                "class_name": "dashboard-description",
            },
            "Analiza los tiempos de ejecución de robots considerando el número de repeticiones. Muestra tiempo por repetición (tiempo total dividido por número de repeticiones), latencia de inicio (delay entre disparo e inicio real), y métricas estadísticas excluyendo extremos.",
        ),
        html.p(
            {
                "class_name": "dashboard-alert dashboard-alert-yellow",
            },
            "ℹ️ Métricas importantes: El tiempo por repetición es el tiempo real de procesamiento de un ticket. La latencia muestra el delay entre que SAM dispara el robot y A360 realmente lo inicia. Los datos incluyen ejecuciones actuales e históricas. NOTA: Para mayor precisión, se excluyen los outliers (15% más rápidos y 15% más lentos). Si no se detectan repeticiones en los parámetros, se usa el valor por defecto configurado (LANZADOR_REPETICIONES_ROBOT).",
        ),
        # Filtros
        html.div(
            {
                "class_name": "filters dashboard-filters",
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
                html.label("Ordenar por:"),
                html.select(
                    {
                        "value": sort_by,
                        "on_change": lambda e: set_sort_by(e["target"]["value"]),
                    },
                    html.option({"value": "tiempo_desc"}, "Tiempo por Repetición (Más Lento)"),
                    html.option({"value": "latencia_desc"}, "Latencia de Inicio (Mayor)"),
                ),
            ),
            html.div(
                html.label("Top N:"),
                html.input(
                    {
                        "type": "number",
                        "min": "1",
                        "max": "100",
                        "value": top_n,
                        "on_change": lambda e: set_top_n(int(e["target"]["value"]) if e["target"]["value"] else 20),
                    }
                ),
            ),
            html.div(
                {
                    "title": "Excluye ejecuciones en progreso o con errores. Solo analiza ejecuciones finalizadas exitosamente para métricas más precisas.",
                    "style": {"display": "flex", "align-items": "center"},
                },
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
                ),
            ),
            html.button(
                {"on_click": handle_refresh, "type": "button"}, html.i({"class_name": "fa-solid fa-filter"}), " Aplicar"
            ),
        ),
        # Gráfico de tiempo por repetición
        html.div(
            {"class_name": "chart-container"},
            html.h3(f"Top {top_n} Tiempo Promedio por Repetición por Robot"),
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
            {"class_name": "chart-container"},
            html.h3(f"Top {top_n} Latencia Promedio de Inicio por Robot"),
            html.p(
                {"class_name": "metric-description"},
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
            {"class_name": "metrics-table"},
            html.h3(f"Top {top_n} Métricas Detalladas por Robot"),
            html.table(
                {"class_name": "dashboard-table"},
                html.thead(
                    html.tr(
                        html.th("Robot"),
                        html.th({"title": "Cantidad total de ejecuciones analizadas en el periodo"}, "Ejecuciones"),
                        html.th(
                            {"title": "Tiempo promedio que toma procesar UN solo ítem o vuelta"},
                            "Tiempo/Rep (HH:MM:SS)",
                        ),
                        html.th({"title": "Tiempo promedio total de la ejecución completa"}, "Tiempo Total (HH:MM:SS)"),
                        html.th({"title": "Cantidad promedio de ítems procesados por ejecución"}, "Repeticiones"),
                        html.th(
                            {"title": "Tiempo de espera desde el disparo hasta el inicio real"}, "Latencia (HH:MM:SS)"
                        ),
                        html.th({"title": "Medida de estabilidad (menor es más estable)"}, "Desv. Est. (seg)"),
                    )
                ),
                html.tbody(
                    *[
                        html.tr(
                            html.td(item.get("RobotNombre", "N/A")),
                            html.td(str(item.get("EjecucionesAnalizadas", 0))),
                            html.td(format_minutes_to_hhmmss(item.get("TiempoPromedioPorRepeticionMinutos"))),
                            html.td(format_minutes_to_hhmmss(item.get("TiempoPromedioTotalMinutos"))),
                            html.td(f"{int(item.get('PromedioRepeticiones') or 1)}"),
                            html.td(
                                format_minutes_to_hhmmss(item.get("LatenciaPromedioMinutos"))
                                if item.get("LatenciaPromedioMinutos")
                                else "N/A"
                            ),
                            html.td(f"{(item.get('DesviacionEstandarSegundos') or 0):.1f}"),
                        )
                        for item in filtered_data
                    ]
                ),
            ),
        ),
    )
