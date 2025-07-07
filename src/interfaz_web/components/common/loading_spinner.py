# src/interfaz_web/components/common/loading_spinner.py
from reactpy import component, html


@component
def LoadingSpinner():
    """
    Un spinner de carga estilizado con las clases de Bulma.
    """
    return html.div(
        # 'has-text-centered' centra el spinner horizontalmente
        {"className": "has-text-centered p-6", "aria-label": "Cargando...", "role": "status"},
        # Se usa un botón con el modificador 'is-loading' de Bulma.
        # Las otras clases le dan tamaño, color y quitan los bordes
        # para que solo se vea la animación.
        html.button(
            {
                "className": "button is-large is-info is-loading is-borderless",
            }
        ),
    )
