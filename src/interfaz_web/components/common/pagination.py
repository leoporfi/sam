# src/interfaz_web/components/common/pagination.py
from typing import Callable

from reactpy import component, event, html


@component
def Pagination(current_page: int, total_pages: int, on_page_change: Callable):
    """
    Componente de paginación refactorizado para Pico.css usando un grid.
    """
    is_first_page = current_page == 1
    is_last_page = current_page == total_pages

    def handle_previous(e):
        if not is_first_page:
            on_page_change(current_page - 1)

    def handle_next(e):
        if not is_last_page:
            on_page_change(current_page + 1)

    return html.nav(
        {"className": "grid"},
        # Botón Anterior (a la izquierda)
        html.div(
            html.button(
                {"className": "secondary", "onClick": handle_previous, "disabled": is_first_page},
                "Anterior",
            )
        ),
        # Contador de Página (centrado)
        html.div(
            {"style": {"textAlign": "center", "lineHeight": "2.5rem"}},
            f"Página {current_page} de {total_pages}",
        ),
        # Botón Siguiente (a la derecha)
        html.div(
            {"style": {"textAlign": "right"}},
            html.button(
                {"className": "secondary", "onClick": handle_next, "disabled": is_last_page},
                "Siguiente",
            ),
        ),
    )
