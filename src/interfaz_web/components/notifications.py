# # interfaz_web/components/notifications.py
import asyncio
from typing import Callable

from reactpy import component, create_context, html, use_context, use_effect

# 1. El contexto ahora solo define la estructura de lo que compartiremos.
NotificationContext = create_context(None)


# 2. El componente Toast se mantiene igual (es solo visual).
@component
def Toast(message: str, style: str, on_dismiss: Callable):
    async def dismiss_after_delay():
        await asyncio.sleep(5)
        on_dismiss()

    use_effect(dismiss_after_delay, [])

    # icon_style = "h-6 w-6"
    # if style == "success":
    #     icon = html.svg(
    #         {"className": f"{icon_style} text-green-400", "fill": "none", "viewBox": "0 0 24 24", "stroke": "currentColor"},
    #         html.path({"stroke_linecap": "round", "stroke_linejoin": "round", "stroke_width": "2", "d": "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"}),
    #     )
    # else:  # error
    #     icon = html.svg(
    #         {"className": f"{icon_style} text-red-400", "fill": "none", "viewBox": "0 0 24 24", "stroke": "currentColor"},
    #         html.path({"stroke_linecap": "round", "stroke_linejoin": "round", "stroke_width": "2", "d": "M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"}),
    #     )

    if style == "success":
        icon = html.span({"className": "text-2xl"}, "✅")
    else:  # error
        icon = html.span({"className": "text-2xl"}, "❌")

    return html.div(
        {"className": "max-w-sm w-full bg-white shadow-lg rounded-lg pointer-events-auto ring-1 ring-black ring-opacity-5 overflow-hidden"},
        html.div(
            {"className": "p-4"},
            html.div(
                {"className": "flex items-start"},
                html.div({"className": "flex-shrink-0"}, icon),
                html.div({"className": "ml-3 w-0 flex-1 pt-0.5"}, html.p({"className": "text-sm font-medium text-gray-900"}, message)),
                html.div(
                    {"className": "ml-4 flex-shrink-0 flex"},
                    html.button({"className": "bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500", "onClick": on_dismiss}, "X"),
                ),
            ),
        ),
    )


# 3. El ToastContainer también se mantiene igual.
@component
def ToastContainer():
    notification_ctx = use_context(NotificationContext)
    # Si el contexto aún no está listo, no renderizar nada.
    if not notification_ctx:
        return None

    notifications = notification_ctx["notifications"]
    dismiss_notification = notification_ctx["dismiss_notification"]

    return html.div(
        {"className": "fixed inset-0 flex items-end justify-center px-4 py-6 pointer-events-none sm:p-6 sm:items-start sm:justify-end z-50"},
        html.div(
            {"className": "w-full max-w-sm space-y-4"},
            [Toast(key=n["id"], message=n["message"], style=n["style"], on_dismiss=lambda event=None, nid=n["id"]: dismiss_notification(nid)) for n in notifications],
        ),
    )
