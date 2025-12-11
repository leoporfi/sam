# sam/web/hooks/use_equipos_hook.py
import asyncio

from reactpy import use_callback, use_context, use_effect, use_memo, use_ref, use_state

from ..api.api_client import get_api_client
from ..shared.notifications import NotificationContext

PAGE_SIZE = 100
INITIAL_FILTERS = {"name": None, "active": None, "balanceable": None}
POLLING_INTERVAL_SECONDS = 60
SYNC_POLLING_INTERVAL_SECONDS = 3


def use_equipos():
    """
    Hook para gestionar el estado del dashboard de equipos.
    """
    api_client = get_api_client()
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    equipos, set_equipos = use_state([])
    loading, set_loading = use_state(True)
    is_syncing, set_is_syncing = use_state(False)
    error, set_error = use_state(None)
    total_count, set_total_count = use_state(0)
    filters, set_filters = use_state(INITIAL_FILTERS)
    current_page, set_current_page = use_state(1)
    sort_by, set_sort_by = use_state("Equipo")
    sort_dir, set_sort_dir = use_state("asc")

    # Referencia de montaje
    is_mounted = use_ref(True)

    @use_effect(dependencies=[])
    def mount_lifecycle():
        is_mounted.current = True
        return lambda: setattr(is_mounted, "current", False)

    @use_callback
    async def load_equipos():
        if not is_mounted.current:
            return

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
            data = await api_client.get_equipos(api_params)

            if is_mounted.current:
                set_equipos(data.get("equipos", []))
                set_total_count(data.get("total_count", 0))

        except asyncio.CancelledError:
            raise
        except Exception as e:
            if is_mounted.current:
                set_error(str(e))
                show_notification(f"Error al cargar equipos: {e}", "error")
        finally:
            if is_mounted.current and not asyncio.current_task().cancelled():
                set_loading(False)

    @use_callback
    async def trigger_sync(event=None):
        """Sincroniza solo equipos desde A360."""
        if is_syncing or not is_mounted.current:
            return

        set_is_syncing(True)
        show_notification("Sincronizando equipos desde A360...", "info")
        try:
            await api_client.trigger_sync_equipos()

            if is_mounted.current:
                show_notification("Sincronización iniciada. Esperando finalización...", "info")

            # Bucle seguro
            while is_mounted.current:
                await asyncio.sleep(SYNC_POLLING_INTERVAL_SECONDS)
                try:
                    status_data = await api_client.get_sync_status()
                    if status_data.get("equipos") == "idle":
                        break
                except Exception as poll_error:
                    if is_mounted.current:
                        show_notification(f"Error al consultar estado de sync: {poll_error}", "warning")

            if is_mounted.current:
                show_notification("Sincronización de equipos completada. Actualizando...", "success")
                await load_equipos()
                set_is_syncing(False)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            if is_mounted.current:
                show_notification(f"Error al iniciar sincronización: {e}", "error")
                set_error(f"Error en sincronización: {e}")
                set_is_syncing(False)
        finally:
            # Aseguramos quitar loading si quedó colgado, pero solo si sigue montado
            if is_mounted.current and not asyncio.current_task().cancelled():
                set_loading(False)

    # --- Efecto Unificado: Carga Inicial + Polling ---
    @use_effect(dependencies=[filters, current_page, sort_by, sort_dir])
    def manage_data_lifecycle():
        async def run_lifecycle():
            # 1. Carga inicial
            try:
                await load_equipos()
            except asyncio.CancelledError:
                return

            # 2. Bucle de Polling protegido
            while is_mounted.current:
                await asyncio.sleep(POLLING_INTERVAL_SECONDS)

                if is_syncing:
                    continue

                try:
                    await load_equipos()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    pass

        task = asyncio.create_task(run_lifecycle())
        return lambda: task.cancel()

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
        if not is_mounted.current:
            return

        try:
            await api_client.update_equipo_status(equipo_id, {"field": field, "value": value})
            if is_mounted.current:
                show_notification("Estado del equipo actualizado.", "success")
                await load_equipos()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if is_mounted.current:
                set_error(f"Error al actualizar estado del equipo {equipo_id}: {e}")
                show_notification(f"Error al actualizar: {e}", "error")

    total_pages = use_memo(lambda: max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE), [total_count])

    return {
        "equipos": equipos,
        "loading": loading,
        "is_syncing": is_syncing,
        "error": error,
        "total_count": total_count,
        "filters": filters,
        "set_filters": handle_set_filters,
        "update_equipo_status": update_equipo_status,
        "refresh": load_equipos,
        "trigger_sync": trigger_sync,
        "current_page": current_page,
        "set_current_page": set_current_page,
        "total_pages": total_pages,
        "page_size": PAGE_SIZE,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "handle_sort": handle_sort,
    }
