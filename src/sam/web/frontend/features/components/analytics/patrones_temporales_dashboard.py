# sam/web/frontend/features/components/analytics/patrones_temporales_dashboard.py

import asyncio
import logging
from datetime import datetime, timedelta

from reactpy import component, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client
from sam.web.frontend.shared.async_content import SkeletonTable
from sam.web.frontend.shared.common_components import LoadingOverlay
from sam.web.frontend.shared.formatters import format_minutes_to_hhmmss

logger = logging.getLogger(__name__)


@component
def TemporalPatternsDashboard():
    """Dashboard de análisis de patrones temporales (Heatmap)."""
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

            data = await api_client.get("/api/analytics/patrones-temporales", params=params)
            set_dashboard_data(data)
            set_loading(False)
        except asyncio.CancelledError:
            # Silenciar errores de cancelación y NO actualizar estado
            pass
        except Exception as e:
            set_error(str(e))
            logger.error(f"Error obteniendo dashboard de patrones temporales: {e}")
            set_loading(False)

    def handle_refresh(event=None):
        asyncio.create_task(fetch_dashboard())

    @use_effect(dependencies=[])
    def load_data():
        task = asyncio.create_task(fetch_dashboard())
        return lambda: task.cancel() if not task.done() else None

    # Calcular fechas por defecto (últimos 90 días)
    hoy = datetime.now()
    hace_90_dias = hoy - timedelta(days=90)
    fecha_inicio_default = fecha_inicio or hace_90_dias
    fecha_fin_default = fecha_fin or hoy

    # Renderizado del Heatmap
    def render_heatmap():
        if not dashboard_data:
            return html.p("No hay datos disponibles para el rango seleccionado.")

        # Estructura de datos para el grid: 7 días x 24 horas
        # Inicializar matriz vacía
        grid = {day: {hour: {"count": 0, "duration": 0} for hour in range(24)} for day in range(1, 8)}

        max_executions = 0

        # Llenar con datos
        for item in dashboard_data:
            day = item.get("DiaSemana")
            hour = item.get("HoraDia")
            count = item.get("CantidadEjecuciones", 0)
            duration = item.get("DuracionPromedioMinutos", 0)

            if day in grid and hour in grid[day]:
                grid[day][hour] = {"count": count, "duration": duration}
                if count > max_executions:
                    max_executions = count

        days_map = {1: "Domingo", 2: "Lunes", 3: "Martes", 4: "Miércoles", 5: "Jueves", 6: "Viernes", 7: "Sábado"}

        # Generar filas del grid
        rows = []

        # Header de horas
        header_cells = [html.th({"class_name": "heatmap-header-corner"}, "Día/Hora")]
        for h in range(24):
            header_cells.append(html.th({"class_name": "heatmap-header-hour"}, f"{h:02d}"))
        rows.append(html.tr(header_cells))

        # Filas de días
        for day_num in range(2, 8):  # Lunes a Sábado
            rows.append(render_day_row(day_num, days_map[day_num], grid[day_num], max_executions))
        rows.append(render_day_row(1, days_map[1], grid[1], max_executions))  # Domingo al final

        return html.div(
            {"class_name": "heatmap-container"},
            html.table({"class_name": "heatmap-table"}, html.tbody(rows)),
            render_insights(calculate_insights(grid, days_map)),
        )

    def render_day_row(day_num, day_name, day_data, max_val):
        cells = [html.td({"class_name": "heatmap-row-header"}, day_name)]

        for hour in range(24):
            data = day_data[hour]
            count = data["count"]
            duration = data["duration"]

            # Calcular intensidad del color (0-1)
            intensity = count / max_val if max_val > 0 else 0

            # Color: Verde claro a Verde oscuro (o Azul)
            # Usaremos una clase CSS dinámica o estilo inline
            bg_color = f"rgba(46, 204, 113, {0.1 + (intensity * 0.9)})" if count > 0 else "transparent"
            text_color = "#fff" if intensity > 0.6 else "var(--pico-color)"

            cells.append(
                html.td(
                    {
                        "class_name": "heatmap-cell",
                        "style": {
                            "background-color": bg_color,
                            "color": text_color,
                        },
                        "title": f"{day_name} {hour}:00\nEjecuciones: {count}\nDuración Promedio: {format_minutes_to_hhmmss(duration)}",
                    },
                    str(count) if count > 0 else "",
                )
            )

        return html.tr(cells)

    def calculate_insights(grid, days_map):
        """Calcula insights automáticos basados en los datos del grid."""
        if not grid:
            return None

        # 1. Día Pico
        day_totals = {day: sum(grid[day][h]["count"] for h in range(24)) for day in grid}
        peak_day_num = max(day_totals, key=day_totals.get)
        peak_day_val = day_totals[peak_day_num]
        peak_day_name = days_map[peak_day_num]

        # 2. Hora Pico
        hour_totals = {h: sum(grid[d][h]["count"] for d in grid) for h in range(24)}
        peak_hour = max(hour_totals, key=hour_totals.get)
        peak_hour_val = hour_totals[peak_hour]

        # También buscamos un día/hora específico muy bajo
        min_cell_val = float("inf")
        min_cell_day = 1
        min_cell_hour = 0

        for d in grid:
            for h in range(24):
                val = grid[d][h]["count"]
                if val < min_cell_val:
                    min_cell_val = val
                    min_cell_day = d
                    min_cell_hour = h

        maintenance_window = f"{days_map[min_cell_day]} {min_cell_hour}:00"

        # 4. Perfil Operativo (Diurno vs Nocturno)
        # Diurno: 08:00 - 20:00 (12 horas)
        # Nocturno: 20:00 - 08:00 (12 horas)
        daytime_sum = sum(hour_totals[h] for h in range(8, 20))
        nighttime_sum = sum(hour_totals[h] for h in list(range(0, 8)) + list(range(20, 24)))
        total_sum = daytime_sum + nighttime_sum

        profile = "Equilibrado"
        if total_sum > 0:
            day_pct = (daytime_sum / total_sum) * 100
            if day_pct > 70:
                profile = "Mayormente Diurno"
            elif day_pct < 30:
                profile = "Mayormente Nocturno"
            else:
                profile = "Intensivo 24/7"

        return {
            "peak_day": f"{peak_day_name} ({peak_day_val:,})",
            "peak_hour": f"{peak_hour}:00 hs ({peak_hour_val:,})",
            "maintenance": f"{maintenance_window} ({min_cell_val})",
            "profile": f"{profile} ({int((nighttime_sum / total_sum) * 100) if total_sum > 0 else 0}% nocturno)",
        }

    def render_insights(insights):
        if not insights:
            return None

        return html.div(
            {"class_name": "insights-container", "style": {"margin-top": "2rem"}},
            html.h3("🤖 Análisis Inteligente"),
            html.div(
                {
                    "class_name": "insights-grid",
                    "style": {
                        "display": "grid",
                        "grid-template-columns": "repeat(auto-fit, minmax(200px, 1fr))",
                        "gap": "1rem",
                    },
                },
                # Card Día Pico
                html.div(
                    {
                        "class_name": "insight-card",
                        "style": "background: var(--pico-card-background-color); padding: 1rem; border-radius: 8px; border-left: 4px solid var(--pico-color-red-500);",
                    },
                    html.small({"style": "color: var(--pico-muted-color); text-transform: uppercase;"}, "📅 Día Pico"),
                    html.div(
                        {"style": "font-size: 1.2rem; font-weight: bold; margin-top: 0.5rem;"}, insights["peak_day"]
                    ),
                ),
                # Card Hora Pico
                html.div(
                    {
                        "class_name": "insight-card",
                        "style": "background: var(--pico-card-background-color); padding: 1rem; border-radius: 8px; border-left: 4px solid var(--pico-color-orange-500);",
                    },
                    html.small({"style": "color: var(--pico-muted-color); text-transform: uppercase;"}, "⏰ Hora Pico"),
                    html.div(
                        {"style": "font-size: 1.2rem; font-weight: bold; margin-top: 0.5rem;"}, insights["peak_hour"]
                    ),
                ),
                # Card Mantenimiento
                html.div(
                    {
                        "class_name": "insight-card",
                        "style": "background: var(--pico-card-background-color); padding: 1rem; border-radius: 8px; border-left: 4px solid var(--pico-color-green-500);",
                    },
                    html.small(
                        {"style": "color: var(--pico-muted-color); text-transform: uppercase;"},
                        "🛠️ Ventana Mantenimiento",
                    ),
                    html.div(
                        {"style": "font-size: 1.2rem; font-weight: bold; margin-top: 0.5rem;"}, insights["maintenance"]
                    ),
                ),
                # Card Perfil
                html.div(
                    {
                        "class_name": "insight-card",
                        "style": "background: var(--pico-card-background-color); padding: 1rem; border-radius: 8px; border-left: 4px solid var(--pico-color-blue-500);",
                    },
                    html.small(
                        {"style": "color: var(--pico-muted-color); text-transform: uppercase;"}, "🌙 Perfil Operativo"
                    ),
                    html.div(
                        {"style": "font-size: 1.2rem; font-weight: bold; margin-top: 0.5rem;"}, insights["profile"]
                    ),
                ),
            ),
        )

    if loading and not dashboard_data:
        return html.div(
            {"class_name": "temporal-patterns-dashboard"},
            html.header(
                {"class_name": "dashboard-header"},
                html.h2({"class_name": "dashboard-title"}, "Análisis de Patrones Temporales"),
            ),
            SkeletonTable(rows=8, cols=25),
        )

    if error:
        return html.div(
            {"class_name": "temporal-patterns-dashboard error", "style": {"color": "var(--pico-color-red-600)"}},
            html.h3("Error"),
            html.p(error),
            html.button({"on_click": handle_refresh}, "Reintentar"),
        )

    return html.div(
        {"class_name": "temporal-patterns-dashboard", "style": {"position": "relative"}},
        LoadingOverlay(is_loading=loading),
        html.header(
            {"class_name": "dashboard-header"},
            html.h2({"class_name": "dashboard-title"}, "Análisis de Patrones Temporales"),
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
            "Mapa de calor que muestra la intensidad de ejecuciones por día de la semana y hora del día. Permite identificar ventanas de mantenimiento (zonas vacías) y cuellos de botella (zonas oscuras).",
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
        # Heatmap
        html.div(
            {"class_name": "chart-container heatmap-wrapper"}, html.h3("Mapa de Calor de Ejecuciones"), render_heatmap()
        ),
        # Estilos inline para el heatmap (idealmente irían en CSS)
        html.style(
            """
            .heatmap-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
            .heatmap-cell { text-align: center; border: 1px solid var(--pico-muted-border-color); height: 30px; width: 3.5%; cursor: help; }
            .heatmap-header-hour { text-align: center; font-weight: bold; background-color: var(--pico-card-background-color); }
            .heatmap-row-header { font-weight: bold; text-align: right; padding-right: 10px; background-color: var(--pico-card-background-color); }
        """
        ),
    )
