import asyncio
from typing import Callable, Dict, List, Optional

from reactpy import use_callback, use_context, use_effect, use_memo, use_state

from ..api.api_client import get_api_client
from ..shared.notifications import NotificationContext

PAGE_SIZE = 20
INITIAL_FILTERS = {"robot": None, "tipo": None, "activo": None, "search": None}

POLL_INTERVAL = 120


def use_schedules():
    api = get_api_client()
    ctx = use_context(NotificationContext)
    show: Callable = ctx["show_notification"]

    schedules, set_schedules = use_state([])
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)
    total, set_total = use_state(0)
    filters, set_filters = use_state(INITIAL_FILTERS)
    page, set_page = use_state(1)
    sort_by, set_sort = use_state("Robot")
    sort_dir, set_dir = use_state("asc")

    async def load():
        set_loading(True)
        set_error(None)
        try:
            params: Dict[str, Optional[str | int | bool]] = {
                "page": page,
                "size": PAGE_SIZE,
            }
            if filters["robot"]:
                params["robot"] = filters["robot"]
            if filters["tipo"]:
                params["tipo"] = filters["tipo"]
            if filters["activo"] is not None:
                params["activo"] = filters["activo"]
            if filters["search"]:
                params["search"] = filters["search"]

            data = await api.get_schedules(params)
            set_schedules(data.get("schedules", []))
            set_total(data.get("total_count", 0))
        except Exception as e:
            set_error(str(e))
            show(f"Error al cargar programaciones: {e}", "error")
        finally:
            set_loading(False)

    @use_effect(dependencies=[filters, page])
    def _load_on_filters_or_page_change():
        task = asyncio.create_task(load())
        return lambda: task.cancel()

    @use_effect(dependencies=[])
    def _setup_polling():
        async def poll_loop():
            while True:
                await asyncio.sleep(POLL_INTERVAL)
                try:
                    params = {**filters, "page": page, "size": PAGE_SIZE}
                    data = await api.get_schedules(params)
                    set_schedules(data.get("schedules", []))
                    set_total(data.get("total_count", 0))
                except Exception:
                    pass

        # task = asyncio.create_task(poll_loop())
        # return lambda: task.cancel()
        pass

    @use_callback
    def toggle_active(schedule_id: int, activo: bool):
        async def _logic():
            try:
                await api.toggle_schedule_status(schedule_id, activo)
                show("Estado cambiado", "success")
                await load()
            except Exception as e:
                show(str(e), "error")
                await load()

        asyncio.create_task(_logic())

    @use_callback
    def save_schedule(data: dict):
        async def _logic():
            schedule_id = data.get("ProgramacionId")
            if not schedule_id:
                show("No se pudo guardar: ID de programación no encontrado.", "error")
                return

            try:
                await api.update_schedule_details(schedule_id, data)
                show("Programación actualizada", "success")
                await load()
            except Exception as e:
                show(f"Error al guardar: {e}", "error")

        asyncio.create_task(_logic())

    @use_callback
    async def save_schedule_equipos(schedule_id: int, equipo_ids: List[int], on_success: Optional[Callable] = None):
        """
        Guarda únicamente la lista de equipos para una programación.
        Retomamos async/await directo para que el Modal pueda esperar a que termine.
        """
        if not schedule_id:
            show("No se pudo guardar: ID de programación no encontrado.", "error")
            return

        try:
            # Llama al API
            await api.update_schedule_devices(schedule_id, equipo_ids)
            show("Equipos de la programación actualizados", "success")

            # Ejecutamos el callback si existe
            if on_success:
                if asyncio.iscoroutinefunction(on_success):
                    await on_success()
                else:
                    on_success()

            await load()  # Recargar datos

        except Exception as e:
            show(f"Error al guardar equipos: {e}", "error")
            # Opcional: Si quieres que el modal NO se cierre si hay error real de API,
            # descomenta la siguiente línea para relanzar la excepción hacia el modal.
            # raise e

    total_pages = use_memo(lambda: max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE), [total, PAGE_SIZE])

    return {
        "schedules": schedules,
        "loading": loading,
        "error": error,
        "total_count": total,
        "filters": filters,
        "set_filters": lambda f: (set_filters(f), set_page(1)),
        "current_page": page,
        "set_page": set_page,
        "total_pages": total_pages,
        "toggle_active": toggle_active,
        "save_schedule": save_schedule,
        "save_schedule_equipos": save_schedule_equipos,
        "refresh": load,
    }
