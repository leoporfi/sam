# src/interfaz_web/types/robot_types.py
from typing import List, Optional, TypedDict


# Define la estructura de un objeto Robot
# Basado en lo que devuelve tu endpoint /api/robots
class Robot(TypedDict):
    RobotId: int
    Robot: str
    Descripcion: Optional[str]
    Activo: bool
    EsOnline: bool
    MinEquipos: int
    MaxEquipos: int
    PrioridadBalanceo: int
    TicketsPorEquipoAdicional: Optional[int]
    CantidadEquiposAsignados: int


# Define la estructura de los filtros que usaremos en la API y el frontend
class RobotFilters(TypedDict, total=False):
    name: Optional[str]
    active: Optional[bool]
    online: Optional[bool]
    page: Optional[int]
    size: Optional[int]


# (Opcional por ahora) Podemos añadir más tipos a medida que los necesitemos
class RobotUpdateData(TypedDict):
    # ... por definir
    pass
