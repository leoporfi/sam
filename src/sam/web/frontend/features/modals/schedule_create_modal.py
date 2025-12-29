# sam/web/frontend/features/modals/schedule_create_modal.py
"""
Modal para crear una nueva programación.

Este modal permite crear programaciones con todos los tipos disponibles,
incluyendo el nuevo tipo RangoMensual con opciones de rangos de días.
"""

from typing import Any, Callable, Dict, List

from reactpy import component, event, html, use_context, use_effect, use_memo, use_state

from sam.web.frontend.shared.common_components import ConfirmationModal, LoadingOverlay

from ...shared.notifications import NotificationContext

try:
    from .robots_modals import WeekdaySelector
except ImportError:
    WeekdaySelector = None
    print("ADVERTENCIA: No se pudo importar WeekdaySelector desde robots_modals.py")


@component
def ScheduleCreateForm(form_data: Dict[str, Any], on_change: Callable, robots_list: List[Dict]):
    """
    Formulario completo para crear una nueva programación.
    """
    tipo_actual = form_data.get("TipoProgramacion", "Diaria")
    robot_search, set_robot_search = use_state("")

    # Estados para controlar la apertura de los acordeones
    is_general_open, set_general_open = use_state(True)
    is_details_open, set_details_open = use_state(True)
    # Inicializar cíclico con el valor del formulario, pero permitir toggle independiente
    is_cyclic_open, set_cyclic_open = use_state(form_data.get("EsCiclico", False))

    # Filtrar robots según búsqueda
    filtered_robots = use_memo(
        lambda: [r for r in robots_list if not robot_search or robot_search.lower() in r.get("Robot", "").lower()],
        dependencies=[robot_search, robots_list],
    )

    def handle_change(field, value):
        """Manejador de cambios que limpia campos al cambiar el tipo."""
        # Aplicar trim automático a campos de texto
        if isinstance(value, str) and field not in ["TipoProgramacion", "RobotId", "DiasSemana"]:
            value = value.strip()
        new_form_data = {**form_data, field: value}

        if field == "TipoProgramacion":
            # Limpiar campos específicos al cambiar tipo
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
        {"class_name": "schedule-create-form"},
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
                # Fila 1: Robot (requerido) con buscador
                html.div(
                    html.label("Robot *"),
                    html.input(
                        {
                            "type": "text",
                            "placeholder": "🔍 Buscar robot...",
                            "value": robot_search,
                            "on_change": lambda e: set_robot_search(e["target"]["value"].strip()),
                            "style": {
                                "marginBottom": "0.5rem",
                            },
                        }
                    ),
                    html.select(
                        {
                            "value": str(form_data.get("RobotId", "")),
                            "on_change": lambda e: handle_change("RobotId", int(e["target"]["value"]) if e["target"]["value"] else None),
                            "required": True,
                            "size": min(max(len(filtered_robots), 1), 8),  # Mostrar entre 1 y 8 opciones
                            "style": {
                                "minHeight": "120px",
                                "maxHeight": "200px",
                                "overflowY": "auto",
                            },
                        },
                        html.option({"value": ""}, "Seleccionar robot..."),
                        *[html.option({"value": str(r["RobotId"])}, r["Robot"]) for r in filtered_robots],
                    ),
                    html.small(
                        {"style": {"color": "var(--pico-muted-color)", "fontSize": "0.85em"}},
                        f"{len(filtered_robots)} robot(s) disponible(s)" if robot_search else f"{len(robots_list)} robot(s) disponible(s)",
                    ),
                ),
                # Fila 2: Tipo de Programación
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
                # Fila 3: Hora y Tolerancia (siempre visibles)
                html.div(
                    {"class_name": "grid"},
                    html.label(
                        "Hora de Inicio (HH:MM) *",
                        html.input(
                            {
                                "type": "time",
                                "value": form_data.get("HoraInicio") or "00:00",
                                "on_change": lambda e: handle_change("HoraInicio", e["target"]["value"]),
                                "required": True,
                            }
                        ),
                    ),
                    html.label(
                        "Tolerancia (minutos) *",
                        html.input(
                            {
                                "type": "number",
                                "value": form_data.get("Tolerancia") or 30,
                                "min": 0,
                                "max": 1440,
                                "on_change": lambda e: handle_change("Tolerancia", int(e["target"]["value"] or 0)),
                                "required": True,
                            }
                        ),
                    ),
                ),
                # Equipos (requerido)
                html.label(
                    "Equipos *",
                    html.p(
                        {"style": {"fontSize": "0.9em", "color": "var(--pico-muted-color)"}},
                        "Los equipos se asignarán después de crear la programación.",
                    ),
                ),
            ),
        ),
        # 2. Detalles de Programación (Solo si no es Diaria)
        html.details(
            {"open": is_details_open},
            html.summary(
                {
                    "on_click": lambda e: set_details_open(not is_details_open),
                    "style": {"fontWeight": "bold", "cursor": "pointer", "marginBottom": "0.5rem"},
                },
                "Detalles de Programación",
            ),
            html.div(
                {"style": {"padding": "1rem 0", "borderTop": "1px solid var(--pico-muted-border-color)"}},
                # Si es Semanal
                html.label(
                    "Días de la Semana (ej. Lu,Ma,Mi,Ju,Vi)",
                    WeekdaySelector(
                        value=form_data.get("DiasSemana") or "",
                        on_change=lambda new_days_str: handle_change("DiasSemana", new_days_str),
                    )
                    if (tipo_actual == "Semanal" and WeekdaySelector)
                    else html.input(
                        {
                            "type": "text",
                            "value": form_data.get("DiasSemana") or "",
                            "placeholder": "Lu,Ma,Mi,Ju,Vi",
                            "on_change": lambda e: handle_change("DiasSemana", e["target"]["value"]),
                        }
                    ),
                )
                if tipo_actual == "Semanal"
                else None,
                # Si es Mensual
                html.label(
                    "Día del Mes (1-31)",
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
                if tipo_actual == "Mensual"
                else None,
                # Si es RangoMensual
                html.div(
                    {"class_name": "rango-mensual-options"},
                    html.p({"style": {"fontSize": "0.9em", "color": "var(--pico-muted-color)"}}, "Seleccione una opción:"),
                    html.label(
                        html.input(
                            {
                                "type": "radio",
                                "name": "rango-option",
                                "value": "rango",
                                "checked": form_data.get("DiaInicioMes") is not None and form_data.get("DiaFinMes") is not None,
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
                                    "on_change": lambda e: handle_change("DiaInicioMes", int(e["target"]["value"]) if e["target"]["value"] else None),
                                    "disabled": form_data.get("rango_option") != "rango" and form_data.get("DiaInicioMes") is None,
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
                                    "on_change": lambda e: handle_change("DiaFinMes", int(e["target"]["value"]) if e["target"]["value"] else None),
                                }
                            ),
                        ),
                    )
                    if (
                        form_data.get("rango_option") == "rango"
                        or (form_data.get("DiaInicioMes") is not None and form_data.get("DiaFinMes") is not None)
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
                                "on_change": lambda e: handle_change("PrimerosDiasMes", int(e["target"]["value"]) if e["target"]["value"] else None),
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
                                "on_change": lambda e: handle_change("UltimosDiasMes", int(e["target"]["value"]) if e["target"]["value"] else None),
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
                if tipo_actual == "Especifica"
                else None,
            ),
        )
        if tipo_actual != "Diaria"
        else None,
        # 3. Ejecución Cíclica
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
                                    "value": form_data.get("HoraFin") or "",
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


@component
def ScheduleCreateModal(
    is_open: bool,
    on_close: Callable,
    on_save: Callable,
    robots_list: List[Dict],
):
    """
    Modal para crear una nueva programación.
    """
    notification_context = use_context(NotificationContext)
    show_notification = notification_context["show_notification"]

    form_data, set_form_data = use_state(
        {
            "RobotId": None,
            "TipoProgramacion": "Diaria",
            "HoraInicio": "00:00",
            "Tolerancia": 30,
            "Equipos": [],
            "Activo": True,
            "EsCiclico": False,
            "HoraFin": None,
            "FechaInicioVentana": None,
            "FechaFinVentana": None,
            "IntervaloEntreEjecuciones": None,
        }
    )
    is_loading, set_is_loading = use_state(False)
    show_confirm, set_show_confirm = use_state(False)

    @use_effect(dependencies=[is_open])
    def reset_form():
        """Resetea el formulario cuando se abre el modal."""
        if is_open:
            set_form_data(
                {
                    "RobotId": None,
                    "TipoProgramacion": "Diaria",
                    "HoraInicio": "00:00",
                    "Tolerancia": 30,
                    "Equipos": [],
                    "Activo": True,
                    "EsCiclico": False,
                    "HoraFin": None,
                    "FechaInicioVentana": None,
                    "FechaFinVentana": None,
                    "IntervaloEntreEjecuciones": None,
                }
            )

    def handle_save_click(e):
        """Muestra el diálogo de confirmación"""
        set_show_confirm(True)

    async def handle_confirm_save():
        """Ejecuta el guardado tras confirmar"""
        set_show_confirm(False)
        set_is_loading(True)
        try:
            # Validaciones
            if not form_data.get("RobotId"):
                raise ValueError("Debe seleccionar un robot")
            if not form_data.get("HoraInicio"):
                raise ValueError("Debe especificar la hora de inicio")

            tipo = form_data.get("TipoProgramacion")
            if tipo == "Semanal" and not form_data.get("DiasSemana"):
                raise ValueError("Para 'Semanal', los días de la semana son obligatorios.")
            if tipo == "Mensual" and not form_data.get("DiaDelMes"):
                raise ValueError("Para 'Mensual', el día del mes es obligatorio.")
            if tipo == "Especifica" and not form_data.get("FechaEspecifica"):
                raise ValueError("Para 'Específica', la fecha es obligatoria.")
            if tipo == "RangoMensual":
                has_rango = form_data.get("DiaInicioMes") and form_data.get("DiaFinMes")
                has_primeros = form_data.get("PrimerosDiasMes")
                has_ultimos = form_data.get("UltimosDiasMes")
                if not (has_rango or has_primeros or has_ultimos):
                    raise ValueError("Para 'Rango Mensual', debe especificar un rango, primeros N días, o últimos N días.")

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
            show_notification("Programación creada con éxito.", "success")
            on_close()
        except Exception as ex:
            show_notification(f"Error al crear: {ex}", "error")
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
                    html.h3("Crear Nueva Programación"),
                ),
                html.form(
                    {
                        "id": "create-schedule-form",
                        "on_submit": event(lambda e: handle_save_click(e), prevent_default=True),
                    },
                    ScheduleCreateForm(form_data, set_form_data, robots_list),
                ),
                LoadingOverlay(
                    is_loading=is_loading,
                    message="Creando programación, esto puede tardar unos segundos..." if is_loading else None,
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
                                "form": "create-schedule-form",
                                "aria-busy": str(is_loading).lower(),
                                "disabled": is_loading,
                            },
                            "Procesando..." if is_loading else "Crear Programación",
                        ),
                    )
                ),
            ),
        ),
        ConfirmationModal(
            is_open=show_confirm,
            title="Confirmar Creación",
            message="¿Estás seguro de que deseas crear esta programación?",
            on_confirm=handle_confirm_save,
            on_cancel=lambda: set_show_confirm(False),
        )
        if show_confirm
        else None,
    )
