import asyncio
from typing import Callable, Dict, List, Optional

from reactpy import use_callback, use_context, use_effect, use_memo, use_state

from ..api.api_client import get_api_client
from ..shared.notifications import NotificationContext

PAGE_SIZE = 20
INITIAL_FILTERS = {"robot": None, "tipo": None, "activo": None, "search": None}

# Reducimos el polling para desarrollo, el plan original era 120
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
    # Los hooks de ordenamiento no se usan en el plan, pero los dejamos
    sort_by, set_sort = use_state("Robot")
    sort_dir, set_dir = use_state("asc")

    @use_callback
    async def load():
        set_loading(True)
        set_error(None)
        try:
            # Construye los params
            params: Dict[str, Optional[str | int | bool]] = {
                "page": page,
                "size": PAGE_SIZE,
            }
            # Añadir filtros solo si tienen valor
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
        # Polling para mantener los datos frescos
        async def poll_loop():
            while True:
                await asyncio.sleep(POLL_INTERVAL)
                try:
                    # Recarga silenciosa
                    params = {**filters, "page": page, "size": PAGE_SIZE}
                    data = await api.get_schedules(params)
                    set_schedules(data.get("schedules", []))
                    set_total(data.get("total_count", 0))
                except Exception:
                    # No mostrar error en polling, solo log en consola (si tuviéramos)
                    pass

        # Descomentar para activar el polling
        # task = asyncio.create_task(poll_loop())
        # return lambda: task.cancel()
        pass

    @use_callback
    def toggle_active(schedule_id: int, activo: bool):
        async def _logic():
            try:
                # UI optimista (deshabilitado por simplicidad, recargamos)
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
                await load()  # Recargar datos
            except Exception as e:
                show(f"Error al guardar: {e}", "error")

        asyncio.create_task(_logic())

    @use_callback
    def save_schedule_equipos(schedule_id: int, equipo_ids: List[int]):
        """
        Guarda únicamente la lista de equipos para una programación.
        """
        async def _logic():
            if not schedule_id:
                show("No se pudo guardar: ID de programación no encontrado.", "error")
                return

            try:
                # Llama al nuevo método del API Client que creamos antes
                await api.update_schedule_devices(schedule_id, equipo_ids)
                show("Equipos de la programación actualizados", "success")
                await load()  # Recargar datos
            except Exception as e:
                show(f"Error al guardar equipos: {e}", "error")

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
        "refresh": load, # load sigue siendo async, pero refresh suele manejarse distinto o no usarse en lambdas directas sin wrapper
    }
