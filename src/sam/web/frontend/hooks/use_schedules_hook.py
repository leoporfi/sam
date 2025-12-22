# sam/web/frontend/hooks/use_schedules_hook.py
"""
Hook para gestionar el estado del dashboard de programaciones (schedules).

Este hook maneja la carga, filtrado, paginación de programaciones,
siguiendo el principio de Inyección de Dependencias de la Guía General de SAM.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional

from reactpy import use_callback, use_context, use_effect, use_memo, use_ref, use_state

from ..api.api_client import APIClient, get_api_client
from ..shared.notifications import NotificationContext
from ..state.app_context import use_app_context

PAGE_SIZE = 100
INITIAL_FILTERS = {"robot": None, "tipo": None, "activo": None, "search": None}

POLL_INTERVAL = 120


def use_schedules(api_client: Optional[APIClient] = None) -> Dict[str, Any]:
    """
    Hook para gestionar programaciones (schedules).

    Args:
        api_client: Cliente API opcional para inyección de dependencias (para testing).
                   Si no se proporciona, se obtiene del contexto o se usa get_api_client().

    Returns:
        Dict con las siguientes keys:
            - schedules: List[Dict] - Lista de programaciones
            - loading: bool - Estado de carga
            - error: Optional[str] - Mensaje de error
            - total_count: int - Total de programaciones
            - filters: Dict - Filtros actuales
            - set_filters: Callable - Función para actualizar filtros
            - refresh: Callable - Función para recargar programaciones
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
    api = api_client
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

    # Safety Check
    is_mounted = use_ref(True)

    @use_effect(dependencies=[])
    def mount_lifecycle():
        is_mounted.current = True
        return lambda: setattr(is_mounted, "current", False)

    @use_callback
    async def load_schedules():
        if not is_mounted.current:
            return

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

            if is_mounted.current:
                set_schedules(data.get("schedules", []))
                set_total(data.get("total_count", 0))

        except asyncio.CancelledError:
            raise
        except Exception as e:
            if is_mounted.current:
                set_error(str(e))
                show(f"Error al cargar programaciones: {e}", "error")
        finally:
            if is_mounted.current and not asyncio.current_task().cancelled():
                set_loading(False)

    @use_effect(dependencies=[filters, page])
    def _load_on_filters_or_page_change():
        async def load():
            await load_schedules()

        task = asyncio.create_task(load())
        return lambda: task.cancel()

    # --- Polling desactivado ---
    # Si se necesita reactivar el polling, descomentar el siguiente bloque:
    # @use_effect(dependencies=[])
    # def _setup_polling():
    #     async def poll_loop():
    #         while is_mounted.current:
    #             await asyncio.sleep(POLL_INTERVAL)
    #             try:
    #                 params = {**filters, "page": page, "size": PAGE_SIZE}
    #                 data = await api.get_schedules(params)
    #                 if is_mounted.current:
    #                     set_schedules(data.get("schedules", []))
    #                     set_total(data.get("total_count", 0))
    #             except Exception:
    #                 pass
    #     task = asyncio.create_task(poll_loop())
    #     return lambda: task.cancel()

    @use_callback
    def toggle_active(schedule_id: int, activo: bool):
        async def _logic():
            if not is_mounted.current:
                return
            try:
                await api.toggle_schedule_status(schedule_id, activo)
                if is_mounted.current:
                    show("Estado cambiado", "success")
                    await load_schedules()
            except Exception as e:
                if is_mounted.current:
                    show(str(e), "error")
                    await load_schedules()

        asyncio.create_task(_logic())

    @use_callback
    async def save_schedule(data: dict):
        if not is_mounted.current:
            return

        schedule_id = data.get("ProgramacionId")
        if not schedule_id:
            show("No se pudo guardar: ID de programación no encontrado.", "error")
            raise ValueError("ID de programación no encontrado")

        try:
            await api.update_schedule_details(schedule_id, data)
            if is_mounted.current:
                show("Programación actualizada", "success")
                await load_schedules()
        except Exception as e:
            if is_mounted.current:
                show(f"Error al guardar: {e}", "error")
            raise

    @use_callback
    async def save_schedule_equipos(schedule_id: int, equipo_ids: List[int], on_success: Optional[Callable] = None):
        if not is_mounted.current:
            return

        if not schedule_id:
            show("No se pudo guardar: ID de programación no encontrado.", "error")
            raise ValueError("ID de programación no encontrado")

        try:
            # Llama al API
            await api.update_schedule_devices(schedule_id, equipo_ids)
            if is_mounted.current:
                show("Equipos de la programación actualizados", "success")
                await load_schedules()

        except Exception as e:
            if is_mounted.current:
                show(f"Error al guardar equipos: {e}", "error")
            raise

    @use_callback
    async def delete_schedule(schedule_data: dict):
        """Elimina una programación. Requiere confirmación previa."""
        if not is_mounted.current:
            return

        schedule_id = schedule_data.get("ProgramacionId")
        robot_id = schedule_data.get("RobotId")

        if not schedule_id or not robot_id:
            show("No se pudo eliminar: datos incompletos.", "error")
            raise ValueError("ID de programación o robot no encontrado")

        try:
            await api.delete_schedule(schedule_id, robot_id)
            if is_mounted.current:
                show("Programación eliminada", "success")
                await load_schedules()
        except Exception as e:
            if is_mounted.current:
                show(f"Error al eliminar: {e}", "error")
            raise

    @use_callback
    async def create_schedule(schedule_data: dict):
        """Crea una nueva programación."""
        if not is_mounted.current:
            return

        try:
            await api.create_schedule(schedule_data)
            if is_mounted.current:
                show("Programación creada", "success")
                await load_schedules()
        except Exception as e:
            if is_mounted.current:
                show(f"Error al crear: {e}", "error")
            raise

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
        "delete_schedule": delete_schedule,
        "create_schedule": create_schedule,
        "refresh": load_schedules,
    }
