# interfaz_web/components/layout.py

from reactpy import component, html


@component
def Header():
    """
    El componente reutilizable para la cabecera de la aplicación.
    Basado en el diseño del dashboard.
    """
    return html.header(
        {"className": "flex items-center justify-between whitespace-nowrap border-b border-solid border-gray-200 bg-white px-6 py-4"},
        html.div(
            {"className": "flex items-center gap-10"},
            html.div(
                {"className": "flex items-center gap-3 text-gray-900"},
                html.div(
                    {"className": "size-7 text-blue-600"},
                    # Placeholder para el logo de SAM
                    html.div({"className": "w-7 h-7 bg-blue-600 rounded-full"}),
                ),
                html.h2({"className": "text-xl font-semibold"}, "SAM Project"),
            ),
            html.nav(
                {"className": "hidden md:flex items-center gap-8"},
                html.a({"href": "#", "className": "text-sm font-semibold text-blue-600 border-b-2 border-blue-600 pb-1"}, "Robots"),
                html.a({"href": "#", "className": "text-sm text-gray-500 hover:text-gray-900"}, "Teams"),
                html.a({"href": "#", "className": "text-sm text-gray-500 hover:text-gray-900"}, "Assignments"),
                html.a({"href": "#", "className": "text-sm text-gray-500 hover:text-gray-900"}, "Schedules"),
            ),
        ),
        html.div(
            {"className": "flex items-center gap-6"},
            # ... (resto de los elementos del header como la barra de búsqueda y el perfil)
        ),
    )


@component
def AppLayout(*children):
    """
    El layout principal de la aplicación. Incluye el <head> global y el Header.
    El contenido de la página se pasa como 'children'.
    """
    return html.div(
        # Definimos aquí el <head> para toda la aplicación
        html.head(
            html.meta({"char_set": "utf-8"}),
            html.title("SAM Project"),
            html.link({"crossorigin": "", "rel": "preconnect", "href": "https://fonts.gstatic.com/"}),
            html.link(
                {
                    "as": "style",
                    "rel": "stylesheet",
                    "href": "https://fonts.googleapis.com/css2?display=swap&amp;family=Inter%3Awght%40400%3B500%3B600%3B700%3B900&amp;family=Noto+Sans%3Awght%40400%3B500%3B700%3B900",
                    "onload": "this.rel='stylesheet'",
                }
            ),
            html.link({"rel": "stylesheet", "href": "https://fonts.googleapis.com/css2?family=Material+Icons"}),
            html.script({"src": "https://cdn.tailwindcss.com?plugins=forms,container-queries"}),
            html.link({"rel": "stylesheet", "href": "/static/styles.css"}),
        ),
        html.div(
            {"className": "bg-gray-50 min-h-screen"},
            Header(),
            html.main(
                {"className": "px-8 py-8"},
                # Aquí se insertará el contenido de la página (ej. RobotDashboard)
                *children,
            ),
        ),
    )
