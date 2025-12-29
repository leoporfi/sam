# sam/web/frontend/utils/__init__.py
"""Utilidades compartidas para el frontend."""

from .exceptions import APIException, ValidationException
from .filtering import (
    filter_equipos_by_name,
    filter_equipos_by_status,
    filter_robots_by_name,
    filter_robots_by_pool,
    filter_robots_by_status,
    filter_schedules_by_active,
    filter_schedules_by_robot,
    filter_schedules_by_search,
    filter_schedules_by_type,
    normalize_boolean,
    sort_data,
)
from .input_helpers import create_trimmed_handler, trim_text_input
from .validation import ValidationResult, validate_robot_data

__all__ = [
    # Excepciones
    "APIException",
    "ValidationException",
    # Filtrado (funciones puras)
    "filter_robots_by_pool",
    "filter_robots_by_status",
    "filter_robots_by_name",
    "filter_equipos_by_status",
    "filter_equipos_by_name",
    "filter_schedules_by_robot",
    "filter_schedules_by_type",
    "filter_schedules_by_active",
    "filter_schedules_by_search",
    "sort_data",
    "normalize_boolean",
    # Input helpers
    "trim_text_input",
    "create_trimmed_handler",
    # Validación
    "validate_robot_data",
    "ValidationResult",
]

