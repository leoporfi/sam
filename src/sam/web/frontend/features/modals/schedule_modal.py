import asyncio
from typing import Any, Callable, Dict

from reactpy import component, event, html, use_context, use_effect, use_memo, use_state

from sam.web.frontend.api.api_client import get_api_client
from sam.web.frontend.shared.common_components import ConfirmationModal, LoadingOverlay

from ...shared.notifications import NotificationContext

try:
    from .robots_modals import WeekdaySelector
except ImportError:
    # Fallback por si el componente no existe, aunque esto fallará en runtime si no se encuentra
    # En tu caso, 'robots_modals.py' sí existe.
    WeekdaySelector = None
    print("ADVERTENCIA: No se pudo importar WeekdaySelector desde robots_modals.py")


# -----------------------------------------------------------------------------
# FORMULARIO DE EDICIÓN COMPLETO
# -----------------------------------------------------------------------------
@component
def FullScheduleEditForm(form_data: Dict[str, Any], on_change: Callable):
    """
    Un formulario de edición completo que SÍ permite cambiar el TipoProgramacion
    y muestra/oculta los campos dinámicamente.
    """

    # Obtenemos el tipo actual para la lógica condicional
    tipo_actual = form_data.get("TipoProgramacion", "Diaria")

    # Estados para controlar la apertura de los acordeones
    is_general_open, set_general_open = use_state(True)
    is_cyclic_open, set_cyclic_open = use_state(form_data.get("EsCiclico", False))

    def handle_change(field, value):
        """Manejador de cambios que limpia campos al cambiar el tipo."""
        # Aplicar trim automático a campos de texto (excepto números y campos especiales)
        if isinstance(value, str) and field not in ["TipoProgramacion", "DiasSemana", "HoraInicio"]:
            value = value.strip()

        # FIX: Convertir cadenas vacías a None para campos de fecha/hora opcionales
        if field in ["FechaInicioVentana", "FechaFinVentana", "FechaEspecifica", "HoraFin"] and value == "":
            value = None

        new_form_data = {**form_data, field: value}

        if field == "TipoProgramacion":
            # Si cambiamos el tipo, reseteamos los campos específicos
            # para evitar enviar datos contradictorios (ej. DiasSemana para una 'Diaria')
            new_form_data["DiasSemana"] = None
            new_form_data["DiaDelMes"] = None
            new_form_data["FechaEspecifica"] = None
            new_form_data["DiaInicioMes"] = None
            new_form_data["DiaFinMes"] = None
            new_form_data["UltimosDiasMes"] = None
            new_form_data["PrimerosDiasMes"] = None

        if field == "EsCiclico" and not value:
            # Si se desactiva EsCiclico, limpiar campos relacionados
            new_form_data["HoraFin"] = None
            new_form_data["FechaInicioVentana"] = None
            new_form_data["FechaFinVentana"] = None
            new_form_data["IntervaloEntreEjecuciones"] = None

        on_change(new_form_data)

    return html.div(
        {"class_name": "full-schedule-edit-form"},
        # 1. Configuración General
        html.details(
            {"open": is_general_open},
            html.summary(
                {
                    "on_click": lambda e: set_general_open(not is_general_open),
                    "style": {"fontWeight": "bold", "cursor": "pointer", "marginBottom": "0.5rem"},
                },
                "Configuración General",
            ),
            html.div(
                {"style": {"padding": "1rem 0", "borderTop": "1px solid var(--pico-muted-border-color)"}},
                # Fila 1: Tipo de Programación
                html.label(
                    "Tipo de Programación",
                    html.select(
                        {
                            "value": tipo_actual,
                            "on_change": lambda e: handle_change("TipoProgramacion", e["target"]["value"]),
                        },
                        html.option({"value": "Diaria"}, "Diaria"),
                        html.option({"value": "Semanal"}, "Semanal"),
                        html.option({"value": "Mensual"}, "Mensual"),
                        html.option({"value": "RangoMensual"}, "Rango Mensual"),
                        html.option({"value": "Especifica"}, "Específica"),
                    ),
                ),
                # Fila 2: Hora y Tolerancia (siempre visibles)
                html.div(
                    {"class_name": "grid"},
                    html.label(
                        "Hora de Inicio (HH:MM)",
                        html.input(
                            {
                                "type": "time",
                                "value": form_data.get("HoraInicio") or "00:00",
                                "on_change": lambda e: handle_change("HoraInicio", e["target"]["value"]),
                            }
                        ),
                    ),
                    html.label(
                        "Tolerancia (minutos)",
                        html.input(
                            {
                                "type": "number",
                                "value": form_data.get("Tolerancia") or 30,
                                "min": 0,
                                "max": 1440,
                                "on_change": lambda e: handle_change("Tolerancia", int(e["target"]["value"] or 0)),
                            }
                        ),
                    ),
                ),
                # Fila 3: Campos Condicionales
                # Si es Semanal
                html.label(
                    "Días de la Semana (ej. Lu,Ma,Mi,Ju,Vi)",
                    WeekdaySelector(
                        # El valor es el string "Lu,Ma,Vi"
                        value=form_data.get("DiasSemana") or "",
                        # El on_change nos devuelve el nuevo string
                        on_change=lambda new_days_str: handle_change("DiasSemana", new_days_str),
                    ),
                )
                if (tipo_actual == "Semanal" and WeekdaySelector)  # Usar solo si se importó con éxito
                # Fallback al input de texto si WeekdaySelector no se pudo importar
                else html.label(
                    "Días de la Semana (ej. Lu,Ma,Mi,Ju,Vi)",
                    html.input(
                        {
                            "type": "text",
                            "value": form_data.get("DiasSemana") or "",
                            "placeholder": "Lu,Ma,Mi,Ju,Vi",
                            "on_change": lambda e: handle_change("DiasSemana", e["target"]["value"]),
                        }
                    ),
                )
                if (tipo_actual == "Semanal")
                else None,
                # Si es Mensual
                html.label(
                    "Día del Mes",
                    html.input(
                        {
                            "type": "number",
                            "value": form_data.get("DiaDelMes") or 1,
                            "min": 1,
                            "max": 31,
                            "on_change": lambda e: handle_change("DiaDelMes", int(e["target"]["value"] or 1)),
                        }
                    ),
                )
                if (tipo_actual == "Mensual")
                else None,
                # Si es RangoMensual
                html.div(
                    {"class_name": "rango-mensual-options"},
                    html.p(
                        {"style": {"fontSize": "0.9em", "color": "var(--pico-muted-color)"}}, "Seleccione una opción:"
                    ),
                    html.label(
                        html.input(
                            {
                                "type": "radio",
                                "name": "rango-option",
                                "value": "rango",
                                "checked": form_data.get("DiaInicioMes") is not None
                                and form_data.get("DiaFinMes") is not None
                                and not form_data.get("PrimerosDiasMes")
                                and not form_data.get("UltimosDiasMes"),
                                "on_change": lambda e: handle_change("rango_option", "rango"),
                            }
                        ),
                        " Rango específico (ej: del 1 al 10)",
                    ),
                    html.div(
                        {"class_name": "grid", "style": {"display": "flex", "gap": "1rem"}},
                        html.label(
                            "Día Inicio",
                            html.input(
                                {
                                    "type": "number",
                                    "value": form_data.get("DiaInicioMes") or "",
                                    "min": 1,
                                    "max": 31,
                                    "placeholder": "1",
                                    "on_change": lambda e: handle_change(
                                        "DiaInicioMes", int(e["target"]["value"]) if e["target"]["value"] else None
                                    ),
                                }
                            ),
                        ),
                        html.label(
                            "Día Fin",
                            html.input(
                                {
                                    "type": "number",
                                    "value": form_data.get("DiaFinMes") or "",
                                    "min": 1,
                                    "max": 31,
                                    "placeholder": "10",
                                    "on_change": lambda e: handle_change(
                                        "DiaFinMes", int(e["target"]["value"]) if e["target"]["value"] else None
                                    ),
                                }
                            ),
                        ),
                    )
                    if (
                        form_data.get("rango_option") == "rango"
                        or (
                            form_data.get("DiaInicioMes") is not None
                            and form_data.get("DiaFinMes") is not None
                            and not form_data.get("PrimerosDiasMes")
                            and not form_data.get("UltimosDiasMes")
                        )
                    )
                    else None,
                    html.label(
                        html.input(
                            {
                                "type": "radio",
                                "name": "rango-option",
                                "value": "primeros",
                                "checked": form_data.get("PrimerosDiasMes") is not None,
                                "on_change": lambda e: handle_change("rango_option", "primeros"),
                            }
                        ),
                        " Primeros N días del mes",
                    ),
                    html.label(
                        "Cantidad de días",
                        html.input(
                            {
                                "type": "number",
                                "value": form_data.get("PrimerosDiasMes") or "",
                                "min": 1,
                                "max": 31,
                                "placeholder": "10",
                                "on_change": lambda e: handle_change(
                                    "PrimerosDiasMes", int(e["target"]["value"]) if e["target"]["value"] else None
                                ),
                            }
                        ),
                    )
                    if (form_data.get("rango_option") == "primeros" or form_data.get("PrimerosDiasMes") is not None)
                    else None,
                    html.label(
                        html.input(
                            {
                                "type": "radio",
                                "name": "rango-option",
                                "value": "ultimos",
                                "checked": form_data.get("UltimosDiasMes") is not None,
                                "on_change": lambda e: handle_change("rango_option", "ultimos"),
                            }
                        ),
                        " Últimos N días del mes",
                    ),
                    html.label(
                        "Cantidad de días",
                        html.input(
                            {
                                "type": "number",
                                "value": form_data.get("UltimosDiasMes") or "",
                                "min": 1,
                                "max": 31,
                                "placeholder": "5",
                                "on_change": lambda e: handle_change(
                                    "UltimosDiasMes", int(e["target"]["value"]) if e["target"]["value"] else None
                                ),
                            }
                        ),
                    )
                    if (form_data.get("rango_option") == "ultimos" or form_data.get("UltimosDiasMes") is not None)
                    else None,
                )
                if tipo_actual == "RangoMensual"
                else None,
                # Si es Específica
                html.label(
                    "Fecha Específica",
                    html.input(
                        {
                            "type": "date",
                            "value": form_data.get("FechaEspecifica") or "",
                            "on_change": lambda e: handle_change("FechaEspecifica", e["target"]["value"]),
                        }
                    ),
                )
                if (tipo_actual == "Especifica")
                else None,
                # Fila 4: Toggle de Activo (Mover dentro de Configuración General)
                html.label(
                    html.input(
                        {
                            "type": "checkbox",
                            "role": "switch",
                            "checked": form_data.get("Activo", True),
                            "on_change": lambda e: handle_change("Activo", e["target"]["checked"]),
                        }
                    ),
                    " Programación Activa",
                ),
            ),
        ),
        # 2. Ejecución Cíclica
        html.details(
            {"open": is_cyclic_open},
            html.summary(
                {
                    "on_click": lambda e: set_cyclic_open(not is_cyclic_open),
                    "style": {"fontWeight": "bold", "cursor": "pointer", "marginBottom": "0.5rem"},
                },
                "Ejecución Cíclica",
            ),
            html.div(
                {"style": {"padding": "1rem 0", "borderTop": "1px solid var(--pico-muted-border-color)"}},
                html.label(
                    html.input(
                        {
                            "type": "checkbox",
                            "role": "switch",
                            "checked": form_data.get("EsCiclico", False),
                            "on_change": lambda e: handle_change("EsCiclico", e["target"]["checked"]),
                        }
                    ),
                    " Robot Cíclico (ejecución continua dentro de ventana)",
                ),
                html.div(
                    {
                        "style": {
                            "display": "block" if form_data.get("EsCiclico", False) else "none",
                            "marginTop": "1rem",
                        }
                    },
                    html.div(
                        {"class_name": "grid"},
                        html.label(
                            "Hora de Fin (HH:MM) *",
                            html.input(
                                {
                                    "type": "time",
                                    "value": (form_data.get("HoraFin") or "")[:5] if form_data.get("HoraFin") else "",
                                    "on_change": lambda e: handle_change("HoraFin", e["target"]["value"]),
                                    "required": form_data.get("EsCiclico", False),
                                }
                            ),
                        ),
                        html.label(
                            "Intervalo entre Ejecuciones (minutos) *",
                            html.input(
                                {
                                    "type": "number",
                                    "value": form_data.get("IntervaloEntreEjecuciones") or "",
                                    "min": 1,
                                    "max": 1440,
                                    "placeholder": "30",
                                    "on_change": lambda e: handle_change(
                                        "IntervaloEntreEjecuciones",
                                        int(e["target"]["value"]) if e["target"]["value"] else None,
                                    ),
                                }
                            ),
                        ),
                    ),
                    html.div(
                        {"class_name": "grid"},
                        html.label(
                            "Fecha Inicio Ventana",
                            html.input(
                                {
                                    "type": "date",
                                    "value": form_data.get("FechaInicioVentana") or "",
                                    "on_change": lambda e: handle_change("FechaInicioVentana", e["target"]["value"]),
                                }
                            ),
                        ),
                        html.label(
                            "Fecha Fin Ventana",
                            html.input(
                                {
                                    "type": "date",
                                    "value": form_data.get("FechaFinVentana") or "",
                                    "on_change": lambda e: handle_change("FechaFinVentana", e["target"]["value"]),
                                }
                            ),
                        ),
                    ),
                    html.small(
                        {"style": {"color": "var(--pico-muted-color)", "fontSize": "0.85em"}},
                        "💡 Los robots cíclicos se ejecutan continuamente dentro del rango horario y ventana de fechas especificados.",
                    ),
                ),
            ),
        ),
    )


