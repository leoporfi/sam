# interfaz_web/components/robot_modal.py

from typing import Any, Callable, Dict

import httpx
from reactpy import component, event, html, use_context, use_effect, use_state

from .notifications import NotificationContext
from .styles import BUTTON_STYLES

# Valores por defecto para un robot nuevo
DEFAULT_ROBOT_STATE = {"RobotId": None, "Robot": "", "Descripcion": "", "MinEquipos": 1, "MaxEquipos": -1, "PrioridadBalanceo": 100, "TicketsPorEquipoAdicional": 10}


@component
def RobotEditModal(robot: Dict[str, Any] | None, on_close: Callable, on_save_success: Callable):
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]
    form_data, set_form_data = use_state(DEFAULT_ROBOT_STATE)

    is_loading, set_is_loading = use_state(False)

    # Determina si estamos en modo 'edición' o 'creación'
    is_edit_mode = robot and "RobotId" in robot

    @use_effect(dependencies=[robot])
    def populate_form_data():
        if is_edit_mode:
            print(f"DATOS RECIBIDOS EN EL MODAL: {robot}")
            # Si es modo edición, usamos los datos del robot
            set_form_data(robot)
        else:
            # Si es modo creación, usamos los valores por defecto
            set_form_data(DEFAULT_ROBOT_STATE)

    if robot is None:
        return None

    def handle_form_change(field_name, field_value):
        # Convertir a número si es necesario
        if field_name in ["MinEquipos", "MaxEquipos", "PrioridadBalanceo", "TicketsPorEquipoAdicional"]:
            try:
                # Manejar el caso de un campo vacío en un input numérico
                field_value = int(field_value) if field_value else None
            except (ValueError, TypeError):
                field_value = None
        set_form_data(lambda old_data: {**old_data, field_name: field_value})

    async def handle_save(event):
        show_notification = notification_ctx["show_notification"]
        try:
            payload = form_data.copy()
            async with httpx.AsyncClient() as client:
                if is_edit_mode:
                    # MODO EDICIÓN: Usamos PUT
                    if "RobotId" in payload:
                        payload = {k: v for k, v in form_data.items() if k != "RobotId"}
                    url = f"http://127.0.0.1:8000/api/robots/{robot['RobotId']}"
                    await client.put(url, json=payload)
                    show_notification("Robot actualizado con éxito.", "success")
                else:
                    # MODO CREACIÓN: Usamos POST
                    url = "http://127.0.0.1:8000/api/robots"
                    await client.post(url, json=payload)
                    show_notification("Robot creado con éxito.", "success")

            await on_save_success()
            on_close()

        except Exception as e:
            show_notification(f"Error al guardar: {e}", "error")

    def handle_overlay_click(event):
        if event["target"] == event["currentTarget"]:
            on_close()

    # La UI del modal ahora tiene un título dinámico
    # --- Estilos para botones del tema claro ---
    primary_button_style = "px-4 py-2.5 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700"
    secondary_button_style = "px-4 py-2.5 rounded-lg bg-white text-gray-700 border border-gray-300 hover:bg-gray-50"
    input_style = "form-input bg-gray-50 border border-gray-300 text-gray-900 w-full p-2 rounded-md focus:ring-blue-500 focus:border-blue-500"

    return html.div(
        {"className": "fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4", "onClick": handle_overlay_click},
        html.div(
            {"className": "w-full max-w-2xl rounded-lg bg-white shadow-xl text-gray-900"},
            # Cabecera del modal
            html.div(
                {"className": "border-b border-gray-200 p-6"},
                html.h2({"className": "text-2xl font-semibold"}, f"Editar Robot: {form_data.get('Robot')}" if is_edit_mode else "Crear Nuevo Robot"),
                html.p({"className": "mt-1 text-sm text-gray-500"}, "Modifica las propiedades del robot." if is_edit_mode else "Alta robot."),
            ),
            # Formulario
            html.form(
                {"className": "space-y-6 p-6", "onSubmit": event(handle_save, prevent_default=True)},
                # Campos del formulario con nuevos estilos
                html.div(
                    {"style": {"display": "block" if not is_edit_mode else "none"}},
                    html.label({"htmlFor": "robot-id", "className": "block text-sm font-medium pb-1.5"}, "Robot ID (de A360)"),
                    html.input(
                        {
                            "id": "robot-id",
                            "type": "number",
                            "className": input_style,
                            "value": form_data.get("RobotId", ""),
                            "onChange": lambda e: handle_form_change("RobotId", e["target"]["value"]),
                            "required": not is_edit_mode,  # Requerido solo en creación
                        }
                    ),
                ),
                html.div(
                    html.label({"htmlFor": "robot-name", "className": "block text-sm font-medium pb-1.5"}, "Nombre"),
                    html.input(
                        {
                            "id": "robot-name",
                            "type": "text",
                            "className": input_style,
                            "value": form_data.get("Robot", ""),
                            "onChange": lambda e: handle_form_change("Robot", e["target"]["value"]),
                            # "readonly": is_edit_mode,
                            "disabled": is_edit_mode,
                        }
                    ),
                ),
                html.div(
                    html.label({"htmlFor": "robot-desc", "className": "block text-sm font-medium pb-1.5"}, "Descripción"),
                    html.textarea(
                        {
                            "id": "robot-desc",
                            "type": "text",
                            "rows": 3,
                            "className": input_style,
                            "value": form_data.get("Descripcion", ""),
                            "onChange": lambda e: handle_form_change("Descripcion", e["target"]["value"]),
                        }
                    ),
                ),
                html.div(
                    {"className": "grid grid-cols-1 sm:grid-cols-2 gap-6 font-medium pb-1.5"},
                    html.div(
                        html.label({"htmlFor": "min-equipos"}, "Mín. Equipos"),
                        html.input(
                            {
                                "id": "min-equipos",
                                "type": "number",
                                "className": input_style,
                                "value": form_data.get("MinEquipos", ""),
                                "onChange": lambda e: handle_form_change("MinEquipos", e["target"]["value"]),
                            }
                        ),
                    ),
                    html.div(
                        html.label({"htmlFor": "max-equipos"}, "Máx. Equipos"),
                        html.input(
                            {
                                "id": "max-equipos",
                                "type": "number",
                                "className": input_style,
                                "value": form_data.get("MaxEquipos", ""),
                                "onChange": lambda e: handle_form_change("MaxEquipos", e["target"]["value"]),
                            }
                        ),
                    ),
                    html.div(
                        html.label({"htmlFor": "prioridad"}, "Prioridad"),
                        html.input(
                            {
                                "id": "prioridad",
                                "type": "number",
                                "className": input_style,
                                "value": form_data.get("PrioridadBalanceo", ""),
                                "onChange": lambda e: handle_form_change("PrioridadBalanceo", e["target"]["value"]),
                            }
                        ),
                    ),
                    html.div(
                        html.label({"htmlFor": "tickets"}, "Tickets Máximos por Equipo"),
                        html.input(
                            {
                                "id": "tickets",
                                "type": "number",
                                "className": input_style,
                                "value": form_data.get("TicketsPorEquipoAdicional", ""),
                                "onChange": lambda e: handle_form_change("TicketsPorEquipoAdicional", e["target"]["value"]),
                            }
                        ),
                    ),
                ),
                # Botones de acción
                html.div(
                    {"className": "flex justify-end gap-3 pt-4"},
                    html.button(
                        {"type": "button", "className": BUTTON_STYLES["secondary"], "disabled": is_loading, "onClick": lambda e: on_close()},
                        "Cancelar",
                    ),
                    html.button({"type": "submit", "className": BUTTON_STYLES["primary"], "disabled": is_loading}, "Guardar Cambios"),
                ),
            ),
        ),
    )
