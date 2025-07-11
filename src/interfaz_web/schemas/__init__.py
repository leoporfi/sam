# src/interfaz_web/schemas/__init__.py
from .robot import RobotCreateRequest, RobotUpdateRequest
from .asignacion import AssignmentUpdateRequest
from .programacion import ScheduleData

__all__ = ["RobotCreateRequest", "RobotUpdateRequest", "AssignmentUpdateRequest", "ScheduleData"]
