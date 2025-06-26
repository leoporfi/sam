# src/interfaz_web/components/common/loading_spinner.py
from reactpy import component, html


@component
def LoadingSpinner():
    """
    Un simple spinner de carga para mostrar mientras se obtienen los datos.
    Usa animaciones de Tailwind CSS.
    """
    return html.div(
        {"className": "flex justify-center items-center p-8", "aria-label": "Cargando...", "role": "status"},
        html.div({"className": "h-12 w-12 animate-spin rounded-full border-4 border-solid border-blue-600 border-t-transparent"}),
    )
