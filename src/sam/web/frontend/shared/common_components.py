from typing import Callable, List, Optional

from reactpy import component, html
from reactpy_router import link


@component
def Pagination(
    current_page: int,
    total_pages: int,
    total_items: int,
    items_per_page: int,
    on_page_change: Callable,
    max_visible_pages: int = 5,
):
    """Componente de paginación con resumen y controles."""

    # --- Lógica para generar los números de página visibles ---
    page_numbers: List[int | str] = []
    if total_pages <= max_visible_pages:
        page_numbers = list(range(1, total_pages + 1))
    else:
        half_visible = max_visible_pages // 2
        start_page = max(1, current_page - half_visible)
        end_page = min(total_pages, start_page + max_visible_pages - 1)

        # Ajustar si estamos cerca del final
        if end_page == total_pages:
            start_page = max(1, total_pages - max_visible_pages + 1)
        # Ajustar si estamos cerca del principio
        if start_page == 1 and end_page < total_pages:
            end_page = min(total_pages, max_visible_pages)

        if start_page > 1:
            page_numbers.append(1)
            if start_page > 2:
                page_numbers.append("...")  # Ellipsis

        for i in range(start_page, end_page + 1):
            page_numbers.append(i)

        if end_page < total_pages:
            if end_page < total_pages - 1:
                page_numbers.append("...")  # Ellipsis
            page_numbers.append(total_pages)

    # --- Resumen de paginación ---
    start_item = ((current_page - 1) * items_per_page) + 1
    end_item = min(current_page * items_per_page, total_items)
    summary = f"Mostrando {start_item}-{end_item} de {total_items} resultados"

    def handle_page_click(page_number):
        if isinstance(page_number, int) and page_number != current_page:
            on_page_change(page_number)

    return html.nav(
        {"class_name": "pagination-container", "aria-label": "Paginación"},
        html.span({"class_name": "pagination-summary"}, summary),
        html.ul(
            {"class_name": "pagination-controls"},
            # Botón Anterior
            html.li(
                html.a(
                    {
                        "href": "#",
                        "on_click": lambda e: handle_page_click(current_page - 1),
                        "aria-disabled": str(current_page == 1).lower(),
                        "aria-label": "Página anterior",
                        "class_name": "secondary" if current_page == 1 else "",
                    },
                    "‹",
                )
            ),
            # Números de Página
            *[
                html.li(
                    html.a(
                        {
                            "href": "#",
                            "on_click": (lambda p: lambda e: handle_page_click(p))(page)
                            if isinstance(page, int)
                            else None,
                            "aria-current": "page" if page == current_page else None,
                            "style": {"cursor": "default", "pointerEvents": "none"}
                            if not isinstance(page, int)
                            else {},
                            "aria-label": f"Ir a página {page}" if isinstance(page, int) else None,
                            "class_name": (
                                "primary"
                                if page == current_page
                                else "secondary outline"
                                if isinstance(page, int)
                                else ""
                            ),
                        },
                        "…" if page == "..." else str(page),  # text inside <a>
                    )
                )
                for page in page_numbers
            ],
            # Botón Siguiente
            html.li(
                html.a(
                    {
                        "href": "#",
                        "on_click": lambda e: handle_page_click(current_page + 1),
                        "aria-disabled": str(current_page == total_pages).lower(),
                        "aria-label": "Página siguiente",
                        "class_name": "secondary" if current_page == total_pages else "",
                    },
                    "›",
                )
            ),
        ),
    )


@component
def LoadingSpinner(size: str = "medium"):
    """Muestra un spinner de carga."""
    style = {}
    if size == "small":
        style = {"width": "1.5rem", "height": "1.5rem"}
    elif size == "large":
        style = {"width": "3rem", "height": "3rem"}
    # PicoCSS usa aria-busy="true" para mostrar el spinner
    return html.span({"aria-busy": "true", "style": style})


