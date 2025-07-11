# src/interfaz_web/components/common/loading_spinner.py
from reactpy import component, html

@component
def LoadingSpinner():
    """
    Un spinner de carga estilizado usando el atributo aria-busy de Pico.css.
    """
    return html.div(
        {"className": "container", "style": {"textAlign": "center", "padding": "2rem"}},
        html.article(
            {"aria-busy": "true"},
            # El texto dentro del elemento se muestra mientras carga
            "Cargando datos..."
        )
    )