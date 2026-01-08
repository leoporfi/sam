import asyncio
import logging

from reactpy import component, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client

logger = logging.getLogger(__name__)


@component
def AnalyticsSummary(on_navigate, initial_data=None, on_refresh=None):
    """
    Vista resumen del dashboard de analítica.
    Muestra métricas clave y permite navegar a los detalles.
    """
    # Estados para los datos (inicializados desde props si existen)
    status_data, set_status_data = use_state(initial_data.get("status") if initial_data else None)
    critical_executions, set_critical_executions = use_state(initial_data.get("critical") if initial_data else [])
    performance_data, set_performance_data = use_state(initial_data.get("performance") if initial_data else None)
    success_data, set_success_data = use_state(initial_data.get("success") if initial_data else None)

    # Si tenemos datos iniciales, no estamos cargando
    loading, set_loading = use_state(not bool(initial_data))
    error, set_error = use_state(None)

    api_client = get_api_client()

    async def fetch_all_data():
        try:
            set_loading(True)
            set_error(None)

            # Ejecutar peticiones en paralelo
            status_task = api_client.get("/api/analytics/status")
            critical_task = api_client.get("/api/analytics/executions", params={"limit": 10, "critical_only": True})
            # Para tiempos, traemos un resumen general (sin filtros específicos de percentiles por ahora)
            performance_task = api_client.get("/api/analytics/tiempos-ejecucion")
            success_task = api_client.get("/api/analytics/tasas-exito")

            results = await asyncio.gather(
                status_task, critical_task, performance_task, success_task, return_exceptions=True
            )

            new_data = {}

            # Procesar resultados
            # Status
            if isinstance(results[0], Exception):
                logger.error(f"Error fetching status: {results[0]}")
            else:
                set_status_data(results[0])
                new_data["status"] = results[0]

            # Critical Executions
            if isinstance(results[1], Exception):
                logger.error(f"Error fetching critical executions: {results[1]}")
            else:
                set_critical_executions(results[1])
                new_data["critical"] = results[1]

            # Performance
            if isinstance(results[2], Exception):
                logger.error(f"Error fetching performance: {results[2]}")
            else:
                set_performance_data(results[2])
                new_data["performance"] = results[2]

            # Success Rates
            if isinstance(results[3], Exception):
                logger.error(f"Error fetching success rates: {results[3]}")
            else:
                set_success_data(results[3])
                new_data["success"] = results[3]

            # Notificar al padre los nuevos datos para caché
            if on_refresh and new_data:
                on_refresh(new_data)

        except Exception as e:
            set_error(str(e))
            logger.error(f"Error general en AnalyticsSummary: {e}")
        finally:
            set_loading(False)

    @use_effect(dependencies=[])
    def load_data():
        # Solo cargar si no tenemos datos iniciales
        if not initial_data:
            task = asyncio.create_task(fetch_all_data())
            return lambda: task.cancel()
        return None

    if loading:
        return html.div(
            {"class_name": "analytics-summary loading", "style": {"text-align": "center", "padding": "2rem"}},
            html.span({"aria-busy": "true"}, "Cargando resumen..."),
        )

    # --- Procesamiento de datos para visualización ---

    # 1. Infraestructura / Recursos
    active_robots = 0
    total_robots = 0
    active_teams = 0
    total_teams = 0
    if status_data:
        active_robots = status_data.get("robots", {}).get("RobotsActivos", 0)
        total_robots = status_data.get("robots", {}).get("TotalRobots", 0)
        active_teams = status_data.get("equipos", {}).get("EquiposActivos", 0)
        total_teams = status_data.get("equipos", {}).get("TotalEquipos", 0)

    # 2. Desvíos Críticos - Contar por tipo
    critical_count = 0
    fallos_count = 0
    demoradas_count = 0
    huerfanas_count = 0

    if critical_executions and isinstance(critical_executions, list):
        for exec in critical_executions:
            tipo = exec.get("TipoCritico")
            if tipo == "Fallo":
                fallos_count += 1
            elif tipo == "Demorada":
                demoradas_count += 1
            elif tipo == "Huerfana":
                huerfanas_count += 1
        critical_count = fallos_count + demoradas_count + huerfanas_count

    # 3. Performance (Tiempos)
    slowest_robot = "N/A"
    fastest_robot = "N/A"
    highest_latency_robot = "N/A"

    if performance_data and isinstance(performance_data, list) and len(performance_data) > 0:
        # Ordenar por TiempoPromedioPorRepeticionMinutos (tiempo por repetición)
        sorted_by_time = sorted(
            performance_data, key=lambda x: float(x.get("TiempoPromedioPorRepeticionMinutos", 0) or 0)
        )
        if sorted_by_time:
            fastest = sorted_by_time[0]
            slowest = sorted_by_time[-1]
            # Convertir minutos a segundos para mostrar
            fastest_time_sec = (fastest.get("TiempoPromedioPorRepeticionMinutos", 0) or 0) * 60
            slowest_time_sec = (slowest.get("TiempoPromedioPorRepeticionMinutos", 0) or 0) * 60
            fastest_robot = f"{fastest.get('RobotNombre', 'N/A')} ({fastest_time_sec:.1f}s)"
            slowest_robot = f"{slowest.get('RobotNombre', 'N/A')} ({slowest_time_sec:.1f}s)"

        # Ordenar por LatenciaPromedioMinutos
        sorted_by_latency = sorted(
            performance_data, key=lambda x: float(x.get("LatenciaPromedioMinutos", 0) or 0), reverse=True
        )
        if sorted_by_latency and sorted_by_latency[0].get("LatenciaPromedioMinutos"):
            highest = sorted_by_latency[0]
            # Convertir minutos a segundos para mostrar
            latency_sec = (highest.get("LatenciaPromedioMinutos", 0) or 0) * 60
            highest_latency_robot = f"{highest.get('RobotNombre', 'N/A')} ({latency_sec:.1f}s)"

    # 4. Tasas de Éxito / Errores
    top_error_type = "Ninguno"
    error_rate_avg = "0%"

    if success_data:
        # success_data suele tener { "resumen_global": ..., "detalle_robots": ..., "top_errores": ... }
        # Ajustar según la respuesta real del SP/API.
        # Revisando api.py -> get_success_analysis -> db_service.get_success_analysis
        # Si devuelve lista directa o dict. Asumiremos dict con claves si es el nuevo SP.
        # Si es lista plana, procesamos.

        # Si es el formato nuevo (Phase 3):
        top_errors = success_data.get("top_errores", [])
        if top_errors:
            top_error = top_errors[0]
            top_error_type = f"{top_error.get('MensajeError', 'Error')} ({top_error.get('Cantidad', 0)})"

        global_stats = success_data.get("resumen_global", {})
        if global_stats:
            total = global_stats.get("TotalEjecuciones", 0)
            errors = global_stats.get("TotalFallidas", 0)
            if total > 0:
                rate = (errors / total) * 100
                error_rate_avg = f"{rate:.1f}%"

    # --- Renderizado de Cards ---

    def render_card(title, icon, content, color_class, target_view, footer=None):
        return html.article(
            {
                "class_name": f"summary-card {color_class}",
                "on_click": lambda e: on_navigate(target_view),
                "style": {
                    "cursor": "pointer",
                    "transition": "transform 0.2s, box-shadow 0.2s",
                    "position": "relative",
                    "overflow": "hidden",
                },
                # Hover effect inline for simplicity, or use CSS class
            },
            html.header(
                {"style": "display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;"},
                html.h4(
                    {"style": "margin: 0; font-size: 1rem; text-transform: uppercase; letter-spacing: 1px;"}, title
                ),
                html.i({"class_name": f"fa-solid {icon}", "style": "font-size: 1.5rem; opacity: 0.8;"}),
            ),
            html.div({"class_name": "card-content"}, content),
            html.footer(
                {"style": "font-size: 0.8rem; margin-top: 1rem; opacity: 0.8;"},
                footer if footer else html.span("Ver detalles →"),
            ),
        )

    return html.div(
        {"class_name": "analytics-summary-container"},
        html.h2("Resumen General"),
        html.div(
            {
                "class_name": "summary-grid",
                "style": {
                    "display": "grid",
                    "grid-template-columns": "repeat(auto-fit, minmax(300px, 1fr))",
                    "gap": "1.5rem",
                    "margin-top": "1rem",
                },
            },
            # Card 1: Estado del Sistema
            render_card(
                "Infraestructura",
                "fa-server",
                html.div(
                    html.div(f"🤖 Robots: {active_robots} / {total_robots} Activos"),
                    html.div(f"💻 Equipos: {active_teams} / {total_teams} Activos"),
                ),
                "card-blue",
                "status",
                "Ver estado en tiempo real",
            ),
            # Card 2: Desvíos Críticos
            render_card(
                "Alertas Críticas",
                "fa-triangle-exclamation",
                html.div(
                    html.h3(
                        {
                            "style": {
                                "margin": "0",
                                "font-size": "2rem",
                                "color": "var(--pico-color-red-500)"
                                if fallos_count > 0
                                else "var(--pico-color-yellow-500)"
                                if (demoradas_count + huerfanas_count) > 0
                                else "var(--pico-color-green-500)",
                            }
                        },
                        str(critical_count),
                    ),
                    html.div(
                        {"style": {"font-size": "0.9rem", "margin-top": "0.5rem"}},
                        f"❌ {fallos_count} fallos" if fallos_count > 0 else "",
                        html.br() if fallos_count > 0 and (demoradas_count + huerfanas_count) > 0 else "",
                        f"⏱️ {demoradas_count} demoradas" if demoradas_count > 0 else "",
                        html.br() if demoradas_count > 0 and huerfanas_count > 0 else "",
                        f"⚠️ {huerfanas_count} huérfanas" if huerfanas_count > 0 else "",
                    )
                    if critical_count > 0
                    else html.span("Sin ejecuciones críticas"),
                ),
                "card-red"
                if fallos_count > 0
                else "card-yellow"
                if (demoradas_count + huerfanas_count) > 0
                else "card-green",
                "status",  # Lleva al status dashboard que tiene la tabla de ejecuciones
                "Revisar ejecuciones críticas",
            ),
            # Card 3: Performance (Tiempos)
            render_card(
                "Performance",
                "fa-stopwatch",
                html.div(
                    html.div(html.strong("Más Lento: "), slowest_robot),
                    html.div(html.strong("Más Rápido: "), fastest_robot),
                ),
                "card-purple",
                "tiempos",
                "Analizar tiempos de ejecución",
            ),
            # Card 4: Latencia
            render_card(
                "Latencia de Inicio",
                "fa-clock",
                html.div(
                    html.div(html.strong("Mayor Delay: ")),
                    html.div(
                        {"style": "color: var(--pico-color-orange-500); font-weight: bold;"}, highest_latency_robot
                    ),
                ),
                "card-orange",
                "tiempos",  # Latencia está en el dashboard de tiempos
                "Ver análisis de latencia",
            ),
            # Card 5: Tasas de Éxito
            render_card(
                "Calidad",
                "fa-chart-pie",
                html.div(
                    html.div(f"Tasa de Error Global: {error_rate_avg}"),
                    html.div(html.strong("Top Error: "), top_error_type),
                ),
                "card-cyan",
                "tasas",
                "Ver desglose de errores",
            ),
            # Card 6: Patrones Temporales
            render_card(
                "Patrones de Uso",
                "fa-calendar-days",
                html.div("Mapa de calor de actividad por día y hora."),
                "card-indigo",
                "patrones",
                "Ver mapa de calor",
            ),
        ),
    )
