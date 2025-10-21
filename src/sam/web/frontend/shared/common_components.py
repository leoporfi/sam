from typing import Callable, Dict, List

from reactpy import component, event, html


@component
def Pagination(
    current_page: int,
    total_pages: int,
    total_items: int,
    items_per_page: int,
    on_page_change: Callable,
    max_visible_pages: int = 5,
):
    """
    Componente de paginación avanzado, inspirado en templates modernos.
    Muestra botones de primero/último, anterior/siguiente y un rango de páginas.
    """

    def handle_page_click(page_number):
        if 1 <= page_number <= total_pages:
            on_page_change(page_number)

    def render_page_numbers():
        if total_pages <= max_visible_pages:
            start_page, end_page = 1, total_pages
        else:
            offset = max_visible_pages // 2
            start_page = max(1, current_page - offset)
            end_page = min(total_pages, start_page + max_visible_pages - 1)
            if end_page - start_page < max_visible_pages - 1:
                start_page = max(1, end_page - max_visible_pages + 1)

        pages = []
        for i in range(start_page, end_page + 1):
            is_current = i == current_page
            pages.append(
                html.li(
                    html.a(
                        {
                            "href": "#",
                            "role": "button" if not is_current else None,
                            "class_name": "" if is_current else "secondary",
                            "aria-current": "page" if is_current else None,
                            "onClick": event((lambda p: lambda e: handle_page_click(p))(i), prevent_default=True),
                        },
                        str(i),
                    )
                )
            )
        return pages

    start_item = (current_page - 1) * items_per_page + 1
    end_item = min(current_page * items_per_page, total_items)
    is_first_page = current_page == 1
    is_last_page = current_page == total_pages

    return html.nav(
        {"aria-label": "Pagination", "class_name": "pagination-container"},
        html.div(
            {"class_name": "pagination-summary"},
            f"Mostrando {start_item}-{end_item} de {total_items} robots",
        ),
        html.ul(
            {"class_name": "pagination-controls"},
            html.li(
                html.a(
                    {
                        "href": "#",
                        "class_name": "secondary",
                        "onClick": event(lambda e: handle_page_click(1), prevent_default=True),
                        "aria-label": "Primera página",
                        "data-tooltip": "Primera página",
                        "disabled": is_first_page,
                    },
                    "«",
                )
            ),
            html.li(
                html.a(
                    {
                        "href": "#",
                        "class_name": "secondary",
                        "onClick": event(lambda e: handle_page_click(current_page - 1), prevent_default=True),
                        "aria-label": "Página anterior",
                        "data-tooltip": "Página anterior",
                        "disabled": is_first_page,
                    },
                    "‹",
                )
            ),
            *render_page_numbers(),
            html.li(
                html.a(
                    {
                        "href": "#",
                        "class_name": "secondary",
                        "onClick": event(lambda e: handle_page_click(current_page + 1), prevent_default=True),
                        "aria-label": "Página siguiente",
                        "data-tooltip": "Página siguiente",
                        "disabled": is_last_page,
                    },
                    "›",
                )
            ),
            html.li(
                html.a(
                    {
                        "href": "#",
                        "class_name": "secondary",
                        "onClick": event(lambda e: handle_page_click(total_pages), prevent_default=True),
                        "aria-label": "Última página",
                        "data-tooltip": "Última página",
                        "disabled": is_last_page,
                    },
                    "»",
                )
            ),
        ),
    )


@component
def LoadingSpinner():
    """
    Un spinner de carga estilizado usando el atributo aria-busy de Pico.css.
    """
    return html.div(
        {"class_name": "container", "style": {"text_align": "center", "padding": "2rem"}},
        html.article(
            {"aria-busy": "true"},
            "Cargando datos...",
        ),
    )


@component
def ActionMenu(actions: List[Dict[str, any]]):
    """
    Menú desplegable de acciones que usa la estructura <details> de Pico.css.
    """
    return html.details(
        {"class_name": "dropdown"},
        html.summary(
            {"role": "", "class_name": "outline"},
        ),
        html.ul(
            {"role": "listbox"},
            *[
                html.li(
                    html.a(
                        {"href": "#", "onClick": event(action["on_click"], prevent_default=True)},
                        html.small(action["label"]),
                    )
                )
                for action in actions
            ],
        ),
    )


@component
def ThemeSwitcher(is_dark: bool, on_toggle: Callable):
    """
    Un interruptor para cambiar entre tema claro y oscuro, con iconos de sol y luna.
    """

    def handle_change(event):
        on_toggle(event["target"]["checked"])

    return html.label(
        {"htmlFor": "theme-switcher", "class_name": "theme-switcher"},
        html.span({"class_name": "material-symbols-outlined"}, "light_mode"),
        html.input(
            {
                "type": "checkbox",
                "id": "theme-switcher",
                "role": "switch",
                "checked": is_dark,
                "onChange": handle_change,
            }
        ),
        html.span({"class_name": "material-symbols-outlined"}, "dark_mode"),
    )


@component
def ConfirmationModal(is_open: bool, title: str, message: str, on_confirm: Callable, on_cancel: Callable):
    """Un modal genérico para solicitar confirmación del usuario."""
    if not is_open:
        return None

    async def handle_confirm_click(event):
        await on_confirm()

    return html.dialog(
        {"open": True},
        html.article(
            html.header(
                html.button({"aria-label": "Close", "rel": "prev", "onClick": lambda e: on_cancel()}),
                html.h3(title),
            ),
            html.p(message),
            html.footer(
                html.div(
                    {"class_name": "grid"},
                    html.button({"class_name": "secondary", "onClick": lambda e: on_cancel()}, "Cancelar"),
                    html.button(
                        {
                            "onClick": handle_confirm_click,
                            "style": {
                                "backgroundColor": "var(--pico-color-pink-550)",
                                "borderColor": "var(--pico-color-pink-550)",
                            },
                        },
                        "Confirmar",
                    ),
                ),
            ),
        ),
    )
