# SAM/src/common/utils/logging_setup.py
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Dict

# Importar ConfigManager para obtener la configuración
from src.common.utils.config_manager import ConfigManager

# Variable para asegurar que la configuración se aplique solo una vez
_is_configured = False


class RobustTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Una versión más robusta de TimedRotatingFileHandler que maneja errores de permisos
    en entornos Windows, reintentando la rotación del archivo de log.
    """

    def doRollover(self):
        """Sobrescribe el método doRollover para manejar errores de permisos."""
        try:
            super().doRollover()
        except (OSError, PermissionError) as e:
            # En Windows, si el archivo está en uso, puede lanzar PermissionError.
            # Se registra el error en stderr y se continúa sin rotar.
            sys.stderr.write(f"LOGGING_SETUP: No se pudo rotar el archivo de log. Error: {e}\n")
        except Exception as e:
            sys.stderr.write(f"LOGGING_SETUP: Error inesperado al rotar el archivo de log: {e}\n")


def setup_logging(service_name: str):
    """
    Configura el logger raíz para un servicio específico.
    Esta función debe ser llamada UNA SOLA VEZ al inicio del servicio.

    Args:
        service_name: El nombre del servicio (ej. 'lanzador', 'balanceador').
    """
    global _is_configured
    if _is_configured:
        return

    # 1. Obtener la configuración de logging y del servicio específico
    log_config = ConfigManager.get_log_config()

    # Mapeo de service_name a la clave de nombre de archivo en la configuración
    filename_key_map = {
        "lanzador": "app_log_filename_lanzador",
        "balanceador": "app_log_filename_balanceador",
        "callback": "callback_log_filename",
        "interfaz_web": "interfaz_web_log_filename",
    }

    log_filename = log_config.get(filename_key_map.get(service_name, f"sam_{service_name}_app.log"))
    log_directory = Path(log_config.get("directory", "C:/RPA/Logs/SAM"))
    log_file_path = log_directory / log_filename

    # Crear el directorio de logs si no existe
    log_directory.mkdir(parents=True, exist_ok=True)

    # 2. Configurar el formateador
    log_formatter = logging.Formatter(
        fmt=log_config.get("format"),
        datefmt=log_config.get("datefmt"),
    )

    # 3. Configurar los handlers
    # Handler para escribir en archivo con rotación
    file_handler = RobustTimedRotatingFileHandler(
        filename=log_file_path,
        when=log_config.get("when", "midnight"),
        interval=log_config.get("interval", 1),
        backupCount=log_config.get("backupCount", 7),
        encoding=log_config.get("encoding", "utf-8"),
    )
    file_handler.setFormatter(log_formatter)

    # Handler para mostrar logs en la consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)

    # 4. Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_config.get("level_str", "INFO").upper())

    # Limpiar handlers existentes para evitar duplicados
    root_logger.handlers.clear()

    # Añadir los nuevos handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    _is_configured = True
    logging.info(f"Logging configurado para el servicio '{service_name}'. Los logs se guardarán en: {log_file_path}")
