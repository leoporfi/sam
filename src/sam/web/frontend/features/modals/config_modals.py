# src/sam/web/frontend/features/modals/config_modals.py
from typing import Any, Callable, Dict, Optional

from reactpy import component, html, use_effect, use_state


@component
def ConfigEditModal(
    config: Optional[Dict[str, Any]],
    is_open: bool,
    on_close: Callable,
    on_save: Callable[[str, Any], Any],
):
    """Modal para editar un valor de configuración."""
    # Los hooks deben llamarse SIEMPRE en el mismo orden, antes de cualquier return condicional.
    local_value, set_local_value = use_state("")
    is_saving, set_is_saving = use_state(False)
    show_confirm, set_show_confirm = use_state(False)

    @use_effect(dependencies=[config.get("Clave") if config else None])
    def sync_local_value():
        """Sincroniza el valor local cuando cambia la configuración seleccionada."""
        if config:
            set_local_value(config.get("Valor", ""))

    if not is_open or not config:
        return None

    key = config.get("Clave", "")
    current_value = config.get("Valor", "")
    description = config.get("Descripcion", "")

    # Detección de tipo mejorada
    def get_value_type(k, v):
        v_str = str(v).strip().lower()
        # Booleanos: Detectamos si el valor actual parece booleano
        if v_str in ("true", "false", "1", "0"):
            return "boolean"
        # Números: Basado en sufijos comunes o si el valor es puramente numérico
        if (
            k.endswith(("_SEG", "_MIN", "_SIZE", "_COUNT", "_ID", "_PORT", "_VUELTAS", "_MAX", "_PUERTO", "_TAMANO"))
            or v_str.isdigit()
        ):
            return "number"
        # Listas: Basado en sufijos o presencia de comas/punto y coma
        if (
            k.endswith(("_LIST", "_RECIPIENTS", "_EMAILS", "_PROVIDERS", "_DESTINATARIOS"))
            or "," in str(v)
            or ";" in str(v)
        ):
            return "list"
        # JSON: Si empieza con { o [
        if v_str.startswith(("{", "[")):
            return "json"
        return "string"

    val_type = get_value_type(key, current_value)

    def handle_value_change(e):
        new_val = e["target"]["value"]
        set_local_value(new_val)

    def handle_toggle_change(e):
        # Normalizamos siempre a "True" o "False" (Capitalizado) para consistencia
        new_val = "True" if e["target"]["checked"] else "False"
        set_local_value(new_val)

    def get_normalized_value():
        """Retorna el valor local normalizado según el tipo detectado."""
        if val_type == "boolean":
            return "True" if str(local_value).strip().lower() in ("true", "1") else "False"
        if val_type == "number":
            return str(local_value).strip()
        return str(local_value).strip()

    async def handle_save(event=None):
        set_is_saving(True)
        try:
            final_value = get_normalized_value()
            success = await on_save(key, final_value)
            if success:
                on_close()
        finally:
            set_is_saving(False)
            set_show_confirm(False)

    if show_confirm:
        normalized_new_value = get_normalized_value()
        return html.dialog(
            {"open": True},
            html.article(
                html.header(
                    html.h3("Confirmar Cambio"),
                ),
                html.p(f"¿Estás seguro de que deseas cambiar el valor de '{key}'?"),
                html.div(
                    {
                        "style": {
                            "margin": "1rem 0",
                            "padding": "1rem",
                            "background": "rgba(0,0,0,0.05)",
                            "border-radius": "8px",
                        }
                    },
                    html.p(html.strong("Valor anterior: "), html.code(str(current_value))),
                    html.p(html.strong("Nuevo valor: "), html.mark(str(normalized_new_value))),
                ),
                html.footer(
                    html.div(
                        {"class_name": "grid"},
                        html.button(
                            {"class_name": "secondary outline", "on_click": lambda e: set_show_confirm(False)},
                            "Volver",
                        ),
                        html.button(
                            {"on_click": handle_save, "aria-busy": str(is_saving).lower()},
                            "Confirmar y Guardar",
                        ),
                    )
                ),
            ),
        )

    # Renderizado del input según el tipo
    input_element = None
    if val_type == "boolean":
        input_element = html.label(
            {"style": {"display": "flex", "align-items": "center", "gap": "1rem"}},
            html.input(
                {
                    "type": "checkbox",
                    "role": "switch",
                    "checked": str(local_value).lower() in ("true", "1"),
                    "on_change": handle_toggle_change,
                }
            ),
            html.span("Activado" if str(local_value).lower() in ("true", "1") else "Desactivado"),
        )
    elif val_type == "number":
        input_element = html.input(
            {
                "type": "number",
                "value": local_value,
                "on_change": handle_value_change,
                "placeholder": "Ej: 30",
            }
        )
    elif val_type in ("list", "json"):
        input_element = html.textarea(
            {
                "rows": 5 if val_type == "json" else 3,
                "value": local_value,
                "on_change": handle_value_change,
                "placeholder": "ej: admin@empresa.com, soporte@empresa.com"
                if val_type == "list"
                else '{"key": "value"}',
                "style": {"font-family": "monospace", "font-size": "0.9rem"} if val_type == "json" else {},
            }
        )
    else:
        input_element = html.input(
            {
                "type": "text",
                "value": local_value,
                "on_change": handle_value_change,
                "placeholder": "Ingrese el valor...",
            }
        )

    return html.dialog(
        {"open": True},
        html.article(
            html.header(
                html.button(
                    {"aria-label": "Close", "rel": "prev", "on_click": lambda e: on_close()},
                ),
                html.h3(f"Editar Configuración: {key}"),
            ),
            html.div(
                html.p(html.strong("Descripción: "), description),
                html.label({"style": {"margin-top": "1rem"}}, "Valor", input_element),
                html.small(
                    {"style": {"display": "block", "margin-top": "0.5rem"}}, f"Tipo detectado: {val_type.capitalize()}"
                ),
                html.small(
                    {"style": {"display": "block", "margin-top": "1rem", "color": "var(--muted-color)"}},
                    html.span(
                        {
                            "style": {"color": "var(--secondary)", "font-weight": "bold"}
                            if config.get("RequiereReinicio")
                            else {}
                        },
                        "⚠️ Nota: Este cambio requiere el reinicio de los servicios SAM para aplicarse."
                        if config.get("RequiereReinicio")
                        else "✅ Nota: Este cambio es dinámico y se aplicará automáticamente en todos los servicios (máx 60s).",
                    ),
                ),
            ),
            html.footer(
                html.div(
                    {"class_name": "grid"},
                    html.button(
                        {"class_name": "secondary outline", "on_click": lambda e: on_close()},
                        "Cancelar",
                    ),
                    html.button(
                        {
                            "on_click": lambda e: set_show_confirm(True),
                            "aria-busy": str(is_saving).lower(),
                            "disabled": is_saving or str(local_value) == str(current_value),
                        },
                        "Guardar Cambios",
                    ),
                )
            ),
        ),
    )
