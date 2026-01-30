# sam/web/features/modals/robots_modals.py
import asyncio
from typing import Any, Callable, Dict, List

from reactpy import component, event, html, use_callback, use_context, use_effect, use_memo, use_state

from ...api.api_client import ApiClient, get_api_client
from ...shared.common_components import ConfirmationModal, LoadingOverlay
from ...shared.formatters import format_equipos_list, format_schedule_details, format_time
from ...shared.notifications import NotificationContext
from ...state.app_context import use_app_context
from ..components.bot_input_editor import BotInputEditor

# --- Constantes y Estados por Defecto ---

DEFAULT_ROBOT_STATE = {
    "RobotId": None,
    "Robot": "",
    "Descripcion": "",
    "Activo": True,
    "EsOnline": False,
    "MinEquipos": 1,
    "MaxEquipos": -1,
    "PrioridadBalanceo": 100,
    "TicketsPorEquipoAdicional": 10,
    "Parametros": None,
}

# Incluir todos los tipos soportados por la BD (incluye RangoMensual)
SCHEDULE_TYPES = ["Diaria", "Semanal", "Mensual", "RangoMensual", "Especifica"]
DEFAULT_FORM_STATE = {
    "ProgramacionId": None,
    "TipoProgramacion": "Diaria",
    "HoraInicio": "09:00",
    "Tolerancia": 60,
    "DiasSemana": "Lu,Ma,Mi,Ju,Vi,Sa,Do",
    "DiaDelMes": 1,
    "FechaEspecifica": "",
    # Campos para RangoMensual
    "DiaInicioMes": None,
    "DiaFinMes": None,
    "UltimosDiasMes": None,
    "PrimerosDiasMes": None,
    # Campos para robots cíclicos
    "EsCiclico": False,
    "HoraFin": None,
    "FechaInicioVentana": None,
    "FechaFinVentana": None,
    "IntervaloEntreEjecuciones": None,
    "Equipos": [],
}

# Definimos los días con la etiqueta de una sola letra que solicitaste
# El 'id' (Lu, Ma, Sa) es lo que espera el SP y NO cambia.
DAYS_OF_WEEK = [
    {"id": "Lu", "label": "L"},
    {"id": "Ma", "label": "M"},
    {"id": "Mi", "label": "M"},
    {"id": "Ju", "label": "J"},
    {"id": "Vi", "label": "V"},
    {"id": "Sa", "label": "S"},
    {"id": "Do", "label": "D"},
]


@component
def WeekdaySelector(value: str, on_change: Callable):
    """
    Un componente de checkboxes para seleccionar días de la semana.
    Renderiza un layout tradicional con etiquetas (L,M,M...) y checkboxes debajo.
    """

    # Convertimos el string "Lu,Ma,Vi" en un set {"Lu", "Ma", "Vi"}
    selected_days_set = use_memo(lambda: set((value or "").split(",")), [value])

    def handle_day_change(day_id, is_checked):
        # Creamos una copia del set actual
        new_set = set(selected_days_set)

        if is_checked:
            new_set.add(day_id)
        else:
            new_set.discard(day_id)

        # Reconstruimos el string en el orden de DAYS_OF_WEEK
        ordered_days = [day["id"] for day in DAYS_OF_WEEK if day["id"] in new_set]
        # Llamamos al on_change del formulario con el nuevo string
        on_change(",".join(ordered_days))

    return html.fieldset(
        {"class_name": "weekday-selector-traditional"},  # Clase CSS
        html.legend("Días de la Semana"),
        html.div(
            {"class_name": "weekday-grid"},
            # Iteramos UNA vez para crear las 7 columnas
            *[
                html.div(
                    {"key": day["id"], "class_name": "weekday-day-column"},  # Columna
                    # Fila 1: Etiqueta (L, M, M...)
                    html.span({"class_name": "weekday-header"}, day["label"]),
                    # Fila 2: Checkbox
                    html.label(
                        {"class_name": "weekday-checkbox-label"},  # Label para centrar
                        html.input(
                            {
                                "type": "checkbox",
                                "name": f"weekday-{day['id']}",
                                "checked": day["id"] in selected_days_set,
                                "on_change": lambda e, d_id=day["id"]: handle_day_change(d_id, e["target"]["checked"]),
                            }
                        ),
                    ),
                )
                for day in DAYS_OF_WEEK
            ],
        ),
    )


