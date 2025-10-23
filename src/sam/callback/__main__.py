# sam/callback/__main__.py
"""Entry point for callback service"""

from sam.common.config_loader import ConfigLoader

from .run_callback import main

ConfigLoader.initialize_service("callback")

if __name__ == "__main__":
    main()
