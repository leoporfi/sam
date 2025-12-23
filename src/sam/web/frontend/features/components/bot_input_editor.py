# sam/web/frontend/features/components/bot_input_editor.py
"""
Componente para editar los parámetros de bot_input de forma amigable.
Permite agregar/eliminar variables y configurar sus tipos y valores sin necesidad de conocer JSON.
"""

import json
from typing import Any, Callable, Dict, List, Optional

from reactpy import component, event, html, use_callback, use_effect, use_state

# Tipos de datos soportados por la API de Automation Anywhere
AA360_ATTRIBUTE_TYPES = [
    "STRING",
    "NUMBER",
    "BOOLEAN",
    # "FILE",
    # "ITERATOR",
    "LIST",
    "DICTIONARY",
    # "TABLE",
    # "VARIABLE",
    # "CONDITIONAL",
    # "WINDOW",
    # "TASKBOT",
    # "DATETIME",
    # "UIOBJECT",
    # "RECORD",
    # "EXCEPTION",
    # "CREDENTIAL",
    # "COORDINATE",
    # "IMAGE",
    # "REGION",
    # "PROPERTIES",
    # "TRIGGER",
    # "CONDITIONALGROUP",
    # "FORM",
    # "FORMELEMENT",
    # "HOTKEY",
    # "WORKITEM",
]

# Tipos más comunes (mostrados primero)
COMMON_TYPES = ["STRING", "NUMBER", "BOOLEAN", "LIST", "DICTIONARY"]


