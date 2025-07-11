# src/interfaz_web/components/common/action_menu.py
from typing import Callable, Dict, List

from reactpy import component, event, html


@component
def ActionMenu(actions: List[Dict[str, any]]):
    """
    Menú desplegable de acciones que usa la estructura <details> de Pico.css.
    Es semántico y no necesita estado para funcionar.
    """
    return html.details(
        # La clase 'dropdown' le da el estilo y posicionamiento correcto.
        {"className": "dropdown"},
        # Esto es lo que se ve siempre: el icono de 3 puntos.
        html.summary({"role": "button", "className": "outline"}, html.i({"className": "fas fa-ellipsis-v"})),
        # Esto es lo que se despliega.
        html.ul(
            {"role": "listbox"},
            *[
                html.li(html.a({"href": "#", "onClick": event(action["on_click"], prevent_default=True)}, html.small(action["label"])))
                for action in actions
            ],
        ),
    )
