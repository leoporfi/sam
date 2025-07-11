# src/interfaz_web/components/common/theme_switcher.py
from typing import Callable

from reactpy import component, html


@component
def ThemeSwitcher(is_dark: bool, on_toggle: Callable):
    """
    Un interruptor para cambiar entre el tema claro y oscuro.
    """

    def handle_change(event):
        on_toggle(event["target"]["checked"])

    return html.fieldset(
        html.label(
            html.input({"type": "checkbox", "role": "switch", "checked": is_dark, "onChange": handle_change}),
            "Tema Oscuro" if is_dark else "Tema Claro",
        )
    )
