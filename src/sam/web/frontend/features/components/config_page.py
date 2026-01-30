# src/sam/web/frontend/features/components/config_page.py
from reactpy import component, event, html, use_memo, use_state

from ...hooks.use_config_hook import use_config
from ...hooks.use_equipos_hook import use_equipos
from ...hooks.use_robots_hook import use_robots
from ...shared.async_content import SkeletonTable
from ...shared.common_components import PageWithLayout, SearchInput
from ..modals.config_modals import ConfigEditModal


@component
def ConfigPage(theme_is_dark: bool, on_theme_toggle):
    """Página de gestión de configuración dinámica del sistema."""
    # Hooks de estado global (requeridos por PageWithLayout)
    robots_state = use_robots()
    equipos_state = use_equipos()

    # Hook de configuración
    config_state = use_config()

    # Estado local para búsqueda y modal
    search_term, set_search_term = use_state("")
    selected_config, set_selected_config = use_state(None)
    is_modal_open, set_is_modal_open = use_state(False)

    # Filtrar configuraciones por búsqueda
    filtered_configs = use_memo(
        lambda: [
            c
            for c in config_state["configs"]
            if not search_term
            or search_term.lower() in c["Clave"].lower()
            or search_term.lower() in (c["Descripcion"] or "").lower()
        ],
        [config_state["configs"], search_term],
    )

    def handle_edit(config):
        set_selected_config(config)
        set_is_modal_open(True)

    def handle_close_modal():
        set_is_modal_open(False)
        set_selected_config(None)

    return PageWithLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state=robots_state,
        equipos_state=equipos_state,
        children=html.div(
            html.header(
                html.div(
                    html.h1("Configuración del Sistema"),
                    html.p("Gestión dinámica de parámetros de negocio y operativos."),
                ),
            ),
            # Controles de búsqueda
            html.div(
                {"class_name": "grid", "style": {"margin-bottom": "1rem"}},
                SearchInput(
                    placeholder="Buscar por clave o descripción...",
                    value=search_term,
                    on_execute=set_search_term,
                ),
                html.div(),  # Espaciador
                html.div(),  # Espaciador
            ),
            # Tabla de configuración
            html.article(
                SkeletonTable(rows=10, cols=5)
                if config_state["loading"]
                else html.div(
                    {"style": {"overflow-x": "auto"}},
                    html.table(
                        html.thead(
                            html.tr(
                                html.th("Clave"),
                                html.th("Valor"),
                                html.th("Descripción"),
                                html.th({"style": {"text-align": "center"}}, "Estado"),
                                html.th({"style": {"text-align": "center"}}, "Acciones"),
                            )
                        ),
                        html.tbody(
                            *[
                                html.tr(
                                    {"key": c["Clave"]},
                                    html.td(html.p(c["Clave"])),
                                    html.td(
                                        (
                                            html.p("True")
                                            if str(c["Valor"]).strip().lower() in ("true", "1")
                                            else html.p("False")
                                        )
                                        if str(c["Valor"]).strip().lower() in ("true", "false", "1", "0")
                                        else (
                                            html.p(c["Valor"])
                                            if len(str(c["Valor"])) < 50
                                            else html.p(str(c["Valor"])[:50] + "...")
                                        )
                                    ),
                                    html.td(html.small(c["Descripcion"] or "-")),
                                    html.td(
                                        {"style": {"text-align": "center"}},
                                        html.span(
                                            {
                                                "class_name": "badge",
                                                "style": {
                                                    "background": "var(--secondary)"
                                                    if c.get("RequiereReinicio")
                                                    else "var(--primary)",
                                                    "color": "white",
                                                    "padding": "0.2rem 0.5rem",
                                                    "border-radius": "4px",
                                                    "font-size": "0.7rem",
                                                    "white-space": "nowrap",
                                                },
                                                "data-tooltip": "Requiere reiniciar servicios para aplicar"
                                                if c.get("RequiereReinicio")
                                                else "Se aplica en tiempo real (máx 60s)",
                                            },
                                            "Reiniciar" if c.get("RequiereReinicio") else "Dinámico",
                                        ),
                                    ),
                                    html.td(
                                        {"style": {"text-align": "center"}},
                                        html.div(
                                            {"class_name": "grid"},
                                            html.a(
                                                {
                                                    "href": "#",
                                                    "class_name": "secondary",
                                                    "on_click": event(
                                                        lambda e, c=c: handle_edit(c), prevent_default=True
                                                    ),
                                                    "data-tooltip": "Editar parámetro",
                                                },
                                                html.i({"class_name": "fa-solid fa-pencil"}),
                                            ),
                                        ),
                                    ),
                                )
                                for c in filtered_configs
                            ]
                            if filtered_configs
                            else [
                                html.tr(
                                    html.td(
                                        {"colspan": 5, "style": {"text-align": "center", "padding": "2rem"}},
                                        "No se encontraron configuraciones." if not config_state["loading"] else "",
                                    )
                                )
                            ]
                        ),
                    ),
                )
            ),
            # Modal de edición
            ConfigEditModal(
                config=selected_config,
                is_open=is_modal_open,
                on_close=handle_close_modal,
                on_save=config_state["update_config"],
            ),
        ),
    )
