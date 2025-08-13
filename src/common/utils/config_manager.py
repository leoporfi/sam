# SAM/src/common/utils/config_manager.py
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """
    Gestor de Configuración Centralizado para el Proyecto SAM.

    Funciona junto con ConfigLoader para leer variables de entorno
    cargadas desde archivos .env con jerarquía definida.
    """

    @staticmethod
    def _get_env_with_warning(key: str, default: Any = None, warning_msg: str = None) -> Any:
        """
        Obtiene una variable de entorno con advertencia opcional si no existe.
        """
        value = os.getenv(key, default)
        if value is None or (isinstance(value, str) and not value.strip()):
            if warning_msg:
                print(f"ADVERTENCIA ConfigManager: {warning_msg}", file=sys.stderr)
        return value

    # --- LOGGING ---
    @staticmethod
    def get_log_config() -> Dict[str, Any]:
        """Obtiene la configuración de logging."""
        return {
            "directory": os.getenv("LOG_DIRECTORY", "C:/RPA/Logs/SAM"),
            "app_log_filename_lanzador": os.getenv("APP_LOG_FILENAME_LANZADOR", "sam_lanzador_app.log"),
            "app_log_filename_balanceador": os.getenv("APP_LOG_FILENAME_BALANCEADOR", "sam_balanceador_app.log"),
            "callback_log_filename": os.getenv("CALLBACK_LOG_FILENAME", "sam_callback_server.log"),
            "interfaz_web_log_filename": os.getenv("INTERFAZ_WEB_LOG_FILENAME", "sam_interfaz_web.log"),
            "level_str": os.getenv("LOG_LEVEL", "INFO").upper(),
            "when": "midnight",
            "interval": 1,
            "backupCount": int(os.getenv("LOG_BACKUP_COUNT", 7)),
            "encoding": "utf-8",
            "format": os.getenv("LOG_FORMAT", "%(asctime)s - PID:%(process)d - %(name)s - %(levelname)s - %(funcName)s - %(message)s"),
            "datefmt": os.getenv("LOG_DATEFMT", "%Y-%m-%d %H:%M:%S"),
        }

    # --- SQL SERVER ---
    @staticmethod
    def get_sql_server_config(db_prefix: str) -> Dict[str, Any]:
        """
        Obtiene la configuración para una conexión SQL Server específica.

        Args:
            db_prefix: Prefijo de las variables de entorno (ej: "SQL_SAM", "SQL_RPA360")
        """
        config = {
            "driver": os.getenv(f"{db_prefix}_DRIVER", "{SQL Server}"),
            "server": os.getenv(f"{db_prefix}_HOST") or os.getenv(f"{db_prefix}_SERVER"),
            "database": os.getenv(f"{db_prefix}_DB_NAME"),
            "uid": os.getenv(f"{db_prefix}_UID") or os.getenv(f"{db_prefix}_USER"),
            "pwd": os.getenv(f"{db_prefix}_PWD") or os.getenv(f"{db_prefix}_PASSWORD"),
            "timeout_conexion_inicial": int(os.getenv(f"{db_prefix}_TIMEOUT_CONEXION_INICIAL", 30)),
            "max_reintentos_query": int(os.getenv(f"{db_prefix}_MAX_REINTENTOS_QUERY", 3)),
            "delay_reintento_query_base_seg": int(os.getenv(f"{db_prefix}_DELAY_REINTENTO_QUERY_BASE_SEG", 2)),
            "codigos_sqlstate_reintentables": os.getenv(f"{db_prefix}_CODIGOS_SQLSTATE_REINTENTABLES", "40001,HYT00,HYT01,08S01").split(","),
        }

        # Validación de configuración crítica
        required_keys = ["server", "database", "uid", "pwd"]
        missing_keys = [k for k in required_keys if not config.get(k)]
        if missing_keys:
            print(f"ERROR ConfigManager: Configuración SQL crítica faltante para {db_prefix}: {missing_keys}", file=sys.stderr)

        return config

    # --- AUTOMATION ANYWHERE API ---
    @staticmethod
    def get_aa_config() -> Dict[str, Any]:
        """Obtiene la configuración de Automation Anywhere."""
        # Construcción dinámica de URL de callback
        callback_host = os.getenv("CALLBACK_SERVER_PUBLIC_HOST", os.getenv("CALLBACK_SERVER_HOST", "localhost"))
        callback_port = int(os.getenv("CALLBACK_SERVER_PORT", 8008))
        callback_path = os.getenv("CALLBACK_ENDPOINT_PATH", "/sam_callback").strip("/")

        default_callback_url = f"http://{callback_host}:{callback_port}/{callback_path}".rstrip("/")

        config = {
            "url": ConfigManager._get_env_with_warning("AA_URL", warning_msg="URL de Automation Anywhere no configurada (AA_URL)"),
            "user": ConfigManager._get_env_with_warning("AA_USER", warning_msg="Usuario de Automation Anywhere no configurado (AA_USER)"),
            "pwd": ConfigManager._get_env_with_warning("AA_PWD", warning_msg="Contraseña de Automation Anywhere no configurada (AA_PWD)"),
            "apiKey": os.getenv("AA_API_KEY"),  # Opcional
            "url_callback": os.getenv("AA_URL_CALLBACK", default_callback_url),
            "api_timeout_seconds": int(os.getenv("AA_API_TIMEOUT_SECONDS", 60)),
            "token_ttl_refresh_buffer_sec": int(os.getenv("AA_TOKEN_REFRESH_BUFFER_SEC", 1140)),
            "api_default_page_size": int(os.getenv("API_DEFAULT_PAGE_SIZE", 100)),
            "api_max_pagination_pages": int(os.getenv("API_MAX_PAGINATION_PAGES", 1000)),
        }

        return config

    # --- EMAIL ---
    @staticmethod
    def get_email_config(email_prefix: str = "EMAIL") -> Dict[str, Any]:
        """
        Obtiene la configuración de Email.

        Args:
            email_prefix: Prefijo de las variables de entorno (ej: "EMAIL", "BALANCEADOR_EMAIL")
        """
        default_domain = os.getenv("EMAIL_DOMAIN", "example.com")

        config = {
            "smtp_server": ConfigManager._get_env_with_warning(
                f"{email_prefix}_SMTP_SERVER", warning_msg=f"Servidor SMTP no configurado para {email_prefix}_SMTP_SERVER"
            ),
            "smtp_port": int(os.getenv(f"{email_prefix}_SMTP_PORT", 25)),
            "from_email": os.getenv(f"{email_prefix}_FROM", f"sam_service@{default_domain}"),
            "recipients": [rec.strip() for rec in os.getenv(f"{email_prefix}_RECIPIENTS", f"admin@{default_domain}").split(",") if rec.strip()],
            "use_tls": os.getenv(f"{email_prefix}_USE_TLS", "False").lower() == "true",
            "smtp_user": os.getenv(f"{email_prefix}_USER"),
            "smtp_password": os.getenv(f"{email_prefix}_PASSWORD"),
        }

        return config

    # --- CONFIGURACIONES ESPECÍFICAS DE SERVICIOS ---
    @staticmethod
    def get_lanzador_config() -> Dict[str, Any]:
        """Obtiene la configuración específica del Lanzador."""
        return {
            "repeticiones": int(os.getenv("LANZADOR_BOT_INPUT_VUELTAS", 5)),
            "intervalo_lanzador_seg": int(os.getenv("LANZADOR_INTERVALO_LANZADOR_SEG", 30)),
            "intervalo_conciliador_seg": int(os.getenv("LANZADOR_INTERVALO_CONCILIADOR_SEG", 180)),
            "intervalo_sync_tablas_seg": int(os.getenv("LANZADOR_INTERVALO_SYNC_TABLAS_SEG", 3600)),
            "max_lanzamientos_concurrentes": int(os.getenv("LANZADOR_MAX_LANZAMIENTOS_CONCURRENTES", 5)),
            "reintento_lanzamiento_delay_seg": int(os.getenv("LANZADOR_REINTENTO_LANZAMIENTO_DELAY_SEG", 10)),
            "pausa_lanzamiento_inicio_hhmm": os.getenv("LANZADOR_PAUSA_INICIO_HHMM", "23:00"),
            "pausa_lanzamiento_fin_hhmm": os.getenv("LANZADOR_PAUSA_FIN_HHMM", "05:00"),
            "habilitar_sync": os.getenv("LANZADOR_HABILITAR_SYNC", "True").lower() == "true",
        }

    @staticmethod
    def get_callback_server_config() -> Dict[str, Any]:
        """Obtiene la configuración del servidor de callbacks."""
        return {
            "host": os.getenv("CALLBACK_SERVER_HOST", "0.0.0.0"),
            "port": int(os.getenv("CALLBACK_SERVER_PORT", 8008)),
            "threads": int(os.getenv("CALLBACK_SERVER_THREADS", 8)),
            "callback_token": os.getenv("CALLBACK_TOKEN", ""),
            "public_host": os.getenv("CALLBACK_SERVER_PUBLIC_HOST", os.getenv("CALLBACK_SERVER_HOST", "localhost")),
            "endpoint_path": os.getenv("CALLBACK_ENDPOINT_PATH", "/sam_callback"),
        }

    @classmethod
    def get_balanceador_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración específica del balanceador."""
        return {
            "intervalo_ciclo_balanceo_seg": int(os.getenv("BALANCEADOR_INTERVALO_CICLO_SEG", "120")),
            "default_tickets_por_equipo": int(os.getenv("BALANCEADOR_DEFAULT_TICKETS_POR_EQUIPO", "10")),
            "cooling_period_seg": int(os.getenv("BALANCEADOR_COOLING_PERIOD_SEG", "300")),  # Nuevo parámetro
            "mapa_robots": json.loads(os.getenv("MAPA_ROBOTS", "{}")),
        }

    @staticmethod
    def get_mapa_robots() -> Dict[str, str]:
        """
        Obtiene el mapeo de nombres de robots de Clouders a SAM.

        Returns:
            Dict[str, str]: Diccionario con el mapeo de nombres de robots.
        """
        try:
            mapa_robots_str = os.getenv("MAPA_ROBOTS", "{}")
            mapa = json.loads(mapa_robots_str)
            if not isinstance(mapa, dict):
                raise ValueError("MAPA_ROBOTS debe ser un objeto JSON válido")
            return mapa
        except (json.JSONDecodeError, ValueError) as e:
            print(f"ERROR ConfigManager: Error al decodificar MAPA_ROBOTS: {e}. Se usará un mapa vacío.", file=sys.stderr)
            return {}

    @staticmethod
    def get_ssh_mysql_clouders_config() -> Dict[str, Any]:
        """Obtiene la configuración SSH y MySQL para Clouders."""
        config = {
            "host_ssh": ConfigManager._get_env_with_warning(
                "CLOUDERS_SSH_HOST", warning_msg="Host SSH de Clouders no configurado (CLOUDERS_SSH_HOST)"
            ),
            "puerto_ssh": int(os.getenv("CLOUDERS_SSH_PORT", 22)),
            "usuario_ssh": ConfigManager._get_env_with_warning(
                "CLOUDERS_SSH_USER", warning_msg="Usuario SSH de Clouders no configurado (CLOUDERS_SSH_USER)"
            ),
            "pass_ssh": ConfigManager._get_env_with_warning(
                "CLOUDERS_SSH_PASS", warning_msg="Contraseña SSH de Clouders no configurada (CLOUDERS_SSH_PASS)"
            ),
            "db_host_mysql": os.getenv("CLOUDERS_MYSQL_DB_HOST", "127.0.0.1"),
            "db_port_mysql": int(os.getenv("CLOUDERS_MYSQL_DB_PORT", 3306)),
            "database_mysql": ConfigManager._get_env_with_warning(
                "CLOUDERS_MYSQL_DB_NAME", warning_msg="Base de datos MySQL de Clouders no configurada (CLOUDERS_MYSQL_DB_NAME)"
            ),
            "usuario_mysql": ConfigManager._get_env_with_warning(
                "CLOUDERS_MYSQL_USER", warning_msg="Usuario MySQL de Clouders no configurado (CLOUDERS_MYSQL_USER)"
            ),
            "pass_mysql": ConfigManager._get_env_with_warning(
                "CLOUDERS_MYSQL_PASS", warning_msg="Contraseña MySQL de Clouders no configurada (CLOUDERS_MYSQL_PASS)"
            ),
            "max_reintentos_ssh_connect": int(os.getenv("CLOUDERS_MAX_REINTENTOS_SSH_CONNECT", 3)),
            "delay_reintento_ssh_seg": int(os.getenv("CLOUDERS_DELAY_REINTENTO_SSH_SEG", 5)),
            "max_reintentos_mysql_query": int(os.getenv("CLOUDERS_MAX_REINTENTOS_MYSQL_QUERY", 2)),
            "delay_reintento_mysql_query_seg": int(os.getenv("CLOUDERS_DELAY_REINTENTO_MYSQL_QUERY_SEG", 3)),
        }

        return config

    @classmethod
    def get_clouders_api_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración de la API de Clouders."""
        return {
            "clouders_api_url": os.getenv("CLOUDERS_API_URL"),
            "clouders_auth": os.getenv("CLOUDERS_AUTH"),
            "api_timeout": int(os.getenv("API_TIMEOUT", "30")),
            "verify_ssl": os.getenv("CLOUDERS_VERIFY_SSL", "false").lower() == "true"
        }

    @staticmethod
    def get_interfaz_web_config() -> Dict[str, Any]:
        """Obtiene la configuración específica de la Interfaz Web."""
        return {
            "host": os.getenv("INTERFAZ_WEB_HOST", "127.0.0.1"),
            "port": int(os.getenv("INTERFAZ_WEB_PORT", 8080)),
            "debug": os.getenv("INTERFAZ_WEB_DEBUG", "False").lower() == "true",
            "secret_key": os.getenv("INTERFAZ_WEB_SECRET_KEY", "dev-secret-key-change-in-production"),
            "session_timeout_minutes": int(os.getenv("INTERFAZ_WEB_SESSION_TIMEOUT_MIN", 30)),
            "max_upload_size_mb": int(os.getenv("INTERFAZ_WEB_MAX_UPLOAD_SIZE_MB", 16)),
        }

    # --- MÉTODOS DE UTILIDAD ---
    @staticmethod
    def get_environment_info() -> Dict[str, Any]:
        """Obtiene información del entorno actual."""
        try:
            from .config_loader import ConfigLoader

            project_root = ConfigLoader.get_project_root() if ConfigLoader.is_initialized() else "No inicializado"
            src_root = ConfigLoader.get_src_root() if ConfigLoader.is_initialized() else "No inicializado"
        except Exception:
            project_root = "Error al obtener"
            src_root = "Error al obtener"

        return {
            "project_root": str(project_root),
            "src_root": str(src_root),
            "python_version": sys.version,
            "platform": sys.platform,
            "config_loader_initialized": ConfigLoader.is_initialized() if "ConfigLoader" in locals() else False,
        }

    @staticmethod
    def validate_all_configs() -> Dict[str, Any]:
        """
        Valida todas las configuraciones y retorna un reporte de estado.

        Returns:
            Dict con el estado de validación de cada componente.
        """
        validation_report = {"timestamp": str(Path(__file__).stat().st_mtime), "components": {}}

        # Validar configuraciones críticas
        components_to_validate = [
            ("log", ConfigManager.get_log_config),
            ("sql_sam", lambda: ConfigManager.get_sql_server_config("SQL_SAM")),
            ("aa", ConfigManager.get_aa_config),
            ("email", ConfigManager.get_email_config),
            ("callback_server", ConfigManager.get_callback_server_config),
        ]

        for component_name, config_getter in components_to_validate:
            try:
                config = config_getter()
                # Verificar si hay valores críticos faltantes
                critical_missing = []

                if component_name == "sql_sam":
                    critical_keys = ["server", "database", "uid", "pwd"]
                    critical_missing = [k for k in critical_keys if not config.get(k)]
                elif component_name == "aa":
                    critical_keys = ["url", "user", "pwd"]
                    critical_missing = [k for k in critical_keys if not config.get(k)]
                elif component_name == "email":
                    critical_keys = ["smtp_server", "from_email"]
                    critical_missing = [k for k in critical_keys if not config.get(k)]

                validation_report["components"][component_name] = {
                    "status": "OK" if not critical_missing else "WARNING",
                    "missing_critical": critical_missing,
                    "config_keys_count": len(config),
                }

            except Exception as e:
                validation_report["components"][component_name] = {
                    "status": "ERROR",
                    "error": str(e),
                }

        return validation_report

    @staticmethod
    def print_config_summary(service_name: Optional[str] = None) -> None:
        """
        Imprime un resumen de la configuración actual.

        Args:
            service_name: Nombre del servicio para mostrar configuración específica.
        """
        print("=" * 60, file=sys.stderr)
        print("RESUMEN DE CONFIGURACIÓN SAM", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        # Información del entorno
        env_info = ConfigManager.get_environment_info()
        print(f"Proyecto Root: {env_info['project_root']}", file=sys.stderr)
        print(f"Src Root: {env_info['src_root']}", file=sys.stderr)
        print(f"ConfigLoader inicializado: {env_info['config_loader_initialized']}", file=sys.stderr)

        # Validación general
        validation = ConfigManager.validate_all_configs()
        print("\nValidación de componentes:", file=sys.stderr)
        for comp, status in validation["components"].items():
            status_symbol = "✓" if status["status"] == "OK" else "⚠" if status["status"] == "WARNING" else "✗"
            print(f"  {status_symbol} {comp}: {status['status']}", file=sys.stderr)
            if status.get("missing_critical"):
                print(f"    Faltantes: {', '.join(status['missing_critical'])}", file=sys.stderr)

        # Configuración específica del servicio
        if service_name:
            print(f"\nConfiguración específica de '{service_name}':", file=sys.stderr)
            try:
                if service_name == "lanzador":
                    config = ConfigManager.get_lanzador_config()
                elif service_name == "balanceador":
                    config = ConfigManager.get_balanceador_config()
                elif service_name == "callback":
                    config = ConfigManager.get_callback_server_config()
                elif service_name == "interfaz_web":
                    config = ConfigManager.get_interfaz_web_config()
                else:
                    config = {}

                for key, value in config.items():
                    # Ocultar contraseñas y datos sensibles
                    if any(sensitive in key.lower() for sensitive in ["pass", "pwd", "secret", "token"]):
                        display_value = "*" * len(str(value)) if value else "No configurado"
                    else:
                        display_value = value
                    print(f"  {key}: {display_value}", file=sys.stderr)

            except Exception as e:
                print(f"  Error al obtener configuración: {e}", file=sys.stderr)

        print("=" * 60, file=sys.stderr)
