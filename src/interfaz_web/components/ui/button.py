# src/interfaz_web/components/ui/button.py
from reactpy import component, html

from ..styles import BUTTON_STYLES


@component
def Button(*children, on_click=None, variant="primary", type="button", disabled=False, **kwargs):
    """
    Un componente de botón reutilizable con variantes de estilo.
    """
    # Selecciona el estilo del diccionario basado en la variante
    style_classes = BUTTON_STYLES.get(variant, BUTTON_STYLES["primary"])

    props = kwargs.copy()
    props["className"] = f"{style_classes} {kwargs.get('className', '')}"
    props["onClick"] = on_click
    props["type"] = type
    props["disabled"] = disabled

    return html.button(props, *children)
