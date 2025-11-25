# sam/callback/__main__.py
"""
Punto de entrada para `uv run -m sam.callback`
"""

from sam.common.config_loader import ConfigLoader

from .run_callback import main  # noqa: I001

SERVICE_NAME = "callback"
ConfigLoader.initialize_service(SERVICE_NAME)
main(SERVICE_NAME)
