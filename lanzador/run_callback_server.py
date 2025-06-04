# SAM/Lanzador/service/callback_server.py
import sys
from pathlib import Path


LANZADOR_MODULE_ROOT = Path(__file__).resolve().parent 
SAM_PROJECT_ROOT = LANZADOR_MODULE_ROOT.parent 

if str(SAM_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SAM_PROJECT_ROOT))

from common.utils.logging_setup import RobustTimedRotatingFileHandler # Esto debería funcionar ahora
from common.utils.config_manager import ConfigManager
from common.database.sql_client import DatabaseConnector

from lanzador.service.callback_server import start_callback_server_main

if __name__ == "__main__":
    # Esta parte solo se ejecutaría si corres `python lanzador/service/callback_server.py` directamente
    # lo cual ahora no sería la forma principal.
    print("INFO: callback_server.py ejecutado directamente. Para operación normal, usar run_callback_server.py o python -m ...")
    start_callback_server_main()