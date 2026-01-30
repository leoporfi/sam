# SAM/src/common/config_manager.py
import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# Esta función auxiliar no pertenece a la clase y se mantiene separada.
def get_ip_local():
    """Obtiene la dirección IP local de la máquina."""
    import socket

    try:
        return socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        return "127.0.0.1"


class ConfigManager:
    """
    Gestor de Configuración Centralizado para el Proyecto SAM.

    Soporta lectura híbrida:
    1. Base de Datos (ConfiguracionSistema) - Prioridad Alta (si está disponible)
    2. Variables de Entorno (.env) - Fallback
    3. Valor por defecto

    Convención de nombres: {SERVICIO}_{TEMA}_{ACCION}[_{UNIDAD}]
    Usa _get_with_fallback() para mantener compatibilidad con nombres antiguos.
    """

    _db_connector = None
    _config_cache: Dict[str, Any] = {}
    _cache_ttl = 60  # Segundos
    _last_cache_update = 0

    @classmethod
    def set_db_connector(cls, db_connector):
        """Inyecta el conector de BD para permitir lectura de configuración dinámica."""
        cls._db_connector = db_connector

    @classmethod
    def _get_config_value(cls, key: str, default: Any = None, warning_msg: str = None) -> Any:
        """
        Obtiene un valor de configuración con la siguiente precedencia:
        1. Caché local (si es válido)
        2. Base de Datos (si hay conector)
        3. Variable de Entorno
        4. Default
        """
        # 1. Intentar leer de BD (con caché)
        if cls._db_connector:
            current_time = time.time()
            # Si el caché expiró o no tiene la clave, intentamos refrescar
            if current_time - cls._last_cache_update > cls._cache_ttl or key not in cls._config_cache:
                try:
                    # Leemos TODO la config de una vez para optimizar
                    # Nota: Esto asume que db_connector tiene un método para ejecutar querys.
                    # Usamos una query directa para evitar dependencia circular con métodos complejos de DB
                    # Pero debemos usar el método público ejecutar_consulta
                    rows = cls._db_connector.ejecutar_consulta(
                        "SELECT Clave, Valor FROM dbo.ConfiguracionSistema", es_select=True
                    )
                    if rows:
                        for row in rows:
                            cls._config_cache[row["Clave"]] = row["Valor"]
                        cls._last_cache_update = current_time
                except Exception as e:
                    # Si falla la BD, logueamos (una sola vez por ciclo idealmente) y seguimos con env
                    # Para no spammear logs, solo logueamos si es debug o si es un error nuevo
                    logger.debug(f"No se pudo leer configuración de BD: {e}")

            # Si está en caché (ya sea por lectura reciente o anterior), lo usamos
            if key in cls._config_cache:
                val = cls._config_cache[key]
                # Si el valor es "True"/"False" (string), convertir a booleans si el default es bool?
                # No, mejor dejar que el caller haga el cast, pero ConfigManager suele devolver strings o ints casteados.
                return val

        # 2. Fallback a Variable de Entorno
        return cls._get_env_with_warning(key, default, warning_msg)

    @classmethod
    def _get_with_fallback(cls, new_key: str, old_key: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración con fallback para compatibilidad hacia atrás.
        1. Intenta con la nueva clave (new_key)
        2. Si no existe, intenta con la clave antigua (old_key)
        3. Si no existe, usa el valor por defecto.
        """
        val = cls._get_config_value(new_key)
        if val is None:
            val = cls._get_config_value(old_key, default)
        return val

    @classmethod
    def _get_env_with_warning(cls, key: str, default: Any = None, warning_msg: str = None) -> Any:
        """
        Método de ayuda interno para obtener una variable de entorno.
        Advierte si la variable no está definida y se esperaba que lo estuviera.
        """
        value = os.getenv(key, default)
        if value is None or (isinstance(value, str) and not value.strip()):
            if warning_msg:
                logger.warning(f"ADVERTENCIA ConfigManager: {warning_msg}", file=sys.stderr)
            # Devuelve el valor por defecto si el valor encontrado es una cadena vacía
            return default
        return value

    # --- CONFIGURACIONES GENERALES ---

    @classmethod
    def get_log_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración de logging de forma unificada."""
        return {
            "directory": cls._get_with_fallback("LOG_DIRECTORIO", "LOG_DIRECTORY", "C:/RPA/Logs/SAM"),
            "level_str": cls._get_with_fallback("LOG_NIVEL", "LOG_LEVEL", "INFO"),
            "format": cls._get_with_fallback(
                "LOG_FORMATO",
                "LOG_FORMAT",
                "%(asctime)s - PID:%(process)d - %(levelname)s - %(name)s - %(funcName)s - %(message)s",
            ),
            "datefmt": cls._get_with_fallback("LOG_FECHA_FORMATO", "LOG_DATEFMT", "%Y-%m-%d %H:%M:%S"),
            "backupCount": int(cls._get_with_fallback("LOG_BACKUP_CANTIDAD", "LOG_BACKUP_COUNT", 7)),
            # Nombres de archivo específicos para cada servicio
            "app_log_filename_lanzador": cls._get_with_fallback(
                "LOG_ARCHIVO_LANZADOR", "APP_LOG_FILENAME_LANZADOR", "sam_lanzador_app.log"
            ),
            "app_log_filename_balanceador": cls._get_with_fallback(
                "LOG_ARCHIVO_BALANCEADOR", "APP_LOG_FILENAME_BALANCEADOR", "sam_balanceador_app.log"
            ),
            "app_log_filename_callback": cls._get_with_fallback(
                "LOG_ARCHIVO_CALLBACK", "APP_LOG_FILENAME_CALLBACK", "sam_callback_server.log"
            ),
            "app_log_filename_interfaz_web": cls._get_with_fallback(
                "LOG_ARCHIVO_INTERFAZ_WEB", "APP_LOG_FILENAME_INTERFAZ_WEB", "sam_interfaz_web.log"
            ),
            # Parámetros fijos de rotación
            "when": "midnight",
            "interval": 1,
            "encoding": "utf-8",
        }

    @classmethod
    def get_email_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración de email para alertas."""
        # Filtrar cadenas vacías de la lista de destinatarios
        # Soportar tanto comas como punto y coma como delimitadores

        # USA _get_with_fallback para permitir DB y compatibilidad
        recipients_raw = cls._get_with_fallback("EMAIL_DESTINATARIOS", "EMAIL_RECIPIENTS", "")

        # Reemplazar punto y coma por coma para normalizar
        recipients_normalized = recipients_raw.replace(";", ",")
        recipients = [email.strip() for email in recipients_normalized.split(",") if email.strip()]

        return {
            "smtp_server": cls._get_with_fallback("EMAIL_SMTP_HOST", "EMAIL_SMTP_SERVER", None),
            "smtp_port": int(cls._get_with_fallback("EMAIL_SMTP_PUERTO", "EMAIL_SMTP_PORT", 587)),
            "from_email": cls._get_with_fallback("EMAIL_REMITENTE", "EMAIL_FROM", None),
            "recipients": recipients,
            "use_tls": str(cls._get_with_fallback("EMAIL_TLS_HABILITAR", "EMAIL_USE_TLS", "True")).lower() == "true",
            "smtp_user": cls._get_with_fallback("EMAIL_USUARIO", "EMAIL_USER", None),
            "smtp_password": cls._get_with_fallback("EMAIL_PASSWORD", "EMAIL_PASSWORD", None),
        }

    @classmethod
    def get_sql_server_config(cls, prefix: str) -> Dict[str, Any]:
        """Obtiene la configuración para una conexión a SQL Server usando un prefijo (ej: 'SQL_SAM')."""
        return {
            "servidor": cls._get_env_with_warning(f"{prefix}_HOST"),
            "base_datos": cls._get_with_fallback(f"{prefix}_BD_NOMBRE", f"{prefix}_DB_NAME", None),
            "usuario": cls._get_with_fallback(f"{prefix}_USUARIO", f"{prefix}_UID", None),
            "contrasena": cls._get_with_fallback(f"{prefix}_PASSWORD", f"{prefix}_PWD", None),
            "driver": cls._get_env_with_warning(f"{prefix}_DRIVER", "{ODBC Driver 17 for SQL Server}"),
            "timeout": int(
                cls._get_with_fallback(f"{prefix}_CONEXION_TIMEOUT_SEG", f"{prefix}_TIMEOUT_CONEXION_INICIAL", 60)
            ),
            "max_retries": int(
                cls._get_with_fallback(f"{prefix}_QUERY_REINTENTOS_MAX", f"{prefix}_MAX_REINTENTOS_QUERY", 3)
            ),
            "initial_delay": float(
                cls._get_with_fallback(
                    f"{prefix}_QUERY_REINTENTO_DELAY_SEG", f"{prefix}_DELAY_REINTENTO_QUERY_BASE_SEG", 2
                )
            ),
            "retryable_sqlstates": cls._get_with_fallback(
                f"{prefix}_QUERY_SQLSTATE_REINTENTABLES",
                f"{prefix}_CODIGOS_SQLSTATE_REINTENTABLES",
                "40001,HYT00,HYT01,08S01",
            ).split(","),
            "pool_size": int(cls._get_with_fallback(f"{prefix}_POOL_TAMANO", f"{prefix}_POOL_SIZE", 5)),
        }

    # --- CONFIGURACIONES ESPECÍFICAS POR SERVICIO ---

    @classmethod
    def get_lanzador_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración específica para el servicio Lanzador."""
        # Pausas
        pausa_inicio = cls._get_config_value("LANZADOR_PAUSA_INICIO_HHMM", "22:00")
        pausa_fin = cls._get_config_value("LANZADOR_PAUSA_FIN_HHMM", "06:00")

        # Parámetros de robot (JSON)
        default_params_str = cls._get_with_fallback(
            "LANZADOR_ROBOT_PARAMETROS_JSON", "LANZADOR_PARAMETROS_PREDETERMINADOS_JSON", "{}"
        )
        # Fallback adicional para nombre muy viejo
        if default_params_str == "{}":
            default_params_str = cls._get_config_value("LANZADOR_PARAMETROS_DEFAULT_JSON", "{}")

        default_params = {}
        try:
            default_params = json.loads(default_params_str)
            if not isinstance(default_params, dict):
                logger.error("LANZADOR_ROBOT_PARAMETROS_JSON no es un objeto JSON válido. Se usarán parámetros vacíos.")
                default_params = {}
        except json.JSONDecodeError:
            logger.error(
                "Error al decodificar LANZADOR_ROBOT_PARAMETROS_JSON. Se usarán parámetros vacíos.",
                exc_info=True,
            )
            default_params = {}

        return {
            # Ciclo principal
            "intervalo_lanzamiento": int(
                cls._get_with_fallback("LANZADOR_CICLO_INTERVALO_SEG", "LANZADOR_INTERVALO_LANZAMIENTO_SEG", 15)
            ),
            "max_workers_lanzador": int(cls._get_with_fallback("LANZADOR_WORKERS_MAX", "LANZADOR_MAX_WORKERS", 10)),
            "shutdown_timeout_seg": int(cls._get_env_with_warning("LANZADOR_SHUTDOWN_TIMEOUT_SEG", 60)),
            # Sincronización
            "habilitar_sync": str(
                cls._get_with_fallback("LANZADOR_SYNC_HABILITAR", "LANZADOR_HABILITAR_SINCRONIZACION", "True")
            ).lower()
            == "true",
            "intervalo_sincronizacion": int(
                cls._get_with_fallback("LANZADOR_SYNC_INTERVALO_SEG", "LANZADOR_INTERVALO_SINCRONIZACION_SEG", 3600)
            ),
            # Conciliación
            "intervalo_conciliacion": int(
                cls._get_with_fallback(
                    "LANZADOR_CONCILIACION_INTERVALO_SEG", "LANZADOR_INTERVALO_CONCILIACION_SEG", 900
                )
            ),
            "conciliador_batch_size": int(
                cls._get_with_fallback("LANZADOR_CONCILIACION_LOTE_TAMANO", "LANZADOR_CONCILIADOR_TAMANO_LOTE", 25)
            ),
            "dias_tolerancia_unknown": int(
                cls._get_with_fallback(
                    "LANZADOR_CONCILIACION_UNKNOWN_TOLERANCIA_DIAS",
                    "LANZADOR_CONCILIADOR_DIAS_TOLERANCIA_ESTADO_UNKNOWN",
                    30,
                )
            ),
            "conciliador_mensaje_inferido": cls._get_with_fallback(
                "LANZADOR_CONCILIACION_INFERENCIA_MENSAJE",
                "LANZADOR_CONCILIADOR_MENSAJE_INFERIDO",
                "Finalizado (Inferido por ausencia en lista de activos)",
            ),
            "conciliador_max_intentos_inferencia": int(
                cls._get_with_fallback(
                    "LANZADOR_CONCILIACION_INFERENCIA_MAX_INTENTOS",
                    "LANZADOR_CONCILIADOR_MAX_INTENTOS_INFERENCIA",
                    5,
                )
            ),
            # Deploy
            "max_reintentos_deploy": int(
                cls._get_with_fallback("LANZADOR_DEPLOY_REINTENTOS_MAX", "LANZADOR_MAX_REINTENTOS_DEPLOY", 2)
            ),
            "delay_reintentos_deploy_seg": int(
                cls._get_with_fallback("LANZADOR_DEPLOY_REINTENTO_DELAY_SEG", "LANZADOR_DELAY_REINTENTO_DEPLOY_SEG", 5)
            ),
            # Robot
            "repeticiones": int(
                cls._get_with_fallback("LANZADOR_ROBOT_REPETICIONES", "LANZADOR_REPETICIONES_ROBOT", 3)
            ),
            "parametros_default": default_params,
            # Pausa
            "pausa_lanzamiento": (pausa_inicio, pausa_fin),
            # Alertas
            "umbral_alertas_412": int(
                cls._get_with_fallback("LANZADOR_ALERTAS_ERROR_412_UMBRAL", "LANZADOR_UMBRAL_ALERTAS_ERROR_412", 20)
            ),
            "links": cls.get_external_links(),
        }

    @classmethod
    def get_balanceador_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración específica para el servicio Balanceador."""
        # Soporte para múltiples nombres antiguos de enfriamiento
        cooling_period = cls._get_config_value("BALANCEADOR_POOL_ENFRIAMIENTO_SEG")
        if cooling_period is None:
            cooling_period = cls._get_config_value("BALANCEADOR_PERIODO_ENFRIAMIENTO_SEG")
        if cooling_period is None:
            cooling_period = cls._get_config_value("BALANCEADOR_COOLING_PERIOD_SEG")
        if cooling_period is None:
            cooling_period = cls._get_config_value("BALANCEADOR_POOL_COOLDOWN_SEG", 300)

        return {
            # Ciclo
            "intervalo_ciclo_seg": int(
                cls._get_with_fallback("BALANCEADOR_CICLO_INTERVALO_SEG", "BALANCEADOR_INTERVALO_CICLO_SEG", 120)
            ),
            # Pool
            "cooling_period_seg": int(cooling_period),
            "aislamiento_estricto_pool": str(
                cls._get_config_value("BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO", "True")
            ).lower()
            == "true",
            "preemption_habilitado": str(
                cls._get_with_fallback("BALANCEADOR_PREEMPTION_HABILITAR", "BALANCEO_PREEMPTION_MODE", "False")
            ).lower()
            == "true",
            # Carga
            "proveedores_carga": [
                p.strip()
                for p in str(
                    cls._get_with_fallback(
                        "BALANCEADOR_CARGA_PROVEEDORES", "BALANCEADOR_PROVEEDORES_CARGA", "clouders,rpa360"
                    )
                ).split(",")
            ],
            "tickets_por_equipo_default": int(
                cls._get_with_fallback(
                    "BALANCEADOR_TICKETS_DEFAULT_POR_EQUIPO",
                    "BALANCEADOR_TICKETS_PREDETERMINADOS_POR_EQUIPO",
                    15,
                )
            ),
        }

    @classmethod
    def get_callback_server_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración para el servidor de Callbacks."""
        return {
            "host": cls._get_with_fallback("CALLBACK_HOST", "CALLBACK_SERVER_HOST", "0.0.0.0"),
            "port": int(cls._get_with_fallback("CALLBACK_PUERTO", "CALLBACK_SERVER_PORT", 8008)),
            "threads": int(cls._get_with_fallback("CALLBACK_THREADS", "CALLBACK_SERVER_THREADS", 8)),
            "token": cls._get_env_with_warning("CALLBACK_TOKEN"),
            "auth_mode": cls._get_with_fallback("CALLBACK_AUTH_MODO", "CALLBACK_AUTH_MODE", "strict").lower(),
            "public_host": cls._get_with_fallback(
                "CALLBACK_HOST_PUBLICO",
                "CALLBACK_SERVER_PUBLIC_HOST",
                os.getenv("CALLBACK_HOST", os.getenv("CALLBACK_SERVER_HOST", "localhost")),
            ),
            "endpoint_path": cls._get_with_fallback(
                "CALLBACK_ENDPOINT", "CALLBACK_ENDPOINT_PATH", "/api/callback"
            ).strip("/"),
        }

    @classmethod
    def get_interfaz_web_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración para la Interfaz Web."""
        return {
            "host": cls._get_env_with_warning("INTERFAZ_WEB_HOST", "0.0.0.0"),
            "port": int(cls._get_with_fallback("INTERFAZ_WEB_PUERTO", "INTERFAZ_WEB_PORT", 8000)),
            "debug": cls._get_env_with_warning("INTERFAZ_WEB_DEBUG", "False").lower() == "true",
            "session_timeout_min": int(
                cls._get_with_fallback("INTERFAZ_WEB_SESION_TIMEOUT_MIN", "INTERFAZ_WEB_SESSION_TIMEOUT_MIN", 30)
            ),
            "max_upload_size_mb": int(
                cls._get_with_fallback("INTERFAZ_WEB_UPLOAD_MAX_MB", "INTERFAZ_WEB_MAX_UPLOAD_SIZE_MB", 16)
            ),
            # Umbrales de ejecución
            "umbral_ejecucion_demorada_min": int(
                cls._get_with_fallback(
                    "INTERFAZ_WEB_EJECUCION_DEMORA_UMBRAL_MIN",
                    "INTERFAZ_WEB_UMBRAL_EJECUCION_DEMORADA_MINUTOS",
                    25,
                )
            ),
            "factor_umbral_dinamico": float(
                cls._get_with_fallback(
                    "INTERFAZ_WEB_EJECUCION_UMBRAL_FACTOR", "INTERFAZ_WEB_FACTOR_UMBRAL_DINAMICO", 1.5
                )
            ),
            "piso_umbral_dinamico_min": int(
                cls._get_with_fallback(
                    "INTERFAZ_WEB_EJECUCION_UMBRAL_PISO_MIN", "INTERFAZ_WEB_PISO_UMBRAL_DINAMICO_MINUTOS", 10
                )
            ),
            "filtro_ejecuciones_cortas_min": int(
                cls._get_with_fallback(
                    "INTERFAZ_WEB_EJECUCION_FILTRO_CORTAS_MIN",
                    "INTERFAZ_WEB_FILTRO_EJECUCIONES_CORTAS_MINUTOS",
                    2,
                )
            ),
            # Límites de conexión (mitigación errores ReactPy con concurrencia)
            "limite_conexiones": int(cls._get_env_with_warning("INTERFAZ_WEB_LIMITE_CONEXIONES", "50")),
            "timeout_keepalive_seg": int(cls._get_env_with_warning("INTERFAZ_WEB_TIMEOUT_KEEPALIVE_SEG", "10")),
        }

    @classmethod
    def get_aa360_web_config(cls) -> Dict[str, Any]:
        """
        Obtiene la configuración de A360 específica para la Interfaz Web.
        Hereda la URL y configuraciones base de la config general, pero
        sobrescribe las credenciales con las específicas de la web.
        """
        # 1. Obtenemos la config base (URLs, timeouts, SSL)
        base_config = cls.get_aa360_config()

        # 2. Obtenemos las credenciales específicas (con fallback)
        web_user = cls._get_with_fallback("INTERFAZ_WEB_AA_USUARIO", "INTERFAZ_WEB_AA_USER", None)
        web_apikey = cls._get_env_with_warning("INTERFAZ_WEB_AA_APIKEY")

        # 3. Si existen, sobrescribimos. Si no, advertimos y usamos las default (o fallamos)
        if web_user and web_apikey:
            base_config["cr_user"] = web_user
            base_config["cr_api_key"] = web_apikey
        else:
            logger.warning(
                "ADVERTENCIA: No se definieron credenciales AA específicas para la Web (INTERFAZ_WEB_AA_USUARIO). "
                "Se usarán las credenciales globales, lo que puede causar conflictos de sesión."
            )

        return base_config

    # --- CONFIGURACIONES DE CLIENTES EXTERNOS ---
    @classmethod
    def get_mapa_robots(cls) -> Dict[str, str]:
        """
        Obtiene el mapeo de nombres de robots desde la variable de entorno.
        La variable debe contener un string JSON válido.
        """
        mapa_str = cls._get_with_fallback("ROBOTS_MAPA_JSON", "MAPA_ROBOTS", "{}")
        try:
            mapa = json.loads(mapa_str)
            if not isinstance(mapa, dict):
                logger.warning("ROBOTS_MAPA_JSON no es un diccionario JSON válido. Se usará un mapa vacío.")
                return {}
            return mapa
        except json.JSONDecodeError:
            logger.error(
                "Error al decodificar ROBOTS_MAPA_JSON. Asegúrese de que es un JSON válido. Se usará un mapa vacío.",
                exc_info=True,
            )
            return {}

    @classmethod
    def get_clouders_api_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración para la API de Clouders."""
        return {
            "clouders_api_url": cls._get_with_fallback("CLOUDERS_URL", "CLOUDERS_API_URL", None),
            "clouders_auth": cls._get_env_with_warning("CLOUDERS_AUTH"),
            "clouders_api_timeout": int(cls._get_with_fallback("CLOUDERS_TIMEOUT_SEG", "CLOUDERS_API_TIMEOUT", 30)),
            "clouders_verify_ssl": str(
                cls._get_with_fallback("CLOUDERS_SSL_VERIFICAR", "CLOUDERS_VERIFY_SSL", "False")
            ).lower()
            == "true",
        }

    @classmethod
    def get_aa360_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración de Automation Anywhere."""
        return {
            "cr_url": cls._get_with_fallback("AA_URL", "AA_CR_URL", None),
            "cr_user": cls._get_with_fallback("AA_USUARIO", "AA_CR_USER", None),
            "cr_pwd": cls._get_with_fallback("AA_PASSWORD", "AA_CR_PWD", None),
            "cr_api_key": cls._get_with_fallback("AA_API_KEY", "AA_CR_API_KEY", None),
            "verify_ssl": str(cls._get_with_fallback("AA_SSL_VERIFICAR", "AA_VERIFY_SSL", "false")).lower() == "true",
            "api_timeout_seconds": int(cls._get_with_fallback("AA_API_TIMEOUT_SEG", "AA_API_TIMEOUT_SECONDS", 120)),
            "callback_url_deploy": cls._get_with_fallback("AA_CALLBACK_URL", "AA_URL_CALLBACK", None),
            # Paginación
            "default_page_size": int(
                cls._get_with_fallback("AA_PAGINACION_TAMANO_DEFAULT", "AA_DEFAULT_PAGE_SIZE", 100)
            ),
            "max_pagination_pages": int(
                cls._get_with_fallback("AA_PAGINACION_PAGINAS_MAX", "AA_MAX_PAGINATION_PAGES", 1000)
            ),
            "token_refresh_buffer_sec": int(
                cls._get_with_fallback("AA_TOKEN_REFRESH_BUFFER_SEG", "AA_TOKEN_REFRESH_BUFFER_SEC", 1140)
            ),
        }

    @classmethod
    def get_apigw_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración para el API Gateway."""
        return {
            "url": cls._get_with_fallback("APIGW_URL", "API_GATEWAY_URL", None),
            "client_id": cls._get_with_fallback("APIGW_CLIENT_ID", "API_GATEWAY_CLIENT_ID", None),
            "client_secret": cls._get_with_fallback("APIGW_CLIENT_SECRET", "API_GATEWAY_CLIENT_SECRET", None),
            "grant_type": cls._get_with_fallback("APIGW_GRANT_TYPE", "API_GATEWAY_GRANT_TYPE", "client_credentials"),
            "scope": cls._get_with_fallback("APIGW_SCOPE", "API_GATEWAY_SCOPE", "scope1"),
            "timeout_seconds": int(cls._get_with_fallback("APIGW_TIMEOUT_SEG", "API_GATEWAY_TIMEOUT_SECONDS", 30)),
            "token_expiration_buffer_sec": int(
                cls._get_with_fallback("APIGW_TOKEN_BUFFER_SEG", "API_GATEWAY_TOKEN_EXPIRATION_BUFFER_SEC", 300)
            ),
        }

    @classmethod
    def get_jwt_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración de JWT para autenticación."""
        return {
            "public_key": cls._get_with_fallback("JWT_CLAVE_PUBLICA", "JWT_PUBLIC_KEY", None),
            "private_key": cls._get_with_fallback("JWT_CLAVE_PRIVADA", "JWT_PRIVATE_KEY", None),
            "audience": cls._get_env_with_warning("JWT_AUDIENCE", "sam-callback-service"),
            "issuer": cls._get_env_with_warning("JWT_ISSUER", "sam-auth-server"),
        }

    @classmethod
    def get_auth_server_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración del servidor de autenticación."""
        return {
            "host": cls._get_with_fallback("AUTH_HOST", "AUTH_SERVER_HOST", "0.0.0.0"),
            "port": int(cls._get_with_fallback("AUTH_PUERTO", "AUTH_SERVER_PORT", 5001)),
            "client_id": cls._get_env_with_warning("APIGW_CLIENT_ID"),
            "client_secret": cls._get_env_with_warning("APIGW_CLIENT_SECRET"),
        }

    @classmethod
    def get_external_links(cls) -> Dict[str, str]:
        """Obtiene enlaces externos a documentación y estados de servicio."""
        return {
            "aa_status_page": cls._get_config_value("AA_STATUS_PAGE_URL", "https://status.automationanywhere.digital/"),
            "aa_docs_run_settings": cls._get_config_value(
                "AA_DOCS_RUN_SETTINGS_URL",
                "https://docs.automationanywhere.com/bundle/enterprise-v2019/page/enterprise-cloud/topics/control-room/bots/my-bots/run-bot-settings.html",
            ),
            "aa_docs_bot_agent_status": cls._get_config_value(
                "AA_DOCS_BOT_AGENT_STATUS_URL",
                "https://docs.automationanywhere.com/bundle/enterprise-v2019/page/enterprise-cloud/topics/bot-agent/install/bot-agent-status.html",
            ),
            "aa_docs_api_key": cls._get_config_value(
                "AA_DOCS_API_KEY_URL",
                "https://docs.automationanywhere.com/bundle/enterprise-v2019/page/enterprise-cloud/topics/control-room/administration/settings/cr-settings-api-key.html",
            ),
        }

    # --- UTILIDADES ---

    @classmethod
    def check_and_display_config(cls, service_name: Optional[str] = None):
        """Muestra la configuración cargada y valida la presencia de variables críticas."""
        logger.info("=" * 60, file=sys.stderr)
        logger.info(" VERIFICACIÓN DE CONFIGURACIÓN ".center(60, "="), file=sys.stderr)
        logger.info(f"Servicio: {service_name or 'No especificado'}", file=sys.stderr)
        logger.info(f"IP Local: {get_ip_local()}", file=sys.stderr)
        logger.info("=" * 60, file=sys.stderr)

        # Mapeo de configuraciones a verificar (usa nuevos nombres con fallback implícito)
        configs_a_verificar = {
            "SQL SAM": (["SQL_SAM_HOST", "SQL_SAM_BD_NOMBRE", "SQL_SAM_USUARIO", "SQL_SAM_PASSWORD"], True),
            "SQL RPA360": (
                ["SQL_RPA360_HOST", "SQL_RPA360_BD_NOMBRE", "SQL_RPA360_USUARIO", "SQL_RPA360_PASSWORD"],
                True,
            ),
            "EMAIL": (["EMAIL_SMTP_HOST", "EMAIL_REMITENTE", "EMAIL_DESTINATARIOS"], False),
            "Clouders API": (["CLOUDERS_URL", "CLOUDERS_AUTH"], False),
            "Callback": (["CALLBACK_TOKEN"], False),
            "API Gateway": (["APIGW_URL", "APIGW_CLIENT_ID", "APIGW_CLIENT_SECRET"], False),
            "Interfaz Web AA": (["INTERFAZ_WEB_AA_USUARIO", "INTERFAZ_WEB_AA_APIKEY"], False),
        }

        for config_name, (keys, is_critical) in configs_a_verificar.items():
            faltantes = [key for key in keys if not os.getenv(key)]
            if faltantes:
                estado = "FALTAN VARIABLES CRÍTICAS" if is_critical else "OK (con opcionales faltantes)"
                logger.warning(f"\n[ {config_name} ]", file=sys.stderr)
                logger.warning(f"  - Estado: {estado}", file=sys.stderr)
                logger.warning(f"  - Faltantes: {', '.join(faltantes)}", file=sys.stderr)

        # Mapeo de métodos de configuración específica del servicio
        config_method_map = {
            "lanzador": cls.get_lanzador_config,
            "balanceador": cls.get_balanceador_config,
            "callback": cls.get_callback_server_config,
            "interfaz_web": cls.get_interfaz_web_config,
        }

        if service_name and service_name in config_method_map:
            logger.info(f"\nConfiguración específica de '{service_name}':", file=sys.stderr)
            try:
                config_method = config_method_map[service_name]
                config = config_method()
                for key, value in config.items():
                    # Ocultar contraseñas y datos sensibles
                    if any(sensitive in key.lower() for sensitive in ["pass", "pwd", "secret", "token", "auth"]):
                        display_value = ("*" * 8) if value else "No configurado"
                    else:
                        display_value = value
                    logger.warning(f"  - {key}: {display_value}", file=sys.stderr)

            except Exception as e:
                logger.warning(f"  Error al obtener configuración específica: {e}", file=sys.stderr)

        logger.info("=" * 60, file=sys.stderr)
        logger.info("=" * 60, file=sys.stderr)
