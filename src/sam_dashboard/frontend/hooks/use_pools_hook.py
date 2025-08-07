# src/sam_dashboard/frontend/hooks/use_pools_hook.py

from reactpy import use_callback, use_effect, use_state

from ..api_client import get_api_client


def use_pools_management():
    """Hook completo para la gestión de pools."""
    api_client = get_api_client()
    pools, set_pools = use_state([])
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)

    @use_callback
    async def load_pools():
        set_loading(True)
        set_error(None)
        try:
            data = await api_client.get_pools()
            set_pools(data)
        except Exception as e:
            set_error(str(e))
        finally:
            set_loading(False)

    use_effect(load_pools, [])

    # Esto asegura que la función sea estable entre renderizados y maneje correctamente los eventos.
    @use_callback
    async def add_pool(pool_data):
        # La lógica de la API es la misma, pero ahora está correctamente registrada como un callback.
        await api_client.create_pool(pool_data)
        # Después de crear, volvemos a cargar toda la lista para asegurar consistencia.
        await load_pools()

    @use_callback
    async def edit_pool(pool_id, pool_data):
        await api_client.update_pool(pool_id, pool_data)
        await load_pools()  # Recargar para ver los cambios

    @use_callback
    async def remove_pool(pool_id):
        await api_client.delete_pool(pool_id)
        # En lugar de filtrar localmente, recargamos para obtener el estado más reciente de la BD.
        await load_pools()

    return {
        "pools": pools,
        "loading": loading,
        "error": error,
        "refresh": load_pools,
        "add_pool": add_pool,
        "edit_pool": edit_pool,
        "remove_pool": remove_pool,
    }
