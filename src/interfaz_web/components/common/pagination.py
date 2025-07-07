# src/interfaz_web/components/common/pagination.py
from typing import Callable

from reactpy import component, html


@component
def Pagination(current_page: int, total_pages: int, on_page_change: Callable):
    """
    Un componente reutilizable para la navegación por páginas, estilizado con Bulma.
    """
    # La lógica de Python para manejar el estado no necesita cambios.
    is_first_page = current_page == 1
    is_last_page = current_page == total_pages

    def handle_previous(event=None):
        if not is_first_page:
            on_page_change(current_page - 1)

    def handle_next(event=None):
        if not is_last_page:
            on_page_change(current_page + 1)

    # --- CORRECCIÓN: Se utiliza 'buttons is-centered' para centrar la paginación ---
    return html.nav(
        {"className": "py-4"},
        html.div(
            {"className": "buttons is-centered"},
            html.button(
                {
                    "className": "button is-small",
                    "onClick": handle_previous,
                    "disabled": is_first_page,
                },
                "Anterior",
            ),
            html.p(
                {"className": "is-size-7 mx-4", "style": {"align-self": "center"}},
                f"Página {current_page} de {total_pages}",
            ),
            html.button(
                {
                    "className": "button is-small",
                    "onClick": handle_next,
                    "disabled": is_last_page,
                },
                "Siguiente",
            ),
        ),
    )
