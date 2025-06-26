# src/interfaz_web/components/common/pagination.py
from typing import Callable

from reactpy import component, html


@component
def Pagination(current_page: int, total_pages: int, on_page_change: Callable):
    """
    Un componente reutilizable para la navegación por páginas.
    """
    # Lógica para deshabilitar los botones si estamos en la primera o última página
    is_first_page = current_page == 1
    is_last_page = current_page == total_pages

    def handle_previous(event=None):
        if not is_first_page:
            on_page_change(current_page - 1)

    def handle_next(event=None):
        if not is_last_page:
            on_page_change(current_page + 1)

    # Estilos para los botones
    button_style = "relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
    disabled_button_style = "relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-400 bg-gray-100 cursor-not-allowed"

    return html.nav(
        {"className": "flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6 rounded-b-lg"},
        # Botón Anterior
        html.div(
            html.button(
                {
                    "className": disabled_button_style if is_first_page else button_style,
                    "onClick": handle_previous,
                    "disabled": is_first_page,
                },
                "Anterior",
            )
        ),
        # Contador de Página
        html.div(
            {"className": "hidden sm:block"},
            html.p(
                {"className": "text-sm text-gray-700"},
                "Página ",
                html.span({"className": "font-medium"}, current_page),
                " de ",
                html.span({"className": "font-medium"}, total_pages),
            ),
        ),
        # Botón Siguiente
        html.div(
            html.button(
                {
                    "className": disabled_button_style if is_last_page else button_style,
                    "onClick": handle_next,
                    "disabled": is_last_page,
                },
                "Siguiente",
            )
        ),
    )
