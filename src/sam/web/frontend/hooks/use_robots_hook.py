# sam/web/frontend/hooks/use_robots_hook.py
"""
Hook para gestionar el estado del dashboard de robots.

Este hook maneja la carga, filtrado, paginación y sincronización de robots,
siguiendo el principio de Inyección de Dependencias de la Guía General de SAM.
"""

import asyncio
from typing import Any, Dict, Optional

from reactpy import use_callback, use_context, use_effect, use_memo, use_ref, use_state

from ..api.api_client import APIClient, get_api_client
from ..shared.notifications import NotificationContext
from ..state.app_context import use_app_context

# --- Constantes de configuración ---
PAGE_SIZE = 100
# Filtros iniciales:
# - name: búsqueda por nombre de robot
# - active: solo activos por defecto
# - online: filtro por robots online/offline (None = todos)
# - programado: filtra por robots con/sin programaciones activas (None = todos)
INITIAL_FILTERS = {"name": None, "active": True, "online": None, "programado": None}
POLLING_INTERVAL_SECONDS = 120
SYNC_POLLING_INTERVAL_SECONDS = 3


def use_robots(api_client: Optional[APIClient] = None) -> Dict[str, Any]:
    """
    Hook para gestionar el estado del dashboard de robots con recuperación de estado de Sync.

    Args:
        api_client: Cliente API opcional para inyección de dependencias (para testing).
                   Si no se proporciona, se obtiene del contexto o se usa get_api_client().

    Returns:
        Dict con las siguientes keys:
            - robots: List[Dict] - Lista de robots
            - loading: bool - Estado de carga
            - is_syncing: bool - Si está sincronizando
            - error: Optional[str] - Mensaje de error
            - total_count: int - Total de robots
            - filters: Dict - Filtros actuales
            - set_filters: Callable - Función para actualizar filtros
            - update_robot_status: Callable - Función para actualizar estado de robot
            - refresh: Callable - Función para recargar robots
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
    # IMPORTANTE: Todos los hooks deben llamarse incondicionalmente al inicio
    # para cumplir con las reglas de ReactPy (hooks siempre en el mismo orden)
    try:
        app_context = use_app_context()
    except Exception:
        app_context = {}

    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    # Rastrear si ya se mostró la alerta de fallback (para evitar spam)
    fallback_alert_shown = use_ref(False)

    # Determinar qué api_client usar (después de llamar todos los hooks)
    if api_client is None:
        api_client = app_context.get("api_client")
        if api_client is None:
            # Fallback a get_api_client() para compatibilidad temporal
            api_client = get_api_client()  # type: ignore

            # Mostrar alerta solo una vez cuando se detecta el uso del fallback
            if not fallback_alert_shown.current:
                fallback_alert_shown.current = True
                show_notification(
                    "⚠️ Advertencia: Se está usando fallback a singleton get_api_client(). "
                    "El contexto de aplicación no está disponible. Esto debería resolverse pronto.",
                    "warning",
                )

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

    # Safety Check: Referencia de montaje
    is_mounted = use_ref(True)

    @use_effect(dependencies=[])
    def mount_lifecycle():
        is_mounted.current = True
        return lambda: setattr(is_mounted, "current", False)

    # --- Función de carga de datos ---
    @use_callback
    async def load_robots():
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
            if is_mounted.current and not asyncio.current_task().cancelled():
                set_loading(False)

    # --- Lógica centralizada de Monitoreo de Sync ---
    async def monitor_active_sync():
        """Bucle que espera a que la sincronización termine."""
        if not is_mounted.current:
            return

        try:
            while is_mounted.current:
                await asyncio.sleep(SYNC_POLLING_INTERVAL_SECONDS)
                try:
                    status_data = await api_client.get_sync_status()
                    # Si ya no está corriendo, rompemos el bucle
                    if status_data.get("robots") == "idle":
                        break
                except Exception as poll_error:
                    if is_mounted.current:
                        print(f"Warn polling sync: {poll_error}")

            # Al terminar el bucle, actualizamos todo
            if is_mounted.current:
                show_notification("Sincronización completada. Actualizando lista...", "success")
                await load_robots()
                set_is_syncing(False)
        except Exception as e:
            if is_mounted.current:
                show_notification(f"Error durante monitoreo de sync: {e}", "error")
                set_is_syncing(False)

    # --- Efecto: Recuperación de estado de Sync al cargar página ---
    @use_effect(dependencies=[])
    def check_sync_on_load():
        async def check():
            if not is_mounted.current:
                return
            try:
                # Preguntar al backend si ya está trabajando
                status_data = await api_client.get_sync_status()
                if status_data.get("robots") != "idle":
                    if is_mounted.current:
                        set_is_syncing(True)
                        show_notification("Sincronización en curso detectada (Background)...", "info")
                        # Retomamos el monitoreo
                        await monitor_active_sync()
            except Exception:
                pass  # Fallo silencioso en check inicial para no molestar

        task = asyncio.create_task(check())
        return lambda: task.cancel()

    # --- Efecto: Carga Inicial + Polling de Datos ---
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

    # --- Acción manual de Sync ---
    @use_callback
    async def trigger_sync(event=None):
        """Sincroniza solo robots desde A360."""
        if is_syncing or not is_mounted.current:
            return

        set_is_syncing(True)
        show_notification("Sincronizando robots desde A360...", "info")
        try:
            # 1. Lanzar la orden
            await api_client.trigger_sync_robots()

            if is_mounted.current:
                show_notification("Sincronización iniciada. Esperando finalización...", "info")

            # 2. Esperar (usando la misma lógica que el recovery)
            await monitor_active_sync()

        except Exception as e:
            if is_mounted.current:
                #  Si es 409 Conflict, significa que ya corría.
                # Podríamos manejarlo soft, pero el monitor de inicio ya debería haberlo atrapado.
                show_notification(f"Error al iniciar sincronización: {e}", "error")
                # set_error(f"Error en sincronización: {e}")
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
