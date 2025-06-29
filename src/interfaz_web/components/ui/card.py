# src/interfaz_web/components/ui/card.py
from reactpy import component, html


@component
def Card(*children, **kwargs):
    """
    Un componente de tarjeta reutilizable con estilos por defecto.
    Acepta clases de CSS adicionales a través de `class_name`.
    """
    # Clases de CSS base para todas las tarjetas
    base_classes = "bg-white shadow-sm rounded-lg overflow-hidden"

    # Combina las clases base con cualquier clase adicional que se pase
    props = kwargs.copy()
    props["className"] = f"{base_classes} {kwargs.get('className', '')}"

    return html.div(props, *children)
