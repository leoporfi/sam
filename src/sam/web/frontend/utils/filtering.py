# sam/web/frontend/utils/filtering.py
"""
Funciones puras para filtrado y transformación de datos.

Este módulo contiene funciones puras (sin efectos secundarios) que facilitan
el testing unitario y la separación de responsabilidades, siguiendo la Guía
General de SAM.

Todas las funciones en este módulo son:
- Puras: no modifican los datos de entrada
- Determinísticas: mismo input = mismo output
- Sin dependencias de I/O: no hacen llamadas a API ni acceso a archivos
- Testeables: fáciles de testear unitariamente
"""

from typing import Any, Callable, Dict, List, Optional


def filter_robots_by_pool(robots: List[Dict[str, Any]], pool_name: Optional[str]) -> List[Dict[str, Any]]:
    """
    Filtra robots por nombre de pool.

    Args:
        robots: Lista de diccionarios con datos de robots
        pool_name: Nombre del pool a filtrar (None = no filtrar)

    Returns:
        Lista filtrada de robots. Si pool_name es None, retorna todos los robots.
    """
    if pool_name is None:
        return robots
    return [robot for robot in robots if robot.get("Pool") == pool_name]


def filter_robots_by_status(
    robots: List[Dict[str, Any]],
    active: Optional[bool] = None,
    online: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """
    Filtra robots por estado (activo/online).

    Args:
        robots: Lista de diccionarios con datos de robots
        active: Si True, solo robots activos; si False, solo inactivos; None = todos
        online: Si True, solo robots online; si False, solo offline; None = todos

    Returns:
        Lista filtrada de robots
    """
    filtered = robots

    if active is not None:
        filtered = [r for r in filtered if r.get("Activo") == active]

    if online is not None:
        filtered = [r for r in filtered if r.get("EsOnline") == online]

    return filtered


def filter_robots_by_name(robots: List[Dict[str, Any]], search_term: Optional[str]) -> List[Dict[str, Any]]:
    """
    Filtra robots por nombre (búsqueda parcial case-insensitive).

    Args:
        robots: Lista de diccionarios con datos de robots
        search_term: Término de búsqueda (None o vacío = no filtrar)

    Returns:
        Lista filtrada de robots cuyo nombre contiene el término de búsqueda
    """
    if not search_term:
        return robots

    search_lower = search_term.lower().strip()
    return [
        robot
        for robot in robots
        if search_lower in robot.get("Robot", "").lower() or search_lower in robot.get("Nombre", "").lower()
    ]


def filter_equipos_by_status(
    equipos: List[Dict[str, Any]],
    active: Optional[bool] = None,
    balanceable: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """
    Filtra equipos por estado.

    Args:
        equipos: Lista de diccionarios con datos de equipos
        active: Si True, solo equipos activos; si False, solo inactivos; None = todos
        balanceable: Si True, solo balanceables; si False, solo no balanceables; None = todos

    Returns:
        Lista filtrada de equipos
    """
    filtered = equipos

    if active is not None:
        filtered = [e for e in filtered if e.get("Activo") == active]

    if balanceable is not None:
        filtered = [e for e in filtered if e.get("PermiteBalanceoDinamico") == balanceable]

    return filtered


def filter_equipos_by_name(equipos: List[Dict[str, Any]], search_term: Optional[str]) -> List[Dict[str, Any]]:
    """
    Filtra equipos por nombre (búsqueda parcial case-insensitive).

    Args:
        equipos: Lista de diccionarios con datos de equipos
        search_term: Término de búsqueda (None o vacío = no filtrar)

    Returns:
        Lista filtrada de equipos cuyo nombre contiene el término de búsqueda
    """
    if not search_term:
        return equipos

    search_lower = search_term.lower().strip()
    return [
        equipo
        for equipo in equipos
        if search_lower in equipo.get("Equipo", "").lower() or search_lower in equipo.get("Nombre", "").lower()
    ]


def filter_schedules_by_robot(schedules: List[Dict[str, Any]], robot_id: Optional[int]) -> List[Dict[str, Any]]:
    """
    Filtra programaciones por ID de robot.

    Args:
        schedules: Lista de diccionarios con datos de programaciones
        robot_id: ID del robot a filtrar (None = no filtrar)

    Returns:
        Lista filtrada de programaciones
    """
    if robot_id is None:
        return schedules
    return [s for s in schedules if s.get("RobotId") == robot_id]


def filter_schedules_by_type(schedules: List[Dict[str, Any]], tipo: Optional[str]) -> List[Dict[str, Any]]:
    """
    Filtra programaciones por tipo.

    Args:
        schedules: Lista de diccionarios con datos de programaciones
        tipo: Tipo de programación ("Diaria", "Semanal", "Mensual", etc.) o None para no filtrar

    Returns:
        Lista filtrada de programaciones
    """
    if tipo is None:
        return schedules
    return [s for s in schedules if s.get("TipoProgramacion") == tipo]


def filter_schedules_by_active(schedules: List[Dict[str, Any]], active: Optional[bool]) -> List[Dict[str, Any]]:
    """
    Filtra programaciones por estado activo.

    Args:
        schedules: Lista de diccionarios con datos de programaciones
        active: Si True, solo activas; si False, solo inactivas; None = todas

    Returns:
        Lista filtrada de programaciones
    """
    if active is None:
        return schedules
    return [s for s in schedules if s.get("Activo") == active]


def filter_schedules_by_search(schedules: List[Dict[str, Any]], search_term: Optional[str]) -> List[Dict[str, Any]]:
    """
    Filtra programaciones por término de búsqueda (busca en nombre de robot y detalles).

    Args:
        schedules: Lista de diccionarios con datos de programaciones
        search_term: Término de búsqueda (None o vacío = no filtrar)

    Returns:
        Lista filtrada de programaciones
    """
    if not search_term:
        return schedules

    search_lower = search_term.lower().strip()
    return [
        s
        for s in schedules
        if search_lower in s.get("RobotNombre", "").lower()
        or search_lower in s.get("Robot", "").lower()
        or search_lower in str(s.get("TipoProgramacion", "")).lower()
    ]


def sort_data(
    data: List[Dict[str, Any]],
    sort_by: str,
    sort_dir: str = "asc",
    key_mapping: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Ordena una lista de diccionarios por una clave específica.

    Args:
        data: Lista de diccionarios a ordenar
        sort_by: Clave del diccionario por la que ordenar
        sort_dir: Dirección de ordenamiento ("asc" o "desc")
        key_mapping: Diccionario opcional con funciones de transformación para claves específicas.
                    Ejemplo: {"Robot": lambda x: x.get("Robot", "").lower()}

    Returns:
        Lista ordenada (nueva lista, no modifica la original)
    """
    if not data:
        return []

    # Crear copia para no modificar la original
    sorted_data = data.copy()

    # Función de extracción de valor
    def get_sort_value(item: Dict[str, Any]) -> Any:
        value = item.get(sort_by)
        # Si hay una función de transformación para esta clave, usarla
        if key_mapping and sort_by in key_mapping:
            return key_mapping[sort_by](item)
        # Manejar None colocándolo al final
        if value is None:
            return "" if sort_dir == "asc" else "zzz"
        return value

    # Ordenar
    reverse = sort_dir.lower() == "desc"
    sorted_data.sort(key=get_sort_value, reverse=reverse)

    return sorted_data


def normalize_boolean(value: Any) -> bool:
    """
    Normaliza un valor a booleano.

    Convierte valores como None, 0, 1, "0", "1", "true", "false" a booleano.

    Args:
        value: Valor a normalizar

    Returns:
        Valor booleano normalizado
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        value_lower = value.lower().strip()
        if value_lower in ("true", "1", "yes", "si", "sí"):
            return True
        if value_lower in ("false", "0", "no"):
            return False
        # Si no coincide con ningún patrón conocido, convertir a bool
        return bool(value)
    return bool(value)
