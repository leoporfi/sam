import asyncio
from typing import Any, Dict

from reactpy import use_callback, use_context, use_effect, use_memo, use_state

from ..api.api_client import get_api_client
from ..shared.notifications import NotificationContext

PAGE_SIZE = 20
INITIAL_FILTERS = {"name": None, "active": None, "balanceable": None}
POLLING_INTERVAL_SECONDS = 30


def use_equipos():
    """
    Hook para gestionar el estado del dashboard de equipos.
    """
    api_client = get_api_client()
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    equipos, set_equipos = use_state([])
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)
    total_count, set_total_count = use_state(0)
    filters, set_filters = use_state(INITIAL_FILTERS)
    current_page, set_current_page = use_state(1)
    sort_by, set_sort_by = use_state("Equipo")
    sort_dir, set_sort_dir = use_state("asc")

    @use_callback
    async def load_equipos():
        set_loading(True)
        set_error(None)
        try:
            api_params = {
                **filters,
                "page": current_page,
                "size": PAGE_SIZE,
                "sort_by": sort_by,
                "sort_dir": sort_dir,
            }
            api_params = {k: v for k, v in api_params.items() if v is not None}

            # Asumimos que el cliente API tendrá un método get_equipos
            data = await api_client.get_equipos(api_params)
            set_equipos(data.get("equipos", []))
            set_total_count(data.get("total_count", 0))
        except Exception as e:
            set_error(str(e))
            show_notification(f"Error al cargar equipos: {e}", "error")
        finally:
            set_loading(False)

    use_effect(load_equipos, [filters, current_page, sort_by, sort_dir])

    @use_effect(dependencies=[filters, current_page, sort_by, sort_dir])
    def setup_polling():
        task = asyncio.ensure_future(polling_loop())
        return lambda: task.cancel()

    async def polling_loop():
        while True:
            await asyncio.sleep(POLLING_INTERVAL_SECONDS)
            try:
                await load_equipos()
            except asyncio.CancelledError:
                break
            except Exception as e:
                set_error(f"Error de actualización automática: {e}")

    def handle_sort(column_name: str):
        if sort_by == column_name:
            set_sort_dir("desc" if sort_dir == "asc" else "asc")
        else:
            set_sort_by(column_name)
            set_sort_dir("asc")
        set_current_page(1)

    def handle_set_filters(new_filters_func):
        set_current_page(1)
        set_filters(new_filters_func)

    @use_callback
    async def update_equipo_status(equipo_id: int, field: str, value: bool):
        try:
            # Asumimos que el cliente API tendrá este método
            await api_client.update_equipo_status(equipo_id, {"field": field, "value": value})
            show_notification("Estado del equipo actualizado.", "success")
            await load_equipos()
        except Exception as e:
            set_error(f"Error al actualizar estado del equipo {equipo_id}: {e}")
            show_notification(f"Error al actualizar: {e}", "error")

    total_pages = use_memo(lambda: max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE), [total_count])

    return {
        "equipos": equipos,
        "loading": loading,
        "error": error,
        "total_count": total_count,
        "filters": filters,
        "set_filters": handle_set_filters,
        "update_equipo_status": update_equipo_status,
        "refresh": load_equipos,
        "current_page": current_page,
        "set_current_page": set_current_page,
        "total_pages": total_pages,
        "page_size": PAGE_SIZE,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "handle_sort": handle_sort,
    }
