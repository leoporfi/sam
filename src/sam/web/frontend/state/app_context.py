# sam/web/frontend/state/app_context.py
"""
Contexto global de la aplicación para inyección de dependencias.

Este módulo proporciona un contexto ReactPy para compartir dependencias
globales como el cliente API, siguiendo el principio de Inyección de
Dependencias de la Guía General de SAM.

Uso:
    # En app.py (componente raíz)
    api_client = APIClient(base_url="http://127.0.0.1:8000")
    context_value = {
        "api_client": api_client,
        # ... otras dependencias
    }
    return AppContext(value=context_value, children=...)

    # En hooks o componentes
    from sam.web.frontend.state.app_context import use_app_context
    context = use_app_context()
    api_client = context["api_client"]
"""

from typing import Any, Dict

from reactpy import component, create_context, use_context

# Crear el contexto global
AppContext = create_context({})


# AppProvider no es necesario como componente separado
# En ReactPy, el contexto creado con create_context se puede usar directamente
# como componente: AppContext(value=context_value, children=...)


def use_app_context() -> Dict[str, Any]:
    """
    Hook para acceder al contexto global de la aplicación.

    Returns:
        Diccionario con las dependencias compartidas (ej: api_client)

    Raises:
        RuntimeError: Si se usa fuera de un AppContext provider
    """
    return use_context(AppContext)
