# src/sam/web/frontend/features/components/mappings_page.py
import asyncio
from typing import Dict, List

from reactpy import component, event, html, use_effect, use_state

# Importación manual para datalist
from reactpy.core.vdom import make_vdom_constructor

from sam.web.frontend.api.api_client import get_api_client
from sam.web.frontend.shared.common_components import LoadingSpinner, PageWithLayout

# Definición manual de la etiqueta datalist
datalist = make_vdom_constructor("datalist")


@component
def MappingsPage(theme_is_dark: bool, on_theme_toggle):
    mappings, set_mappings = use_state([])
    robots, set_robots = use_state([])
    known_providers, set_known_providers = use_state(["A360", "Orquestador", "RPA360", "Tisam", "General"])
    loading, set_loading = use_state(True)

    # Form State
    new_proveedor, set_new_proveedor = use_state("")
    new_externo, set_new_externo = use_state("")

    # ESTADO PARA EL BUSCADOR DE ROBOTS
    new_robot_id, set_new_robot_id = use_state(None)
    robot_search, set_robot_search = use_state("")  # Texto que ve el usuario

    # Función para cargar datos
    async def load_data():
        api = get_api_client()
        try:
            m_data = await api.get_mappings()
            r_data = await api.get_robots({"size": 1000, "active": True})

            set_mappings(m_data)
            set_robots(r_data.get("robots", []))

            # Extraer proveedores existentes
            existing_providers = sorted(list(set(m["Proveedor"] for m in m_data)))
            all_providers = sorted(
                list(set(existing_providers + ["A360", "Orquestador", "RPA360", "Tisam", "General"]))
            )
            set_known_providers(all_providers)

        except Exception as e:
            print(f"Error cargando datos de mapeo: {e}")
        finally:
            set_loading(False)

    @use_effect(dependencies=[])
    def init():
        asyncio.create_task(load_data())

    # LOGICA DE BÚSQUEDA DE ROBOT (Nombre -> ID)
    def handle_robot_search(event):
        val = event["target"]["value"]
        set_robot_search(val)  # Actualizamos lo que ve el usuario

        # Buscamos si el nombre coincide con alguno de la lista para obtener el ID
        found = next((r for r in robots if r["Robot"] == val), None)
        if found:
            set_new_robot_id(found["RobotId"])
        else:
            set_new_robot_id(None)  # Si no coincide exacto, no hay ID válido aún

    async def handle_create(event):
        if not new_externo or not new_robot_id:
            return

        prov_to_save = new_proveedor.strip() or "General"

        try:
            api = get_api_client()
            await api.create_mapping(
                {
                    "Proveedor": prov_to_save,
                    "NombreExterno": new_externo,
                    "RobotId": int(new_robot_id),
                    "Descripcion": "Creado desde Web",
                }
            )
            # Resetear campos
            set_new_externo("")
            set_robot_search("")  # Limpiar buscador
            set_new_robot_id(None)

            await load_data()
        except Exception as e:
            print(f"Error creando mapeo: {e}")

    async def handle_delete(mid):
        try:
            api = get_api_client()
            await api.delete_mapping(mid)
            await load_data()
        except Exception as e:
            print(f"Error eliminando mapeo: {e}")

    return PageWithLayout(
        theme_is_dark=theme_is_dark,
        on_theme_toggle=on_theme_toggle,
        robots_state={},
        equipos_state={},
        children=html.div(
            html.h2("Mapeo de Robots (Alias)"),
            html.p("Asocia nombres externos con los Robots reales de SAM."),
            html.article(
                # html.header(html.h4("Nuevo Alias / Mapeo")),
                html.div(
                    {"class_name": "grid"},
                    # 1. Proveedor (Con sugerencias)
                    html.div(
                        html.label(
                            "Proveedor / Origen",
                            html.input(
                                {
                                    "list": "providers-list",
                                    "value": new_proveedor,
                                    "placeholder": "Escribe o selecciona...",
                                    "on_change": lambda e: set_new_proveedor(e["target"]["value"]),
                                }
                            ),
                            datalist({"id": "providers-list"}, [html.option({"value": p}) for p in known_providers]),
                        )
                    ),
                    # 2. Nombre Externo
                    html.div(
                        html.label(
                            "Nombre Externo",
                            html.input(
                                {
                                    "type": "text",
                                    "value": new_externo,
                                    "placeholder": "Ej: Bot_Cobranzas_V1",
                                    "on_change": lambda e: set_new_externo(e["target"]["value"]),
                                }
                            ),
                        ),
                    ),
                    # 3. ROBOT INTERNO (BUSCADOR)
                    html.div(
                        html.label(
                            "Robot Interno (Buscar en SAM)",
                            html.input(
                                {
                                    "list": "robots-list",  # Vinculamos al datalist de robots
                                    "value": robot_search,
                                    "placeholder": "Escribe para buscar robot...",
                                    "autocomplete": "off",
                                    "on_change": handle_robot_search,
                                    # Feedback visual: Borde rojo si hay texto pero no ID válido
                                    "style": {"borderColor": "var(--pico-form-element-invalid-border-color)"}
                                    if robot_search and not new_robot_id
                                    else "",
                                }
                            ),
                            # Lista de Robots filtrable
                            datalist({"id": "robots-list"}, [html.option({"value": r["Robot"]}) for r in robots]),
                            # Pequeño texto de ayuda para confirmar selección
                        ),
                        html.small(
                            {"style": {"color": "var(--pico-primary)" if new_robot_id else "var(--pico-muted-color)"}},
                            f"ID Seleccionado: {new_robot_id}" if new_robot_id else "Selecciona un robot de la lista.",
                        ),
                    ),
                ),
                html.button(
                    {
                        "type": "button",
                        "on_click": handle_create,
                        "disabled": not new_robot_id or not new_externo,
                    },
                    html.i({"class_name": "fa-solid fa-plus", "style": {"marginRight": "8px"}}),
                    "Crear",
                ),
            ),
            LoadingSpinner()
            if loading
            else html.article(
                html.table(
                    html.thead(
                        html.tr(
                            html.th("Nombre Externo (Alias)"),
                            html.th("Proveedor"),
                            html.th("Se ejecuta como"),
                            html.th("Acciones"),
                        )
                    ),
                    html.tbody(
                        *[
                            html.tr(
                                {"key": m["MapeoId"]},
                                html.td(html.strong(m["NombreExterno"])),
                                html.td(html.p(m["Proveedor"])),
                                html.td(
                                    html.span(
                                        {"style": {"color": "var(--pico-primary)"}},
                                        html.i({"class_name": "fa-solid fa-robot", "style": {"marginRight": "5px"}}),
                                        m.get("RobotNombre") or f"ID: {m['RobotId']}",
                                    )
                                ),
                                html.td(
                                    html.a(
                                        {
                                            "href": "#",
                                            "class_name": "secondary",
                                            "data-tooltip": "Eliminar Alias",
                                            "on_click": lambda e, mid=m["MapeoId"]: asyncio.create_task(
                                                handle_delete(mid)
                                            ),
                                        },
                                        html.i({"class_name": "fa-solid fa-trash"}),
                                    )
                                ),
                            )
                            for m in mappings
                        ]
                        if mappings
                        else html.tr(
                            html.td(
                                {"colspan": 4, "style": {"text-align": "center", "padding": "2rem"}},
                                "No hay mapeos definidos aún.",
                            )
                        )
                    ),
                ),
            ),
        ),
    )
