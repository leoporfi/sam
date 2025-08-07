from typing import Callable

from reactpy import component, html

from .common_components import ThemeSwitcher


@component
def AppLayout(children, theme_is_dark: bool, on_theme_toggle: Callable):
    """
    Layout principal que ahora recibe y pasa los props del tema.
    """
    return html._(
        Header(theme_is_dark=theme_is_dark, on_theme_toggle=on_theme_toggle),
        html.main(
            {"className": "container"},
            *children,
        ),
    )


@component
def Header(theme_is_dark: bool, on_theme_toggle: Callable):
    """
    Header que ahora recibe los props y renderiza el ThemeSwitcher.
    """
    return html.header(
        {"className": "container"},
        html.a({"aria-label": "SAM", "data-discover": "true", "href": "/"}),
        html.nav(
            # Lado izquierdo: Logo y Links
            html.ul(
                html.li(html.strong(html.a({"href": "/", "className": "contrast"}, "SAM"))),
                html.li(html.a({"href": "/pools", "className": "secondary"}, "Pools")),
                # html.li(html.a({"href": "#"}, "Robots")),
                # html.li(html.a({"href": "#", "className": "secondary"}, "Equipos")),
                # html.li(html.a({"href": "#", "className": "secondary"}, "Asignaciones")),
                # html.li(html.a({"href": "#", "className": "secondary"}, "Programaciones")),
            ),
            # Lado derecho: Interruptor del tema
            html.ul(html.li(ThemeSwitcher(is_dark=theme_is_dark, on_toggle=on_theme_toggle))),
        ),
    )


@component
def Footer(): ...
