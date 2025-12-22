# sam/web/frontend/hooks/use_equipos_hook.py
"""
Hook para gestionar el estado del dashboard de equipos.

Este hook maneja la carga, filtrado, paginación y sincronización de equipos,
siguiendo el principio de Inyección de Dependencias de la Guía General de SAM.
"""
import asyncio
from typing import Any, Callable, Dict, List, Optional

from reactpy import use_callback, use_context, use_effect, use_memo, use_ref, use_state

from ..api.api_client import APIClient, get_api_client
from ..shared.notifications import NotificationContext
from ..state.app_context import use_app_context

PAGE_SIZE = 100
INITIAL_FILTERS = {"name": None, "active": None, "balanceable": None}
POLLING_INTERVAL_SECONDS = 60
SYNC_POLLING_INTERVAL_SECONDS = 3


def use_equipos(api_client: Optional[APIClient] = None) -> Dict[str, Any]:
    """
    Hook para gestionar equipos con recuperación de estado de Sync.
    
    Args:
        api_client: Cliente API opcional para inyección de dependencias (para testing).
                   Si no se proporciona, se obtiene del contexto o se usa get_api_client().
    
    Returns:
        Dict con las siguientes keys:
            - equipos: List[Dict] - Lista de equipos
            - loading: bool - Estado de carga
            - is_syncing: bool - Si está sincronizando
            - error: Optional[str] - Mensaje de error
            - total_count: int - Total de equipos
            - filters: Dict - Filtros actuales
            - set_filters: Callable - Función para actualizar filtros
            - update_equipo_status: Callable - Función para actualizar estado de equipo
            - refresh: Callable - Función para recargar equipos
            - trigger_sync: Callable - Función para iniciar sincronización
            - current_page: int - Página actual
            - set_current_page: Callable - Función para cambiar página
            - total_pages: int - Total de páginas
            - page_size: int - Tamaño de página
            - sort_by: str - Columna de ordenamiento
            - sort_dir: str - Dirección de ordenamiento ("asc" o "desc")
            - handle_sort: Callable - Función para manejar ordenamiento
    """
    # Aplicar Inyección de Dependencias: permitir inyectar api_client para testing
    # Si no se proporciona, intentar obtener del contexto de la aplicación
    if api_client is None:
        try:
            app_context = use_app_context()
            api_client = app_context.get("api_client")
            if api_client is None:
                # Fallback a get_api_client() para compatibilidad temporal
                api_client = get_api_client()  # type: ignore
        except Exception:
            # Fallback a get_api_client() para compatibilidad temporal
            api_client = get_api_client()  # type: ignore
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

    # Safety Check
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

    # --- Lógica centralizada de Monitoreo ---
    async def monitor_active_sync():
        if not is_mounted.current:
            return
        try:
            while is_mounted.current:
                await asyncio.sleep(SYNC_POLLING_INTERVAL_SECONDS)
                try:
                    status_data = await api_client.get_sync_status()
                    # A360 devuelve "idle" o "running" bajo la key "equipos"
                    if status_data.get("equipos") == "idle":
                        break
                except Exception as poll_error:
                    if is_mounted.current:
                        show_notification(f"Error al consultar estado de sync: {poll_error}", "warning")

            if is_mounted.current:
                show_notification("Sincronización de equipos completada.", "success")
                await load_equipos()
                set_is_syncing(False)
        except Exception as e:
            if is_mounted.current:
                show_notification(f"Error monitoreando sync: {e}", "error")
                set_is_syncing(False)

    # --- Efecto: Recuperación de estado Sync al inicio ---
    @use_effect(dependencies=[])
    def check_sync_on_load():
        async def check():
            if not is_mounted.current:
                return
            try:
                status = await api_client.get_sync_status()
                if status.get("equipos") != "idle":
                    if is_mounted.current:
                        set_is_syncing(True)
                        show_notification("Sincronización de equipos en curso...", "info")
                        await monitor_active_sync()
            except Exception:
                pass

        task = asyncio.create_task(check())
        return lambda: task.cancel()

    @use_callback
    async def trigger_sync(event=None):
        if is_syncing or not is_mounted.current:
            return

        set_is_syncing(True)
        show_notification("Iniciando sincronización de equipos...", "info")
        try:
            await api_client.trigger_sync_equipos()
            if is_mounted.current:
                show_notification("Petición enviada. Esperando...", "info")

            # Reutilizamos el monitor
            await monitor_active_sync()

        except asyncio.CancelledError:
            raise
        except Exception as e:
            if is_mounted.current:
                show_notification(f"Error al iniciar sincronización: {e}", "error")
                # set_error(f"Error en sincronización: {e}")
                set_is_syncing(False)
        finally:
            if is_mounted.current and not asyncio.current_task().cancelled():
                # Solo por si acaso algo falló muy temprano
                pass

    # --- Ciclo de vida de Datos ---
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
        except Exception as e:
            if is_mounted.current:
                # set_error(f"Error al actualizar estado del equipo {equipo_id}: {e}")
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
