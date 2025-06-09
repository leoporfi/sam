# SAM/common/utils/config_manager.py
import os
import sys # Para los prints de advertencia si falta config
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
import json

# Cargar variables de entorno desde .env al importar este módulo.
# load_dotenv() buscará .env en el directorio actual o superiores.
# Si tus .env están en las carpetas de cada módulo (Lanzador, Balanceador),
# el script principal de cada módulo (run_lanzador.py, run_balanceador.py)
# debería llamar a load_dotenv() antes de importar cualquier cosa que use ConfigManager,
# o puedes pasar la ruta al .env a ConfigManager.
# Para un enfoque central, podrías tener un .env principal en SAM_PROJECT_ROOT
# con prefijos para las variables de Lanzador y Balanceador.

# Alternativa: Cargar un .env específico si se pasa una ruta.
# def load_specific_env(dotenv_path: Optional[str] = None):
# if dotenv_path and os.path.exists(dotenv_path):
# load_dotenv(dotenv_path=dotenv_path)
# else:
# load_dotenv() # Comportamiento por defecto
# load_specific_env() # Llamar una vez

# Por ahora, asumimos que load_dotenv() sin argumentos es suficiente
# y se llama desde el script principal del módulo (Lanzador o Balanceador)
# o que el .env está en un lugar que python-dotenv encuentra.
# Si los `run_...py` están en `SAM/Lanzador` y `SAM/Balanceador` respectivamente,
# y los `.env` están en esas mismas carpetas, `load_dotenv()` debería funcionar
# si se llama desde esos `run_...py` antes de importar service.main.

