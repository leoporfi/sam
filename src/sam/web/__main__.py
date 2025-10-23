# sam/web/__main__.py
"""Entry point for web service"""

from sam.common.config_loader import ConfigLoader

from .run_web import main

ConfigLoader.initialize_service("interfaz_web")

if __name__ == "__main__":
    main()
