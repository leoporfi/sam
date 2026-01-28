# sam/web/frontend/features/components/docs_glossary.py
"""
Página del Glosario del Proyecto SAM.
Renderiza términos técnicos organizados por secciones.
"""

import asyncio

from reactpy import component, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client
from sam.web.frontend.shared.common_components import ErrorMessage, LoadingSpinner
from sam.web.frontend.shared.docs_components import (
    DocsBreadcrumbs,
    DocsLayout,
    DocsSidebar,
    GlossaryTerm,
)


@component
def GlossaryPage(theme_is_dark: bool, on_theme_toggle):
    """Página principal del Glosario del Proyecto."""

    # Importar hooks necesarios
    from ...hooks.use_equipos_hook import use_equipos
    from ...hooks.use_robots_hook import use_robots

    robots_state = use_robots()
    equipos_state = use_equipos()

    # Estados locales
    glossary_data, set_glossary_data = use_state(None)
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)

    # Obtener API client
    api_client = get_api_client()

    # Efecto para cargar datos al montar
    @use_effect(dependencies=[])
    def load_glossary():
        async def fetch_data():
            try:
                set_loading(True)
                data = await api_client.get("/api/docs/glossary")
                set_glossary_data(data.get("sections", {}))
                set_error(None)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"Error cargando glosario: {e}")
                set_error(f"Error al cargar el glosario: {str(e)}")
            finally:
                set_loading(False)

        task = asyncio.create_task(fetch_data())
        return lambda: task.cancel()

    # Breadcrumbs
    breadcrumbs = DocsBreadcrumbs(
        items=[
            {"label": "Inicio", "url": "/"},
            {"label": "Glosario"},
        ]
    )

    # Construir estructura de secciones para el sidebar
    sections = []
    if glossary_data:
        sections = [
            {"id": section_id, "title": section_data["title"]} for section_id, section_data in glossary_data.items()
        ]

    # Sidebar
    sidebar = DocsSidebar(sections=sections)

    # Contenido principal
    if loading:
        main_content = html.div(
            {"style": {"display": "flex", "justify-content": "center", "padding": "3rem"}},
            LoadingSpinner(size="large"),
        )
    elif error:
        main_content = ErrorMessage(error)
    elif glossary_data:
        main_content = html._(
            html.header(
                html.h1("Glosario del Proyecto SAM"),
                html.p(
                    {
                        "style": {
                            "color": "var(--pico-muted-color)",
                            "font-size": "1.1rem",
                            "margin-top": "0.5rem",
                        }
                    },
                    "Términos técnicos, conceptos de negocio y componentes del sistema SAM.",
                ),
            ),
            # Renderizar todas las secciones
            *[
                html.section(
                    {
                        "id": section_id,
                        "class_name": "glossary-section",
                    },
                    html.h2(section_data["title"]),
                    # Renderizar todos los términos de la sección
                    *[
                        GlossaryTerm(
                            term=term_data["term"],
                            description=term_data["description"],
                            slug=term_data["slug"],
                        )
                        for term_data in section_data["terms"]
                    ],
                )
                for section_id, section_data in glossary_data.items()
            ],
        )
    else:
        main_content = html.p("No hay datos disponibles.")

    return DocsLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state=robots_state,
        equipos_state=equipos_state,
        sidebar_content=sidebar,
        main_content=main_content,
        breadcrumbs=breadcrumbs,
    )
