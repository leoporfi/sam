# src/interfaz_web/components/layout.py
from reactpy import component, html, use_state


@component
def AppLayout(*children):
    """
    Layout principal, ahora solo se preocupa por la estructura visual.
    """
    return html.section(
        {"className": "section"},
        html.div(
            {"className": "container"},
            Header(),
            html.main(*children),
        ),
    )


@component
def Header():
    """
    Componente Header refactorizado con Bulma y preparado para tema oscuro.
    """
    is_active, set_is_active = use_state(False)
    navbar_menu_class = f"navbar-menu {'is-active' if is_active else ''}"

    return html.nav(
        # La clase 'is-dark' adapta el navbar al tema oscuro
        {"className": "navbar", "role": "navigation", "aria-label": "main navigation"},
        html.div(
            {"className": "navbar-brand"},
            html.a(
                {"className": "navbar-item"},
                # Placeholder para el logo
                # html.div({"className": "box has-background-info", "style": {"width": "28px", "height": "28px", "padding": "0"}}),
                html.h2({"className": "title is-1"}, "SAM"),
            ),
            # html.a(
            #     {
            #         "role": "button",
            #         "className": f"navbar-burger {'is-active' if is_active else ''}",
            #         "aria-label": "menu",
            #         "aria-expanded": "false",
            #         "onClick": lambda e: set_is_active(not is_active),
            #     },
            #     html.span(),
            #     html.span(),
            #     html.span(),
            #     html.span(),  # Spans para el ícono de hamburguesa
            # ),
        ),
        # html.div(
        #     {"className": navbar_menu_class},
        #     html.div(
        #         {"className": "navbar-start"},
        #         html.a({"className": "navbar-item is-active"}, "Robots"),
        #         html.a({"className": "navbar-item"}, "Equipos"),
        #         html.a({"className": "navbar-item"}, "Asignaciones"),
        #         html.a({"className": "navbar-item"}, "Programaciones"),
        #     ),
        # ),
    )
