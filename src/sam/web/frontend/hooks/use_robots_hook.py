# sam/web/hooks/use_robots_hook.py
import asyncio
from typing import Dict

from reactpy import use_callback, use_context, use_effect, use_memo, use_ref, use_state

from ..api.api_client import get_api_client
from ..shared.notifications import NotificationContext

# --- Constantes de configuración ---
PAGE_SIZE = 100
INITIAL_FILTERS = {"name": None, "active": True, "online": None}
POLLING_INTERVAL_SECONDS = 120
SYNC_POLLING_INTERVAL_SECONDS = 3


def use_robots():
    """
    Hook para gestionar el estado del dashboard de robots.
    """
    api_client = get_api_client()
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    # --- Estados del hook ---
    robots, set_robots = use_state([])
    loading, set_loading = use_state(True)
    is_syncing, set_is_syncing = use_state(False)
    error, set_error = use_state(None)
    total_count, set_total_count = use_state(0)
    filters, set_filters = use_state(INITIAL_FILTERS)
    current_page, set_current_page = use_state(1)
    sort_by, set_sort_by = use_state("Robot")
    sort_dir, set_sort_dir = use_state("asc")

    # Referencia para saber si el componente está montado
    is_mounted = use_ref(True)

    @use_effect(dependencies=[])
    def mount_lifecycle():
        is_mounted.current = True
        return lambda: setattr(is_mounted, "current", False)

    # --- Función de carga de datos ---
    @use_callback
    async def load_robots():
        # [CHECK] Si ya no existe la UI, abortamos inmediatamente
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

            data = await api_client.get_robots(api_params)

            # [CHECK] Solo actualizamos estado si seguimos montados
            if is_mounted.current:
                set_robots(data.get("robots", []))
                set_total_count(data.get("total_count", 0))

        except asyncio.CancelledError:
            raise
        except Exception as e:
            if is_mounted.current:
                set_error(str(e))
                show_notification(f"Error al cargar robots: {e}", "error")
        finally:
            # [CHECK] Evitar setear loading en un componente desmontado
            if is_mounted.current and not asyncio.current_task().cancelled():
                set_loading(False)

    # --- Efecto Unificado: Carga Inicial + Polling ---
    @use_effect(dependencies=[filters, current_page, sort_by, sort_dir])
    def manage_data_lifecycle():
        async def run_lifecycle():
            # 1. Carga inicial inmediata al montar o cambiar filtros
            try:
                await load_robots()
            except asyncio.CancelledError:
                return

            # 2. Bucle de Polling
            # Usamos is_mounted.current como condición de seguridad extra
            while is_mounted.current:
                await asyncio.sleep(POLLING_INTERVAL_SECONDS)

                # Si estamos sincronizando manualmente, saltamos este ciclo de polling
                if is_syncing:
                    continue

                try:
                    await load_robots()
                except asyncio.CancelledError:
                    break  # Salir si el componente se desmonta o dependencias cambian
                except Exception:
                    pass  # Ignorar errores silenciosos en polling

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
    async def trigger_sync(event=None):
        """Sincroniza solo robots desde A360."""
        if is_syncing or not is_mounted.current:
            return

        set_is_syncing(True)
        show_notification("Sincronizando robots desde A360...", "info")
        try:
            await api_client.trigger_sync_robots()

            if is_mounted.current:
                show_notification("Sincronización iniciada. Esperando finalización...", "info")

            # Bucle seguro que muere si el componente muere
            while is_mounted.current:
                await asyncio.sleep(SYNC_POLLING_INTERVAL_SECONDS)
                try:
                    status_data = await api_client.get_sync_status()
                    if status_data.get("robots") == "idle":
                        break
                except Exception as poll_error:
                    if is_mounted.current:
                        show_notification(f"Error al consultar estado de sync: {poll_error}", "warning")

            if is_mounted.current:
                show_notification("Sincronización completada. Actualizando lista...", "success")
                await load_robots()
                set_is_syncing(False)

        except Exception as e:
            if is_mounted.current:
                show_notification(f"Error al iniciar sincronización: {e}", "error")
                set_error(f"Error en sincronización: {e}")
                set_is_syncing(False)

    @use_callback
    async def update_robot_status(robot_id: int, status_data: Dict[str, bool]):
        if not is_mounted.current:
            return
        try:
            await api_client.update_robot_status(robot_id, status_data)
            if is_mounted.current:
                await load_robots()
        except Exception as e:
            if is_mounted.current:
                set_error(f"Error al actualizar estado del robot {robot_id}: {e}")

    total_pages = use_memo(lambda: max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE), [total_count])

    return {
        "robots": robots,
        "loading": loading,
        "is_syncing": is_syncing,
        "error": error,
        "total_count": total_count,
        "filters": filters,
        "set_filters": handle_set_filters,
        "update_robot_status": update_robot_status,
        "refresh": load_robots,
        "trigger_sync": trigger_sync,
        "current_page": current_page,
        "set_current_page": set_current_page,
        "total_pages": total_pages,
        "page_size": PAGE_SIZE,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "handle_sort": handle_sort,
    }
