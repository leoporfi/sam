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

    ConfigLoader.initialize_service("callback", __file__)

except Exception as e:
    print(f"Error crítico durante la inicialización de la configuración: {e}")
    sys.exit(1)

from src.callback.service.main import CallbackService
from src.common.utils.config_manager import ConfigManager

# --- Importaciones del Proyecto (Después de la configuración) ---
from src.common.utils.logging_setup import setup_logging

# --- Constantes ---
SERVICE_NAME = "callback"


def main():
    """Función principal que inicializa y ejecuta el servidor de Callbacks."""

    # 1. Configurar el logging para este servicio.
    setup_logging(service_name=SERVICE_NAME)
    logging.info(f"Iniciando el servicio: {SERVICE_NAME.capitalize()}")

    try:
        # 2. Crear una instancia del servicio.
        # La clase CallbackService ahora maneja su propia configuración y ciclo de vida.
        server = CallbackService()

        # 3. Iniciar el servidor.
        server.start()

    except Exception as e:
        logging.critical(f"Error crítico no controlado al iniciar el servicio {SERVICE_NAME}: {e}", exc_info=True)
        sys.exit(1)

    finally:
        logging.info(f"El servicio {SERVICE_NAME} ha concluido.")


if __name__ == "__main__":
    main()
