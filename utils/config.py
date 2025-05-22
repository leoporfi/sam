# utils/config.py
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de base de datos
SQL_SERVER_CONFIG = {
    "driver": os.getenv("SQL_SERVER_DRIVER", "{ODBC Driver 17 for SQL Server}"),
    "server": os.getenv("SQL_SERVER_HOST"),
    "database": os.getenv("SQL_SERVER_DB_NAME", os.getenv("DB_NAME")), # Usar DB_NAME como fallback
    "uid": os.getenv("SQL_SERVER_UID", os.getenv("DB_USER")), # Usar DB_USER como fallback
    "pwd": os.getenv("SQL_SERVER_PWD", os.getenv("DB_PASSWORD")), # Usar DB_PASSWORD como fallback
    "timeout_conexion_inicial": int(os.getenv("SQL_TIMEOUT_CONEXION_INICIAL", 30)), # Nueva variable
    # Nuevas configuraciones para reintentos de query:
    "max_reintentos_query": int(os.getenv("SQL_MAX_REINTENTOS_QUERY", 3)),
    "delay_reintento_query_base_seg": int(os.getenv("SQL_DELAY_REINTENTO_QUERY_BASE_SEG", 2)),
    "codigos_sqlstate_reintentables": os.getenv("SQL_CODIGOS_SQLSTATE_REINTENTABLES", "40001,HYT00,HYT01,08S01").split(',')
}

# Configuración de Automation Anywhere
AA_CONFIG = {
    "url": os.getenv("AA_URL"),
    "user": os.getenv("AA_USER"),
    "pwd": os.getenv("AA_PWD"),
    "apiKey": os.getenv("AA_API_KEY"),
    "url_callback": os.getenv("AA_URL_CALLBACK"),
}

# Configuración de correo
EMAIL_CONFIG = {
    "smtp_server": os.getenv("EMAIL_SMTP_SERVER"),
    "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", 587)), # Default a 587
    "from_email": os.getenv("EMAIL_FROM"), # O un "from_email" dedicado
    "from_email": os.getenv("EMAIL_FROM"), # O un "from_email" dedicado
    "recipients": [os.getenv("EMAIL_RECIPIENTS", "admin@example.com")],
    "use_tls": [os.getenv("EMAIL_USE_TLS", False)],
}

# Configuración del lanzador
LANZADOR_CONFIG = {
    "vueltas": int(os.getenv("BOT_INPUT_VUELTAS", 5)),
    "api_timeout_seconds": int(os.getenv("AA_API_TIMEOUT_SECONDS", 60)),
    "token_ttl_refresh_buffer_sec": int(os.getenv("AA_TOKEN_REFRESH_BUFFER_SEC", 1140)),
    "api_default_page_size": int(os.getenv("API_DEFAULT_PAGE_SIZE", 100)),
    "api_max_pagination_pages": int(os.getenv("API_MAX_PAGINATION_PAGES", 1000)),
    "intervalo_lanzador_seg": int(os.getenv("INTERVALO_LANZADOR_SEG", 30)),
    "intervalo_conciliador_seg": int(os.getenv("INTERVALO_CONCILIADOR_SEG", 180)),
    "intervalo_sync_tablas_seg": int(os.getenv("INTERVALO_SYNC_TABLAS_SEG", 3600)),
    "max_lanzamientos_concurrentes": int(os.getenv("MAX_LANZAMIENTOS_CONCURRENTES", 5)),
    "reintento_lanzamiento_delay_seg": int(os.getenv("REINTENTO_LANZAMIENTO_DELAY_SEG", 10)),
    # Nuevas configuraciones para la pausa programada:
    "pausa_lanzamiento_inicio_hhmm": os.getenv("PAUSA_LANZAMIENTO_INICIO_HHMM", "23:00"), # Formato HH:MM
    "pausa_lanzamiento_fin_hhmm": os.getenv("PAUSA_LANZAMIENTO_FIN_HHMM", "05:00"),   # Formato HH:MM
}


