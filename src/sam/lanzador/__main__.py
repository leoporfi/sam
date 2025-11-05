# sam/lanzador/__main__.py
"""
Punto de entrada para `uv run -m sam.lanzador`
"""
from sam.common.config_loader import ConfigLoader

from .run_lanzador import main  # noqa: I001

SERVICE_NAME = "lanzador"
ConfigLoader.initialize_service(SERVICE_NAME)
main(SERVICE_NAME)