# -----------------------------------------------------------------------------
# MODAL DE EDICIÓN
# -----------------------------------------------------------------------------
@component
def ScheduleEditModal(
    schedule_id: int,
    schedule: Dict,
    is_open: bool,
    on_close: Callable,
    on_save: Callable,
):
    """
    Modal para editar los detalles de una programación existente.
    """

    notification_context = use_context(NotificationContext)
    show_notification = notification_context["show_notification"]
    form_data, set_form_data = use_state(schedule)
    is_loading, set_is_loading = use_state(False)
    show_confirm, set_show_confirm = use_state(False)

    @use_effect(dependencies=[schedule])
    def sync_form_state():
        """Asegura que el formulario se resetee cada vez que 'schedule' (la prop) cambia."""
        if schedule:
            # Formatear HoraFin si viene como time object
            formatted_schedule = {**schedule}
            if formatted_schedule.get("HoraFin"):
                hora_fin = formatted_schedule["HoraFin"]
                if hasattr(hora_fin, "strftime"):
                    # Es un objeto time, convertir a string
                    formatted_schedule["HoraFin"] = hora_fin.strftime("%H:%M")
                elif isinstance(hora_fin, str) and len(hora_fin) > 5:
                    # Es un string con segundos, tomar solo HH:MM
                    formatted_schedule["HoraFin"] = hora_fin[:5]

            # Asegurar que EsCiclico sea un booleano (puede venir como None, 0, 1, True, False)
            es_ciclico = formatted_schedule.get("EsCiclico")
            if es_ciclico is None:
                formatted_schedule["EsCiclico"] = False
            elif isinstance(es_ciclico, (int, str)):
                # Convertir 0/1 o "0"/"1" a booleano
                formatted_schedule["EsCiclico"] = (
                    bool(int(es_ciclico)) if str(es_ciclico).isdigit() else bool(es_ciclico)
                )
            else:
                formatted_schedule["EsCiclico"] = bool(es_ciclico)

            set_form_data(formatted_schedule)

    def handle_save_click(e):
        """Muestra el diálogo de confirmación"""
        set_show_confirm(True)

    async def handle_confirm_save():
        """Ejecuta el guardado tras confirmar"""
        set_show_confirm(False)
        set_is_loading(True)
        try:
            tipo = form_data.get("TipoProgramacion")
            if tipo == "Semanal" and not form_data.get("DiasSemana"):
                raise ValueError("Para 'Semanal', los días de la semana son obligatorios.")
            if tipo == "Mensual" and not form_data.get("DiaDelMes"):
                raise ValueError("Para 'Mensual', el día del mes es obligatorio.")
            if tipo == "RangoMensual":
                has_rango = form_data.get("DiaInicioMes") and form_data.get("DiaFinMes")
                has_primeros = form_data.get("PrimerosDiasMes")
                has_ultimos = form_data.get("UltimosDiasMes")
                if not (has_rango or has_primeros or has_ultimos):
                    raise ValueError(
                        "Para 'Rango Mensual', debe especificar un rango, primeros N días, o últimos N días."
                    )
            if tipo == "Especifica" and not form_data.get("FechaEspecifica"):
                raise ValueError("Para 'Específica', la fecha es obligatoria.")

            # Validaciones para robots cíclicos
            if form_data.get("EsCiclico"):
                if not form_data.get("HoraFin"):
                    raise ValueError("Para robots cíclicos, la hora de fin es obligatoria.")

                hora_inicio = form_data.get("HoraInicio", "00:00")
                hora_fin = form_data.get("HoraFin")
                if hora_fin <= hora_inicio:
                    raise ValueError("La hora de fin debe ser mayor que la hora de inicio.")

                fecha_inicio = form_data.get("FechaInicioVentana")
                fecha_fin = form_data.get("FechaFinVentana")
                if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
                    raise ValueError("La fecha de inicio de ventana debe ser menor o igual a la fecha de fin.")

                intervalo = form_data.get("IntervaloEntreEjecuciones")
                if intervalo and intervalo < 1:
                    raise ValueError("El intervalo entre ejecuciones debe ser al menos 1 minuto si se especifica.")

            await on_save(form_data)
            show_notification("Programación actualizada con éxito.", "success")
            on_close()
        except Exception as ex:
            show_notification(f"Error al guardar: {ex}", "error")
        finally:
            set_is_loading(False)

    async def handle_submit(e):
        """Manejador del evento 'submit' del formulario."""
        set_is_loading(True)
        try:
            # Validación simple en el frontend
            tipo = form_data.get("TipoProgramacion")
            if tipo == "Semanal" and not form_data.get("DiasSemana"):
                raise ValueError("Para 'Semanal', los días de la semana son obligatorios.")
            if tipo == "Mensual" and not form_data.get("DiaDelMes"):
                raise ValueError("Para 'Mensual', el día del mes es obligatorio.")
            if tipo == "RangoMensual":
                has_rango = form_data.get("DiaInicioMes") and form_data.get("DiaFinMes")
                has_primeros = form_data.get("PrimerosDiasMes")
                has_ultimos = form_data.get("UltimosDiasMes")
                if not (has_rango or has_primeros or has_ultimos):
                    raise ValueError(
                        "Para 'Rango Mensual', debe especificar un rango, primeros N días, o últimos N días."
                    )
            if tipo == "Especifica" and not form_data.get("FechaEspecifica"):
                raise ValueError("Para 'Específica', la fecha es obligatoria.")

            # Validaciones para robots cíclicos
            if form_data.get("EsCiclico"):
                if not form_data.get("HoraFin"):
                    raise ValueError("Para robots cíclicos, la hora de fin es obligatoria.")

                hora_inicio = form_data.get("HoraInicio", "00:00")
                hora_fin = form_data.get("HoraFin")
                if hora_fin <= hora_inicio:
                    raise ValueError("La hora de fin debe ser mayor que la hora de inicio.")

                fecha_inicio = form_data.get("FechaInicioVentana")
                fecha_fin = form_data.get("FechaFinVentana")
                if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
                    raise ValueError("La fecha de inicio de ventana debe ser menor o igual a la fecha de fin.")

                intervalo = form_data.get("IntervaloEntreEjecuciones")
                if intervalo and intervalo < 1:
                    raise ValueError("El intervalo entre ejecuciones debe ser al menos 1 minuto si se especifica.")

            # Llamamos a la función 'on_save' (que viene del hook)
            # await on_save(schedule_id, form_data)
            await on_save(form_data)
            show_notification("Programación actualizada con éxito.", "success")
            on_close()
        except Exception as e:
            # Mostramos el error (ya sea de la validación de frontend o del backend)
            show_notification(f"Error al guardar: {e}", "error")
        finally:
            set_is_loading(False)

    if not is_open:
        return html.dialog({"open": False, "style": {"display": "none"}})

    return html._(
        html.dialog(
            {"open": True, "class_name": "modal-dialog"},
            html.article(
                {"style": {"position": "relative"}},
                html.header(
                    html.a(
                        {
                            "href": "#",
                            "aria-label": "Close",
                            "class_name": "close",
                            "on_click": event(lambda e: on_close(), prevent_default=True),
                            "style": {
                                "pointerEvents": "none" if is_loading else "auto",
                                "opacity": "0.5" if is_loading else "1",
                            },
                        }
                    ),
                    html.h3(f"Editar Programación: {schedule.get('RobotNombre', '')}"),
                ),
                html.form(
                    {"id": "edit-schedule-form", "on_submit": event(handle_submit, prevent_default=True)},
                    FullScheduleEditForm(form_data, set_form_data),
                ),
                LoadingOverlay(
                    is_loading=is_loading,
                    message="Guardando cambios, esto puede tardar unos segundos..." if is_loading else None,
                ),
                html.footer(
                    html.div(
                        {"class_name": "grid"},
                        html.button(
                            {
                                "type": "button",
                                "class_name": "secondary",
                                "on_click": event(lambda e: on_close(), prevent_default=True),
                                "disabled": is_loading,
                            },
                            "Cancelar",
                        ),
                        html.button(
                            {
                                "type": "button",
                                "on_click": event(handle_save_click, prevent_default=True),
                                "form": "edit-schedule-form",
                                "aria-busy": str(is_loading).lower(),
                                "disabled": is_loading,
                            },
                            "Procesando..." if is_loading else "Guardar Cambios",
                        ),
                    )
                ),
            ),
        ),
        ConfirmationModal(
            is_open=show_confirm,
            title="Confirmar Cambios",
            message=f"¿Estás seguro de que deseas guardar los cambios en la programación de '{schedule.get('RobotNombre', '')}'?",
            on_confirm=handle_confirm_save,
            on_cancel=lambda: set_show_confirm(False),
        )
        if show_confirm
        else None,
    )


