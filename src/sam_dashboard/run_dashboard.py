# SAM/src/sam_dashboard/run_dashboard.py (Estandarizado)
import logging
import os
import sys

# --- Configuración del Path y Carga de Configuración (DEBE SER LO PRIMERO) ---
try:
    # Agrega el directorio raíz del proyecto a sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Importar y usar ConfigLoader para cargar las variables de .env
    from src.common.utils.config_loader import ConfigLoader

    # Usamos "interfaz_web" como nombre del servicio para ser consistentes con el ConfigManager
    ConfigLoader.initialize_service("interfaz_web", __file__)

except Exception as e:
    print(f"Error crítico durante la inicialización de la configuración: {e}")
    sys.exit(1)

# --- Importaciones del Proyecto (Después de la configuración) ---
import uvicorn

from src.common.utils.config_manager import ConfigManager
from src.common.utils.logging_setup import setup_logging

# --- Constantes ---
SERVICE_NAME = "interfaz_web"


def main():
    """
    Función principal que inicializa y ejecuta el servidor de la Interfaz Web.
    """
    # 1. Configurar el logging para este servicio.
    setup_logging(service_name=SERVICE_NAME)
    logging.info(f"Iniciando el servicio: {SERVICE_NAME.capitalize()}")

    try:
        # 2. Obtener la configuración específica del servidor web.
        web_config = ConfigManager.get_interfaz_web_config()
        host = web_config.get("host", "127.0.0.1")
        port = web_config.get("port", 8080)
        reload = web_config.get("debug", False)
        log_level = ConfigManager.get_log_config().get("level_str", "info").lower()

        logging.info(f"Servidor Uvicorn se iniciará en http://{host}:{port} (Reload: {reload})")

        # 3. Ejecutar el servidor Uvicorn.
        # Uvicorn maneja su propio ciclo de vida y cierre controlado.
        # Apunta a la instancia 'app' dentro de 'src.sam_dashboard.main'.
        uvicorn.run("src.sam_dashboard.main:app", host=host, port=port, reload=reload, log_level=log_level)

    except Exception as e:
        logging.critical(f"Error crítico no controlado al iniciar el servicio {SERVICE_NAME}: {e}", exc_info=True)
        sys.exit(1)

    finally:
        logging.info(f"El servicio {SERVICE_NAME} ha concluido.")


if __name__ == "__main__":
    main()
