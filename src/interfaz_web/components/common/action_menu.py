# src/interfaz_web/components/common/action_menu.py
from typing import Callable, Dict, List

from reactpy import component, html, use_state


@component
def ActionMenu(actions: List[Dict[str, any]]):
    """
    Menú desplegable de acciones genérico.
    Ahora es más simple, solo llama a la función que recibe.
    """
    is_visible, set_is_visible = use_state(False)

    # El 'onClick' de cada botón ahora llamará directamente a la función 'async'
    # que le pasamos desde RobotRow, y ReactPy la ejecutará correctamente.

    # --- INICIO DE LA CORRECCIÓN ---
    # Ya no necesitamos la función 'handle_click' aquí.
    # --- FIN DE LA CORRECCIÓN ---

    return html.div(
        {"className": "relative inline-block text-left"},
        html.button(
            {
                "className": "inline-flex justify-center w-full rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50",
                "onClick": lambda event: set_is_visible(not is_visible),
            },
            "Acciones",
            html.span({"className": "-mr-1 ml-2 h-5 w-5"}, "▼"),
        ),
        html.div(
            {"className": f"origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-10 {'block' if is_visible else 'hidden'}"},
            html.div(
                {"className": "py-1", "role": "menu"},
                *[
                    html.button(
                        {
                            "key": action["label"],
                            "className": "block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100",
                            "role": "menuitem",
                            # Simplemente pasamos la función del prop 'on_click' directamente
                            "onClick": action["on_click"],
                        },
                        action["label"],
                    )
                    for action in actions
                ],
            ),
        ),
    )
