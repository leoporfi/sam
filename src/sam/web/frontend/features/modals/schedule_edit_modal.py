from typing import Any, Callable, Dict

from reactpy import component, event, html, use_context, use_effect, use_state

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

    def handle_change(field, value):
        """Manejador de cambios que limpia campos al cambiar el tipo."""
        new_form_data = {**form_data, field: value}

        if field == "TipoProgramacion":
            # Si cambiamos el tipo, reseteamos los campos específicos
            # para evitar enviar datos contradictorios (ej. DiasSemana para una 'Diaria')
            new_form_data["DiasSemana"] = None
            new_form_data["DiaDelMes"] = None
            new_form_data["FechaEspecifica"] = None

        on_change(new_form_data)

    return html.div(
        {"class_name": "full-schedule-edit-form"},
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
        # Fila 4: Toggle de Activo
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
    on_save: Callable,  # Esta es la función 'save_schedule' del hook
):
    """
    Modal para editar los detalles de una programación existente.
    """

    notification_context = use_context(NotificationContext)
    show_notification = notification_context["show_notification"]
    form_data, set_form_data = use_state(schedule)
    is_loading, set_is_loading = use_state(False)

    @use_effect(dependencies=[schedule])
    def sync_form_data():
        """Asegura que el formulario se resetee cada vez que 'schedule' (la prop) cambia."""
        if schedule:
            set_form_data(schedule)

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
            if tipo == "Especifica" and not form_data.get("FechaEspecifica"):
                raise ValueError("Para 'Específica', la fecha es obligatoria.")

            # Llamamos a la función 'on_save' (que viene del hook)
            # await on_save(schedule_id, form_data)
            await on_save(form_data)
            show_notification("Programación actualizada con éxito.", "success")
            on_close()
        except Exception as ex:
            # Mostramos el error (ya sea de la validación de frontend o del backend)
            show_notification(f"Error al guardar: {ex}", "error")
        finally:
            set_is_loading(False)

    if not is_open:
        return None

    return html.dialog(
        {"open": True, "class_name": "modal-dialog"},
        html.article(
            html.header(
                html.a(
                    {
                        "href": "#",
                        "aria-label": "Close",
                        "class_name": "close",
                        "on_click": event(lambda e: on_close(), prevent_default=True),
                    }
                ),
                html.h3(f"Editar Programación: {schedule.get('RobotNombre', '')}"),
            ),
            html.form(
                {"id": "edit-schedule-form", "on_submit": event(handle_submit, prevent_default=True)},
                FullScheduleEditForm(form_data, set_form_data),
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
                            "type": "submit",
                            "form": "edit-schedule-form",
                            "aria-busy": str(is_loading).lower(),
                            "disabled": is_loading,
                        },
                        "Guardar Cambios",
                    ),
                )
            ),
        ),
    )
