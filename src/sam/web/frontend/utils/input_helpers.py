# sam/web/frontend/utils/input_helpers.py
"""
Utilidades para manejo de inputs de texto.
Incluye funciones para hacer trim automático de espacios al inicio y final.
"""

from typing import Any, Callable, Optional


def trim_text_input(value: Any) -> str:
    """
    Hace trim (elimina espacios al inicio y final) de un valor de input de texto.
    
    Args:
        value: El valor del input (puede ser str, None, o cualquier otro tipo)
    
    Returns:
        str: El valor con trim aplicado, o cadena vacía si el valor es None/empty
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    # Si no es string, convertir a string y hacer trim
    return str(value).strip()


def create_trimmed_handler(original_handler: Callable, field_name: Optional[str] = None) -> Callable:
    """
    Crea un handler que aplica trim automáticamente antes de llamar al handler original.
    
    Args:
        original_handler: El handler original que se llamará después del trim
        field_name: Nombre del campo (opcional, para logging)
    
    Returns:
        Callable: Un nuevo handler que aplica trim y luego llama al original
    """
    def trimmed_handler(event_or_value: Any) -> Any:
        # Manejar tanto eventos como valores directos
        if isinstance(event_or_value, dict) and "target" in event_or_value:
            # Es un evento de ReactPy
            value = event_or_value["target"]["value"]
            trimmed_value = trim_text_input(value)
            # Actualizar el valor en el evento también
            event_or_value["target"]["value"] = trimmed_value
            return original_handler(event_or_value)
        else:
            # Es un valor directo
            trimmed_value = trim_text_input(event_or_value)
            return original_handler(trimmed_value)
    
    return trimmed_handler

