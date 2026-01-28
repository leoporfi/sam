# sam/web/frontend/features/components/docs_faq.py
"""
Página de Preguntas Frecuentes (FAQ) del Proyecto SAM.
Organiza preguntas y respuestas por categorías.
"""

import asyncio

from reactpy import component, html, use_effect, use_state

from sam.web.frontend.api.api_client import get_api_client
from sam.web.frontend.shared.common_components import ErrorMessage, LoadingSpinner
from sam.web.frontend.shared.docs_components import (
    DocsBreadcrumbs,
    DocsLayout,
    DocsSidebar,
    FAQItem,
)


@component
def FAQPage(theme_is_dark: bool, on_theme_toggle):
    """Página principal de FAQ del Proyecto."""

    # Importar hooks necesarios
    from ...hooks.use_equipos_hook import use_equipos
    from ...hooks.use_robots_hook import use_robots

    robots_state = use_robots()
    equipos_state = use_equipos()

    # Estados locales
    faq_data, set_faq_data = use_state(None)
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)

    # Obtener API client
    api_client = get_api_client()

    # Efecto para cargar datos al montar
    @use_effect(dependencies=[])
    def load_faq():
        async def fetch_data():
            try:
                set_loading(True)
                data = await api_client.get("/api/docs/faq")
                set_faq_data(data.get("sections", {}))
                set_error(None)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"Error cargando FAQ: {e}")
                set_error(f"Error al cargar las FAQ: {str(e)}")
            finally:
                set_loading(False)

        task = asyncio.create_task(fetch_data())
        return lambda: task.cancel()

    # Breadcrumbs
    breadcrumbs = DocsBreadcrumbs(
        items=[
            {"label": "Inicio", "url": "/"},
            {"label": "FAQ"},
        ]
    )

    # Construir estructura de secciones para el sidebar
    sections = []
    if faq_data:
        sections = [{"id": section_id, "title": section_data["title"]} for section_id, section_data in faq_data.items()]

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
    elif faq_data:
        main_content = html._(
            html.header(
                html.h1("Preguntas Frecuentes (FAQ)"),
                html.p(
                    {
                        "style": {
                            "color": "var(--pico-muted-color)",
                            "font-size": "1.1rem",
                            "margin-top": "0.5rem",
                        }
                    },
                    "Respuestas a preguntas comunes sobre el funcionamiento, arquitectura y operación de SAM.",
                ),
            ),
            # Renderizar todas las secciones
            *[
                html.section(
                    {
                        "id": section_id,
                        "class_name": "faq-section",
                    },
                    html.h2(section_data["title"]),
                    # Renderizar todas las preguntas de la sección
                    *[
                        FAQItem(
                            question=q_data["question"],
                            answer=q_data["answer"],
                            slug=q_data["slug"],
                        )
                        for q_data in section_data["questions"]
                    ],
                )
                for section_id, section_data in faq_data.items()
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
