# src/interfaz_web/components/ui/input.py
from reactpy import component, html

from ..styles import INPUT_STYLES


@component
def Input(type="text", value="", placeholder="", on_change=None, **kwargs):
    """
    Un componente de input de texto reutilizable.
    """
    print(type, value, on_change, kwargs)
    props = kwargs.copy()
    props["className"] = f"{INPUT_STYLES.get('default', '')} {kwargs.get('className', '')}"
    props["type"] = type
    props["onChange"] = on_change
    props["value"] = value
    props["placeholder"] = placeholder

    return html.input(props)
