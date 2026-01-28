# src/sam/web/frontend/hooks/use_config_hook.py
import asyncio
from typing import Any

from reactpy import use_context, use_effect, use_state

from ..api.api_client import get_api_client
from ..shared.notifications import NotificationContext
from ..state.app_context import use_app_context


def use_config():
    """Hook para gestionar la configuración dinámica del sistema."""
    configs, set_configs = use_state([])
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)

    # Contextos
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]

    try:
        app_context = use_app_context()
        api_client = app_context.get("api_client") or get_api_client()
    except Exception:
        api_client = get_api_client()

    async def fetch_configs():
        set_loading(True)
        try:
            data = await api_client.get_configs()
            set_configs(data)
            set_error(None)
        except Exception as e:
            set_error(str(e))
            show_notification(f"Error al cargar configuración: {e}", "error")
        finally:
            set_loading(False)

    async def update_config(key: str, value: Any):
        try:
            await api_client.update_config(key, value)
            show_notification(f"Configuración '{key}' actualizada", "success")
            await fetch_configs()
            return True
        except Exception as e:
            show_notification(f"Error al actualizar '{key}': {e}", "error")
            return False

    @use_effect(dependencies=[])
    def init_load():
        task = asyncio.create_task(fetch_configs())
        return lambda: task.cancel()

    return {
        "configs": configs,
        "loading": loading,
        "error": error,
        "refresh": fetch_configs,
        "update_config": update_config,
    }
