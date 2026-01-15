# sam/web/features/modals/equipos_modals.py
import asyncio
from typing import Any, Callable, Dict, Optional

from reactpy import component, event, html, use_context, use_effect, use_state

from ...api.api_client import get_api_client
from ...shared.notifications import NotificationContext

# Estado inicial para el formulario de creación/edición de equipos
DEFAULT_EQUIPO_STATE = {
    "EquipoId": None,
    "Equipo": "",
    "UserId": None,
    "UserName": "",
    "Licencia": "RUNTIME",  # Valor común por defecto
    # Campos no editables manualmente aquí (vienen de sync o estado)
    # "Activo_SAM": True,
    # "PermiteBalanceoDinamico": False,
    # "RobotAsignado": None,
    # "Pool": None,
}

LICENCIA_OPTIONS = ["RUNTIME", "ATTENDEDRUNTIME", "NONE"]  # Opciones comunes


@component
def EquipoEditModal(
    equipo: Optional[Dict[str, Any]],  # Recibe None para crear, o datos para editar
    is_open: bool,
    on_close: Callable,
    on_save_success: Callable,  # Callback para refrescar la lista
):
    """Modal para crear o editar un Equipo manualmente."""
    form_data, set_form_data = use_state(DEFAULT_EQUIPO_STATE)
    is_loading, set_is_loading = use_state(False)
    error, set_error = use_state("")
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]
    # Obtener api_client del contexto
    try:
        from ...state.app_context import use_app_context

        app_context = use_app_context()
        api_client = app_context.get("api_client") or get_api_client()
    except Exception:
        api_client = get_api_client()

    # Determinar si estamos en modo creación o edición
    # Por ahora, este modal SOLO crea, así que is_edit_mode siempre será False
    is_edit_mode = False  # bool(equipo and equipo.get("EquipoId"))

    # Efecto para inicializar/resetear el formulario cuando 'equipo' o 'is_open' cambian
    @use_effect(dependencies=[equipo, is_open])
    def sync_form_state():
        if is_open:
            if is_edit_mode:
                # Si implementáramos edición, aquí cargaríamos los datos
                # set_form_data(equipo)
                set_form_data(DEFAULT_EQUIPO_STATE)  # Temporalmente resetea incluso en 'edit'
            else:
                # Modo creación: asegurar que el estado es el inicial
                set_form_data(DEFAULT_EQUIPO_STATE)
            set_error("")  # Limpiar errores al abrir/cambiar
        else:
            # Opcional: resetear al cerrar si prefieres
            # set_form_data(DEFAULT_EQUIPO_STATE)
            set_error("")

    def handle_change(field: str, value: Any):
        """Actualiza el estado del formulario."""
        set_error("")  # Limpiar error al empezar a escribir

        # Aplicar trim automático a campos de texto (excepto números)
        if field not in ["EquipoId", "UserId"]:
            if isinstance(value, str):
                value = value.strip()
            elif value is None:
                value = ""

        # Convertir IDs a int si es posible, manejar vacío
        if field in ["EquipoId", "UserId"]:
            try:
                value = int(value) if value else None
            except ValueError:
                value = None  # Mantener None si no es un número válido

        set_form_data(lambda old: {**old, field: value})

    async def handle_submit(event_data):
        """Maneja el envío del formulario."""
        set_error("")
        # Validación básica
        if not form_data.get("EquipoId") or form_data["EquipoId"] <= 0:
            set_error("El ID del Equipo (de A360) es requerido y debe ser positivo.")
            return
        if not form_data.get("Equipo") or not form_data["Equipo"].strip():
            set_error("El Nombre del Equipo (hostname) es requerido.")
            return
        if not form_data.get("UserId") or form_data["UserId"] <= 0:
            set_error("El ID del Usuario (de A360) es requerido y debe ser positivo.")
            return

        set_is_loading(True)
        try:
            payload = {
                "EquipoId": form_data["EquipoId"],
                "Equipo": form_data["Equipo"].strip(),
                "UserId": form_data["UserId"],
                "UserName": form_data.get("UserName", "").strip() or None,
                "Licencia": form_data.get("Licencia") if form_data.get("Licencia") != "NONE" else None,
                # "Activo": form_data.get("Activo", True) # Si tu API lo soporta
            }
            if is_edit_mode:
                # Lógica de actualización (si se implementa)
                # await api_client.update_equipo(equipo["EquipoId"], payload)
                # show_notification("Equipo actualizado con éxito.", "success")
                pass  # Por ahora, no hay edición
            else:
                await api_client.create_equipo(payload)
                show_notification("Equipo creado con éxito.", "success")

            await on_save_success()  # Refrescar lista en la página
            set_is_loading(False)
            on_close()
        except asyncio.CancelledError:
            # Silenciar errores de cancelación y NO actualizar estado
            pass
        except Exception as e:
            error_message = str(e)
            # Intentar extraer el 'detail' si es una APIException
            if hasattr(e, "message") and "Error en la API:" in e.message:
                error_message = e.message.split("Error en la API:", 1)[-1].strip()
            set_error(f"Error al guardar: {error_message}")
            show_notification(f"Error al guardar: {error_message}", "error")
            set_is_loading(False)

    # No renderizar si no está abierto
    if not is_open:
        return html.dialog({"open": False, "style": {"display": "none"}})

    return html.dialog(
        {"open": True},
        html.article(
            html.header(
                html.button({"aria-label": "Close", "rel": "prev", "on_click": lambda e: on_close()}),
                # Cambiar título según modo
                html.h2("Crear Nuevo Equipo"),  # if not is_edit_mode else "Editar Equipo"
            ),
            html.form(
                {"id": "equipo-form", "onSubmit": event(handle_submit, prevent_default=True)},
                # --- Campos del Formulario ---
                html.div(
                    {"class_name": "grid"},
                    html.label(
                        "ID Equipo (A360)",
                        html.input(
                            {
                                "type": "number",
                                "name": "equipo_id",
                                "placeholder": "Ej: 123",
                                "value": form_data.get("EquipoId") or "",
                                "on_change": lambda e: handle_change("EquipoId", e["target"]["value"]),
                                "required": True,
                                "min": "1",
                                "disabled": is_edit_mode,  # ID no editable
                            }
                        ),
                    ),
                    html.label(
                        "ID Usuario (A360)",
                        html.input(
                            {
                                "type": "number",
                                "name": "user_id",
                                "placeholder": "Ej: 456",
                                "value": form_data.get("UserId") or "",
                                "on_change": lambda e: handle_change("UserId", e["target"]["value"]),
                                "required": True,
                                "min": "1",
                            }
                        ),
                    ),
                ),
                html.label(
                    "Nombre Equipo (Hostname)",
                    html.input(
                        {
                            "type": "text",
                            "name": "equipo_nombre",
                            "placeholder": "Ej: RPA-BOT-001",
                            "value": form_data.get("Equipo") or "",
                            "on_change": lambda e: handle_change("Equipo", e["target"]["value"]),
                            "required": True,
                        }
                    ),
                ),
                html.div(
                    {"class_name": "grid"},
                    html.label(
                        "Nombre Usuario (A360)",
                        # --- CORRECCIÓN: Atributos dentro de un dict ---
                        html.input(
                            {
                                "type": "text",
                                "name": "user_name",
                                "placeholder": "Ej: bot.runner",
                                "value": form_data.get("UserName") or "",
                                "on_change": lambda e: handle_change("UserName", e["target"]["value"]),
                            }
                        ),
                    ),
                    html.label(
                        "Licencia",
                        # --- CORRECCIÓN: Atributos dentro de un dict ---
                        html.select(
                            {
                                "value": form_data.get("Licencia", "NONE"),
                                "on_change": lambda e: handle_change("Licencia", e["target"]["value"]),
                            },
                            # Los hijos (options) van DESPUÉS del dict
                            [html.option({"value": lic}, lic) for lic in LICENCIA_OPTIONS],
                        ),
                    ),
                ),
                # --- Mostrar Mensaje de Error ---
                html.p({"style": {"color": "var(--pico-color-red-600)"}}, error) if error else None,
            ),
            # --- Footer con Botones ---
            html.footer(
                html.div(
                    {"class_name": "grid"},
                    # --- CORRECCIÓN: Atributos dentro de un dict ---
                    html.button(
                        {
                            "type": "button",
                            "class_name": "secondary",
                            "on_click": lambda e: on_close(),
                            "disabled": is_loading,
                        },
                        "Cancelar",
                    ),
                    # --- CORRECCIÓN: Atributos dentro de un dict ---
                    html.button(
                        {
                            "type": "submit",
                            "form": "equipo-form",
                            "aria-busy": str(is_loading).lower(),
                            "disabled": is_loading,
                        },
                        "Procesando..." if is_loading else "Guardar",
                    ),
                )
            ),
        ),
    )