@component
def ErrorMessage(error: Optional[str]):
    """
    Muestra un mensaje de error en un 'article' de PicoCSS si el error no es None.
    """
    if not error:
        return None

    return html.article(
        {
            "style": {
                "backgroundColor": "var(--pico-color-red-200)",
                "borderColor": "var(--pico-color-red-600)",
                "color": "var(--pico-color-red-900)",
                "padding": "1em",
                "marginBottom": "1em",
            },
            "role": "alert",
        },
        html.strong("Error: "),
        str(error),
    )


@component
def ActionMenu(actions: List[dict]):
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
                        {"href": "#", "on_click": lambda e, action=action: action["on_click"](e)},
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
                "on_change": handle_change,
            }
        ),
        html.span({"class_name": "material-symbols-outlined"}, "dark_mode"),
    )


@component
def ConfirmationModal(is_open: bool, title: str, message: str, on_confirm: Callable, on_cancel: Callable):
    """Un modal genérico para solicitar confirmación del usuario."""
    if not is_open:
        return None

    async def handle_confirm(_event):  # ← async
        await on_confirm()

    return html.dialog(
        {"open": True},
        html.article(
            html.header(
                html.button({"aria-label": "Close", "rel": "prev", "on_click": lambda e: on_cancel()}),
                html.h3(title),
            ),
            html.p(message),
            html.footer(
                html.div(
                    {"class_name": "grid"},
                    html.button({"class_name": "secondary", "on_click": lambda e: on_cancel()}, "Cancelar"),
                    html.button(
                        {
                            "style": {
                                "backgroundColor": "var(--pico-color-pink-550)",
                                "borderColor": "var(--pico-color-pink-550)",
                            },
                            "on_click": handle_confirm,
                        },
                        "Confirmar",
                    ),
                ),
            ),
        ),
    )


@component
def HeaderNav(theme_is_dark: bool, on_theme_toggle, robots_state, equipos_state):
    """Header de navegación con botones de sincronización globales."""
    return html.header(
        {"class_name": "sticky-header"},
        html.div(
            {"class_name": "container"},
            html.nav(
                html.ul(
                    html.li(html.strong("SAM")),
                    html.li(link({"to": "/"}, "Robots")),
                    html.li(link({"to": "/equipos"}, "Equipos")),
                    html.li(link({"to": "/pools"}, "Pools")),
                    html.li(link({"to": "/programaciones"}, "Programaciones")),
                ),
                html.ul(
                    html.li(
                        html.button(
                            {
                                "on_click": robots_state.get("trigger_sync"),
                                "disabled": robots_state.get("is_syncing", False),
                                "aria-busy": str(robots_state.get("is_syncing", False)).lower(),
                                "class_name": "pico-background-fuchsia-500",
                                "data-tooltip": "Sincronizar Robots",
                                "data-placement": "bottom",
                            },
                            html.i({"class_name": "fa-solid fa-robot"}),
                        )
                    ),
                    html.li(
                        html.button(
                            {
                                "on_click": equipos_state.get("trigger_sync"),
                                "disabled": equipos_state.get("is_syncing", False),
                                "aria-busy": str(equipos_state.get("is_syncing", False)).lower(),
                                "class_name": "pico-background-purple-500",
                                "data-tooltip": "Sincronizar Equipos",
                                "data-placement": "bottom",
                            },
                            html.i({"class_name": "fa-solid fa-desktop"}),
                        )
                    ),
                    html.li(ThemeSwitcher(is_dark=theme_is_dark, on_toggle=on_theme_toggle)),
                ),
            ),
        ),
    )


@component
def PageWithLayout(theme_is_dark: bool, on_theme_toggle, robots_state, equipos_state, children):
    """Wrapper que incluye el header y la estructura principal en cada página."""
    return html._(
        HeaderNav(
            theme_is_dark=theme_is_dark,
            on_theme_toggle=on_theme_toggle,
            robots_state=robots_state,
            equipos_state=equipos_state,
        ),
        html.main({"class_name": "container"}, children),
    )
