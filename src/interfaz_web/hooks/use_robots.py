# src/interfaz_web/hooks/use_robots.py
from typing import Any, Dict, Optional

from reactpy import use_callback, use_effect, use_memo, use_state

from ..schemas.robot_types import RobotFilters
from ..services.api_service import get_api_service

INITIAL_FILTERS: RobotFilters = {"name": None, "active": None, "online": None}
PAGE_SIZE = 20  # Definimos el tamaño de página como una constante


def use_robots():
    api_service = get_api_service()

    robots, set_robots = use_state([])
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)
    total_count, set_total_count = use_state(0)
    filters, set_filters = use_state(INITIAL_FILTERS)

    # --- INICIO DE LA MODIFICACIÓN ---

    # 1. AÑADIMOS EL ESTADO PARA LA PÁGINA ACTUAL
    current_page, set_current_page = use_state(1)

    # 2. MODIFICAMOS 'load_robots' PARA QUE MANEJE LA NUEVA RESPUESTA Y ENVÍE LOS PARÁMETROS
    @use_callback
    async def load_robots():
        set_loading(True)
        set_error(None)
        try:
            # Añadimos los parámetros de paginación a los filtros existentes
            api_filters = {**filters, "page": current_page, "size": PAGE_SIZE}

            # La respuesta de la API ahora es un diccionario
            data = await api_service.get_robots(api_filters)

            # Actualizamos los estados con la nueva estructura de datos
            set_robots(data.get("robots", []))
            set_total_count(data.get("total_count", 0))

        except Exception as e:
            set_error(str(e))
            set_robots([])
        finally:
            set_loading(False)

    # 3. EL 'useEffect' AHORA TAMBIÉN DEPENDE DE 'current_page'
    # Se ejecutará si cambian los filtros O si cambia la página
    use_effect(load_robots, [filters, current_page])

    # 4. CUANDO CAMBIAN LOS FILTROS, DEBEMOS REGRESAR A LA PÁGINA 1
    # Creamos un 'set_filters_and_reset_page' para manejar esto
    def handle_set_filters(new_filters_func):
        set_current_page(1)  # Resetea a la página 1
        set_filters(new_filters_func)  # Aplica los nuevos filtros

    # 'update_robot_status' no necesita cambios, ya que llama a load_robots()
    # que a su vez ya usa el estado de filtros y página actual.
    @use_callback
    async def update_robot_status(robot_id: int, status_data: Dict[str, bool]):
        try:
            await api_service.update_robot_status(robot_id, status_data)
            await load_robots()
        except Exception as e:
            set_error(f"Error al actualizar estado del robot {robot_id}: {e}")

    # 5. CALCULAMOS EL NÚMERO TOTAL DE PÁGINAS USANDO 'use_memo'
    total_pages = use_memo(lambda: max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE), [total_count])

    # --- FIN DE LA MODIFICACIÓN ---

    # 6. EXPONEMOS TODO LO NUEVO EN EL RETURN
    return {
        "robots": robots,
        "loading": loading,
        "error": error,
        "total_count": total_count,
        "filters": filters,
        "set_filters": handle_set_filters,  # Exponemos la nueva función
        "update_robot_status": update_robot_status,
        "refresh": load_robots,
        # --- Nuevos valores expuestos para paginación ---
        "current_page": current_page,
        "set_current_page": set_current_page,
        "total_pages": total_pages,
        "page_size": PAGE_SIZE,
    }
