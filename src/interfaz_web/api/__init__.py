# src/interfaz_web/api/__init__.py
# Este archivo hace que el directorio 'api' sea un paquete de Python.

# Opcionalmente, puedes importar los routers aquí para facilitar el acceso
from .robots import router as robots_router
from .asignaciones import router as asignaciones_router
from .programaciones import router as programaciones_router
from .equipos import router as equipos_router

__all__ = ["robots_router", "asignaciones_router", "programaciones_router", "equipos_router"]
