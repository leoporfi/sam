# En: src/interfaz_web/components/ui/label.py

from reactpy import component, html

from ..styles import LABEL_STYLES


@component
def Label(*children, **kwargs):
    """
    Un componente de label reutilizable que acepta propiedades
    y cualquier número de hijos (el texto o contenido).
    """
    # Hacemos una copia para no modificar el diccionario original de kwargs
    props = kwargs.copy()

    # Obtenemos las clases base del diccionario de estilos
    base_classes = LABEL_STYLES.get("default", "")

    # Obtenemos cualquier clase adicional que se haya pasado en la llamada
    extra_classes = kwargs.get("className", "")

    # Combinamos las clases de forma segura
    props["className"] = f"{base_classes} {extra_classes}".strip()

    return html.label(props, *children)
