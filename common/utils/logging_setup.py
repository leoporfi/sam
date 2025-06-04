# SAM/common/utils/logging_setup.py
import os
import sys
import logging
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Dict, Any, Optional

# No importamos ConfigManager aquí para evitar dependencia circular si ConfigManager lo usa.
# Los parámetros de log se pasarán a esta función.

_loggers_configured: Dict[str, bool] = {} # Para rastrear loggers ya configurados


class RobustTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Una versión más robusta de TimedRotatingFileHandler que maneja errores de permisos.
    
    Esta clase sobrescribe el método doRollover para manejar errores cuando otro proceso
    está utilizando el archivo de log, permitiendo que el logging continúe sin interrupciones.
    """
    
    def __init__(self, *args, **kwargs):
        self.max_retries = kwargs.pop('max_retries', 3) if 'max_retries' in kwargs else 3
        self.retry_delay = kwargs.pop('retry_delay', 0.5) if 'retry_delay' in kwargs else 0.5
        super().__init__(*args, **kwargs)
    
    def doRollover(self):
        """Sobrescribe el método doRollover para manejar errores de permisos."""
        for attempt in range(self.max_retries):
            try:
                # Intenta realizar la rotación normal
                super().doRollover()
                return  # Si tiene éxito, salimos del método
            except PermissionError as e:
                # Si es el último intento, registramos el error pero no lo propagamos
                if attempt == self.max_retries - 1:
                    sys.stderr.write(f"Error al rotar archivo de log después de {self.max_retries} intentos: {e}\n")
                    # No propagamos la excepción para que el logging pueda continuar
                    return
                # Si no es el último intento, esperamos un poco y volvemos a intentar
                time.sleep(self.retry_delay)
            except Exception as e:
                # Para otros errores, los registramos pero no los propagamos
                sys.stderr.write(f"Error inesperado al rotar archivo de log: {e}\n")
                return

def setup_logging(
        log_config: Dict[str, Any], # Diccionario con la configuración de LOG_CONFIG
        logger_name: Optional[str] = None, # Si es None, configura el logger raíz
        log_file_name_override: Optional[str] = None # Para especificar un nombre de archivo diferente
    ) -> logging.Logger:
    """
    Configura y devuelve un logger basado en la configuración proporcionada.
    """
    target_logger_name = logger_name if logger_name else logging.getLogger().name # '' para raíz, o el nombre

    if _loggers_configured.get(target_logger_name):
        logger.debug(f"Logger '{target_logger_name}' ya configurado, devolviendo instancia existente.")
        return logging.getLogger(target_logger_name) # Devolver instancia existente si ya se configuró

    log_level_str = log_config.get("level_str", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    target_logger = logging.getLogger(target_logger_name)
    target_logger.setLevel(log_level)
    # Evitar que los loggers nombrados propaguen al raíz si el raíz ya tiene handlers o si no queremos duplicados
    if target_logger_name != logging.getLogger().name : # Si es un logger nombrado
         target_logger.propagate = False


    # Determinar nombre de archivo
    if log_file_name_override:
        actual_log_filename = log_file_name_override
    elif target_logger_name == "SAMCallbackServer": # Nombre específico usado en callback_server
        actual_log_filename = log_config.get("callback_log_filename", "sam_callback_server.log")
    elif target_logger_name == "SAMBalanceador": # Nombre específico para el Balanceador
        actual_log_filename = log_config.get("app_log_filename_balanceador", "sam_balanceador_app.log")
    else: # Para el lanzador principal u otros (incluyendo el raíz)
        actual_log_filename = log_config.get("app_log_filename_lanzador", "sam_lanzador_app.log")

    log_directory = log_config.get("directory", "C:/RPA/Logs/SAM_Default")
    log_file_path = Path(log_directory) / actual_log_filename
    
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Configurar handlers solo si no tiene (para evitar duplicados)
    if not target_logger.handlers:
        # Handler para archivo
        try:
            file_handler = RobustTimedRotatingFileHandler(
                filename=str(log_file_path),
                when=log_config.get("when", "midnight"),
                interval=log_config.get("interval", 1),
                backupCount=log_config.get("backupCount", 7),
                encoding=log_config.get("encoding", "utf-8"),
                max_retries=3,
                retry_delay=0.5
            )
            formatter = logging.Formatter(
                fmt=log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
                datefmt=log_config.get("datefmt", "%Y-%m-%d %H:%M:%S")
            )
            file_handler.setFormatter(formatter)
            target_logger.addHandler(file_handler)
        except Exception as e_fh:
            print(f"Error CRÍTICO creando FileHandler para '{log_file_path}': {e_fh}", file=sys.stderr)

        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter( # Mismo formato o uno más simple para consola
             fmt=log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
             datefmt=log_config.get("datefmt", "%Y-%m-%d %H:%M:%S")
        )
        console_handler.setFormatter(console_formatter)
        target_logger.addHandler(console_handler)
        
        print(f"Logger '{target_logger_name}' configurado con handlers. Path: {log_file_path}")

    _loggers_configured[target_logger_name] = True
    return target_logger