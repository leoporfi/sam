import logging
import os
import sys

import uvicorn

# --- Configuración del Path y Carga de Configuración ---
# Este bloque es crucial para asegurar que las importaciones funcionen correctamente
# cuando se ejecuta como un script o servicio.
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Asumiendo que run_callback.py está en SAM_PROJECT_ROOT/src/callback/
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Importar y usar ConfigLoader para cargar las variables de .env
    from src.common.utils.config_loader import ConfigLoader

    ConfigLoader.initialize_service("callback", __file__)

except Exception as e:
    print(f"Error crítico durante la inicialización de la configuración: {e}")
    sys.exit(1)

# --- Importaciones del Proyecto (después de configurar el path) ---
from src.common.utils.config_manager import ConfigManager
from src.common.utils.logging_setup import setup_logging

# --- Constantes ---
SERVICE_NAME = "callback"


def main():
    """Función principal que inicializa y ejecuta el servidor de Callbacks con Uvicorn."""

    # 1. Configurar el logging para este servicio.
    setup_logging(service_name=SERVICE_NAME)
    logger = logging.getLogger(__name__)

    logger.info(f"Iniciando el servicio FastAPI: {SERVICE_NAME.capitalize()}")

    try:
        # 2. Obtener la configuración del servidor desde ConfigManager.
        server_config = ConfigManager.get_callback_server_config()
        host = server_config.get("host", "0.0.0.0")
        port = server_config.get("port", 8008)

        # El número de 'threads' de Waitress se puede mapear a 'workers' en Uvicorn para producción.
        # Para desarrollo, 1 worker es suficiente.
        # En producción, esto se gestionaría mejor con un orquestador como Gunicorn + Uvicorn workers.
        workers = server_config.get("threads", 1)

        logger.info(f"Iniciando Uvicorn en http://{host}:{port} con {workers} worker(s)...")

        # 3. Iniciar el servidor Uvicorn.
        #    La cadena "src.callback.service.main:app" apunta al objeto 'app' de FastAPI
        #    en el archivo 'main.py' dentro del path especificado.
        uvicorn.run(
            "src.callback.service.main:app",
            host=host,
            port=port,
            workers=workers,
            log_level=logging.getLogger().getEffectiveLevel(),
            reload=False,  # 'reload' debe ser False para producción
        )

    except Exception as e:
        logger.critical(f"Error crítico no controlado al iniciar el servicio {SERVICE_NAME}: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info(f"El servicio {SERVICE_NAME} ha concluido.")


if __name__ == "__main__":
    main()
