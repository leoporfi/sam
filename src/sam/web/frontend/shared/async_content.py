# sam/web/frontend/shared/async_content.py
"""
Componentes para manejar estados asíncronos de manera consistente.

Este módulo proporciona componentes reutilizables para manejar estados de carga,
error y vacío en componentes que cargan datos de forma asíncrona.

Uso:
    from sam.web.frontend.shared.async_content import AsyncContent

    return AsyncContent(
        loading=is_loading,
        error=error_message,
        data=robots,
        skeleton_type="table",
        children=RobotList(robots=robots)
    )
"""

from typing import List, Optional

from reactpy import component, html


@component
def AsyncContent(
    loading: bool,
    error: Optional[str] = None,
    data: Optional[List] = None,
    loading_component=None,
    skeleton_type: Optional[str] = None,  # "table", "card", "text"
    skeleton_rows: int = 5,
    error_component=None,
    empty_component=None,
    empty_message: str = "No hay datos disponibles",
    children=None,
):
    """
    Wrapper para manejar estados de carga de manera consistente.

    Args:
        loading: Si True, muestra el componente de carga
        error: Mensaje de error a mostrar (si existe)
        data: Datos a verificar si están vacíos
        loading_component: Componente personalizado para estado de carga
        error_component: Componente personalizado para estado de error
        empty_component: Componente personalizado para estado vacío
        empty_message: Mensaje a mostrar cuando no hay datos
        children: Contenido a mostrar cuando hay datos y no hay errores

    Returns:
        Componente ReactPy según el estado actual
    """
    # Prioridad 1: Error
    if error:
        if error_component:
            return error_component
        return ErrorAlert(message=error)

    # Prioridad 2: Cargando
    if loading:
        if loading_component:
            return loading_component

        if skeleton_type == "table":
            return SkeletonTable(rows=skeleton_rows)
        elif skeleton_type == "card":
            return SkeletonCardGrid(count=skeleton_rows)
        elif skeleton_type == "text":
            return SkeletonText(lines=skeleton_rows)

        from .common_components import LoadingSpinner as CommonLoadingSpinner

        return CommonLoadingSpinner()

    # Prioridad 3: Datos vacíos
    if data is not None and len(data) == 0:
        if empty_component:
            return empty_component
        return EmptyState(message=empty_message)

    # Prioridad 4: Mostrar contenido
    return children


@component
def LoadingSpinner(size: str = "medium"):
    """
    Muestra un spinner de carga.

    Re-exporta el LoadingSpinner de common_components para mantener
    compatibilidad y consistencia.
    """
    from .common_components import LoadingSpinner as CommonLoadingSpinner

    return CommonLoadingSpinner(size=size)


@component
def ErrorAlert(message: str):
    """
    Muestra un mensaje de error de manera consistente.

    Args:
        message: Mensaje de error a mostrar

    Returns:
        Componente ReactPy con el mensaje de error
    """
    if not message:
        return None

    return html.article(
        {
            "aria-invalid": "true",
            "role": "alert",
            "style": {
                "backgroundColor": "var(--pico-color-red-200)",
                "borderColor": "var(--pico-color-red-600)",
                "color": "var(--pico-color-red-900)",
                "padding": "1em",
                "marginBottom": "1em",
                "borderRadius": "var(--pico-border-radius)",
            },
        },
        html.strong("Error: "),
        str(message),
    )


@component
def EmptyState(message: str = "No hay datos disponibles"):
    """
    Muestra un estado vacío cuando no hay datos.

    Args:
        message: Mensaje a mostrar cuando no hay datos

    Returns:
        Componente ReactPy con el mensaje de estado vacío
    """
    return html.article(
        {
            "style": {
                "textAlign": "center",
                "padding": "2rem",
                "color": "var(--pico-muted-color)",
            },
        },
        html.p(
            {"style": {"fontSize": "1.1rem", "marginBottom": "0.5rem"}},
            "📭",
        ),
        html.p(message),
    )


@component
def SkeletonText(lines: int = 3):
    """Muestra líneas de texto tipo skeleton."""
    return html.div(*[html.div({"class_name": "skeleton skeleton-text"}) for _ in range(lines)])


@component
def SkeletonTable(rows: int = 5, cols: int = 5):
    """Muestra una tabla tipo skeleton."""
    return html.article(
        html.table(
            html.thead(
                html.tr(
                    *[
                        html.th(html.div({"class_name": "skeleton skeleton-text", "style": {"width": "80%"}}))
                        for _ in range(cols)
                    ]
                )
            ),
            html.tbody(
                *[
                    html.tr(
                        {"class_name": "skeleton-table-row"},
                        *[
                            html.td(html.div({"class_name": "skeleton skeleton-text", "style": {"width": "90%"}}))
                            for _ in range(cols)
                        ],
                    )
                    for _ in range(rows)
                ]
            ),
        )
    )


@component
def SkeletonCard():
    """Muestra una tarjeta tipo skeleton."""
    return html.article(
        {"class_name": "skeleton-card"},
        html.div({"class_name": "skeleton skeleton-title"}),
        html.div({"class_name": "skeleton skeleton-text"}),
        html.div({"class_name": "skeleton skeleton-text", "style": {"width": "80%"}}),
        html.footer(
            html.div(
                {"class_name": "grid"},
                html.div({"class_name": "skeleton skeleton-button"}),
                html.div({"class_name": "skeleton skeleton-button"}),
            )
        ),
    )


@component
def SkeletonCardGrid(count: int = 6):
    """Muestra una grilla de tarjetas tipo skeleton."""
    # Usamos las clases de custom.css para mantener la grilla responsive
    return html.div(
        {"class_name": "cards-container", "style": {"display": "grid"}},  # Forzar display grid para el skeleton
        *[SkeletonCard() for _ in range(count)],
    )
