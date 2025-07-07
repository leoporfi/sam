# interfaz_web/components/notifications.py
import asyncio
from typing import Callable

from reactpy import component, create_context, html, use_context, use_effect

# El contexto no cambia, es lógica pura.
NotificationContext = create_context(None)


@component
def Toast(message: str, style: str, on_dismiss: Callable):
    # La lógica para auto-descartar la notificación se mantiene.
    async def dismiss_after_delay():
        await asyncio.sleep(5)
        # Usamos un try-except en caso de que el componente se desmonte antes.
        try:
            on_dismiss()
        except Exception:
            pass  # El componente ya no existe, no hay nada que hacer.

    use_effect(dismiss_after_delay, [])

    # Mapeamos el 'style' a las clases de color de Bulma.
    # 'is-light' da un fondo de color suave que se ve muy bien.
    color_class = "is-success" if style == "success" else "is-danger"

    return html.div(
        # Usamos el componente 'notification' de Bulma.
        {"className": f"notification {color_class} is-light"},
        # Bulma incluye un botón de cierre estándar con la clase 'delete'.
        html.button({"className": "delete", "onClick": on_dismiss}),
        # El mensaje se muestra directamente dentro del div.
        message,
    )


@component
def ToastContainer():
    notification_ctx = use_context(NotificationContext)
    if not notification_ctx:
        return None

    notifications = notification_ctx["notifications"]
    dismiss_notification = notification_ctx["dismiss_notification"]

    return html.div(
        # Usamos nuestra clase CSS personalizada para el posicionamiento.
        {"className": "toast-container"},
        html.div(
            {"className": "space-y-4"},  # Esta clase ya no existe, pero Bulma espaciará bien.
            [
                Toast(
                    key=n["id"],
                    message=n["message"],
                    style=n["style"],
                    on_dismiss=lambda event=None, nid=n["id"]: dismiss_notification(nid),
                )
                for n in notifications
            ],
        ),
    )
