# sam/web/__main__.py
"""
Punto de entrada para `uv run -m sam.web`
"""

from sam.common.config_loader import ConfigLoader

from .run_web import main  # noqa: I001

# El SERVICE_NAME debe coincidir con el del runner
SERVICE_NAME = "web"
ConfigLoader.initialize_service(SERVICE_NAME)
main(SERVICE_NAME)
