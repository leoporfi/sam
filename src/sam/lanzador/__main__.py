# sam/lanzador/__main__.py
"""Entry point for lanzador service"""

import asyncio

from sam.common.config_loader import ConfigLoader

from .run_lanzador import main_async

ConfigLoader.initialize_service("lanzador")

if __name__ == "__main__":
    asyncio.run(main_async())