def parse_bot_input_json(json_str: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """
    Parsea el JSON de parámetros y retorna un diccionario de variables.
    Retorna un diccionario vacío si hay error o está vacío.
    """
    if not json_str or not json_str.strip():
        return {}

    try:
        parsed = json.loads(json_str)
        if isinstance(parsed, dict):
            return parsed
        return {}
    except json.JSONDecodeError:
        return {}


def build_bot_input_json(variables: Dict[str, Dict[str, Any]]) -> str:
    """
    Construye el JSON string a partir del diccionario de variables.
    """
    if not variables:
        return ""

    try:
        return json.dumps(variables, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return ""


def validate_variable_value(var_type: str, value: str) -> tuple[bool, Optional[str]]:
    """
    Valida que el valor sea correcto para el tipo especificado.
    Retorna (es_valido, mensaje_error)
    """
    if not value or not value.strip():
        return (False, "El valor no puede estar vacío")

    if var_type == "NUMBER":
        try:
            float(value)
        except ValueError:
            return (False, "El valor debe ser un número válido")
    elif var_type == "BOOLEAN":
        if value.lower() not in ("true", "false", "1", "0", "yes", "no"):
            return (False, "El valor debe ser true/false, 1/0, o yes/no")

    return (True, None)


def get_variable_display_value(var_obj: Dict[str, Any]) -> str:
    """
    Obtiene el valor a mostrar para una variable según su tipo.
    """
    var_type = var_obj.get("type", "STRING")

    if var_type == "NUMBER":
        return var_obj.get("number", "")
    elif var_type == "BOOLEAN":
        return var_obj.get("boolean", "")
    else:
        return var_obj.get("string", "")


@component
def BotInputEditor(value: Optional[str], on_change: Callable):
    """
    Editor amigable para los parámetros de bot_input.

    Args:
        value: JSON string con los parámetros actuales
        on_change: Callback que recibe el nuevo JSON string cuando cambia
    """
    # Parsear el JSON inicial
    initial_vars = parse_bot_input_json(value)

    # Estado: diccionario de variables {nombre_variable: {type: "...", value: "..."}}
    variables, set_variables = use_state(initial_vars)

    # Actualizar variables cuando cambia el value externo
    def sync_with_external_value():
        parsed = parse_bot_input_json(value)
        if parsed != variables:
            set_variables(parsed)

    use_effect(sync_with_external_value, dependencies=[value])

    # Estado para nueva variable
    new_var_name, set_new_var_name = use_state("")
    new_var_type, set_new_var_type = use_state("NUMBER")
    new_var_value, set_new_var_value = use_state("")
    new_var_error, set_new_var_error = use_state(None)

    def update_json_output(vars_dict=None):
        """Actualiza el JSON de salida cuando cambian las variables."""
        vars_to_use = vars_dict if vars_dict is not None else variables
        json_output = build_bot_input_json(vars_to_use)
        on_change(json_output)

    def handle_add_variable(event_data=None):
        """Agrega una nueva variable a la lista."""
        if not new_var_name or not new_var_name.strip():
            set_new_var_error("El nombre de la variable es requerido")
            return

        var_name = new_var_name.strip()

        # Verificar que no exista ya
        if var_name in variables:
            set_new_var_error(f"La variable '{var_name}' ya existe")
            return

        # Validar el valor según el tipo
        is_valid, error_msg = validate_variable_value(new_var_type, new_var_value)
        if not is_valid:
            set_new_var_error(error_msg)
            return

        # Construir el objeto de la variable según el tipo
        var_obj = {"type": new_var_type}

        if new_var_type == "STRING":
            var_obj["string"] = new_var_value
        elif new_var_type == "NUMBER":
            var_obj["number"] = new_var_value  # La API espera string
        elif new_var_type == "BOOLEAN":
            # Normalizar a "true" o "false"
            bool_val = new_var_value.lower()
            if bool_val in ("1", "yes", "true"):
                var_obj["boolean"] = "true"
            else:
                var_obj["boolean"] = "false"
        else:
            # Para otros tipos, usar "string" como valor por defecto
            var_obj["string"] = new_var_value

        # Crear el nuevo diccionario de variables
        new_variables = {**variables, var_name: var_obj}

        # Actualizar el estado
        set_variables(new_variables)

        # Limpiar el formulario
        set_new_var_name("")
        set_new_var_value("")
        set_new_var_type("STRING")
        set_new_var_error(None)

        # Actualizar el JSON de salida con el nuevo diccionario directamente
        update_json_output(new_variables)

    def handle_remove_variable(var_name: str):
        """Elimina una variable de la lista."""
        new_variables = {k: v for k, v in variables.items() if k != var_name}
        set_variables(new_variables)
        update_json_output(new_variables)

    def handle_value_change(var_name: str, new_value: str):
        """Actualiza el valor de una variable existente."""
        if var_name not in variables:
            return

        # Aplicar trim automático a valores de texto
        if isinstance(new_value, str):
            new_value = new_value.strip()

        var_obj = variables[var_name].copy()
        var_type = var_obj.get("type", "STRING")

        # Validar el nuevo valor
        is_valid, error_msg = validate_variable_value(var_type, new_value)
        if not is_valid:
            # Aún así permitimos el cambio, pero mostramos el error
            set_new_var_error(f"Advertencia: {error_msg}")

        # Actualizar el campo correspondiente según el tipo
        if var_type == "STRING":
            var_obj["string"] = new_value
        elif var_type == "NUMBER":
            var_obj["number"] = new_value
        elif var_type == "BOOLEAN":
            bool_val = new_value.lower()
            if bool_val in ("1", "yes", "true"):
                var_obj["boolean"] = "true"
            else:
                var_obj["boolean"] = "false"
        else:
            var_obj["string"] = new_value

        new_variables = {**variables, var_name: var_obj}
        set_variables(new_variables)
        update_json_output(new_variables)

    # Construir la lista de opciones de tipos
    type_options = []
    # Primero los comunes
    for t in COMMON_TYPES:
        if t in AA360_ATTRIBUTE_TYPES:
            type_options.append(html.option({"value": t, "key": f"common-{t}"}, t))

    # Luego los demás
    for t in AA360_ATTRIBUTE_TYPES:
        if t not in COMMON_TYPES:
            type_options.append(html.option({"value": t, "key": t}, t))

    return html.div(
        {"class_name": "bot-input-editor"},
        html.small(
            {
                "style": {
                    "display": "block",
                    "marginBottom": "1rem",
                    "color": "var(--pico-muted-color)",
                }
            },
            "Configure las variables que se enviarán al bot cuando se ejecute. Si no se configuran, se usará el valor por defecto del sistema.",
        ),
        # Lista de variables existentes
        html.div(
            {"class_name": "bot-input-variables-list", "style": {"marginBottom": "1.5rem"}},
            *[
                html.div(
                    {
                        "key": var_name,
                        "class_name": "bot-input-variable-item",
                        "style": {
                            "display": "grid",
                            "gridTemplateColumns": "2fr 1fr 2fr auto",
                            "gap": "0.5rem",
                            "alignItems": "center",
                            "padding": "0.5rem",
                            "border": "1px solid var(--pico-border-color)",
                            "borderRadius": "var(--pico-border-radius)",
                            "marginBottom": "0.5rem",
                        },
                    },
                    html.strong(var_name),
                    html.span(
                        {
                            "style": {
                                "fontSize": "0.85em",
                                "color": "var(--pico-muted-color)",
                            }
                        },
                        var_obj.get("type", "STRING"),
                    ),
                    html.input(
                        {
                            "type": "text",
                            "name": f"bot-input-value-{var_name}",
                            "value": get_variable_display_value(var_obj),
                            "placeholder": "Valor...",
                            "on_change": lambda e, vn=var_name: handle_value_change(vn, e["target"]["value"]),
                            "style": {"fontSize": "0.9em"},
                        }
                    ),
                    html.button(
                        {
                            "type": "button",
                            "class_name": "secondary outline",
                            "on_click": lambda e, vn=var_name: handle_remove_variable(vn),
                            "aria_label": f"Eliminar {var_name}",
                            "style": {"padding": "0.25rem 0.5rem"},
                        },
                        html.i({"class_name": "fa-solid fa-trash"}),
                    ),
                )
                for var_name, var_obj in variables.items()
            ]
            if variables
            else [
                html.p(
                    {
                        "style": {
                            "textAlign": "center",
                            "color": "var(--pico-muted-color)",
                            "fontStyle": "italic",
                        }
                    },
                    "No hay variables configuradas. Agregue una nueva variable abajo.",
                )
            ],
        ),
        # Formulario para agregar nueva variable
        html.div(
            {"class_name": "bot-input-add-form"},
            html.h6("Agregar Nueva Variable"),
            html.div(
                {
                    "class_name": "grid",
                    "style": {"gridTemplateColumns": "2fr 1fr 2fr auto", "gap": "0.5rem", "alignItems": "end"},
                },
                html.label(
                    "Nombre de Variable",
                    html.input(
                        {
                            "type": "text",
                            "name": "bot-input-var-name",
                            "placeholder": "Ej: in_NumRepeticion",
                            "value": new_var_name,
                            "on_change": lambda e: (set_new_var_name(e["target"]["value"].strip()), set_new_var_error(None)),
                        }
                    ),
                ),
                html.label(
                    "Tipo",
                    html.select(
                        {
                            "name": "bot-input-var-type",
                            "value": new_var_type,
                            "on_change": lambda e: set_new_var_type(e["target"]["value"]),
                        },
                        *type_options,
                    ),
                ),
                html.label(
                    "Valor",
                    html.input(
                        {
                            "type": "text" if new_var_type != "NUMBER" else "number",
                            "name": "bot-input-var-value",
                            "placeholder": "Valor..." if new_var_type != "BOOLEAN" else "true/false",
                            "value": new_var_value,
                            "on_change": lambda e: (
                                set_new_var_value(e["target"]["value"].strip() if isinstance(e["target"]["value"], str) else e["target"]["value"]),
                                set_new_var_error(None),
                            ),
                        }
                    ),
                ),
                html.button(
                    {
                        "type": "button",
                        "on_click": event(handle_add_variable, prevent_default=True),
                        "title": "Agregar variable",
                    },
                    html.i({"class_name": "fa-solid fa-plus"}),
                    " Agregar",
                ),
            ),
            html.small(
                {
                    "style": {
                        "display": "block",
                        "marginTop": "0.5rem",
                        "color": "var(--pico-muted-color)",
                    }
                },
                "Tipos comunes: STRING (texto), NUMBER (número), BOOLEAN (true/false). "
                "El nombre debe coincidir con el nombre de la variable en el bot de A360.",
            ),
            new_var_error
            and html.div(
                {
                    "class_name": "bot-input-error",
                    "style": {
                        "marginTop": "0.5rem",
                        "padding": "0.5rem",
                        "backgroundColor": "var(--pico-del-color)",
                        "color": "var(--pico-del-ins-color)",
                        "borderRadius": "var(--pico-border-radius)",
                    },
                },
                html.i({"class_name": "fa-solid fa-exclamation-triangle"}),
                " ",
                new_var_error,
            ),
        ),
    )
