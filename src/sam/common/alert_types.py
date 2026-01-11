from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AlertLevel(Enum):
    """Nivel de severidad de la alerta."""

    CRITICAL = "CRITICAL"  # Requiere acción inmediata (minutos)
    HIGH = "HIGH"  # Requiere acción pronto (horas)
    MEDIUM = "MEDIUM"  # Monitorear, actuar si persiste (días)


class AlertScope(Enum):
    """Alcance del problema reportado."""

    SYSTEM = "SYSTEM"  # Afecta capacidad global de ejecución
    ROBOT = "ROBOT"  # Específico de un robot
    DEVICE = "DEVICE"  # Específico de un equipo


class AlertType(Enum):
    """Naturaleza del problema."""

    PERMANENT = "PERMANENT"  # Error de configuración, requiere corrección manual
    TRANSIENT = "TRANSIENT"  # Temporal (red, offline), se autocorrige
    THRESHOLD = "THRESHOLD"  # Acumulación de eventos que superó umbral
    RECOVERY = "RECOVERY"  # Proceso de recuperación en curso


@dataclass
class AlertContext:
    """Contexto estructurado para una alerta."""

    alert_level: AlertLevel
    alert_scope: AlertScope
    alert_type: AlertType
    subject: str
    summary: str  # Resumen ejecutivo (1 línea qué pasó + 1 línea impacto)
    technical_details: Dict[str, Any]  # Datos estructurados (IDs, nombres, errores)
    actions: List[str]  # Lista ordenada de acciones requeridas
    frequency_info: Optional[str] = None  # Información sobre recurrencia


@dataclass
class ServerErrorPattern:
    """Estructura para trackear errores de servidor (5xx)."""

    status_code: int
    timestamp: datetime
