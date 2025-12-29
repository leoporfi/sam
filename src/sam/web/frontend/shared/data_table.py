# sam/web/frontend/shared/data_table.py
"""
Componente DataTable genérico y reutilizable.

Este módulo proporciona un componente de tabla genérico que puede ser usado
en toda la aplicación para mostrar listas de datos de manera consistente.

Uso:
    from sam.web.frontend.shared.data_table import DataTable

    columns = [
        {"key": "name", "label": "Nombre", "render": lambda row: row["name"]},
        {"key": "status", "label": "Estado", "render": lambda row: StatusBadge(row["status"])},
    ]

    return DataTable(
        data=robots,
        columns=columns,
        loading=is_loading,
        on_row_click=lambda row: handle_click(row),
        empty_message="No hay robots disponibles"
    )
"""

from typing import Any, Callable, Dict, List, Optional

from reactpy import component, event, html

from .async_content import AsyncContent, EmptyState, ErrorAlert, LoadingSpinner


@component
def DataTable(
    data: List[Dict[str, Any]],
    columns: List[Dict[str, Any]],
    loading: bool = False,
    error: Optional[str] = None,
    on_row_click: Optional[Callable] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    empty_message: str = "No hay datos disponibles",
    sort_by: Optional[str] = None,
    sort_dir: Optional[str] = None,
    on_sort: Optional[Callable] = None,
    row_key: Optional[Callable] = None,
    row_class_name: Optional[Callable] = None,
) -> html.article:
    """
    Tabla genérica reutilizable para listados de datos.

    Args:
        data: Lista de diccionarios con los datos a mostrar
        columns: Lista de definiciones de columnas. Cada columna debe tener:
            - "key": clave del dato en el row
            - "label": etiqueta a mostrar en el header
            - "render": (opcional) función para renderizar el contenido
            - "sortable": (opcional) si la columna es ordenable (default: True)
        loading: Si True, muestra estado de carga
        error: Mensaje de error a mostrar
        on_row_click: Callback cuando se hace click en una fila
        actions: Lista de acciones a mostrar en columna adicional
        empty_message: Mensaje a mostrar cuando no hay datos
        sort_by: Clave de la columna por la que se está ordenando
        sort_dir: Dirección del ordenamiento ("asc" o "desc")
        on_sort: Callback cuando se hace click en un header ordenable
        row_key: Función para generar la key única de cada fila (default: usa "id" o índice)
        row_class_name: Función para generar la clase CSS de cada fila

    Returns:
        Componente ReactPy con la tabla
    """
    # Manejar estados async con AsyncContent
    return AsyncContent(
        loading=loading,
        error=error,
        data=data,
        loading_component=LoadingSpinner(),
        error_component=ErrorAlert(message=error) if error else None,
        empty_component=EmptyState(message=empty_message),
        children=_render_table(
            data=data,
            columns=columns,
            on_row_click=on_row_click,
            actions=actions,
            sort_by=sort_by,
            sort_dir=sort_dir,
            on_sort=on_sort,
            row_key=row_key,
            row_class_name=row_class_name,
            empty_message=empty_message,
        ),
    )


def _render_table(
    data: List[Dict[str, Any]],
    columns: List[Dict[str, Any]],
    on_row_click: Optional[Callable] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    sort_by: Optional[str] = None,
    sort_dir: Optional[str] = None,
    on_sort: Optional[Callable] = None,
    row_key: Optional[Callable] = None,
    row_class_name: Optional[Callable] = None,
    empty_message: str = "No hay datos disponibles",
) -> html.article:
    """Renderiza la tabla con los datos."""

    def get_row_key(row: Dict[str, Any], index: int) -> str:
        """Obtiene la key única para una fila."""
        if row_key:
            return str(row_key(row))
        # Intentar usar "id" o "Id" o el índice
        return str(row.get("id") or row.get("Id") or row.get("RobotId") or row.get("EquipoId") or index)

    def get_row_class(row: Dict[str, Any]) -> str:
        """Obtiene la clase CSS para una fila."""
        base_class = "clickable" if on_row_click else ""
        if row_class_name:
            custom_class = row_class_name(row)
            return f"{base_class} {custom_class}".strip()
        return base_class

    def render_header(column: Dict[str, Any]) -> html.th:
        """Renderiza el header de una columna."""
        is_sortable = column.get("sortable", True)
        column_key = column.get("key", "")

        if not is_sortable or not on_sort:
            return html.th({"scope": "col"}, column.get("label", ""))

        # Columna ordenable
        sort_indicator = ""
        if sort_by == column_key:
            sort_indicator = " ▲" if sort_dir == "asc" else " ▼"

        return html.th(
            {"scope": "col"},
            html.a(
                {
                    "href": "#",
                    "on_click": event(
                        lambda e, key=column_key: on_sort(key) if on_sort else None, prevent_default=True
                    ),
                },
                column.get("label", ""),
                sort_indicator,
            ),
        )

    def render_cell(row: Dict[str, Any], column: Dict[str, Any]) -> html.td:
        """Renderiza una celda de la tabla."""
        # Si hay función de renderizado personalizada, usarla
        if "render" in column and callable(column["render"]):
            return html.td(column["render"](row))

        # Si no, usar el valor directo
        key = column.get("key", "")
        value = row.get(key, "")
        return html.td(str(value))

    def render_row(row: Dict[str, Any], index: int) -> html.tr:
        """Renderiza una fila de la tabla."""
        row_key_value = get_row_key(row, index)
        row_class = get_row_class(row)

        row_attrs = {
            "key": row_key_value,
        }

        if row_class:
            row_attrs["class_name"] = row_class

        if on_row_click:
            row_attrs["on_click"] = lambda e, r=row: on_row_click(r)

        cells = [render_cell(row, col) for col in columns]

        # Agregar columna de acciones si existe
        if actions:
            action_cells = _render_actions(row, actions)
            cells.append(html.td(action_cells))

        return html.tr(row_attrs, cells)

    # Renderizar headers
    headers = [render_header(col) for col in columns]
    if actions:
        headers.append(html.th({"scope": "col"}, "Acciones"))

    # Renderizar filas
    rows = [render_row(row, idx) for idx, row in enumerate(data)]

    return html.article(
        html.table(
            html.thead(html.tr(headers)),
            html.tbody(
                rows
                if rows
                else [
                    html.tr(
                        html.td(
                            {"colSpan": len(columns) + (1 if actions else 0), "style": {"textAlign": "center"}},
                            empty_message if data is not None else "No hay datos disponibles",
                        )
                    )
                ]
            ),
        )
    )


def _render_actions(row: Dict[str, Any], actions: List[Dict[str, Any]]) -> html.div:
    """Renderiza las acciones para una fila."""
    action_buttons = []

    for action in actions:
        label = action.get("label", "")
        on_click = action.get("on_click")
        class_name = action.get("class_name", "secondary")
        icon = action.get("icon")

        if not on_click:
            continue

        button_content = [label]
        if icon:
            button_content.insert(0, html.i({"class_name": icon}))

        action_buttons.append(
            html.button(
                {
                    "class_name": f"outline {class_name}",
                    "on_click": event(lambda e, r=row, handler=on_click: handler(r), prevent_default=True),
                    "type": "button",
                },
                *button_content,
            )
        )

    return html.div({"style": {"display": "flex", "gap": "0.5rem"}}, *action_buttons)
