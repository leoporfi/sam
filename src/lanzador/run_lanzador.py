import logging
import os
import signal
import sys
from typing import Optional

# --- Configuración del Path ---
try:
    # Agrega el directorio raíz del proyecto a sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Importar y usar ConfigLoader para cargar las variables de .env
    from src.common.utils.config_loader import ConfigLoader

    ConfigLoader.initialize_service("lanzador", __file__)

except Exception as e:
    print(f"Error crítico durante la inicialización de la configuración: {e}")
    sys.exit(1)

# --- Importaciones del Proyecto ---
from src.common.utils.logging_setup import setup_logging
from src.lanzador.service.main import LanzadorService

# --- Constantes y Globales ---
SERVICE_NAME = "lanzador"
service_instance: Optional[LanzadorService] = None


def graceful_shutdown(signum, frame):
    """Manejador de señales para un cierre ordenado."""
    logging.info(f"Señal de parada recibida (Señal: {signum}). Iniciando cierre ordenado...")
    if service_instance:
        service_instance.stop()
    logging.info("El servicio ha finalizado correctamente.")
    sys.exit(0)


def main():
    """Función principal que inicializa y ejecuta el servicio."""
    global service_instance

    # 1. Configurar el logging para este servicio.
    # Esta llamada ahora funciona porque ConfigLoader ya cargó las variables.
    setup_logging(service_name=SERVICE_NAME)
    logging.info(f"Iniciando el servicio: {SERVICE_NAME.capitalize()}")

    try:
        # 2. Registrar los manejadores de señales.
        signal.signal(signal.SIGINT, graceful_shutdown)
        signal.signal(signal.SIGTERM, graceful_shutdown)

        # 3. Crear e iniciar la instancia del servicio.
        # Ya no pasamos un objeto 'config', la clase usará el ConfigManager estático.
        logging.info("Creando instancia del servicio Lanzador...")
        service_instance = LanzadorService()

        logging.info("Iniciando el ciclo principal del servicio Lanzador...")
        service_instance.run()

    except Exception as e:
        logging.critical(f"Error crítico no controlado en el servicio {SERVICE_NAME}: {e}", exc_info=True)
        sys.exit(1)

    finally:
        logging.info(f"El servicio {SERVICE_NAME} ha concluido su ejecución.")


if __name__ == "__main__":
    main()
