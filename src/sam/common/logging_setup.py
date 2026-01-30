# sam/src/common/logging_setup.py
import logging
import logging.handlers
import os
from pathlib import Path

from .config_loader import ConfigLoader
from .config_manager import ConfigManager


class RelativePathFormatter(logging.Formatter):
    """
    Un formateador de logs que convierte las rutas absolutas de los archivos
    en rutas relativas a la raíz del proyecto, haciendo los logs más limpios.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_root = str(ConfigLoader.get_project_root())

    def format(self, record):
        if hasattr(record, "pathname") and record.pathname.startswith(self.project_root):
            record.pathname = os.path.relpath(record.pathname, self.project_root)
        return super().format(record)


class ReactPyErrorFilter(logging.Filter):
    """
    Filtra errores conocidos de ReactPy que son ruidosos y no afectan
    el funcionamiento core de SAM (bugs internos de ReactPy 1.1.0).
    """

    def filter(self, record):
        msg = record.getMessage()
        # Filtramos los errores específicos que provienen del core de ReactPy
        bad_messages = [
            "Hook stack is in an invalid state",
            "'Layout' object has no attribute '_rendering_queue'",
            "Failed to schedule render via",
            "Task was destroyed but it is pending!",
        ]
        if any(bad in msg for bad in bad_messages):
            # Solo permitimos que se loguee como DEBUG si quisiéramos verlo,
            # pero por ahora lo silenciamos del flujo normal de errores.
            return False
        return True


def setup_logging(service_name: str):
    """
    Configura el sistema de logging para un servicio específico.
    Utiliza TimedRotatingFileHandler para rotar los logs diariamente.
    """
    log_config = ConfigManager.get_log_config()
    log_directory = Path(log_config["directory"])
    log_directory.mkdir(parents=True, exist_ok=True)

    # Determinar el nombre del archivo de log para el servicio actual
    log_filename_key = f"app_log_filename_{service_name}"
    log_filename = log_config.get(log_filename_key, f"sam_{service_name}_app.log")
    log_file_path = log_directory / log_filename

    # Configurar el nivel de logging
    log_level_str = log_config.get("level_str", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Crear el formateador con la ruta relativa
    formatter = RelativePathFormatter(log_config["format"], datefmt=log_config["datefmt"])

    # Configurar el handler de rotación de archivos
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file_path,
        when=log_config["when"],
        interval=log_config["interval"],
        backupCount=log_config["backupCount"],
        encoding=log_config["encoding"],
    )
    file_handler.setFormatter(formatter)

    # Configurar el handler de la consola (para ver los logs en la terminal)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Filtro específico para ReactPy en la Interfaz Web
    if service_name == "interfaz_web":
        rp_filter = ReactPyErrorFilter()
        file_handler.addFilter(rp_filter)
        console_handler.addFilter(rp_filter)

    # Configurar el logger raíz para que envíe los logs a ambos handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [file_handler, console_handler]

    logging.getLogger("httpx").setLevel(logging.WARNING)

    if service_name == "interfaz_web":
        # RFR-40: Reducimos ruidos de reactpy si el filtro no captura algo (bugs concurrencia 1.1.0)
        logging.getLogger("reactpy.core").setLevel(logging.CRITICAL)
        logging.getLogger("reactpy.backend").setLevel(logging.CRITICAL)

    logging.info(f"Logging configurado para el servicio '{service_name}'. Los logs se guardarán en: {log_file_path}")
