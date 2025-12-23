from datetime import date, time
from typing import List, Optional, TypedDict

from pydantic import BaseModel, Field


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
    Parametros: Optional[str] = None  # JSON string con los parámetros de bot_input


class ScheduleData(BaseModel):
    RobotId: int
    TipoProgramacion: str = Field(..., max_length=50)
    HoraInicio: str
    Tolerancia: int
    Equipos: List[int]
    DiasSemana: Optional[str] = None
    DiaDelMes: Optional[int] = None
    FechaEspecifica: Optional[str] = None
    # Campos para RangoMensual
    DiaInicioMes: Optional[int] = None  # Día inicial del rango (1-31)
    DiaFinMes: Optional[int] = None  # Día final del rango (1-31)
    UltimosDiasMes: Optional[int] = None  # Últimos N días del mes (1-31)
    PrimerosDiasMes: Optional[int] = None  # Primeros N días del mes (1-31) - se mapea a DiaInicioMes=1, DiaFinMes=N


class ScheduleEditData(BaseModel):
    """
    Schema para editar una programación desde la página de Programaciones.
    NO requiere la lista de equipos.
    """

    TipoProgramacion: str = Field(..., max_length=50)
    HoraInicio: time
    DiasSemana: Optional[str] = Field(None, max_length=50)
    DiaDelMes: Optional[int] = None
    FechaEspecifica: Optional[date] = None
    Tolerancia: int
    Activo: bool
    # Campos para RangoMensual
    DiaInicioMes: Optional[int] = None
    DiaFinMes: Optional[int] = None
    UltimosDiasMes: Optional[int] = None
    PrimerosDiasMes: Optional[int] = None  # Se mapea a DiaInicioMes=1, DiaFinMes=N
    # (Nota: No incluimos 'Equipos' a propósito)


class AssignmentUpdateRequest(BaseModel):
    asignar_equipo_ids: List[int]
    desasignar_equipo_ids: List[int]


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
    Parametros: Optional[str]  # JSON string con los parámetros de bot_input
    CantidadEquiposAsignados: int


# Define la estructura de los filtros que usaremos en la API y el frontend
class RobotFilters(TypedDict, total=False):
    name: Optional[str]
    active: Optional[bool]
    online: Optional[bool]
    programado: Optional[bool]
    page: Optional[int]
    size: Optional[int]


class PoolCreate(BaseModel):
    Nombre: str
    Descripcion: Optional[str] = None


class PoolUpdate(BaseModel):
    Nombre: str
    Descripcion: Optional[str] = None


class PoolAssignmentsRequest(BaseModel):
    robot_ids: List[int]
    # RFR-34: Se estandariza el nombre del campo para que sea consistente.
    equipo_ids: List[int]


class Equipo(TypedDict):
    EquipoId: int
    Equipo: str
    UserName: Optional[str]
    Licencia: Optional[str]
    Activo_SAM: bool
    PermiteBalanceoDinamico: bool
    RobotAsignado: Optional[str]
    Pool: Optional[str]


class EquipoStatusUpdate(BaseModel):
    field: str
    value: bool


class EquipoCreateRequest(BaseModel):
    EquipoId: int = Field(..., gt=0, description="ID del equipo obtenido de A360")
    Equipo: str = Field(..., min_length=1, description="Nombre del host del equipo")
    UserId: int = Field(..., gt=0, description="ID del usuario asociado obtenido de A360")
    UserName: Optional[str] = Field(None, description="Nombre del usuario asociado (opcional)")
    Licencia: Optional[str] = Field(None, description="Tipo de licencia (opcional, ej: RUNTIME)")
    Activo_SAM: bool = 1
    PermiteBalanceoDinamico: bool = 0
    RobotAsignado: Optional[str] = None
    Pool: Optional[str] = None


# --- Schemas para Mapeo de Robots ---


class MapeoRobotCreate(BaseModel):
    Proveedor: str
    NombreExterno: str
    RobotId: int
    Descripcion: Optional[str] = None


class MapeoRobotUpdate(BaseModel):
    Proveedor: Optional[str] = None
    NombreExterno: Optional[str] = None
    RobotId: Optional[int] = None
    Descripcion: Optional[str] = None


class MapeoRobotResponse(MapeoRobotCreate):
    MapeoId: int
    RobotNombre: Optional[str] = None  # Para mostrar el nombre interno en la UI
