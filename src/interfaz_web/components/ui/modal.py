# src/interfaz_web/components/ui/modal.py
from reactpy import component, event, html


@component
def Modal(*children, title: str, on_close=None, is_visible: bool = False):
    """
    Un componente de esqueleto para modales. Muestra el fondo y el panel,
    y renderiza cualquier contenido que se le pase.
    """
    if not is_visible:
        return None

    def handle_overlay_click(event_data):
        # Cierra el modal solo si se hace clic en el fondo oscuro
        if event_data["target"] == event_data["currentTarget"] and on_close:
            on_close()

    return html.div(
        {"className": "fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4", "onClick": handle_overlay_click},
        html.div(
            {"className": "w-full max-w-2xl flex flex-col rounded-lg bg-white shadow-2xl", "onClick": event(lambda: None, stop_propagation=True)},
            # Cabecera del modal
            html.div({"className": "p-6 border-b border-gray-200"}, html.h2({"className": "text-2xl font-semibold text-gray-900"}, title)),
            # Contenido (aquí se insertará el formulario, etc.)
            html.div({"className": "flex-grow p-6 overflow-y-auto"}, *children),
        ),
    )