class ConfigManager:
    """
    Gestor de Configuración Centralizado para el Proyecto SAM.
    Lee variables de entorno (idealmente cargadas desde un archivo .env).
    """

    # --- LOGGING ---
    @staticmethod
    def get_log_config() -> Dict[str, Any]:
        return {
            "directory": os.getenv("LOG_DIRECTORY", "C:/RPA/Logs/SAM"), # Directorio base común
            "app_log_filename_lanzador": os.getenv("APP_LOG_FILENAME_LANZADOR", "sam_lanzador_app.log"),
            "app_log_filename_balanceador": os.getenv("APP_LOG_FILENAME_BALANCEADOR", "sam_balanceador_app.log"),
            "callback_log_filename": os.getenv("CALLBACK_LOG_FILENAME", "sam_callback_server.log"),
            "level_str": os.getenv("LOG_LEVEL", "INFO").upper(),
            "console_level_str": os.getenv("CONSOLE_LOG_LEVEL", "INFO").upper(),
            "when": "midnight",
            "interval": 1,
            "backupCount": int(os.getenv("LOG_BACKUP_COUNT", 7)),
            "encoding": "utf-8",
            "format": os.getenv("LOG_FORMAT", "%(asctime)s - PID:%(process)d - %(name)s - %(levelname)s - %(funcName)s - %(message)s"),
            "datefmt": os.getenv("LOG_DATEFMT", "%Y-%m-%d %H:%M:%S"),
        }

    # --- SQL SERVER (Genérico, usado por Lanzador para SAM DB, y por Balanceador para SAM y RPA360 DBs) ---
    @staticmethod
    def get_sql_server_config(db_prefix: str) -> Dict[str, Any]:
        """
        Obtiene la configuración para una conexión SQL Server específica.
        db_prefix: Ej. "SQL_SAM", "SQL_RPA360" (usado para leer las variables de entorno)
        """
        config = {
            "driver": os.getenv(f"{db_prefix}_DRIVER", "{ODBC Driver 17 for SQL Server}"),
            "server": os.getenv(f"{db_prefix}_HOST"),
            "database": os.getenv(f"{db_prefix}_DB_NAME"),
            "uid": os.getenv(f"{db_prefix}_UID"),
            "pwd": os.getenv(f"{db_prefix}_PWD"),
            "timeout_conexion_inicial": int(os.getenv(f"{db_prefix}_TIMEOUT_CONEXION_INICIAL", 30)),
            "max_reintentos_query": int(os.getenv(f"{db_prefix}_MAX_REINTENTOS_QUERY", 3)),
            "delay_reintento_query_base_seg": int(os.getenv(f"{db_prefix}_DELAY_REINTENTO_QUERY_BASE_SEG", 2)),
            "codigos_sqlstate_reintentables": os.getenv(f"{db_prefix}_CODIGOS_SQLSTATE_REINTENTABLES", "40001,HYT00,HYT01,08S01").split(','),
        }
        required_keys = ["server", "database", "uid", "pwd"]
        if not all(config.get(k) for k in required_keys):
            print(f"ADVERTENCIA: Configuración SQL crítica faltante para el prefijo {db_prefix} (server, database, uid, pwd).", file=sys.stderr)
        return config
    
    # --- AUTOMATION ANYWHERE API (Usado por Lanzador, opcionalmente por Balanceador) ---
    @staticmethod
    def get_aa_config() -> Dict[str, Any]:
        # La URL de callback se construye dinámicamente si no se provee explícitamente.
        _callback_server_public_host = os.getenv('CALLBACK_SERVER_PUBLIC_HOST', os.getenv('CALLBACK_SERVER_HOST', 'localhost'))
        _callback_server_port = int(os.getenv('CALLBACK_SERVER_PORT', 8008)) # Puerto del callback server
        _callback_endpoint_path = os.getenv('CALLBACK_ENDPOINT_PATH', '/sam_callback').strip('/')
        
        default_constructed_callback_url = f"http://{_callback_server_public_host}:{_callback_server_port}/{_callback_endpoint_path}".rstrip('/')

        config = {
            "url": os.getenv("AA_URL"),
            "user": os.getenv("AA_USER"),
            "pwd": os.getenv("AA_PWD"),
            "apiKey": os.getenv("AA_API_KEY"),
            "url_callback": os.getenv("AA_URL_CALLBACK", default_constructed_callback_url),
        }
        required_keys = ["url", "user", "pwd"] # url_callback es importante pero puede ser auto-construida
        if not all(config.get(k) for k in required_keys):
            print("ADVERTENCIA: Configuración AA crítica faltante (url, user, pwd).", file=sys.stderr)
        if not config.get("url_callback"): # Si después de intentar construirla, sigue vacía
            print("ADVERTENCIA: AA_URL_CALLBACK no está definida ni pudo ser construida desde CALLBACK_SERVER_PUBLIC_HOST/PORT/PATH.", file=sys.stderr)
        return config

    # --- EMAIL (Común para Lanzador y Balanceador, pueden usar el mismo .env o prefijos) ---
    @staticmethod
    def get_email_config(email_prefix: Optional[str] = "EMAIL") -> Dict[str, Any]:
        """
        Obtiene la configuración de Email.
        email_prefix: Ej. "EMAIL" (default), "BALANCEADOR_EMAIL" si hay configs separadas.
        """
        config = {
            "smtp_server": os.getenv(f"{email_prefix}_SMTP_SERVER"),
            "smtp_port": int(os.getenv(f"{email_prefix}_SMTP_PORT", 25)),
            "from_email": os.getenv(f"{email_prefix}_FROM", f"sam_service@{os.getenv('EMAIL_DOMAIN', 'example.com')}"),
            "recipients": [rec.strip() for rec in os.getenv(f"{email_prefix}_RECIPIENTS", f"admin@{os.getenv('EMAIL_DOMAIN', 'example.com')}").split(',') if rec.strip()],
            "use_tls": os.getenv(f"{email_prefix}_USE_TLS", "False").lower() == "true",
            "smtp_user": os.getenv(f"{email_prefix}_USER"),
            "smtp_password": os.getenv(f"{email_prefix}_PASSWORD"),
        }
        required_keys = ["smtp_server", "from_email", "recipients"]
        if not all(config.get(k) for k in required_keys):
            print(f"ADVERTENCIA: Configuración Email crítica faltante para el prefijo {email_prefix}.", file=sys.stderr)
        return config

    # --- LANZADOR (Configuración específica) ---
    @staticmethod
    def get_lanzador_config() -> Dict[str, Any]:
        return {
            "bot_input_vueltas": int(os.getenv("LANZADOR_BOT_INPUT_VUELTAS", 5)), # Prefijado
            "api_timeout_seconds": int(os.getenv("AA_API_TIMEOUT_SECONDS", 60)), # Puede ser común con AA_CONFIG
            "token_ttl_refresh_buffer_sec": int(os.getenv("AA_TOKEN_REFRESH_BUFFER_SEC", 1140)), # Común con AA_CONFIG
            "api_default_page_size": int(os.getenv("API_DEFAULT_PAGE_SIZE", 100)), # Común
            "api_max_pagination_pages": int(os.getenv("API_MAX_PAGINATION_PAGES", 1000)), # Común
            
            "intervalo_lanzador_seg": int(os.getenv("LANZADOR_INTERVALO_LANZADOR_SEG", 30)),
            "intervalo_conciliador_seg": int(os.getenv("LANZADOR_INTERVALO_CONCILIADOR_SEG", 180)),
            "intervalo_sync_tablas_seg": int(os.getenv("LANZADOR_INTERVALO_SYNC_TABLAS_SEG", 3600)),
            
            "max_lanzamientos_concurrentes": int(os.getenv("LANZADOR_MAX_LANZAMIENTOS_CONCURRENTES", 5)),
            "reintento_lanzamiento_delay_seg": int(os.getenv("LANZADOR_REINTENTO_LANZAMIENTO_DELAY_SEG", 10)),
            
            "pausa_lanzamiento_inicio_hhmm": os.getenv("LANZADOR_PAUSA_INICIO_HHMM", "23:00"),
            "pausa_lanzamiento_fin_hhmm": os.getenv("LANZADOR_PAUSA_FIN_HHMM", "05:00"),
        }

    # --- CALLBACK SERVER (Común para el Lanzador, pero parámetros leídos del .env) ---
    @staticmethod
    def get_callback_server_config() -> Dict[str, Any]:
        return {
            "host": os.getenv("CALLBACK_SERVER_HOST", "0.0.0.0"),
            "port": int(os.getenv("CALLBACK_SERVER_PORT", 8008)),
            "threads": int(os.getenv("CALLBACK_SERVER_THREADS", 8)),
            # La URL pública que A360 usará se toma de AA_CONFIG["url_callback"]
        }
        
    # --- BALANCEADOR (Configuración específica) ---
    @staticmethod
    def get_balanceador_config() -> Dict[str, Any]:
        """Obtiene la configuración específica del Balanceador."""
        return {
            "intervalo_ciclo_balanceo_seg": int(os.getenv("BALANCEADOR_INTERVALO_CICLO_SEG", "120")),
            "default_tickets_por_equipo": int(os.getenv("BALANCEADOR_DEFAULT_TICKETS_POR_EQUIPO", "10")),
            "mapa_robots": ConfigManager.get_mapa_robots()
        }

    @staticmethod
    def get_mapa_robots() -> Dict[str, str]:
        """
        Obtiene el mapeo de nombres de robots de Clouders a SAM desde el entorno.
        
        Returns:
            Dict[str, str]: Diccionario con el mapeo de nombres de robots.
        """
        try:
            mapa_robots_str = os.getenv("MAPA_ROBOTS", "{}")
            return json.loads(mapa_robots_str)
        except json.JSONDecodeError as e:
            print(f"ADVERTENCIA: Error al decodificar MAPA_ROBOTS desde la variable de entorno: {e}. Se usará un mapa vacío.\n", file=sys.stderr)
            return {}

    # --- SSH y MySQL para "clouders" (Específico del Balanceador) ---
    @staticmethod
    def get_ssh_mysql_clouders_config() -> Dict[str, Any]:
        config = {
            "host_ssh": os.getenv("CLOUDERS_SSH_HOST"),
            "puerto_ssh": int(os.getenv("CLOUDERS_SSH_PORT", 22)),
            "usuario_ssh": os.getenv("CLOUDERS_SSH_USER"),
            "pass_ssh": os.getenv("CLOUDERS_SSH_PASS"),
            "db_host_mysql": os.getenv("CLOUDERS_MYSQL_DB_HOST", "127.0.0.1"),
            "db_port_mysql": int(os.getenv("CLOUDERS_MYSQL_DB_PORT", 3306)),
            "database_mysql": os.getenv("CLOUDERS_MYSQL_DB_NAME"),
            "usuario_mysql": os.getenv("CLOUDERS_MYSQL_USER"),
            "pass_mysql": os.getenv("CLOUDERS_MYSQL_PASS"),
            "max_reintentos_ssh_connect": int(os.getenv("CLOUDERS_MAX_REINTENTOS_SSH_CONNECT", 3)),
            "delay_reintento_ssh_seg": int(os.getenv("CLOUDERS_DELAY_REINTENTO_SSH_SEG", 5)),
            "max_reintentos_mysql_query": int(os.getenv("CLOUDERS_MAX_REINTENTOS_MYSQL_QUERY", 2)),
            "delay_reintento_mysql_query_seg": int(os.getenv("CLOUDERS_DELAY_REINTENTO_MYSQL_QUERY_SEG", 3)),
        }
        required_keys = ["host_ssh", "usuario_ssh", "pass_ssh", "usuario_mysql", "pass_mysql", "database_mysql"]
        if not all(config.get(k) for k in required_keys):
            print("ADVERTENCIA: Configuración SSH/MySQL Clouders crítica faltante.", file=sys.stderr)
        return config