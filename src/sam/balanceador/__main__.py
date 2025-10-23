"""Entry point for balanceador service"""

from sam.common.config_loader import ConfigLoader

from .run_balanceador import main

ConfigLoader.initialize_service("balanceador")

if __name__ == "__main__":
    main()
