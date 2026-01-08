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
                {d.get("Equipo") or d.get("Nombre", "") for d in equipos if d.get("Equipo") or d.get("Nombre")}
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
            - Campos para robots cíclicos (EsCiclico, HoraFin, etc.)

    Returns:
        String descriptivo de los detalles de la programación
    """
    t = schedule.get("TipoProgramacion", "")
    detalles = []

    # Información básica según tipo
    if t == "Semanal":
        detalles.append(schedule.get("DiasSemana") or "-")
    elif t == "Mensual":
        dia = schedule.get("DiaDelMes")
        detalles.append(f"Día {dia}" if dia else "-")
    elif t == "RangoMensual":
        dia_inicio = schedule.get("DiaInicioMes")
        dia_fin = schedule.get("DiaFinMes")
        ultimos = schedule.get("UltimosDiasMes")

        # Últimos N días del mes
        if ultimos:
            detalles.append(f"Últimos {ultimos} día(s) del mes")
        # Rango específico
        elif dia_inicio and dia_fin:
            # Caso común de "primeros N días" (se mapea a 1..N)
            if dia_inicio == 1:
                detalles.append(f"Primeros {dia_fin} día(s) del mes")
            else:
                detalles.append(f"Del {dia_inicio} al {dia_fin} de cada mes")
        else:
            detalles.append("-")
    elif t == "Especifica":
        detalles.append(schedule.get("FechaEspecifica") or "-")
    else:
        detalles.append("-")  # Diaria no tiene detalles específicos aparte de la hora

    # Información adicional para robots cíclicos
    # Asegurar que EsCiclico sea un booleano (puede venir como None, 0, 1, True, False)
    es_ciclico = schedule.get("EsCiclico")
    if es_ciclico is None:
        es_ciclico = False
    elif isinstance(es_ciclico, (int, str)):
        es_ciclico = bool(int(es_ciclico)) if str(es_ciclico).isdigit() else bool(es_ciclico)
    else:
        es_ciclico = bool(es_ciclico)

    if es_ciclico:
        ciclico_info = []
        hora_fin = schedule.get("HoraFin")
        if hora_fin:
            hora_fin_str = format_time(hora_fin)
            hora_inicio = format_time(schedule.get("HoraInicio"))
            ciclico_info.append(f"{hora_inicio}-{hora_fin_str}")

        intervalo = schedule.get("IntervaloEntreEjecuciones")
        if intervalo:
            ciclico_info.append(f"Cada {intervalo} min")

        fecha_inicio = schedule.get("FechaInicioVentana")
        fecha_fin = schedule.get("FechaFinVentana")
        if fecha_inicio and fecha_fin:
            ciclico_info.append(f"{fecha_inicio} a {fecha_fin}")
        elif fecha_inicio:
            ciclico_info.append(f"Desde {fecha_inicio}")
        elif fecha_fin:
            ciclico_info.append(f"Hasta {fecha_fin}")

        if ciclico_info:
            detalles.append(f"[Cíclico: {', '.join(ciclico_info)}]")

    return " | ".join(detalles) if detalles else "-"


def format_minutes_to_hhmmss(minutes: Union[float, int, None]) -> str:
    """
    Convierte una cantidad de minutos a formato HH:MM:SS o Dd HH:MM:SS si supera las 24hs.
    Ejemplo:
        1.5 -> 00:01:30
        1500 -> 1d 01:00:00
    """
    if minutes is None:
        return "-"

    try:
        total_seconds = int(float(minutes) * 60)

        days = total_seconds // 86400
        remaining_seconds_after_days = total_seconds % 86400

        hours = remaining_seconds_after_days // 3600
        minutes_rem = (remaining_seconds_after_days % 3600) // 60
        seconds = remaining_seconds_after_days % 60

        if days > 0:
            return f"{days}d {hours:02d}:{minutes_rem:02d}:{seconds:02d}"
        else:
            return f"{hours:02d}:{minutes_rem:02d}:{seconds:02d}"
    except (ValueError, TypeError):
        return "-"
