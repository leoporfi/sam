# sam/balanceador/__main__.py
"""
Punto de entrada para `uv run -m sam.balanceador`
"""

from sam.common.config_loader import ConfigLoader

from .run_balanceador import main  # noqa: I001

SERVICE_NAME = "balanceador"
ConfigLoader.initialize_service(SERVICE_NAME)
main(SERVICE_NAME)
