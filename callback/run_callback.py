# SAM/callback/run_callback.py

import sys
from pathlib import Path

# Añadir la raíz del proyecto al sys.path para permitir importaciones
CALLBACK_MODULE_ROOT = Path(__file__).resolve().parent
SAM_PROJECT_ROOT = CALLBACK_MODULE_ROOT.parent

if str(SAM_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SAM_PROJECT_ROOT))

# Importar el punto de entrada del servicio de callback desde su nueva ubicación
from callback.service.main import start_callback_server_main

if __name__ == "__main__":
    start_callback_server_main()