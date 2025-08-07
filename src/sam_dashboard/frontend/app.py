# src/interfaz_web/app_component.py
import uuid

from reactpy import component, html, use_effect, use_state
from reactpy_router import browser_router, route

# Importamos los componentes de la UI
from .features.dashboard.components import RobotDashboard
from .features.pools.components import PoolsDashboard
from .shared.layout import AppLayout
from .shared.notifications import NotificationContext, ToastContainer


@component
def App():
    """
    Componente raíz de la aplicación ReactPy.
    Maneja el estado global como el tema (claro/oscuro) y las notificaciones.
    """
    notifications, set_notifications = use_state([])
    is_dark, set_is_dark = use_state(True)
    script_to_run, set_script_to_run = use_state(html._())

    @use_effect(dependencies=[is_dark])
    def apply_theme():
        theme = "dark" if is_dark else "light"
        key = f"theme-script-{uuid.uuid4()}"
        js_code = f"document.documentElement.setAttribute('data-theme', '{theme}')"
        set_script_to_run(html.script({"key": key}, js_code))

    # --- Lógica de notificaciones y tema
    def show_notification(message, style="success"):
        new_id = str(uuid.uuid4())
        set_notifications(lambda old: old + [{"id": new_id, "message": message, "style": style}])

    def dismiss_notification(notification_id):
        set_notifications(lambda old: [n for n in old if n["id"] != notification_id])

    context_value = {
        "notifications": notifications,
        "show_notification": show_notification,
        "dismiss_notification": dismiss_notification,
    }

    return NotificationContext(
        html._(
            script_to_run,
            # AppLayout(theme_is_dark=is_dark, on_theme_toggle=set_is_dark, children=[RobotDashboard()]),
            AppLayout(
                theme_is_dark=is_dark,
                on_theme_toggle=set_is_dark,
                children=[
                    # --- 2. El router define qué componente mostrar según la URL ---
                    browser_router(
                        route("/", RobotDashboard()), route("/pools", PoolsDashboard()), route("{404:any}", html.h1("Página no encontrada (404)"))
                    )
                ],
            ),
            ToastContainer(),
        ),
        value=context_value,
    )


# --- Elementos que inyectaremos en el <head> de la página ---
head = html.head(
    html.title("SAM"),
    html.meta({"charset": "utf-8"}),
    html.meta({"name": "viewport", "content": "width=device-width, initial-scale=1"}),
    html.link({"rel": "stylesheet", "href": "/static/css/pico.violet.min.css"}),
    html.link(
        # {"rel": "stylesheet", "href": "/static/css/pico.colors.min.cs"}
        {"rel": "stylesheet", "href": "https://cdn.jsdelivr.net/npm/@picocss/pico@2.1.1/css/pico.colors.min.css"}
    ),
    html.link({"rel": "stylesheet", "href": "/static/css/all.min.css"}),
    html.link({"rel": "stylesheet", "href": "/static/custom.css"}),
)
