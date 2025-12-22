# sam/web/frontend/shared/formatters.py
"""
Funciones de formateo compartidas para la aplicación SAM.

Este módulo contiene funciones reutilizables para formatear datos
como horas, listas de equipos y detalles de programaciones.
"""
from typing import Any, Dict, List, Optional, Union

from reactpy import html


def format_time(hora: Optional[str]) -> str:
    """
    Formatea la hora como HH:MM (sin segundos).

    Args:
        hora: String de hora en formato 'HH:MM' o 'HH:MM:SS', o None

    Returns:
        String formateado como 'HH:MM' o '-' si es None/vacío
    """
    if not hora:
        return "-"
    # Acepta formatos 'HH:MM' o 'HH:MM:SS' y se queda solo con los primeros 5 caracteres.
    return str(hora)[:5]


def format_equipos_list(
    equipos: Union[List[str], str, List[Dict], None],
    max_visible: int = 10,
    separator: str = ", ",
) -> Any:
    """
    Formatea una lista de equipos mostrando hasta max_visible elementos,
    con un indicador de cuántos más hay si excede el límite.

    Args:
        equipos: Puede ser:
            - Una lista de strings (nombres de equipos)
            - Un string separado por comas
            - Una lista de diccionarios con clave 'Equipo' o 'Nombre'
            - None
        max_visible: Número máximo de equipos a mostrar antes de truncar
        separator: Separador para unir los nombres (default: ", ")

    Returns:
        - html.span con tooltip si hay más de max_visible equipos
        - String con todos los equipos si hay max_visible o menos
        - "-" o "Ninguno" si la lista está vacía
    """
    # Normalizar entrada a lista de strings
    nombres: List[str] = []

    if not equipos:
        return "-"

    if isinstance(equipos, str):
        # Si es un string separado por comas, dividirlo
        nombres = sorted({name.strip() for name in equipos.split(",") if name.strip()})
    elif isinstance(equipos, list):
        if equipos and isinstance(equipos[0], dict):
            # Lista de diccionarios: extraer 'Equipo' o 'Nombre'
            nombres = sorted(
                {
                    d.get("Equipo") or d.get("Nombre", "")
                    for d in equipos
                    if d.get("Equipo") or d.get("Nombre")
                }
            )
        else:
            # Lista de strings
            nombres = sorted({str(name).strip() for name in equipos if str(name).strip()})

    if not nombres:
        return "Ninguno"

    total = len(nombres)
    full_text = separator.join(nombres)

    if total <= max_visible:
        return full_text

    # Truncar y mostrar indicador
    texto = separator.join(nombres[:max_visible]) + f" (+{total - max_visible} más)"
    return html.span({"title": full_text}, texto)


def format_schedule_details(schedule: Dict) -> str:
    """
    Formatea los detalles de una programación según su tipo.

    Args:
        schedule: Diccionario con datos de la programación que debe incluir:
            - TipoProgramacion: "Diaria", "Semanal", "Mensual", "RangoMensual", "Especifica"
            - Campos específicos según el tipo (DiasSemana, DiaDelMes, etc.)

    Returns:
        String descriptivo de los detalles de la programación
    """
    t = schedule.get("TipoProgramacion", "")
    if t == "Semanal":
        return schedule.get("DiasSemana") or "-"
    if t == "Mensual":
        dia = schedule.get("DiaDelMes")
        return f"Día {dia}" if dia else "-"
    if t == "RangoMensual":
        dia_inicio = schedule.get("DiaInicioMes")
        dia_fin = schedule.get("DiaFinMes")
        ultimos = schedule.get("UltimosDiasMes")

        # Últimos N días del mes
        if ultimos:
            return f"Últimos {ultimos} día(s) del mes"

        # Rango específico
        if dia_inicio and dia_fin:
            # Caso común de "primeros N días" (se mapea a 1..N)
            if dia_inicio == 1:
                return f"Primeros {dia_fin} día(s) del mes"
            return f"Del {dia_inicio} al {dia_fin} de cada mes"

        return "-"
    if t == "Especifica":
        return schedule.get("FechaEspecifica") or "-"
    return "-"  # Diaria no tiene detalles específicos aparte de la hora

