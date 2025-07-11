# src/interfaz_web/schemas/robot.py
from typing import Optional

from pydantic import BaseModel


class RobotCreateRequest(BaseModel):
    RobotId: int
    Robot: str
    Descripcion: Optional[str] = None
    Activo: bool
    EsOnline: bool
    MinEquipos: int = -1
    MaxEquipos: int = 1
    PrioridadBalanceo: int = 100
    TicketsPorEquipoAdicional: Optional[int] = None


class RobotUpdateRequest(BaseModel):
    Robot: str
    Descripcion: Optional[str] = None
    MinEquipos: int
    MaxEquipos: int
    PrioridadBalanceo: int
    TicketsPorEquipoAdicional: Optional[int] = None