# NUEVA: Configuración del Servidor de Callbacks
CALLBACK_SERVER_CONFIG = {
    "host": os.getenv("CALLBACK_SERVER_HOST", "0.0.0.0"),
    "port": int(os.getenv("CALLBACK_SERVER_PORT", 8008)),
    "threads": int(os.getenv("CALLBACK_SERVER_THREADS", 8)),
    # La URL completa que A360 usará para enviar el callback.
    # Debe ser construida aquí o directamente en AA_CONFIG.
    # Por ejemplo, si el endpoint en el callback server es /botstatus:
    "public_url": os.getenv("AA_URL_CALLBACK", f"http://{os.getenv('CALLBACK_SERVER_HOST', 'localhost')}:{os.getenv('CALLBACK_SERVER_PORT', 8008)}/botstatus")
}

LOG_CONFIG = {
    "directory": os.getenv("LOG_DIRECTORY", "C:/RPA/Logs"), # Directorio base de logs
    "app_log_filename": os.getenv("APP_LOG_FILENAME", "sam_lanzador_app.log"), # Para el lanzador principal
    "callback_log_filename": os.getenv("CALLBACK_LOG_FILENAME", "sam_callback_server.log"), # Nuevo
    "when": "midnight",
    # ... (otras configs de log como level, format, etc.)
}

class ConfigManager:
    """Clase para gestionar la configuración centralizada de la aplicación"""

    @staticmethod
    def get_project_name():
        """Obtiene el nombre del proyecto para el archivo de log"""
        try:
            # Intenta obtener el nombre de la carpeta del proyecto
            return os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        except:
            # En caso de error, usa un nombre predeterminado
            return "servicio_lanzador"

    @staticmethod
    def get_sql_server_config():
        return SQL_SERVER_CONFIG

    @staticmethod
    def get_aa_config():
        return AA_CONFIG

    @staticmethod
    def get_email_config():
        return EMAIL_CONFIG

    @staticmethod
    def get_lanzador_config():
        return LANZADOR_CONFIG

    @staticmethod
    def get_callback_server_config():
        return CALLBACK_SERVER_CONFIG
    
    @staticmethod
    def get_log_config():
        return LOG_CONFIG

    @staticmethod
    def get_log_config():
        return {
            "filename": os.path.join("logs", f"{ConfigManager.get_project_name()}.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 7,
            "encoding": "utf-8",
            "level": logging.INFO,
            "format": "%(asctime)s %(levelname)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }


def setup_logging(level=None, file_path=None):
    """
    Configura y devuelve el logger con la configuración especificada.

    Args:
        level: Nivel de logging (opcional)
        file_path: Ruta al archivo de log (opcional)

    Returns:
        Logger configurado
    """
    log_config = ConfigManager.get_log_config()

    # Sobrescribir configuración si se proporcionan parámetros
    if level:
        log_config["level"] = level
    if file_path:
        log_config["filename"] = file_path

    logger = logging.getLogger()

    # Solo configurar si no hay handlers (evita configuración duplicada)
    if not logger.handlers:
        logger.setLevel(log_config["level"])

        # Asegurar que el directorio de logs existe
        os.makedirs(os.path.dirname(log_config["filename"]), exist_ok=True)

        # Crear handler
        log_handler = TimedRotatingFileHandler(
            filename=log_config["filename"],
            when=log_config["when"],
            interval=log_config["interval"],
            backupCount=log_config["backupCount"],
            encoding=log_config["encoding"],
        )

        # Configurar formato
        log_handler.setFormatter(
            logging.Formatter(
                fmt=log_config["format"],
                datefmt=log_config["datefmt"],
            )
        )

        # Agregar handler al logger
        logger.addHandler(log_handler)

        # Agregar handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter(
                fmt=log_config["format"],
                datefmt=log_config["datefmt"],
            )
        )
        logger.addHandler(console_handler)

    return logger
