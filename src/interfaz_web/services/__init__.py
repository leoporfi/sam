# src/interfaz_web/services/__init__.py
# Facilita la importación de los servicios desde otros módulos.

from .robot_service import (
    get_robots,
    update_robot_status,
    update_robot_details,
    create_robot
)
from .asignacion_service import (
    get_asignaciones_by_robot,
    update_asignaciones_robot
)
from .programacion_service import (
    get_schedules_for_robot,
    delete_schedule_full,
    create_new_schedule,
    update_existing_schedule
)
from .equipo_service import get_available_teams_for_robot

__all__ = [
    "get_robots",
    "update_robot_status",
    "update_robot_details",
    "create_robot",
    "get_asignaciones_by_robot",
    "update_asignaciones_robot",
    "get_schedules_for_robot",
    "delete_schedule_full",
    "create_new_schedule",
    "update_existing_schedule",
    "get_available_teams_for_robot"
]
