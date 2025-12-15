# sam/web/frontend/hooks/use_pools_hook.py
"""
Hook para gestionar el estado del dashboard de pools.

Este hook maneja la carga, creación, actualización y eliminación de pools,
siguiendo el principio de Inyección de Dependencias de la Guía General de SAM.
"""
import asyncio
from typing import Any, Callable, Dict, List, Optional

from reactpy import use_callback, use_effect, use_ref, use_state

from ..api.api_client import APIClient, get_api_client


def use_pools_management(api_client: Optional[APIClient] = None) -> Dict[str, Any]:
    """
    Hook completo para la gestión de pools (CRUD y refresh).
    Centraliza toda la lógica de estado y las llamadas a la API para los pools.
    
    Args:
        api_client: Cliente API opcional para inyección de dependencias (para testing).
                   Si no se proporciona, se obtiene del contexto o se usa get_api_client().
    
    Returns:
        Dict con las siguientes keys:
            - pools: List[Dict] - Lista de pools
            - loading: bool - Estado de carga
            - error: Optional[str] - Mensaje de error
            - refresh: Callable - Función para recargar pools
            - create_pool: Callable - Función para crear pool
            - update_pool: Callable - Función para actualizar pool
            - delete_pool: Callable - Función para eliminar pool
            - get_pool_assignments: Callable - Función para obtener asignaciones
            - update_pool_assignments: Callable - Función para actualizar asignaciones
    """
    # Aplicar Inyección de Dependencias: permitir inyectar api_client para testing
    if api_client is None:
        api_client = get_api_client()  # type: ignore
    pools, set_pools = use_state([])
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)

    # [NUEVO] Safety Check
    is_mounted = use_ref(True)

    @use_effect(dependencies=[])
    def mount_lifecycle():
        is_mounted.current = True
        return lambda: setattr(is_mounted, "current", False)

    @use_callback
    async def load_pools():
        """Carga o recarga la lista de pools desde el backend."""
        if not is_mounted.current:
            return

        set_loading(True)
        set_error(None)
        try:
            data = await api_client.get_pools()
            if is_mounted.current:
                set_pools(data.get("pools", []))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if is_mounted.current:
                set_error(str(e))
        finally:
            if is_mounted.current and not asyncio.current_task().cancelled():
                set_loading(False)

    @use_effect(dependencies=[])  # solo al montar
    def setup_load():
        task = asyncio.create_task(load_pools())
        return lambda: task.cancel()

    @use_callback
    async def add_pool(pool_data):
        if not is_mounted.current:
            return
        await api_client.create_pool(pool_data)
        if is_mounted.current:
            await load_pools()

    @use_callback
    async def edit_pool(pool_id, pool_data):
        if not is_mounted.current:
            return
        try:
            await api_client.update_pool(pool_id, pool_data)
            if is_mounted.current:
                await load_pools()
        except asyncio.CancelledError:
            raise
        except Exception:
            raise

    @use_callback
    async def remove_pool(pool_id):
        if not is_mounted.current:
            return
        try:
            await api_client.delete_pool(pool_id)
            if is_mounted.current:
                await load_pools()
        except asyncio.CancelledError:
            raise
        except Exception:
            raise

    return {
        "pools": pools,
        "loading": loading,
        "error": error,
        "refresh": load_pools,
        "add_pool": add_pool,
        "edit_pool": edit_pool,
        "remove_pool": remove_pool,
    }
