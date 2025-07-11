# src/interfaz_web/schemas/programacion.py
from typing import List, Optional

from pydantic import BaseModel


class ScheduleData(BaseModel):
    RobotId: int
    TipoProgramacion: str
    HoraInicio: str
    Tolerancia: int
    Equipos: List[int]  # Lista de EquipoId
    DiasSemana: Optional[str] = None
    DiaDelMes: Optional[int] = None
    FechaEspecifica: Optional[str] = None