# --- Componentes de Modal ---
@component
def RobotEditModal(robot: Dict[str, Any] | None, is_open: bool, on_close: Callable, on_save_success: Callable):
    """Modal para crear o editar un robot. Incluye validación."""

    form_data, set_form_data = use_state(DEFAULT_ROBOT_STATE)
    is_loading, set_is_loading = use_state(False)
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]
    # Obtener api_client del contexto
    try:
        app_context = use_app_context()
        api_service = app_context.get("api_client") or get_api_client()
    except Exception:
        api_service = get_api_client()
    is_edit_mode = bool(robot and robot.get("RobotId") is not None)

    @use_effect(dependencies=[robot])
    def sync_form_state():
        if robot is None:
            # Si el robot es None, reseteamos el formulario completamente
            set_form_data(DEFAULT_ROBOT_STATE)
            return

        if is_edit_mode:
            # Modo edición: rellenamos con los datos del robot
            set_form_data(robot)
        else:
            # Modo creación: reseteamos explicitamente al estado por defecto
            set_form_data(DEFAULT_ROBOT_STATE)

    def handle_form_change(field_name, field_value):
        # Aplicar trim automático a campos de texto (excepto números)
        if field_name not in ["RobotId", "MinEquipos", "MaxEquipos", "PrioridadBalanceo", "TicketsPorEquipoAdicional"]:
            if isinstance(field_value, str):
                field_value = field_value.strip()
            elif field_value is None:
                field_value = ""

        if field_name in ["RobotId", "MinEquipos", "MaxEquipos", "PrioridadBalanceo", "TicketsPorEquipoAdicional"]:
            try:
                # Permitir que el campo quede vacío temporalmente durante la edición
                field_value = int(field_value) if field_value not in [None, ""] else None
            except (ValueError, TypeError):
                field_value = None
        set_form_data(lambda old_data: {**old_data, field_name: field_value})

    async def handle_save(event_data):
        set_is_loading(True)
        try:
            # Validación Min/Max Equipos
            min_equipos = form_data.get("MinEquipos")
            max_equipos = form_data.get("MaxEquipos")
            if min_equipos is not None and max_equipos is not None:
                # Si MaxEquipos es -1, se considera ilimitado, por lo que no se valida el tope.
                if max_equipos != -1 and min_equipos > max_equipos:
                    show_notification("El valor de Min Equipos no puede ser mayor que Max Equipos.", "error")
                    set_is_loading(False)
                    return

            if is_edit_mode:
                # El JSON de parámetros ya está validado por el BotInputEditor
                parametros_json = form_data.get("Parametros")

                payload_to_send = {
                    "Robot": form_data.get("Robot"),
                    "Descripcion": form_data.get("Descripcion"),
                    "MinEquipos": form_data.get("MinEquipos"),
                    "MaxEquipos": form_data.get("MaxEquipos"),
                    "PrioridadBalanceo": form_data.get("PrioridadBalanceo"),
                    "TicketsPorEquipoAdicional": form_data.get("TicketsPorEquipoAdicional"),
                    "Parametros": parametros_json if parametros_json and parametros_json.strip() else None,
                }
                await api_service.update_robot(robot["RobotId"], payload_to_send)
                show_notification("Robot actualizado con éxito.", "success")
            else:
                if not form_data.get("RobotId"):
                    show_notification("El campo 'Robot ID' es requerido.", "error")
                    set_is_loading(False)
                    return
                # Creamos una copia para no modificar el estado directamente
                payload_to_create = form_data.copy()
                await api_service.create_robot(payload_to_create)
                show_notification("Robot creado con éxito.", "success")
            await on_save_success()
            set_is_loading(False)
        except Exception as e:
            show_notification(str(e), "error")
            set_is_loading(False)

    if not is_open or robot is None:
        return html.dialog({"open": False, "style": {"display": "none"}})

    return html.dialog(
        {"open": True if robot is not None else False},
        html.article(
            {"style": {"position": "relative"}},
            html.script(
                """
                (function() {
                    // Función para configurar los acordeones mutuamente exclusivos
                    function setupMutuallyExclusiveAccordions() {
                        const configAccordion = document.getElementById('accordion-config');
                        const paramsAccordion = document.getElementById('accordion-params');

                        if (!configAccordion || !paramsAccordion) {
                            // Si los elementos no existen aún, reintentar después de un breve delay
                            setTimeout(setupMutuallyExclusiveAccordions, 50);
                            return;
                        }

                        const closeOther = (current) => {
                            if (current === configAccordion && paramsAccordion.hasAttribute('open')) {
                                paramsAccordion.removeAttribute('open');
                            } else if (current === paramsAccordion && configAccordion.hasAttribute('open')) {
                                configAccordion.removeAttribute('open');
                            }
                        };

                        // Remover listeners anteriores si existen (para evitar duplicados)
                        if (configAccordion._toggleHandler) {
                            configAccordion.removeEventListener('toggle', configAccordion._toggleHandler);
                        }
                        if (paramsAccordion._toggleHandler) {
                            paramsAccordion.removeEventListener('toggle', paramsAccordion._toggleHandler);
                        }

                        // Agregar nuevos listeners
                        configAccordion._toggleHandler = function(e) {
                            if (e.target.open) {
                                closeOther(e.target);
                            }
                        };
                        paramsAccordion._toggleHandler = function(e) {
                            if (e.target.open) {
                                closeOther(e.target);
                            }
                        };

                        configAccordion.addEventListener('toggle', configAccordion._toggleHandler);
                        paramsAccordion.addEventListener('toggle', paramsAccordion._toggleHandler);
                    }

                    // Ejecutar después de un pequeño delay para asegurar que los elementos existan
                    setTimeout(setupMutuallyExclusiveAccordions, 100);
                })();
                """
            ),
            html.header(
                html.button({"aria-label": "Close", "rel": "prev", "on_click": event(on_close, prevent_default=True)}),
                html.h2("Editar Robot") if is_edit_mode else html.h2("Crear Nuevo Robot"),
            ),
            html.form(
                {"id": "robot-form", "onSubmit": event(handle_save, prevent_default=True)},
                html.div(
                    {"class_name": "grid"},
                    html.label(
                        {"htmlFor": "robot-name"},
                        "Nombre",
                        html.input(
                            {
                                "id": "robot-name",
                                "type": "text",
                                "name": "text-robot-name",
                                "placeholder": "Ej: Robot 1",
                                "value": form_data.get("Robot", ""),
                                "on_change": lambda e: handle_form_change("Robot", e["target"]["value"]),
                                "required": True,
                            }
                        ),
                    ),
                    html.label(
                        {"htmlFor": "robot-id"},
                        "Robot ID (de A360)",
                        html.input(
                            {
                                "id": "robot-id",
                                "type": "number",
                                "name": "number-robot-id",
                                "placeholder": "Ej: 1111",
                                "value": form_data.get("RobotId", ""),
                                "on_change": lambda e: handle_form_change("RobotId", e["target"]["value"]),
                                "required": not is_edit_mode,
                                "disabled": is_edit_mode,
                            }
                        ),
                    ),
                ),
                # Acordeón de Configuración Avanzada
                html.details(
                    {
                        "id": "accordion-config",
                        "style": {"marginTop": "1rem"},
                        "form": "robot-form",
                    },
                    html.summary(
                        {
                            "style": {
                                "cursor": "pointer",
                                "fontWeight": "bold",
                                "padding": "0.5rem",
                                "backgroundColor": "var(--pico-card-background-color)",
                                "borderRadius": "var(--pico-border-radius)",
                            }
                        },
                        "Configuración Avanzada",
                    ),
                    html.div(
                        {"style": {"padding": "1rem", "borderTop": "1px solid var(--pico-border-color)"}},
                        html.label(
                            {"htmlFor": "robot-desc"},
                            "Descripción",
                            html.textarea(
                                {
                                    "id": "robot-desc",
                                    "rows": 3,
                                    "value": form_data.get("Descripcion", ""),
                                    "on_change": lambda e: handle_form_change("Descripcion", e["target"]["value"]),
                                }
                            ),
                        ),
                        html.div(
                            {"class_name": "grid", "style": {"marginTop": "1rem"}},
                            html.label(
                                {"htmlFor": "min-equipos"},
                                "Mín. Equipos",
                                html.div(
                                    {"class_name": "range"},
                                    html.output(form_data.get("MinEquipos", "0")),
                                    html.input(
                                        {
                                            "id": "min-equipos",
                                            "type": "range",
                                            "name": "range-min-equipos",
                                            "min": "1",
                                            "max": "99",
                                            "value": form_data.get("MinEquipos", 0),
                                            "on_change": lambda e: handle_form_change(
                                                "MinEquipos", e["target"]["value"]
                                            ),
                                            "style": {"flexGrow": "1"},
                                        }
                                    ),
                                ),
                            ),
                            html.label(
                                {"htmlFor": "max-equipos"},
                                "Máx. Equipos",
                                html.div(
                                    {"class_name": "range"},
                                    html.output(form_data.get("MaxEquipos", "0")),
                                    html.input(
                                        {
                                            "id": "max-equipos",
                                            "type": "range",
                                            "name": "range-max-equipos",
                                            "min": "-1",
                                            "max": "100",
                                            "value": form_data.get("MaxEquipos", -1),
                                            "on_change": lambda e: handle_form_change(
                                                "MaxEquipos", e["target"]["value"]
                                            ),
                                            "style": {"flexGrow": "1"},
                                        }
                                    ),
                                ),
                            ),
                        ),
                        html.div(
                            {"class_name": "grid", "style": {"marginTop": "1rem"}},
                            html.label(
                                {"htmlFor": "prioridad"},
                                "Prioridad",
                                html.div(
                                    {"class_name": "range"},
                                    html.output({"class_name": "button"}, form_data.get("PrioridadBalanceo", "0")),
                                    html.input(
                                        {
                                            "id": "prioridad",
                                            "type": "range",
                                            "name": "range-prioridad",
                                            "min": "0",
                                            "max": "100",
                                            "step": "5",
                                            "value": form_data.get("PrioridadBalanceo", 100),
                                            "on_change": lambda e: handle_form_change(
                                                "PrioridadBalanceo", e["target"]["value"]
                                            ),
                                            "style": {"flexGrow": "1"},
                                        }
                                    ),
                                ),
                            ),
                            html.label(
                                {"htmlFor": "tickets"},
                                "Tickets/Equipo Adic.",
                                html.div(
                                    {"class_name": "range"},
                                    html.output(form_data.get("TicketsPorEquipoAdicional", "0")),
                                    html.input(
                                        {
                                            "id": "tickets",
                                            "type": "range",
                                            "name": "range-tickets",
                                            "min": "1",
                                            "max": "100",
                                            "value": form_data.get("TicketsPorEquipoAdicional", 10),
                                            "on_change": lambda e: handle_form_change(
                                                "TicketsPorEquipoAdicional", e["target"]["value"]
                                            ),
                                            "style": {"flexGrow": "1"},
                                        }
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                # Editor amigable de parámetros en un acordeón
                html.details(
                    {
                        "id": "accordion-params",
                        "style": {"marginTop": "1rem"},
                        "form": "robot-form",
                    },
                    html.summary(
                        {
                            "style": {
                                "cursor": "pointer",
                                "fontWeight": "bold",
                                "padding": "0.5rem",
                                "backgroundColor": "var(--pico-card-background-color)",
                                "borderRadius": "var(--pico-border-radius)",
                            }
                        },
                        "Parámetros de Bot Input (Opcional)",
                    ),
                    html.div(
                        {"style": {"padding": "1rem", "borderTop": "1px solid var(--pico-border-color)"}},
                        BotInputEditor(
                            value=form_data.get("Parametros"),
                            on_change=lambda json_str: handle_form_change("Parametros", json_str),
                        ),
                    ),
                ),
            ),
            LoadingOverlay(
                is_loading=is_loading,
                message="Guardando cambios..." if is_loading else None,
            ),
            html.footer(
                html.div(
                    {"class_name": "grid"},
                    html.button(
                        {"type": "button", "class_name": "secondary", "on_click": on_close, "disabled": is_loading},
                        "Cancelar",
                    ),
                    html.button(
                        {
                            "type": "submit",
                            "form": "robot-form",
                            "aria-busy": str(is_loading).lower(),
                            "disabled": is_loading,
                        },
                        "Guardar",
                    ),
                )
            ),
        ),
    )


@component
def AssignmentsModal(robot: Dict[str, Any] | None, is_open: bool, on_close: Callable, on_save_success: Callable):
    # Obtener api_client del contexto
    try:
        app_context = use_app_context()
        api_service = app_context.get("api_client") or get_api_client()
    except Exception:
        api_service = get_api_client()
    assigned_devices, set_assigned_devices = use_state([])
    available_devices, set_available_devices = use_state([])
    is_loading, set_is_loading = use_state(False)
    selected_in_available, set_selected_in_available = use_state([])
    selected_in_assigned, set_selected_in_assigned = use_state([])
    confirmation_data, set_confirmation_data = use_state(None)
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]
    search_assigned, set_search_assigned = use_state("")
    search_available, set_search_available = use_state("")

    def sort_devices(devices: List[Dict]) -> List[Dict]:
        """Ordena una lista de diccionarios de equipos por el campo 'Equipo'."""
        return sorted(devices, key=lambda x: x.get("Equipo", "").lower())

    @use_effect(dependencies=[robot])
    def init_data_load():
        def get_highest_priority_assignment(assignments: List[Dict]) -> List[Dict]:
            """
            De-duplica una lista de asignaciones por EquipoId,
            quedándose con el estado de mayor prioridad.
            Prioridad: Programado > Reservado > Dinámico
            """

            def get_priority(asn):
                if asn.get("EsProgramado"):
                    return 1
                if asn.get("Reservado"):
                    return 2
                return 3

            unique_equipos = {}
            for asn in assignments:
                equipo_id = asn.get("EquipoId")
                if not equipo_id:
                    continue

                current_assignment = unique_equipos.get(equipo_id)

                if not current_assignment:
                    unique_equipos[equipo_id] = asn
                else:
                    # Comparamos prioridades
                    current_priority = get_priority(current_assignment)
                    new_priority = get_priority(asn)

                    # Si la nueva asignación tiene mayor prioridad (un nro más bajo),
                    # la reemplazamos.
                    if new_priority < current_priority:
                        unique_equipos[equipo_id] = asn

            return list(unique_equipos.values())

        async def fetch_data():
            if not robot:
                return
            set_is_loading(True)
            set_selected_in_available([])
            set_selected_in_assigned([])
            set_search_assigned("")
            set_search_available("")
            try:
                assigned_res, available_res = await asyncio.gather(
                    api_service.get_robot_assignments(robot["RobotId"]),
                    api_service.get_available_devices(robot["RobotId"]),
                )
                unique_assigned_devices = get_highest_priority_assignment(assigned_res)
                set_assigned_devices(unique_assigned_devices)
                set_available_devices(available_res)
                if not asyncio.current_task().cancelled():
                    set_is_loading(False)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                show_notification(f"Error al cargar datos: {e}", "error")
                set_is_loading(False)

        task = asyncio.create_task(fetch_data())
        return lambda: task.cancel()

    filtered_assigned = use_memo(
        lambda: sort_devices(
            [device for device in assigned_devices if search_assigned.lower() in device.get("Equipo", "").lower()]
        ),
        [assigned_devices, search_assigned],
    )
    filtered_available = use_memo(
        lambda: sort_devices(
            [device for device in available_devices if search_available.lower() in device.get("Equipo", "").lower()]
        ),
        [available_devices, search_available],
    )

    def move_items(source_list, set_source, dest_list, set_dest, selected_ids, clear_selection):
        """Mueve elementos entre listas asegurando que no queden duplicados por EquipoId."""
        items_to_move = {item["EquipoId"]: item for item in source_list if item.get("EquipoId") in selected_ids}

        # Construimos un diccionario único para el destino (dest_list + items_to_move),
        # dejando que la versión "movida" reemplace a una previa si ya existía.
        dest_dict = {item["EquipoId"]: item for item in dest_list if item.get("EquipoId") is not None}
        dest_dict.update(items_to_move)

        new_dest_list = sort_devices(list(dest_dict.values()))
        new_source_list = sort_devices([item for item in source_list if item.get("EquipoId") not in items_to_move])

        set_dest(new_dest_list)
        set_source(new_source_list)
        clear_selection([])

    async def execute_save():
        """Función que ejecuta el guardado después de la confirmación."""
        if not confirmation_data:
            return
        set_is_loading(True)
        try:
            ids_to_assign, ids_to_unassign = confirmation_data["assign"], confirmation_data["unassign"]
            await api_service.update_robot_assignments(robot["RobotId"], ids_to_assign, ids_to_unassign)
            await on_save_success()
            show_notification("Se actualizó la asignación correctamente", "success")
            set_is_loading(False)
            set_confirmation_data(None)
            on_close()
        except Exception as e:
            show_notification(f"Error al guardar: {e}", "error")
            set_is_loading(False)
            set_confirmation_data(None)

    async def handle_save(event_data):
        original_assigned_ids_set = {t["EquipoId"] for t in (await api_service.get_robot_assignments(robot["RobotId"]))}
        current_assigned_ids_set = {t["EquipoId"] for t in assigned_devices}

        ids_to_assign = list(current_assigned_ids_set - original_assigned_ids_set)
        ids_to_unassign = list(original_assigned_ids_set - current_assigned_ids_set)

        if not ids_to_assign and not ids_to_unassign:
            on_close()
            return

        # Abre el modal de confirmación si hay cambios que guardar.
        set_confirmation_data({"assign": ids_to_assign, "unassign": ids_to_unassign})

    if not is_open or not robot:
        return html.dialog({"open": False, "style": {"display": "none"}})

    return html.dialog(
        {"open": True},  # "style": {"width": "90vw", "maxWidth": "1000px"}},
        html.article(
            {"style": {"position": "relative"}},
            html.header(
                html.button(
                    {
                        "aria-label": "Close",
                        "rel": "prev",
                        "on_click": event(on_close, prevent_default=True),
                        "disabled": is_loading,
                    }
                ),
                html.h2("Asignación de Equipos"),
                html.p(f"Robot: {robot.get('Robot', '')}"),
            ),
            html.div(
                {
                    "class_name": "grid",
                    "style": {
                        "gridTemplateColumns": "5fr 1fr 5fr",
                        "alignItems": "center",
                        "gap": "1rem",
                        "height": "400px",
                    },
                },
                DeviceList(
                    title="Equipos Disponibles",
                    devices=filtered_available,
                    selected_ids=selected_in_available,
                    on_selection_change=set_selected_in_available,
                    search_term=search_available,
                    on_search_change=set_search_available,
                ),
                html.div(
                    {"style": {"display": "flex", "flexDirection": "column", "gap": "1rem"}},
                    html.button(
                        {
                            "on_click": lambda e: move_items(
                                available_devices,
                                set_available_devices,
                                assigned_devices,
                                set_assigned_devices,
                                selected_in_available,
                                set_selected_in_available,
                            ),
                            "disabled": not selected_in_available,
                            "data-tooltip": "Asignar seleccionados",
                        },
                        html.i({"class_name": "fa-solid fa-arrow-right"}),
                    ),
                    html.button(
                        {
                            "on_click": lambda e: move_items(
                                assigned_devices,
                                set_assigned_devices,
                                available_devices,
                                set_available_devices,
                                selected_in_assigned,
                                set_selected_in_assigned,
                            ),
                            "disabled": not selected_in_assigned,
                            "data-tooltip": "Desasignar seleccionados",
                        },
                        html.i({"class_name": "fa-solid fa-arrow-left"}),
                    ),
                ),
                DeviceList(
                    title="Equipos Asignados",
                    devices=filtered_assigned,
                    selected_ids=selected_in_assigned,
                    on_selection_change=set_selected_in_assigned,
                    search_term=search_assigned,
                    on_search_change=set_search_assigned,
                ),
            ),
            LoadingOverlay(
                is_loading=is_loading,
                message="Aplicando cambios, esto puede tardar unos segundos..." if is_loading else None,
            ),
            html.footer(
                html.div(
                    {"class_name": "grid"},
                    html.button({"class_name": "secondary", "on_click": on_close, "disabled": is_loading}, "Cancelar"),
                    html.button(
                        {"aria-busy": str(is_loading).lower(), "on_click": handle_save, "disabled": is_loading},
                        "Procesando..." if is_loading else "Guardar",
                    ),
                ),
            ),
        ),
        # Añadir el modal de confirmación
        ConfirmationModal(
            is_open=bool(confirmation_data),
            title="Confirmar Cambios",
            message="¿Estás seguro de que quieres modificar las asignaciones de equipos para este robot?",
            on_confirm=lambda: execute_save(),
            on_cancel=lambda: set_confirmation_data(None),
        ),
    )


@component
def SchedulesModal(robot: Dict[str, Any] | None, is_open: bool, on_close: Callable, on_save_success: Callable):
    # Obtener api_client del contexto
    try:
        app_context = use_app_context()
        api_service = app_context.get("api_client") or get_api_client()
    except Exception:
        api_service = get_api_client()
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]
    view_mode, set_view_mode = use_state("list")
    schedules, set_schedules = use_state([])
    available_devices, set_available_devices = use_state([])
    all_robot_devices, set_all_robot_devices = use_state([])
    form_data, set_form_data = use_state(DEFAULT_FORM_STATE)
    is_loading, set_is_loading = use_state(False)

    @use_effect(dependencies=[robot])
    def init_data_load():
        if not robot:
            return
        task = asyncio.create_task(fetch_data())
        return lambda: task.cancel()

    async def fetch_data():
        set_is_loading(True)
        try:
            schedules_res, devices_res, assigned_res = await asyncio.gather(
                api_service.get_robot_schedules(robot["RobotId"]),
                api_service.get_available_devices(robot["RobotId"]),
                api_service.get_robot_assignments(robot["RobotId"]),
            )
            set_schedules(schedules_res)
            # No seteamos available_devices directamente para evitar duplicados en props posteriores
            # set_available_devices(devices_res)

            # FIX CRÍTICO: Desduplicar la lista combinada por EquipoId
            # La suma devices_res + assigned_res pone al final los asignados.
            # El dict comprehension sobreescribe claves, quedándonos con la versión "Asignada" (más completa) si hay colisión.
            combined = devices_res + assigned_res
            unique_combined_dict = {d["EquipoId"]: d for d in combined}
            unique_list = list(unique_combined_dict.values())

            set_all_robot_devices(unique_list)
            # Usamos la lista única también para available_devices para asegurar consistencia en selectores
            set_available_devices(unique_list)
            set_available_devices(unique_list)
            set_is_loading(False)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            show_notification(str(e), "error")
            set_is_loading(False)

    async def handle_successful_change():
        await on_save_success()
        if robot:
            await fetch_data()

    async def submit_form(event):
        set_is_loading(True)
        if not form_data.get("Equipos"):
            show_notification("Debe seleccionar al menos un equipo.", "error")
            set_is_loading(False)
            return

        # Validaciones para robots cíclicos
        if form_data.get("EsCiclico"):
            if not form_data.get("HoraFin"):
                show_notification("Para robots cíclicos, la hora de fin es obligatoria.", "error")
                set_is_loading(False)
                return

            hora_inicio = form_data.get("HoraInicio", "00:00")
            hora_fin = form_data.get("HoraFin")
            if hora_fin <= hora_inicio:
                show_notification("La hora de fin debe ser mayor que la hora de inicio.", "error")
                set_is_loading(False)
                return

            fecha_inicio = form_data.get("FechaInicioVentana")
            fecha_fin = form_data.get("FechaFinVentana")
            if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
                show_notification("La fecha de inicio de ventana debe ser menor o igual a la fecha de fin.", "error")
                set_is_loading(False)
                return

            intervalo = form_data.get("IntervaloEntreEjecuciones")
            if intervalo and intervalo < 1:
                show_notification(
                    "El intervalo entre ejecuciones debe ser al menos 1 minuto si se especifica.", "error"
                )
                set_is_loading(False)
                return

        # Preparar payload: copiar form_data completo y agregar RobotId
        # Igual que ScheduleCreateModal que pasa form_data directamente
        payload = {**form_data, "RobotId": robot["RobotId"]}

        # Eliminar ProgramacionId si es creación (no debe estar en el payload de creación)
        if not payload.get("ProgramacionId"):
            payload.pop("ProgramacionId", None)

        try:
            if form_data.get("ProgramacionId"):
                await api_service.update_schedule(form_data["ProgramacionId"], payload)
                message = "Programación actualizada con éxito."
            else:
                await api_service.create_schedule(payload)
                message = "Programación creada con éxito."
            show_notification(message, "success")
            set_view_mode("list")
            await handle_successful_change()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            show_notification(str(e), "error")
        finally:
            if not asyncio.current_task().cancelled():
                set_is_loading(False)

    handle_form_submit = use_callback(submit_form, [form_data, robot, on_save_success])

    def handle_edit_click(schedule_to_edit):
        assigned_device_names = {device["Equipo"] for device in schedule_to_edit.get("Equipos", [])}
        equipos_ids = [device["EquipoId"] for device in all_robot_devices if device["Equipo"] in assigned_device_names]
        hora_fin = schedule_to_edit.get("HoraFin")
        if hora_fin:
            if hasattr(hora_fin, "strftime"):
                hora_fin = hora_fin.strftime("%H:%M")
            elif isinstance(hora_fin, str) and len(hora_fin) > 5:
                hora_fin = hora_fin[:5]

        # Asegurar que EsCiclico sea un booleano (puede venir como None, 0, 1, True, False)
        es_ciclico = schedule_to_edit.get("EsCiclico")
        if es_ciclico is None:
            es_ciclico = False
        elif isinstance(es_ciclico, (int, str)):
            # Convertir 0/1 o "0"/"1" a booleano
            es_ciclico = bool(int(es_ciclico)) if str(es_ciclico).isdigit() else bool(es_ciclico)
        else:
            es_ciclico = bool(es_ciclico)

        form_state = {
            "ProgramacionId": schedule_to_edit.get("ProgramacionId"),
            "TipoProgramacion": schedule_to_edit.get("TipoProgramacion", "Diaria"),
            "HoraInicio": (schedule_to_edit.get("HoraInicio") or "09:00")[:5],
            "Tolerancia": schedule_to_edit.get("Tolerancia", 60),
            "DiasSemana": schedule_to_edit.get("DiasSemana", ""),
            "DiaDelMes": schedule_to_edit.get("DiaDelMes", 1),
            "FechaEspecifica": (schedule_to_edit.get("FechaEspecifica") or "")[:10],
            # Campos para RangoMensual (si existen en la respuesta)
            "DiaInicioMes": schedule_to_edit.get("DiaInicioMes"),
            "DiaFinMes": schedule_to_edit.get("DiaFinMes"),
            "UltimosDiasMes": schedule_to_edit.get("UltimosDiasMes"),
            "PrimerosDiasMes": schedule_to_edit.get("PrimerosDiasMes"),
            # Campos para robots cíclicos
            "EsCiclico": es_ciclico,
            "HoraFin": hora_fin,
            "FechaInicioVentana": schedule_to_edit.get("FechaInicioVentana"),
            "FechaFinVentana": schedule_to_edit.get("FechaFinVentana"),
            "IntervaloEntreEjecuciones": schedule_to_edit.get("IntervaloEntreEjecuciones"),
            "Equipos": equipos_ids,
        }
        set_form_data(form_state)
        set_view_mode("form")

    def handle_form_change(field, value):
        if field == "Equipos":
            value = list(value) if value else []

        # FIX: Convertir cadenas vacías a None para campos de fecha/hora opcionales
        if field in ["FechaInicioVentana", "FechaFinVentana", "FechaEspecifica", "HoraFin"] and value == "":
            value = None

        new_data = {**form_data, field: value}
        if field == "EsCiclico" and not value:
            # Si se desactiva EsCiclico, limpiar campos relacionados
            new_data["HoraFin"] = None
            new_data["FechaInicioVentana"] = None
            new_data["FechaFinVentana"] = None
            new_data["IntervaloEntreEjecuciones"] = None
        set_form_data(new_data)

    def handle_new_click():
        set_form_data(DEFAULT_FORM_STATE.copy())
        set_view_mode("form")

    def handle_cancel():
        set_view_mode("list")

    if not is_open or not robot:
        return html.dialog({"open": False, "style": {"display": "none"}})

    return html.dialog(
        {"open": True},
        html.article(
            {"style": {"position": "relative"}},
            html.header(
                html.button(
                    {
                        "aria-label": "Close",
                        "rel": "prev",
                        "on_click": event(on_close, prevent_default=True),
                        "disabled": is_loading,
                    }
                ),
                html.h2("Programación de Robots"),
                html.p(f"{robot.get('Robot', '')}"),
            ),
            html._(
                html.div(
                    {"style": {"display": "block" if view_mode == "list" else "none"}},
                    SchedulesList(
                        api_service=api_service,
                        robot_id=robot["RobotId"],
                        robot_nombre=robot["Robot"],
                        schedules=schedules,
                        on_edit=handle_edit_click,
                        on_delete_success=handle_successful_change,
                    ),
                ),
                html.div(
                    {"style": {"display": "block" if view_mode == "form" else "none"}},
                    ScheduleForm(
                        form_data=form_data,
                        available_devices=available_devices,
                        is_loading=is_loading,
                        on_submit=handle_form_submit,
                        on_cancel=handle_cancel,
                        on_change=handle_form_change,
                    ),
                ),
            ),
            LoadingOverlay(
                is_loading=is_loading,
                message="Aplicando cambios, esto puede tardar unos segundos..." if is_loading else None,
            ),
            html.footer(
                html.button(
                    {"type": "button", "class_name": "secondary", "on_click": on_close, "disabled": is_loading},
                    "Cancelar",
                ),
                html.button(
                    {"type": "button", "on_click": lambda e: handle_new_click(), "disabled": is_loading},
                    "Nueva programación",
                ),
            )
            if view_mode == "list"
            else None,
        ),
    )


@component
def DeviceList(
    title: str,
    devices: List[Dict],
    selected_ids: List[int],
    on_selection_change: Callable,
    search_term: str,
    on_search_change: Callable,
):
    """
    Componente reutilizable que renderiza una lista de equipos con búsqueda y selección.
    """

    def handle_select_all(event):
        if event["target"]["checked"]:
            on_selection_change([device["EquipoId"] for device in devices])
        else:
            on_selection_change([])

    def handle_select_one(device_id, is_checked):
        current_ids = list(selected_ids)
        if is_checked:
            if device_id not in current_ids:
                current_ids.append(device_id)
        else:
            if device_id in current_ids:
                current_ids.remove(device_id)
        on_selection_change(current_ids)

    def get_estado(device: Dict) -> tuple[str, str, str]:
        """
        Determina el estado de un equipo según las reglas de negocio de SAM.

        Args:
            device: Diccionario con información del equipo, debe incluir:
                    - EsProgramado (bool): Flag de asignación programada
                    - Reservado (bool): Flag de reserva manual
                    - RobotId (int, opcional): ID del robot asignado (para detectar dinámico)

        Returns:
            tuple[str, str, str]: (texto_estado, clase_css, tooltip)
                - texto_estado: 'Programado', 'Reservado', 'Dinámico', o 'Libre'
                - clase_css: Nombre de clase CSS para aplicar estilos
                - tooltip: Texto descriptivo para mostrar al hacer hover

        Reglas de Negocio (evaluadas en orden de prioridad):
            1. Programado: EsProgramado=1 (compartible entre robots)
            2. Reservado: Reservado=1 (no compartible, asignación manual)
            3. Dinámico: tiene asignación (RobotId presente) pero no es programado ni reservado
            4. Libre: sin ninguna asignación (solo en lista 'Disponibles')
        """
        # Extraer flags de estado
        es_programado = device.get("EsProgramado", False)
        es_reservado = device.get("Reservado", False)
        # Para detectar asignación: RobotId indica que está asignado a un robot
        # En lista de "Disponibles", no hay RobotId (no están asignados a este robot)
        # En lista de "Asignados", sí hay RobotId
        tiene_asignacion = device.get("RobotId") is not None

        # PRIORIDAD 1: Programado
        # Equipos con EsProgramado=1 pueden ser compartidos entre múltiples robots/programaciones
        if es_programado:
            return (
                "Programado",
                "tag-programado",
                "Compartible entre robots - Asignado vía programación",
            )

        # PRIORIDAD 2: Reservado
        # Equipos con Reservado=1 son de uso exclusivo, asignados manualmente
        # Solo aparece en lista de "Asignados"
        if es_reservado:
            return (
                "Reservado",
                "tag-reservado",
                "Reservado manualmente - No compartible",
            )

        # PRIORIDAD 3: Dinámico
        # Equipos asignados automáticamente por el balanceador
        # Se detecta cuando: tiene asignación (RobotId presente) PERO no es programado NI reservado
        # Solo puede aparecer en lista de "Asignados"
        if tiene_asignacion and not es_programado and not es_reservado:
            return (
                "Dinámico",
                "tag-dinamico",
                "Asignado automáticamente por el balanceador",
            )

        # PRIORIDAD 4: Disponible (estado por defecto)
        # Equipos sin ninguna asignación activa
        # Aparece en lista de "Disponibles" cuando no tienen EsProgramado=1
        return (
            "Disponible",
            "tag-libre",
            "Disponible para asignación",
        )

    # Verificar si hay información de estado disponible
    # Siempre mostrar la columna de estado si:
    # 1. Es la lista de "Equipos Disponibles" (siempre debe mostrar estado)
    # 2. O si los dispositivos tienen información de estado (EsProgramado o Reservado)
    is_available_list = title == "Equipos Disponibles"
    has_status_data = devices and len(devices) > 0 and ("EsProgramado" in devices[0] or "Reservado" in devices[0])
    has_status_column = is_available_list or has_status_data

    return html.div(
        {"class_name": "device-list-section"},
        html.div(
            {"class_name": "device-list-header"},
            html.h5(title),
            html.input(
                {
                    "type": "search",
                    "name": "search-equipos",
                    "placeholder": "Filtrar equipos...",
                    "value": search_term,
                    "on_change": lambda e: on_search_change(e["target"]["value"].strip()),
                }
            ),
        ),
        html.div(
            {"class_name": "device-list-table compact-assignment-table"},
            html.table(
                {"role": "grid"},
                html.thead(
                    html.tr(
                        html.th(
                            {"scope": "col", "style": {"width": "40px"}},
                            html.input(
                                {"type": "checkbox", "name": "checkbox-equipos", "on_change": handle_select_all}
                            ),
                        ),
                        html.th({"scope": "col"}, "Nombre Equipo"),
                        html.th({"scope": "col", "style": {"width": "120px"}}, "Estado") if has_status_column else None,
                    )
                ),
                html.tbody(
                    *[
                        html.tr(
                            {"key": device["EquipoId"]},
                            html.td(
                                html.input(
                                    {
                                        "type": "checkbox",
                                        "checked": device["EquipoId"] in selected_ids,
                                        "on_change": lambda e, eid=device["EquipoId"]: handle_select_one(
                                            eid, e["target"]["checked"]
                                        ),
                                    }
                                )
                            ),
                            html.td(device["Equipo"]),
                            html.td(
                                html.span(
                                    {
                                        "class_name": f"tag {get_estado(device)[1]}",
                                        "title": get_estado(device)[2],  # Tooltip
                                    },
                                    get_estado(device)[0],  # Texto visible
                                )
                            )
                            if has_status_column
                            else None,
                        )
                        for device in devices
                    ]
                    if devices
                    else [
                        html.tr(
                            html.td(
                                {"colSpan": 3 if has_status_column else 2, "style": {"text_align": "center"}},
                                "No hay equipos para mostrar.",
                            )
                        )
                    ]
                ),
            ),
        ),
    )


@component
def SchedulesList(
    api_service: ApiClient,
    robot_id: int,
    robot_nombre: str,
    schedules: List[Dict],
    on_edit: Callable,
    on_delete_success: Callable,
):
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]
    schedule_to_delete, set_schedule_to_delete = use_state(None)

    def format_schedule_details_with_time(schedule):
        """Formatea los detalles de programación incluyendo el tipo y la hora."""
        tipo = schedule.get("TipoProgramacion")
        hora = format_time(schedule.get("HoraInicio"))
        details = f"{tipo or 'N/A'} a las {hora}" if hora else (tipo or "N/A")

        # Agregar detalles específicos según el tipo
        schedule_details = format_schedule_details(schedule)
        if schedule_details and schedule_details != "-":
            if tipo == "Semanal":
                details += f" los días {schedule_details}"
            elif tipo == "Mensual":
                details += f" el {schedule_details.lower()} de cada mes"
            elif tipo == "Especifica":
                details += f" en la fecha {schedule_details}"
            elif tipo == "RangoMensual":
                details += f" {schedule_details.lower()}"
        return details

    async def handle_confirm_delete():
        if not schedule_to_delete:
            return
        try:
            await api_service.delete_schedule(schedule_to_delete["ProgramacionId"], robot_id)
            show_notification("Programación eliminada.", "success")
            await on_delete_success()
        except Exception as e:
            show_notification(str(e), "error")
        finally:
            set_schedule_to_delete(None)

    rows = use_memo(
        lambda: [
            html.tr(
                {"key": s["ProgramacionId"]},
                html.td(format_schedule_details_with_time(s)),
                html.td(format_equipos_list(s.get("Equipos", []), max_visible=6)),
                html.td(
                    html.div(
                        {"class_name": "grid"},
                        html.button(
                            {
                                "class_name": "outline",
                                "on_click": lambda e, sch=s: on_edit(sch),
                                "aria-label": "Editar",
                            },
                            html.i({"class_name": "fa-solid fa-pencil"}),
                        ),
                        html.button(
                            {
                                "class_name": "secondary outline",
                                "on_click": lambda e, sch=s: set_schedule_to_delete(sch),
                                "aria-label": "Eliminar",
                            },
                            html.i({"class_name": "fa-solid fa-trash"}),
                        ),
                    )
                ),
            )
            for s in schedules
        ],
        [schedules, on_edit, on_delete_success],
    )
    return html._(
        html.table(
            {"class_name": "compact-schedule-table"},
            html.thead(html.tr(html.th("Detalles"), html.th("Equipos"), html.th("Acciones"))),
            html.tbody(
                rows
                if rows
                else html.tr(html.td({"colSpan": 3, "style": {"text_align": "center"}}, "No hay programaciones."))
            ),
        ),
        ConfirmationModal(
            is_open=bool(schedule_to_delete),
            title="Confirmar Eliminación",
            message=f"¿Estás seguro de que quieres eliminar la programación para '{robot_nombre}'?",
            on_confirm=handle_confirm_delete,
            on_cancel=lambda: set_schedule_to_delete(None),
        ),
    )


@component
def ScheduleForm(
    form_data: Dict,
    available_devices: List[Dict],
    is_loading: bool,
    on_submit: Callable,
    on_cancel: Callable,
    on_change: Callable,
):
    tipo = form_data.get("TipoProgramacion")
    schedule_options = use_memo(
        lambda: [
            html.option({"value": schedule_type, "key": schedule_type}, schedule_type)
            for schedule_type in SCHEDULE_TYPES
        ],
        [],
    )

    # Estados para controlar la apertura de los acordeones
    is_general_open, set_general_open = use_state(True)
    is_cyclic_open, set_cyclic_open = use_state(form_data.get("EsCiclico", False))
    is_equipos_open, set_equipos_open = use_state(False)

    def handle_form_change(field, value):
        on_change(field, value)

    def handle_device_change(devices):
        on_change("Equipos", list(devices) if devices else [])

    selected_equipos_count = len(form_data.get("Equipos", []))

    return html._(
        html.form(
            {"id": "schedule-form", "onSubmit": event(on_submit, prevent_default=True)},
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
                    html.label(
                        "Tipo de Programación",
                        html.select(
                            {
                                "value": tipo,
                                "on_change": lambda e: handle_form_change("TipoProgramacion", e["target"]["value"]),
                            },
                            *schedule_options,
                        ),
                    ),
                    html.div(
                        {"class_name": "grid"},
                        html.label(
                            "Hora Inicio",
                            html.input(
                                {
                                    "type": "time",
                                    "value": form_data.get("HoraInicio"),
                                    "on_change": lambda e: handle_form_change("HoraInicio", e["target"]["value"]),
                                }
                            ),
                        ),
                        html.label(
                            "Tolerancia (min)",
                            html.input(
                                {
                                    "type": "number",
                                    "min": "0",
                                    "max": "60",
                                    "value": form_data.get("Tolerancia"),
                                    "on_change": lambda e: handle_form_change(
                                        "Tolerancia", int(e["target"]["value"]) if e["target"]["value"] else 0
                                    ),
                                }
                            ),
                        ),
                        ConditionalFields(tipo, form_data, handle_form_change),
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
                                "on_change": lambda e: handle_form_change("EsCiclico", e["target"]["checked"]),
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
                                        "on_change": lambda e: handle_form_change("HoraFin", e["target"]["value"]),
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
                                        "on_change": lambda e: handle_form_change(
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
                                        "on_change": lambda e: handle_form_change(
                                            "FechaInicioVentana", e["target"]["value"]
                                        ),
                                    }
                                ),
                            ),
                            html.label(
                                "Fecha Fin Ventana",
                                html.input(
                                    {
                                        "type": "date",
                                        "value": form_data.get("FechaFinVentana") or "",
                                        "on_change": lambda e: handle_form_change(
                                            "FechaFinVentana", e["target"]["value"]
                                        ),
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
            # 3. Selección de Equipos
            html.details(
                {"open": is_equipos_open},
                html.summary(
                    {
                        "on_click": lambda e: set_equipos_open(not is_equipos_open),
                        "style": {"fontWeight": "bold", "cursor": "pointer", "marginBottom": "0.5rem"},
                    },
                    f"Selección de Equipos ({selected_equipos_count})",
                ),
                html.div(
                    {"style": {"padding": "1rem 0", "borderTop": "1px solid var(--pico-muted-border-color)"}},
                    DeviceSelector(available_devices, form_data.get("Equipos", []), handle_device_change),
                ),
            ),
        ),
        html.footer(
            html.div(
                {"class_name": "grid"},
                html.button(
                    {
                        "type": "button",
                        "class_name": "secondary",
                        "on_click": lambda e: on_cancel(),
                        "disabled": is_loading,
                    },
                    "Cancelar",
                ),
                html.button(
                    {"type": "submit", "form": "schedule-form", "disabled": is_loading, "aria-busy": is_loading},
                    "Guardar",
                ),
            )
        ),
    )


@component
def ConditionalFields(tipo: str, form_data: Dict, on_change: Callable):
    if tipo == "Semanal":
        return WeekdaySelector(
            value=form_data.get("DiasSemana", ""), on_change=lambda new_string: on_change("DiasSemana", new_string)
        )
    elif tipo == "Mensual":
        return html.label(
            "Día del Mes",
            html.input(
                {
                    "type": "number",
                    "min": 1,
                    "max": 31,
                    "value": form_data.get("DiaDelMes", 1),
                    "on_change": lambda e: on_change(
                        "DiaDelMes", int(e["target"]["value"]) if e["target"]["value"] else 1
                    ),
                }
            ),
        )
    elif tipo == "RangoMensual":
        dia_inicio = form_data.get("DiaInicioMes")
        dia_fin = form_data.get("DiaFinMes")
        ultimos = form_data.get("UltimosDiasMes")
        primeros = form_data.get("PrimerosDiasMes")

        # Deducir opción seleccionada si no existe 'rango_option'
        rango_option = form_data.get("rango_option")
        if not rango_option:
            if ultimos:
                rango_option = "ultimos"
            elif primeros or (dia_inicio == 1 and dia_fin):
                rango_option = "primeros"
            elif dia_inicio and dia_fin:
                rango_option = "rango"

        def set_option(option: str):
            # Actualizamos campo de ayuda y limpiamos los que no aplican
            payload: Dict[str, Any] = {"rango_option": option}
            if option == "rango":
                payload["PrimerosDiasMes"] = None
                payload["UltimosDiasMes"] = None
            elif option == "primeros":
                payload["DiaInicioMes"] = 1
                # Mantener DiaFinMes como N (primeros N días)
                payload["UltimosDiasMes"] = None
            elif option == "ultimos":
                payload["DiaInicioMes"] = None
                payload["DiaFinMes"] = None
                payload["PrimerosDiasMes"] = None
            for k, v in payload.items():
                on_change(k, v)

        return html.div(
            {"class_name": "rango-mensual-options"},
            html.p({"style": {"fontSize": "0.9em", "color": "var(--pico-muted-color)"}}, "Seleccione una opción:"),
            html.label(
                html.input(
                    {
                        "type": "radio",
                        "name": "rango-option",
                        "value": "rango",
                        "checked": rango_option == "rango",
                        "on_change": lambda e: set_option("rango"),
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
                            "min": 1,
                            "max": 31,
                            "value": dia_inicio or "",
                            "placeholder": "1",
                            "on_change": lambda e: on_change(
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
                            "min": 1,
                            "max": 31,
                            "value": dia_fin or "",
                            "placeholder": "10",
                            "on_change": lambda e: on_change(
                                "DiaFinMes", int(e["target"]["value"]) if e["target"]["value"] else None
                            ),
                        }
                    ),
                ),
            )
            if rango_option == "rango"
            else None,
            html.label(
                html.input(
                    {
                        "type": "radio",
                        "name": "rango-option",
                        "value": "primeros",
                        "checked": rango_option == "primeros",
                        "on_change": lambda e: set_option("primeros"),
                    }
                ),
                " Primeros N días del mes",
            ),
            html.label(
                "Cantidad de días",
                html.input(
                    {
                        "type": "number",
                        "min": 1,
                        "max": 31,
                        "value": primeros or (dia_fin if dia_inicio == 1 and dia_fin else ""),
                        "placeholder": "10",
                        "on_change": lambda e: on_change(
                            "PrimerosDiasMes", int(e["target"]["value"]) if e["target"]["value"] else None
                        ),
                    }
                ),
            )
            if rango_option == "primeros"
            else None,
            html.label(
                html.input(
                    {
                        "type": "radio",
                        "name": "rango-option",
                        "value": "ultimos",
                        "checked": rango_option == "ultimos",
                        "on_change": lambda e: set_option("ultimos"),
                    }
                ),
                " Últimos N días del mes",
            ),
            html.label(
                "Cantidad de días",
                html.input(
                    {
                        "type": "number",
                        "min": 1,
                        "max": 31,
                        "value": ultimos or "",
                        "placeholder": "5",
                        "on_change": lambda e: on_change(
                            "UltimosDiasMes", int(e["target"]["value"]) if e["target"]["value"] else None
                        ),
                    }
                ),
            )
            if rango_option == "ultimos"
            else None,
        )
    elif tipo == "Especifica":
        return html.label(
            "Fecha Específica",
            html.input(
                {
                    "type": "date",
                    "value": form_data.get("FechaEspecifica", ""),
                    "on_change": lambda e: on_change("FechaEspecifica", e["target"]["value"]),
                }
            ),
        )
    return html._()


@component
def DeviceSelector(available_devices: List[Dict], selected_devices: List[int], on_change: Callable):
    safe_selected_devices = selected_devices or []
    search_term, set_search_term = use_state("")

    filtered_devices = use_memo(
        lambda: sorted(
            [d for d in available_devices if search_term.lower() in d["Equipo"].lower()],
            key=lambda x: x.get("Equipo", "").lower(),
        ),
        [available_devices, search_term],
    )

    all_filtered_ids = use_memo(lambda: [device["EquipoId"] for device in filtered_devices], [filtered_devices])
    are_all_devices_selected = len(safe_selected_devices) > 0 and all(
        item in safe_selected_devices for item in all_filtered_ids
    )

    def handle_select_all_devices(event):
        on_change(all_filtered_ids if event["target"]["checked"] else [])

    def handle_device_select(device_id, checked):
        current_devices = list(safe_selected_devices)
        if checked:
            if device_id not in current_devices:
                current_devices.append(device_id)
        else:
            if device_id in current_devices:
                current_devices.remove(device_id)
        on_change(current_devices)

    return html.fieldset(
        html.legend(
            "Asignar Equipos ",
            html.span(
                {"style": {"fontSize": "0.8em", "fontWeight": "normal", "color": "var(--pico-muted-color)"}},
                "ℹ️ Info: Los equipos seleccionados aquí trabajarán para esta programación específica, ignorando asignaciones dinámicas.",
            ),
        ),
        html.input(
            {
                "type": "search",
                "name": "search-equipos-schedule",
                "placeholder": "Filtrar equipos...",
                "value": search_term,
                "on_change": lambda e: set_search_term(e["target"]["value"].strip()),
                "style": {"marginBottom": "0.75rem"},
            }
        ),
        html.div(
            {"class_name": "device-list-table", "style": {"height": "200px"}},
            html.table(
                {"role": "grid"},
                html.thead(
                    html.tr(
                        html.th(
                            {"scope": "col", "style": {"width": "40px"}},
                            html.input(
                                {
                                    "type": "checkbox",
                                    "checked": are_all_devices_selected,
                                    "on_change": handle_select_all_devices,
                                }
                            ),
                        ),
                        html.th({"scope": "col"}, "Equipo"),
                    )
                ),
                html.tbody(
                    *[
                        html.tr(
                            {"key": device["EquipoId"]},
                            html.td(
                                html.input(
                                    {
                                        "type": "checkbox",
                                        "checked": device["EquipoId"] in safe_selected_devices,
                                        "on_change": lambda e, tid=device["EquipoId"]: handle_device_select(
                                            tid, e["target"]["checked"]
                                        ),
                                    }
                                )
                            ),
                            html.td(device["Equipo"]),
                        )
                        for device in filtered_devices
                    ]
                    if filtered_devices
                    else [
                        html.tr(
                            html.td(
                                {"colSpan": 2, "style": {"text_align": "center"}},
                                "No se encontraron equipos.",
                            )
                        )
                    ]
                ),
            ),
        ),
    )