# -----------------------------------------------------------------------------
# MODAL ASIGNACION
# -----------------------------------------------------------------------------
@component
def DeviceList(title, items, selected_ids_set, handle_selection, handle_select_all):
    # Estado local para búsqueda
    search_term, set_search_term = use_state("")

    # Filtrar items basado en el buscador local
    filtered_items = use_memo(
        lambda: [i for i in (items or []) if search_term.lower() in i.get("Nombre", "").lower()],
        [items, search_term],
    )

    are_all_selected = len(filtered_items) > 0 and all(i["ID"] in selected_ids_set for i in filtered_items)

    def get_estado(item: Dict) -> tuple[str, str, str]:
        """
        Determina el estado de un equipo para el modal de programaciones.
        Lógica idéntica a robots_modals.py para mantener consistencia visual.

        Args:
            item: Diccionario con información del equipo

        Returns:
            tuple[str, str, str]: (texto_estado, clase_css, tooltip)

        Nota: Esta función debe mantenerse sincronizada con la versión en robots_modals.py
        """
        es_programado = item.get("EsProgramado", False)
        es_reservado = item.get("Reservado", False)
        # Para detectar asignación dinámica, verificamos si tiene ID (está en lista de asignados)
        # o si tiene RobotId explícito
        tiene_asignacion = item.get("ID") is not None or item.get("RobotId") is not None

        if es_programado:
            return (
                "Programado",
                "tag-programado",
                "Compartible entre programaciones - Ya programado en otro lugar",
            )

        if es_reservado:
            return (
                "Reservado",
                "tag-reservado",
                "Reservado manualmente - No compartible",
            )

        if tiene_asignacion and not es_programado and not es_reservado:
            return (
                "Dinámico",
                "tag-dinamico",
                "Asignado automáticamente por el balanceador",
            )

        return (
            "Libre",
            "tag-libre",
            "Disponible para asignación a esta programación",
        )

    # Verificar si hay información de estado disponible
    has_status_column = items and len(items) > 0 and ("EsProgramado" in items[0] or "Reservado" in items[0])

    return html.div(
        {"class_name": "device-list-section"},  # Clase CSS original de SAM
        html.div(
            {"class_name": "device-list-header"},
            html.h5(title),
            html.input(
                {
                    "type": "search",
                    "name": "search-equipos",
                    "placeholder": "Filtrar equipos...",
                    "value": search_term,
                    "on_change": lambda e: set_search_term(e["target"]["value"].strip()),
                }
            ),
        ),
        html.div(
            # Esta clase es la clave para el scroll y el borde
            {"class_name": "device-list-table compact-assignment-table"},
            html.table(
                {"role": "grid"},
                html.thead(
                    html.tr(
                        html.th(
                            {"scope": "col", "style": {"width": "40px"}},
                            html.input(
                                {
                                    "type": "checkbox",
                                    "name": "checkbox-equipos",
                                    "checked": are_all_selected,
                                    "on_change": lambda e: handle_select_all(
                                        set(i["ID"] for i in filtered_items) if e["target"]["checked"] else set()
                                    ),
                                }
                            ),
                        ),
                        html.th({"scope": "col"}, "Nombre Equipo"),
                        html.th({"scope": "col", "style": {"width": "120px"}}, "Estado") if has_status_column else None,
                    )
                ),
                html.tbody(
                    *[
                        html.tr(
                            {"key": item["ID"]},
                            html.td(
                                html.input(
                                    {
                                        "type": "checkbox",
                                        "checked": item["ID"] in selected_ids_set,
                                        "on_change": lambda e, i_id=item["ID"]: handle_selection(i_id),
                                    }
                                )
                            ),
                            html.td(item["Nombre"]),
                            html.td(
                                html.span(
                                    {
                                        "class_name": f"tag {get_estado(item)[1]}",
                                        "title": get_estado(item)[2],  # Tooltip
                                    },
                                    get_estado(item)[0],  # Texto visible
                                )
                            )
                            if has_status_column
                            else None,
                        )
                        for item in filtered_items
                    ]
                    if filtered_items
                    else [
                        html.tr(
                            html.td(
                                {"colSpan": 3 if has_status_column else 2, "style": {"text-align": "center"}},
                                "Sin resultados",
                            )
                        )
                    ]
                ),
            ),
        ),
    )


