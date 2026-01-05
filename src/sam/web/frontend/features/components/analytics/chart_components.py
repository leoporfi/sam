# sam/web/frontend/features/components/analytics/chart_components.py

"""
Componentes de gráficos reutilizables usando Chart.js con JavaScript inline.
"""

import json
import uuid

from reactpy import component, html, use_effect, use_state


def _escape_js_string(s: str) -> str:
    """Escapa una cadena para uso en JavaScript."""
    return json.dumps(s)


def _generate_chart_script(chart_id: str, chart_type: str, title: str, labels: list, datasets: list):
    """Genera el código JavaScript para crear un gráfico Chart.js."""
    labels_json = json.dumps(labels)
    datasets_json = json.dumps(datasets)
    title_escaped = _escape_js_string(title)

    return f"""
(function() {{
    function initChart() {{
        if (typeof Chart === 'undefined') {{
            setTimeout(initChart, 100);
            return;
        }}

        const canvas = document.getElementById('{chart_id}');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        // Destruir gráfico anterior si existe
        if (canvas._chartInstance) {{
            canvas._chartInstance.destroy();
        }}

        const chartConfig = {{
            type: '{chart_type}',
            data: {{
                labels: {labels_json},
                datasets: {datasets_json}
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: {title_escaped}
                    }},
                    legend: {{
                        display: true,
                        position: 'top'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }};

        canvas._chartInstance = new Chart(ctx, chartConfig);
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', initChart);
    }} else {{
        initChart();
    }}
}})();
"""


@component
def LineChart(chart_id: str, title: str, labels: list, datasets: list, height: str = "300px"):
    """
    Componente de gráfico de línea usando Chart.js.

    Args:
        chart_id: ID único para el canvas
        title: Título del gráfico
        labels: Lista de etiquetas (eje X)
        datasets: Lista de datasets, cada uno es un dict con:
            - label: Nombre del dataset
            - data: Lista de valores
            - borderColor: Color de la línea
            - backgroundColor: Color de relleno (opcional)
    """
    script_key = use_state(str(uuid.uuid4()))

    # Preparar datasets con valores por defecto
    prepared_datasets = []
    for ds in datasets:
        prepared_datasets.append(
            {
                "label": ds.get("label", ""),
                "data": ds.get("data", []),
                "borderColor": ds.get("borderColor", "rgb(75, 192, 192)"),
                "backgroundColor": ds.get("backgroundColor", "rgba(75, 192, 192, 0.2)"),
                "tension": 0.1,
            }
        )

    chart_script = _generate_chart_script(chart_id, "line", title, labels, prepared_datasets)

    @use_effect(dependencies=[labels, datasets, title])
    def update_chart():
        """Actualiza el gráfico cuando cambian los datos."""
        # Forzar re-render del script con nuevo key
        script_key[1](str(uuid.uuid4()))

    return html.div(
        {"style": {"position": "relative", "height": height, "width": "100%", "margin": "1rem 0"}},
        html.canvas(
            {
                "id": chart_id,
                "style": {"max-width": "100%", "height": height},
            }
        ),
        html.script(
            {
                "key": script_key[0],
            },
            chart_script,
        ),
    )


@component
def BarChart(chart_id: str, title: str, labels: list, datasets: list, height: str = "300px"):
    """
    Componente de gráfico de barras usando Chart.js.

    Args:
        chart_id: ID único para el canvas
        title: Título del gráfico
        labels: Lista de etiquetas (eje X)
        datasets: Lista de datasets, cada uno es un dict con:
            - label: Nombre del dataset
            - data: Lista de valores
            - backgroundColor: Color de las barras
    """
    script_key = use_state(str(uuid.uuid4()))

    # Preparar datasets con valores por defecto
    prepared_datasets = []
    for ds in datasets:
        prepared_datasets.append(
            {
                "label": ds.get("label", ""),
                "data": ds.get("data", []),
                "backgroundColor": ds.get("backgroundColor", "rgba(75, 192, 192, 0.6)"),
            }
        )

    chart_script = _generate_chart_script(chart_id, "bar", title, labels, prepared_datasets)

    @use_effect(dependencies=[labels, datasets, title])
    def update_chart():
        """Actualiza el gráfico cuando cambian los datos."""
        script_key[1](str(uuid.uuid4()))

    return html.div(
        {"style": {"position": "relative", "height": height, "width": "100%", "margin": "1rem 0"}},
        html.canvas(
            {
                "id": chart_id,
                "style": {"max-width": "100%", "height": height},
            }
        ),
        html.script(
            {
                "key": script_key[0],
            },
            chart_script,
        ),
    )
