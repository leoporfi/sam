# sam/web/frontend/features/components/analytics/callbacks_dashboard.py

import asyncio
import logging
from datetime import datetime, timedelta

from reactpy import component, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client
from sam.web.frontend.shared.async_content import SkeletonCardGrid, SkeletonTable
from sam.web.frontend.shared.common_components import LoadingOverlay
from sam.web.frontend.shared.formatters import format_minutes_to_hhmmss

from .chart_components import LineChart

logger = logging.getLogger(__name__)


@component
def CallbacksDashboard():
    """Dashboard de análisis de callbacks."""
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

            data = await api_client.get("/api/analytics/callbacks", params=params)
            set_dashboard_data(data)
            set_loading(False)
        except asyncio.CancelledError:
            # Silenciar errores de cancelación y NO actualizar estado
            pass
        except Exception as e:
            set_error(str(e))
            logger.error(f"Error obteniendo dashboard de callbacks: {e}")
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
            {"class_name": "callbacks-dashboard"},
            html.header(
                {"class_name": "dashboard-header"},
                html.h2({"class_name": "dashboard-title"}, "Análisis de Callbacks y Conciliador"),
            ),
            SkeletonCardGrid(count=4),
            html.div({"style": {"margin-top": "2rem"}}, SkeletonTable(rows=5, cols=5)),
        )

    if error:
        return html.div(
            {"class_name": "callbacks-dashboard error", "style": {"color": "var(--pico-color-red-600)"}},
            html.h3("Error"),
            html.p(error),
            html.button({"on_click": handle_refresh}, "Reintentar"),
        )

    if not dashboard_data:
        return html.div({"class_name": "callbacks-dashboard"}, html.p("No hay datos disponibles"))

    metricas = dashboard_data.get("metricas_generales", {})
    tendencia = dashboard_data.get("tendencia_diaria", [])
    casos_problematicos = dashboard_data.get("casos_problematicos", [])

    # Preparar datos para gráfico de tendencia diaria
    tendencia_labels = []
    tendencia_callbacks = []
    tendencia_conciliador = []
    tendencia_latencia = []

    if tendencia:
        for item in tendencia:
            fecha_str = item.get("Fecha", "")
            if fecha_str:
                # Formatear fecha para mostrar
                try:
                    fecha_obj = datetime.fromisoformat(fecha_str) if isinstance(fecha_str, str) else fecha_str
                    tendencia_labels.append(
                        fecha_obj.strftime("%d/%m") if hasattr(fecha_obj, "strftime") else str(fecha_str)[:10]
                    )
                except (ValueError, AttributeError):
                    tendencia_labels.append(str(fecha_str)[:10])
            else:
                tendencia_labels.append("N/A")

            tendencia_callbacks.append(item.get("CallbacksExitosos", 0))
            tendencia_conciliador.append(item.get("ConciliadorExitosos", 0))
            tendencia_latencia.append(item.get("LatenciaPromedioMinutos", 0))

    # Calcular fechas por defecto (últimos 7 días)
    hoy = datetime.now()
    hace_7_dias = hoy - timedelta(days=7)
    fecha_inicio_default = fecha_inicio or hace_7_dias
    fecha_fin_default = fecha_fin or hoy

    return html.div(
        {"class_name": "callbacks-dashboard", "style": {"position": "relative"}},
        LoadingOverlay(is_loading=loading),
        html.header(
            {
                "class_name": "dashboard-header",
            },
            html.h2({"class_name": "dashboard-title"}, "Análisis de Callbacks y Conciliador"),
            html.button(
                {
                    "on_click": handle_refresh,
                    "class_name": "secondary dashboard-refresh-btn",
                    "title": "Actualizar",
                    "aria-label": "Actualizar dashboard de callbacks",
                },
                html.i({"class_name": "fa-solid fa-rotate"}),
            ),
        ),
        html.p(
            {
                "class_name": "dashboard-description",
            },
            "Analiza el rendimiento del sistema de finalización de ejecuciones. Compara callbacks exitosos (notificaciones automáticas) vs conciliador (verificación periódica). Muestra latencia, tasas de éxito y casos problemáticos. Útil para identificar problemas de comunicación o configuración.",
        ),
        html.p(
            {
                "class_name": "dashboard-alert dashboard-alert-yellow",
            },
            "ℹ️ Datos disponibles: Incluye ejecuciones de las últimas 24 horas (tabla actual) y datos históricos hasta 15 días. El mantenimiento diario mueve datos antiguos a las 5am. Los datos más antiguos de 15 días se purgan automáticamente.",
        ),
        # Filtros de fecha
        html.div(
            {
                "class_name": "filters dashboard-filters",
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
            html.button(
                {
                    "on_click": handle_refresh,
                    "type": "button",
                    "title": "Aplicar filtros y actualizar",
                },
                html.i({"class_name": "fa-solid fa-filter"}),
                " Aplicar",
            ),
        ),
        # Métricas principales
        html.div(
            {
                "class_name": "metrics-grid dashboard-grid",
            },
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Callbacks Exitosos")),
                html.div(
                    {"class_name": "metric-value"},
                    f"{(metricas.get('PorcentajeCallbackExitoso') or 0):.1f}%",
                ),
                html.div(
                    {"class_name": "metric-label"},
                    f"{metricas.get('CallbacksExitosos', 0)} de {metricas.get('TotalEjecuciones', 0)}",
                ),
            ),
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Latencia Promedio")),
                html.div(
                    {"class_name": "metric-value"},
                    f"{format_minutes_to_hhmmss(metricas.get('LatenciaPromedioMinutos'))}",
                ),
                html.div(
                    {"class_name": "metric-label"},
                    f"Max: {format_minutes_to_hhmmss(metricas.get('LatenciaMaximaMinutos'))}",
                ),
            ),
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Tasa de Éxito")),
                html.div(
                    {"class_name": "metric-value"},
                    f"{(metricas.get('PorcentajeExito') or 0):.1f}%",
                ),
                html.div(
                    {"class_name": "metric-label"},
                    f"{metricas.get('EjecucionesExitosas', 0)} exitosas / {metricas.get('EjecucionesFallidas', 0)} fallidas",
                ),
            ),
            html.article(
                {"class_name": "card"},
                html.header(html.h3("Conciliador")),
                html.div(
                    {"class_name": "metric-value"},
                    f"{(metricas.get('PorcentajeConciliadorExitoso') or 0):.1f}%",
                ),
                html.div(
                    {"class_name": "metric-label"},
                    f"{metricas.get('ConciliadorExitosos', 0)} exitosos / {metricas.get('ConciliadorAgotados', 0)} agotados",
                ),
            ),
        ),
        # Gráfico de tendencia diaria
        html.div(
            {"class_name": "chart-container"},
            html.h3("Tendencia Diaria"),
            LineChart(
                chart_id="callbacks-tendencia-chart",
                title="Callbacks vs Conciliador por Día",
                labels=tendencia_labels if tendencia_labels else ["Sin datos"],
                datasets=[
                    {
                        "label": "Callbacks Exitosos",
                        "data": tendencia_callbacks if tendencia_callbacks else [0],
                        "borderColor": "rgb(75, 192, 192)",
                        "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    },
                    {
                        "label": "Conciliador Exitosos",
                        "data": tendencia_conciliador if tendencia_conciliador else [0],
                        "borderColor": "rgb(255, 99, 132)",
                        "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    },
                ],
                height="300px",
            )
            if tendencia
            else html.p("No hay datos de tendencia disponibles"),
        ),
        # Tabla de casos problemáticos
        html.div(
            {"class_name": "problematic-cases metrics-table"},
            html.h3("Casos Problemáticos Recientes"),
            html.table(
                {"role": "table"},
                html.thead(
                    html.tr(
                        html.th("Deployment ID"),
                        html.th("Robot"),
                        html.th("Estado"),
                        html.th("Latencia (HH:MM:SS)"),
                        html.th("Tipo Problema"),
                    )
                ),
                html.tbody(
                    *[
                        html.tr(
                            html.td(caso.get("DeploymentId", "")),
                            html.td(caso.get("RobotNombre", "")),
                            html.td(caso.get("Estado", "")),
                            html.td(format_minutes_to_hhmmss(caso.get("LatenciaActualizacionMinutos"))),
                            html.td(caso.get("TipoProblema", "")),
                        )
                        for caso in casos_problematicos[:10]
                    ]
                    if casos_problematicos
                    else [html.tr(html.td({"colspan": 5}, "No hay casos problemáticos"))]
                ),
            ),
        ),
    )