@component
def ScheduleEquiposModal(
    schedule_id: int,
    schedule: Dict,
    is_open: bool,
    on_close: Callable,
    on_save: Callable,
):
    """
    Modal para asignar/desasignar equipos a una programación específica.
    """
    # Obtener api_client del contexto
    try:
        from ...state.app_context import use_app_context

        app_context = use_app_context()
        api = app_context.get("api_client") or get_api_client()
    except Exception:
        api = get_api_client()
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    is_loading, set_is_loading = use_state(False)
    show_confirm, set_show_confirm = use_state(False)

    # Listas de equipos
    available, set_available = use_state([])
    assigned, set_assigned = use_state([])

    # IDs seleccionados en cada lista
    selected_available_ids, set_selected_available_ids = use_state(set())
    selected_assigned_ids, set_selected_assigned_ids = use_state(set())

    modal_class = f"modal {'is-open' if is_open else ''}"

    @use_effect(dependencies=[schedule_id, is_open])
    def _load_assignments():
        if not schedule_id or not is_open:
            set_available([])
            set_assigned([])
            return

        set_is_loading(True)

        async def fetch():
            try:
                data = await api.get_schedule_devices(schedule_id)
                # Aseguramos orden alfabético inicial
                avail = sorted(data.get("available", []), key=lambda x: x["Nombre"].lower())
                asgn = sorted(data.get("assigned", []), key=lambda x: x["Nombre"].lower())

                set_available(avail)
                set_assigned(asgn)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                show_notification(f"Error al cargar equipos: {e}", "error")
            finally:
                if not asyncio.current_task().cancelled():
                    set_is_loading(False)

        task = asyncio.create_task(fetch())
        return lambda: task.cancel()

    # --- MÉTODOS AUXILIARES ---
    def handle_move(direction: str):
        """Mueve ítems entre las listas 'available' y 'assigned'."""
        if direction == "assign":
            to_move = [item for item in available if item["ID"] in selected_available_ids]
            # Filtrar y Reordenar
            new_available = sorted(
                [item for item in available if item["ID"] not in selected_available_ids],
                key=lambda x: x["Nombre"].lower(),
            )
            new_assigned = sorted(assigned + to_move, key=lambda x: x["Nombre"].lower())

            set_available(new_available)
            set_assigned(new_assigned)
            set_selected_available_ids(set())

        elif direction == "unassign":
            to_move = [item for item in assigned if item["ID"] in selected_assigned_ids]
            # Filtrar y Reordenar
            new_assigned = sorted(
                [item for item in assigned if item["ID"] not in selected_assigned_ids],
                key=lambda x: x["Nombre"].lower(),
            )
            new_available = sorted(available + to_move, key=lambda x: x["Nombre"].lower())

            set_assigned(new_assigned)
            set_available(new_available)
            set_selected_assigned_ids(set())

    def handle_save_click(e):
        """Muestra el diálogo de confirmación"""
        set_show_confirm(True)

    async def handle_confirm_save():
        """Ejecuta el guardado tras confirmar"""
        set_show_confirm(False)
        set_is_loading(True)
        assigned_ids = [item["ID"] for item in assigned]

        try:
            await on_save(schedule_id, assigned_ids)
            show_notification("Equipos actualizados con éxito.", "success")
            on_close()
        except Exception as e:
            show_notification(f"Error al guardar: {e}", "error")
        finally:
            set_is_loading(False)

    # Renderizado condicional para evitar hooks inconsistentes (Return final)
    if not schedule_id and not is_open:
        return html.div({"class_name": modal_class, "style": {"display": "none"}})

    return html._(
        html.dialog(  #
            {"class_name": modal_class, "open": is_open},
            html.article(
                html.header(
                    html.a(
                        {
                            "href": "#",
                            "aria-label": "Close",
                            "class_name": "close",
                            "on_click": event(lambda e: on_close(), prevent_default=True),
                        },
                    ),
                    html.h3(
                        f"Asignar Equipos - {schedule.get('RobotNombre', '')}"
                        if schedule.get("RobotNombre", "")
                        else f"Asignar Equipos (ID: {schedule_id})"
                    ),
                ),
                html.div(
                    {"style": {"marginBottom": "1rem", "fontSize": "0.9em", "color": "var(--pico-muted-color)"}},
                    html.span(
                        html.strong("ℹ️ Info: "),
                        "Los equipos asignados aquí se vincularán exclusivamente a esta programación cuando esté activa.",
                    ),
                ),
                # Contenido del modal con GRID de 3 columnas
                html.div(
                    {
                        "class_name": "grid",
                        "style": {
                            "gridTemplateColumns": "5fr 1fr 5fr",  # Columnas proporcionales
                            "alignItems": "center",
                            "gap": "1rem",
                            "height": "400px",  # Altura fija para que se vea uniforme
                        },
                    },
                    # Columna 1: Disponibles
                    DeviceList(
                        title="Equipos Disponibles",
                        items=available,
                        selected_ids_set=selected_available_ids,
                        handle_selection=lambda i: set_selected_available_ids(lambda s: (s ^ {i})),
                        handle_select_all=lambda new_set: set_selected_available_ids(new_set),
                    ),
                    # Columna 2: Botones Centrales
                    html.div(
                        {"style": {"display": "flex", "flexDirection": "column", "gap": "1rem"}},
                        html.button(
                            {
                                "on_click": lambda e: handle_move("assign"),
                                "disabled": not selected_available_ids,
                                "data-tooltip": "Asignar",
                            },
                            html.i({"class_name": "fa-solid fa-arrow-right"}),
                        ),
                        html.button(
                            {
                                "on_click": lambda e: handle_move("unassign"),
                                "disabled": not selected_assigned_ids,
                                "data-tooltip": "Quitar",
                            },
                            html.i({"class_name": "fa-solid fa-arrow-left"}),
                        ),
                    ),
                    # Columna 3: Asignados
                    DeviceList(
                        title="Equipos Asignados",
                        items=assigned,
                        selected_ids_set=selected_assigned_ids,
                        handle_selection=lambda i: set_selected_assigned_ids(lambda s: (s ^ {i})),
                        handle_select_all=lambda new_set: set_selected_assigned_ids(new_set),
                    ),
                ),
                # Pie del modal
                html.footer(
                    html.div(
                        {"class_name": "grid"},
                        html.button(
                            {"class_name": "secondary", "on_click": lambda e: on_close(), "disabled": is_loading},
                            "Cancelar",
                        ),
                        html.button(
                            {"on_click": handle_save_click, "aria-busy": is_loading, "disabled": is_loading},
                            "Guardar",
                        ),
                    ),
                ),
            ),
        ),
        ConfirmationModal(
            is_open=show_confirm,
            title="Confirmar Asignación",
            message=f"¿Estás seguro de que deseas actualizar los equipos asignados a '{schedule.get('RobotNombre', '')}'?",
            on_confirm=handle_confirm_save,
            on_cancel=lambda: set_show_confirm(False),
        )
        if show_confirm
        else None,
    )
