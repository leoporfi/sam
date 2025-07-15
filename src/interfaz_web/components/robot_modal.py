# src/interfaz_web/components/robot_modal.py

from typing import Any, Callable, Dict

import httpx
from reactpy import component, event, html, use_context, use_effect, use_state

from ..client.api_service import get_api_service
from ..client.config.settings import Settings
from .notifications import NotificationContext

URL_BASE = Settings.API_BASE_URL

DEFAULT_ROBOT_STATE = {
    "RobotId": None,
    "Robot": "",
    "Descripcion": "",
    "Activo": True,  # Campo requerido para la creación
    "EsOnline": False,  # Campo requerido para la creación
    "MinEquipos": 1,
    "MaxEquipos": -1,
    "PrioridadBalanceo": 100,
    "TicketsPorEquipoAdicional": 10,
}


@component
def RobotEditModal(robot: Dict[str, Any] | None, on_close: Callable, on_save_success: Callable):
    form_data, set_form_data = use_state(DEFAULT_ROBOT_STATE)
    is_loading, set_is_loading = use_state(False)
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    #  Usar la instancia del servicio de API
    api_service = get_api_service()
    is_edit_mode = bool(robot and robot.get("RobotId") is not None)

    @use_effect(dependencies=[robot])
    def populate_form_data():
        if robot is not None:
            # Si es un objeto vacío (crear), usa el default. Si tiene datos (editar), lo puebla.
            set_form_data(robot if is_edit_mode else DEFAULT_ROBOT_STATE)

    if robot is None:
        return None

    def handle_form_change(field_name, field_value):
        if field_name in ["RobotId", "MinEquipos", "MaxEquipos", "PrioridadBalanceo", "TicketsPorEquipoAdicional"]:
            try:
                field_value = int(field_value) if field_value != "" else None
            except (ValueError, TypeError):
                field_value = None
        set_form_data(lambda old_data: {**old_data, field_name: field_value})

    async def handle_save(event_data):
        set_is_loading(True)

        try:
            if is_edit_mode:
                # El payload para actualizar debe coincidir con el modelo RobotUpdateRequest
                payload_to_send = {
                    "Robot": form_data.get("Robot"),
                    "Descripcion": form_data.get("Descripcion"),
                    "MinEquipos": form_data.get("MinEquipos"),
                    "MaxEquipos": form_data.get("MaxEquipos"),
                    "PrioridadBalanceo": form_data.get("PrioridadBalanceo"),
                    "TicketsPorEquipoAdicional": form_data.get("TicketsPorEquipoAdicional"),
                }
                await api_service.update_robot(robot["RobotId"], payload_to_send)
                show_notification("Robot actualizado con éxito.", "success")
            else:
                # El payload para crear debe coincidir con RobotCreateRequest
                # Validar que el RobotId no esté vacío
                if not form_data.get("RobotId"):
                    show_notification("El campo 'Robot ID' es requerido.", "error")
                    set_is_loading(False)
                    return

                await api_service.create_robot(form_data)
                show_notification("Robot creado con éxito.", "success")

            await on_save_success()
        except Exception as e:
            show_notification(str(e), "error")
        finally:
            set_is_loading(False)

    return html.dialog(
        {"open": True if robot is not None else False},
        html.article(
            html.header(
                html.button({"aria-label": "Close", "rel": "prev", "onClick": event(on_close, prevent_default=True)}),
                html.h2("Editar Robot") if is_edit_mode else html.h2("Crear Nuevo Robot"),
            ),
            html.form(
                {"id": "robot-form", "onSubmit": event(handle_save, prevent_default=True)},
                html.div(
                    {"className": "grid"},
                    # Campo Nombre
                    html.label(
                        {"htmlFor": "robot-name"},
                        "Nombre",
                        html.input(
                            {
                                "id": "robot-name",
                                "type": "text",
                                "value": form_data.get("Robot", ""),
                                "onChange": lambda e: handle_form_change("Robot", e["target"]["value"]),
                                "required": True,
                            }
                        ),
                    ),
                    # Campo Robot ID
                    html.label(
                        {"htmlFor": "robot-id"},
                        "Robot ID (de A360)",
                        html.input(
                            {
                                "id": "robot-id",
                                "type": "number",
                                "value": form_data.get("RobotId", ""),
                                "onChange": lambda e: handle_form_change("RobotId", e["target"]["value"]),
                                "required": not is_edit_mode,
                                "disabled": is_edit_mode,
                            }
                        ),
                    ),
                ),
                # Campo Descripción
                html.label(
                    {"htmlFor": "robot-desc"},
                    "Descripción",
                    html.textarea(
                        {
                            "id": "robot-desc",
                            "rows": 3,
                            "value": form_data.get("Descripcion", ""),
                            "onChange": lambda e: handle_form_change("Descripcion", e["target"]["value"]),
                        }
                    ),
                ),
                html.div(
                    {"className": "grid"},
                    html.label(
                        {"htmlFor": "min-equipos"},
                        "Mín. Equipos",
                        html.div(
                            {"className": "range"},
                            html.output(
                                form_data.get("MinEquipos", "0"),
                            ),
                            html.input(
                                {
                                    "id": "min-equipos",
                                    "type": "range",
                                    "min": "0",
                                    "max": "99",
                                    "value": form_data.get("MinEquipos", ""),
                                    "onChange": lambda e: handle_form_change("MinEquipos", e["target"]["value"]),
                                    "style": {"flexGrow": "1"},
                                }
                            ),
                        ),
                    ),
                    html.label(
                        {"htmlFor": "max-equipos"},
                        "Máx. Equipos",
                        html.div(
                            {"className": "range"},
                            html.output(
                                form_data.get("MaxEquipos", "0"),
                            ),
                            html.input(
                                {
                                    "id": "max-equipos",
                                    "type": "range",
                                    "min": "-1",
                                    "max": "100",
                                    "value": form_data.get("MaxEquipos", ""),
                                    "onChange": lambda e: handle_form_change("MaxEquipos", e["target"]["value"]),
                                    "style": {"flexGrow": "1"},
                                }
                            ),
                        ),
                    ),
                ),
                html.div(
                    {"className": "grid"},
                    html.label(
                        {"htmlFor": "prioridad"},
                        "Prioridad",
                        html.div(
                            {"className": "range"},
                            html.output(
                                {"className": "button"},
                                form_data.get("PrioridadBalanceo", "0"),
                            ),
                            html.input(
                                {
                                    "id": "prioridad",
                                    "type": "range",
                                    "min": "0",
                                    "max": "100",
                                    "step": "10",
                                    "value": form_data.get("PrioridadBalanceo", ""),
                                    "onChange": lambda e: handle_form_change("PrioridadBalanceo", e["target"]["value"]),
                                    "style": {"flexGrow": "1"},
                                }
                            ),
                        ),
                    ),
                    html.label(
                        {"htmlFor": "tickets"},
                        "Tickets/Equipo Adic.",
                        html.div(
                            {"className": "range"},
                            html.output(
                                form_data.get("TicketsPorEquipoAdicional", "0"),
                            ),
                            html.input(
                                {
                                    "id": "tickets",
                                    "type": "range",
                                    "min": "1",
                                    "max": "100",
                                    "value": form_data.get("TicketsPorEquipoAdicional", ""),
                                    "onChange": lambda e: handle_form_change("TicketsPorEquipoAdicional", e["target"]["value"]),
                                    "style": {"flexGrow": "1"},
                                }
                            ),
                        ),
                    ),
                ),
            ),
            html.footer(
                html.div(
                    {"className": "grid"},
                    html.button({"type": "button", "className": "secondary", "onClick": on_close, "disabled": is_loading}, "Cancelar"),
                    html.button({"type": "submit", "form": "robot-form", "aria-busy": str(is_loading).lower(), "disabled": is_loading}, "Guardar"),
                )
            ),
        ),
    )
