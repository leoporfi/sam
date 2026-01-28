# sam/web/frontend/shared/docs_components.py
"""
Componentes compartidos para la interfaz de documentación (Glosario y FAQ).
Reutilizables y desacoplados del contenido específico.
"""

from typing import List, Optional

from reactpy import component, html


@component
def DocsSidebar(sections: List[dict], current_section: Optional[str] = None):
    """
    Sidebar de navegación para documentación con scroll automático.

    Args:
        sections: Lista de secciones con {id, title}
        current_section: ID de la sección actualmente visible (opcional)
    """
    return html.aside(
        {"class_name": "docs-sidebar"},
        html.nav(
            html.h4({"style": {"margin-top": 0}}, "Secciones"),
            html.ul(
                *[
                    html.li(
                        html.a(
                            {
                                "href": f"#{section['id']}",
                                "class_name": "active" if current_section == section["id"] else "",
                                "on_click": lambda e, sid=section["id"]: None,  # Prevención default para smooth scroll
                            },
                            section["title"],
                        )
                    )
                    for section in sections
                ]
            ),
        ),
    )


def _render_formatted_text(text: str):
    """
    Helper para renderizar texto con formato simple (negritas y saltos de línea).
    """
    if not text:
        return []

    paragraphs = text.strip().split("\n\n")
    elements = []
    for para in paragraphs:
        # Procesar negritas (**)
        parts = para.split("**")
        para_elements = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                para_elements.append(html.strong(part))
            else:
                # Procesar saltos de línea simples
                lines = part.split("\n")
                for j, line in enumerate(lines):
                    if line:
                        para_elements.append(line)
                    if j < len(lines) - 1:
                        para_elements.append(html.br())
        elements.append(html.p({"style": {"margin-bottom": "0.75rem"}}, para_elements))
    return elements


@component
def GlossaryTerm(term: str, description: str, slug: str):
    """
    Renderiza un término del glosario con formato consistente.

    Args:
        term: Nombre del término
        description: Texto descriptivo
        slug: Identificador único para anclas
    """
    return html.article(
        {
            "id": slug,
            "class_name": "glossary-term",
        },
        html.h3(term),
        _render_formatted_text(description),
    )


@component
def FAQItem(question: str, answer: str, slug: str):
    """
    Renderiza una pregunta/respuesta de FAQ usando el componente Accordion de PicoCSS (details/summary).

    Args:
        question: Pregunta
        answer: Respuesta
        slug: Identificador único para anclas
    """
    return html.details(
        {
            "id": slug,
            "class_name": "faq-item",
        },
        html.summary(question),
        html.div(
            {"style": {"padding": "1rem", "border-top": "1px solid var(--pico-muted-border-color)"}},
            _render_formatted_text(answer),
        ),
    )


@component
def DocsBreadcrumbs(items: List[dict]):
    """
    Muestra ruta de navegación contextual.

    Args:
        items: Lista de {label, url} para la ruta de navegación
    """
    from reactpy_router import link

    return html.nav(
        {
            "aria-label": "breadcrumb",
            "style": {"margin-bottom": "1.5rem", "font-size": "0.9rem"},
        },
        html.ol(
            {
                "style": {
                    "list-style": "none",
                    "display": "flex",
                    "gap": "0.5rem",
                    "padding": 0,
                    "color": "var(--pico-muted-color)",
                }
            },
            *[
                html.li(
                    {
                        "style": {
                            "display": "flex",
                            "align-items": "center",
                            "gap": "0.5rem",
                        }
                    },
                    link(
                        {"to": item["url"], "style": {"text-decoration": "none"}},
                        item["label"],
                    )
                    if item.get("url")
                    else html.span({"style": {"font-weight": "600"}}, item["label"]),
                    html.span(" / ") if idx < len(items) - 1 else None,
                )
                for idx, item in enumerate(items)
            ],
        ),
    )


@component
def DocsLayout(
    theme_is_dark: bool,
    on_theme_toggle,
    robots_state,
    equipos_state,
    sidebar_content,
    main_content,
    breadcrumbs,
):
    """
    Layout de 2 columnas reutilizable para páginas de documentación.

    Args:
        theme_is_dark: Estado del tema oscuro
        on_theme_toggle: Callback para cambiar tema
        robots_state: Estado de robots (para header)
        equipos_state: Estado de equipos (para header)
        sidebar_content: Contenido del sidebar (componente ReactPy)
        main_content: Contenido principal (componente ReactPy)
        breadcrumbs: Componente de breadcrumbs
    """
    from .common_components import PageWithLayout

    return PageWithLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state=robots_state,
        equipos_state=equipos_state,
        children=html._(
            breadcrumbs,
            html.div(
                {"class_name": "docs-container"},
                sidebar_content,
                html.main(
                    {"class_name": "docs-main-content"},
                    main_content,
                ),
            ),
        ),
    )
