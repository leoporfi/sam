# SAM/src/callback/service/main.py
"""
Servidor de callbacks optimizado para SAM - Recibe callbacks de Automation Anywhere A360.

Este script implementa un servidor WSGI que escucha callbacks de A360 y actualiza la base de datos SAM.
Incluye manejo robusto de errores, validación de payloads y logging detallado.
"""

import hmac
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from wsgiref.simple_server import make_server

try:
    from waitress import serve

    WAITRESS_AVAILABLE = True
except ImportError:
    WAITRESS_AVAILABLE = False


# --- Configuración de constantes ---
@dataclass
class CallbackServerConfiguration:
    """Clase de datos para la configuración del servidor de callbacks."""

    host: str = "0.0.0.0"
    port: int = 8008
    threads: int = 8  # hilos
    channel_timeout: int = 120  # timeout (para waitress channel_timeout)
    cleanup_interval: int = 30  # cleanup_interval (para waitress)
    max_content_length: int = 1024 * 1024  # Límite de 1MB
    log_payload_max_chars: int = 1000


@dataclass
class LogConfiguration:
    """Clase de datos para la configuración de logging."""

    directory: str = "C:/RPA/Logs/SAM"
    filename: str = "sam_callback_server.log"
    level: str = "INFO"
    backup_count: int = 7
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"


# Imports que ahora funcionan gracias a ConfigLoader
from common.database.sql_client import DatabaseConnector
from common.utils.config_manager import ConfigManager
from common.utils.logging_setup import RobustTimedRotatingFileHandler


# --- Clases de Constantes para Respuestas ---
@dataclass(frozen=True)
class HTTPStatus:
    """Contiene constantes para los códigos de estado HTTP."""

    OK: str = "200 OK"
    BAD_REQUEST: str = "400 Bad Request"
    UNAUTHORIZED: str = "401 Unauthorized"
    METHOD_NOT_ALLOWED: str = "405 Method Not Allowed"
    PAYLOAD_TOO_LARGE: str = "413 Payload Too Large"
    INTERNAL_SERVER_ERROR: str = "500 Internal Server Error"


@dataclass(frozen=True)
class ResponseCodes:
    """Contiene constantes para los códigos de estado en el cuerpo JSON de la respuesta."""

    OK: str = "OK"
    ERROR: str = "ERROR"
    AUTH_ERROR: str = "ERROR_AUTORIZACION"
    PROCESSING_ERROR: str = "ERROR_PROCESAMIENTO"
    SERVER_ERROR: str = "ERROR_SERVIDOR"


# Instanciar las constantes para fácil acceso
HTTP = HTTPStatus()
CODES = ResponseCodes()


class RequestValidationError(Exception):
    """Excepción para encapsular errores de validación de la solicitud HTTP."""

    def __init__(self, status: str, internal_code: str, message: str):
        self.status = status
        self.internal_code = internal_code
        self.message = message
        super().__init__(f"{status} - {message}")


class StopProcessingRequest(Exception):
    """Excepción personalizada para detener el procesamiento de una solicitud y enviar una respuesta inmediata."""

    pass


# --- Clase principal del servidor ---
class CallbackServer:
    """Clase principal del servidor de callbacks con gestión de recursos mejorada."""

    def __init__(self):
        self.config = CallbackServerConfiguration()
        self.log_config = LogConfiguration()
        self.logger = self._setup_logging()
        self.db_connector: Optional[DatabaseConnector] = None
        self.server_instance = None
        self._shutdown_event = threading.Event()
        self._stats = {
            "requests_received": 0,
            "requests_processed": 0,
            "requests_failed": 0,
            "start_time": time.time(),
        }
        self.auth_token: Optional[str] = None

        # Cargar configuración
        self._load_configuration()
        # Inicializar conexión a base de datos (no crítico para el inicio del servidor)
        db_initialized = self._initialize_db_connector_object()
        if not db_initialized:
            self.logger.warning("Base de datos no inicializada al arrancar - se intentará conexión en la primera solicitud")

        # Configurar manejadores de señales
        self._setup_signal_handlers()

    def _setup_logging(self) -> logging.Logger:
        """Configura un logging dedicado para el servidor de callbacks."""
        logger_name = "SAMCallbackServer"
        logger = logging.getLogger(logger_name)

        if logger.hasHandlers():  # Si ya tiene manejadores, no añadir más
            return logger

        logger.setLevel(getattr(logging, self.log_config.level.upper(), logging.INFO))
        logger.propagate = False  # No propagar al logger raíz

        # Crear directorio de log si no existe
        log_dir = Path(self.log_config.directory)
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e_os:
            print(f"ERROR CRITICO: No se pudo crear el directorio de logs '{log_dir}': {e_os}", file=sys.stderr)

        log_file_path: Path = log_dir / self.log_config.filename

        formatter = logging.Formatter(
            fmt=self.log_config.format,
            datefmt=self.log_config.date_format,
        )

        try:
            # Manejador de archivo
            file_handler = RobustTimedRotatingFileHandler(
                str(log_file_path),
                when="midnight",
                interval=1,
                backupCount=self.log_config.backup_count,
                encoding="utf-8",
                max_retries=3,
                retry_delay=0.5,
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        except Exception as e:
            # Si falla el manejador de archivo, al menos el de consola (añadido después) debería funcionar.
            print(f"ERROR: No se pudo crear el manejador de archivo para '{log_file_path}': {e}", file=sys.stderr)

        # Manejador de consola (siempre añadir)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

    def _load_configuration(self):
        """Carga la configuración desde ConfigManager con valores por defecto."""
        try:
            # Cargar configuración del servidor de callbacks
            cb_config = ConfigManager.get_callback_server_config()
            self.config.host = cb_config.get("host", self.config.host)
            self.config.port = cb_config.get("port", self.config.port)
            self.config.threads = cb_config.get("threads", self.config.threads)

            # Cargar configuración de log (usando ConfigManager)
            global_log_config = ConfigManager.get_log_config()
            self.log_config.directory = global_log_config.get("directory", self.log_config.directory)
            self.log_config.filename = global_log_config.get("callback_log_filename", self.log_config.filename)
            self.log_config.level = global_log_config.get("level_str", self.log_config.level)
            self.log_config.format = global_log_config.get("format", self.log_config.format)
            self.log_config.date_format = global_log_config.get("datefmt", self.log_config.date_format)
            self.log_config.backup_count = global_log_config.get("backupCount", self.log_config.backup_count)

            # Re-configurar el logger si los valores de log_config cambiaron
            self.logger = self._setup_logging()
            # Cargar el token de autorización desde la configuración de AA
            aa_config = ConfigManager.get_callback_server_config()

            # Cargar el token de autorización desde la configuración de AA
            self.auth_token = aa_config.get("callback_token")  # Asume que la clave en .env es CALLBACK_TOKEN
            print(self.auth_token)
            if not self.auth_token:
                self.logger.warning(
                    "No se ha configurado un token de autorización (CALLBACK_TOKEN). El servidor aceptará solicitudes sin validar el token."
                )
            else:
                self.logger.info("Token de autorización cargado. El servidor validará el encabezado 'X-Authorization'.")
            self.logger.info("Configuración cargada/recargada exitosamente")

        except Exception as e:
            self.logger.error(f"Error cargando configuración, usando valores por defecto: {e}", exc_info=True)

    def _initialize_db_connector_object_old(self) -> bool:  # Renombrado para claridad
        """
        Intenta crear o recrear la instancia de DatabaseConnector.

        Retorna True si el objeto fue creado, False si la creación del objeto falló.
        No garantiza que la conexión esté viva, solo que el objeto existe.
        """
        max_retries = 2
        retry_delay_seconds = 2

        # Si ya existe un conector, intentar cerrarlo antes de crear uno nuevo.
        if self.db_connector and hasattr(self.db_connector, "cerrar_conexion_hilo_actual"):
            try:
                self.db_connector.cerrar_conexion_hilo_actual()
            except Exception as e_close:
                self.logger.debug(f"Error menor al cerrar conector BD previo: {e_close}")
        self.db_connector = None  # Asegurar que empezamos desde None para recrear

        for attempt in range(1, max_retries + 1):
            try:
                sql_config = ConfigManager.get_sql_server_config("SQL_SAM")
                sam_db_name = sql_config.get("database")

                if not sam_db_name:
                    self.logger.error("Config BD: 'database' (SQL_SAM_DB_NAME) no encontrada.")
                    return False  # No se puede crear sin nombre de BD
                if not all(sql_config.get(k) for k in ["server", "uid", "pwd"]):
                    self.logger.error("Config BD incompleta (falta server, uid o pwd para SQL_SAM).")
                    return False

                self.db_connector = DatabaseConnector(  # Crea la nueva instancia
                    servidor=sql_config["server"], base_datos=sam_db_name, usuario=sql_config["uid"], contrasena=sql_config["pwd"]
                )
                self.logger.info(f"Objeto DatabaseConnector (re)creado exitosamente (intento {attempt}).")
                return True  # Objeto creado
            except Exception as e_init_obj:
                self.logger.warning(f"Intento {attempt}/{max_retries} de creación de objeto DatabaseConnector fallido: {e_init_obj}")
                if attempt < max_retries:
                    time.sleep(retry_delay_seconds)
                else:
                    self.logger.error("Falló la creación del objeto DatabaseConnector después de todos los reintentos.")
                    self.db_connector = None
                    return False
        return False  # No debería llegar si el bucle se completa

    @contextmanager
    def _get_db_connection_old(self):
        """
        Gestor de contexto que asegura que self.db_connector exista y tenga una conexión verificada.

        Lanza ConnectionError si no se puede establecer una conexión válida.
        """
        # Paso 1: Asegurar que el objeto self.db_connector exista.
        if not self.db_connector:
            self.logger.info("Objeto conector BD es None. Intentando creación inicial del objeto.")
            if not self._initialize_db_connector_object():
                self.logger.error("Fallo crítico: No se pudo crear el objeto DatabaseConnector.")
                raise ConnectionError("Fallo crítico al crear el objeto DatabaseConnector.")

        # Paso 2: Verificar la conexión del objeto existente. Reintentar si falla.
        # Permitimos un número limitado de reintentos de verificación/recreación aquí.
        max_verification_attempts = 2
        for verification_attempt in range(1, max_verification_attempts + 1):
            try:
                if self.db_connector and self.db_connector.verificar_conexion():
                    self.logger.debug("Conexión BD verificada exitosamente en _get_db_connection.")
                    yield self.db_connector  # Conexión buena, ceder el conector.
                    return  # Salir del generador y del bucle.
                else:
                    self.logger.warning(
                        f"Verificación de conexión BD falló para el hilo actual (intento {verification_attempt}). Intentando conectar..."
                    )
                    try:
                        self.db_connector.conectar_base_datos()  # Conectar para el hilo actual usando el objeto existente
                        # Si tiene éxito, el siguiente loop de verificación debería pasar.
                    except Exception as e_conn_thread:
                        self.logger.error(f"Error al intentar conectar para el hilo actual: {e_conn_thread}", exc_info=True)
                        # Si falla la conexión aquí, podría ser necesario recrear el objeto o fallar la solicitud.
            except Exception as e_verification_retry:
                self.logger.error(
                    f"Excepción durante intento {verification_attempt} de conexión/verificación BD: {e_verification_retry}", exc_info=True
                )
                # Si hay una excepción, también es una falla. Intentar recrear el objeto por si acaso.
                if not self._initialize_db_connector_object():
                    error_msg = "Fallo crítico al recrear objeto DB tras excepción en verificación."
                    self.logger.error(error_msg)
                    raise ConnectionError(error_msg) from e_verification_retry

            if verification_attempt < max_verification_attempts:
                self.logger.info("Pausa antes del siguiente intento de verificación/recreación de conexión BD.")
                time.sleep(1 + verification_attempt)  # Pequeña pausa incremental

        # Si el bucle termina, todos los intentos de obtener una conexión verificada fallaron.
        final_failure_msg = "No se pudo obtener una conexión de BD válida después de múltiples intentos y recreaciones."
        self.logger.error(final_failure_msg)
        raise ConnectionError(final_failure_msg) from None

    # === PASO 1: DIAGNÓSTICO DETALLADO ===
    # 1.1 Añadir logging más específico en _initialize_db_connector_object
    def _initialize_db_connector_object(self) -> bool:
        """
        Intenta crear o recrear la instancia de DatabaseConnector.

        VERSIÓN CON DIAGNÓSTICO MEJORADO.
        """
        max_retries = 2
        retry_delay_seconds = 2

        # Si ya existe un conector, intentar cerrarlo antes de crear uno nuevo.
        if self.db_connector and hasattr(self.db_connector, "cerrar_conexion_hilo_actual"):
            try:
                self.db_connector.cerrar_conexion_hilo_actual()
            except Exception as e_close:
                self.logger.debug(f"Error menor al cerrar conector BD previo: {e_close}")
        self.db_connector = None

        for attempt in range(1, max_retries + 1):
            try:
                sql_config = ConfigManager.get_sql_server_config("SQL_SAM")
                sam_db_name = sql_config.get("database")

                # DIAGNÓSTICO DETALLADO DE CONFIGURACIÓN
                self.logger.debug(f"=== DIAGNÓSTICO BD (Intento {attempt}) ===")
                self.logger.debug(f"Server: {sql_config.get('server', 'NO_CONFIG')}")
                self.logger.debug(f"Database: {sam_db_name or 'NO_CONFIG'}")
                self.logger.debug(f"User: {sql_config.get('uid', 'NO_CONFIG')}")
                self.logger.debug(f"Password configured: {'YES' if sql_config.get('pwd') else 'NO'}")

                if not sam_db_name:
                    self.logger.error("Config BD: 'database' (SQL_SAM_DB_NAME) no encontrada.")
                    return False
                if not all(sql_config.get(k) for k in ["server", "uid", "pwd"]):
                    self.logger.error("Config BD incompleta (falta server, uid o pwd para SQL_SAM).")
                    return False

                self.db_connector = DatabaseConnector(
                    servidor=sql_config["server"], base_datos=sam_db_name, usuario=sql_config["uid"], contrasena=sql_config["pwd"]
                )

                # VERIFICACIÓN INMEDIATA TRAS CREACIÓN
                self.logger.debug("Objeto DatabaseConnector creado. Verificando conexión inmediatamente...")
                try:
                    # Intentar establecer la conexión. conectar_base_datos()
                    # guardará la conexión en el hilo local y la devolverá,
                    # o levantará una excepción si falla.
                    connection = self.db_connector.conectar_base_datos()  # <--- AÑADIR ESTA LLAMADA
                    if connection:  # Si conectar_base_datos() es exitoso y devuelve la conexión
                        self.logger.debug(f"Conexión BD establecida y verificada exitosamente tras creación (intento {attempt})")
                        # Opcionalmente, podrías incluso llamar a self.db_connector.verificar_conexion() aquí si quieres la doble verificación,
                        # pero el éxito de conectar_base_datos() ya es una buena señal.
                        return True
                    else:
                        # Este caso es menos probable si conectar_base_datos está bien implementado
                        # (debería levantar excepción en fallo, no devolver None silenciosamente)
                        self.logger.warning(f"Conexión a BD no establecida tras creación (intento {attempt}), conectar_base_datos devolvió None.")

                except pyodbc.Error as e_db_connect:  # type: ignore # Capturar específicamente errores de pyodbc  # noqa: F821
                    self.logger.error(f"Error de PyODBC al intentar conectar inmediatamente: {e_db_connect}", exc_info=True)
                except Exception as e_immediate_connect:  # Capturar otras excepciones
                    self.logger.error(f"Excepción al intentar conectar inmediatamente: {e_immediate_connect}", exc_info=True)

            except Exception as e_init_obj:
                self.logger.warning(f"Intento {attempt}/{max_retries} de creación de objeto DatabaseConnector fallido: {e_init_obj}", exc_info=True)

            if attempt < max_retries:
                self.logger.info(f"Esperando {retry_delay_seconds}s antes del siguiente intento...")
                time.sleep(retry_delay_seconds)
            else:
                self.logger.error("Falló la creación/verificación del objeto DatabaseConnector después de todos los reintentos.")
                self.db_connector = None
                return False
        return False

    # === PASO 2: MEJORAR EL MÉTODO _get_db_connection ===
    @contextmanager
    def _get_db_connection(self):
        """VERSIÓN MEJORADA con más diagnóstico y reintentos inteligentes."""
        # Paso 1: Asegurar que el objeto self.db_connector exista.
        if not self.db_connector:
            self.logger.debug("Objeto conector BD es None. Intentando creación inicial del objeto.")
            if not self._initialize_db_connector_object():
                self.logger.error("CRÍTICO: No se pudo crear el objeto DatabaseConnector.")
                raise ConnectionError("Fallo crítico al crear el objeto DatabaseConnector.")

        # Paso 2: Verificar la conexión con diagnóstico mejorado
        max_verification_attempts = 3  # Aumentado de 2 a 3
        for verification_attempt in range(1, max_verification_attempts + 1):
            try:
                self.logger.debug(f"Verificando conexión BD (intento {verification_attempt}/{max_verification_attempts})")

                # DIAGNÓSTICO: Verificar si el objeto existe y tiene los métodos esperados
                if not self.db_connector:
                    self.logger.error("self.db_connector es None durante verificación")
                    raise ConnectionError("Conector BD es None")

                if not hasattr(self.db_connector, "verificar_conexion"):
                    self.logger.error("El objeto db_connector no tiene método 'verificar_conexion'")
                    raise ConnectionError("Objeto DatabaseConnector inválido")

                # Intentar verificación con timeout si es posible
                connection_ok = self.db_connector.verificar_conexion()

                if connection_ok:
                    self.logger.debug(f"Conexión BD verificada exitosamente (intento {verification_attempt})")
                    yield self.db_connector
                    return
                else:
                    self.logger.warning(f"Verificación de conexión BD falló (intento {verification_attempt}/{max_verification_attempts})")

                    # DIAGNÓSTICO ADICIONAL: Intentar obtener más información del error
                    try:
                        # Si tu DatabaseConnector tiene un método para obtener el último error
                        if hasattr(self.db_connector, "ultimo_error"):
                            self.logger.error(f"Último error de BD: {self.db_connector.ultimo_error}")

                        # Intentar una operación simple para diagnóstico
                        if hasattr(self.db_connector, "obtener_conexion"):
                            conn = self.db_connector.obtener_conexion()
                            if conn:
                                self.logger.debug("obtener_conexion() retornó un objeto de conexión")
                                # Intentar un query simple
                                cursor = conn.cursor()
                                cursor.execute("SELECT 1")
                                result = cursor.fetchone()
                                cursor.close()
                                self.logger.debug(f"Query de prueba exitoso: {result}")
                            else:
                                self.logger.error("obtener_conexion() retornó None")
                    except Exception as e_diagnostic:
                        self.logger.error(f"Error durante diagnóstico adicional: {e_diagnostic}")

                    # Recrear el objeto si no es el último intento
                    if verification_attempt < max_verification_attempts:
                        self.logger.info("Recreando objeto DatabaseConnector...")
                        if not self._initialize_db_connector_object():
                            error_msg = "Fallo crítico al recrear objeto DB tras falla de verificación."
                            self.logger.error(error_msg)
                            raise ConnectionError(error_msg) from None

            except Exception as e_verification_retry:
                self.logger.error(
                    f"Excepción durante intento {verification_attempt} de conexión/verificación BD: {e_verification_retry}", exc_info=True
                )

                # Solo recrear si no es el último intento
                if verification_attempt < max_verification_attempts:
                    self.logger.info("Recreando objeto tras excepción...")
                    if not self._initialize_db_connector_object():
                        error_msg = "Fallo crítico al recrear objeto DB tras excepción."
                        self.logger.error(error_msg)
                        raise ConnectionError(error_msg) from None

            # Pausa incremental entre intentos
            if verification_attempt < max_verification_attempts:
                pause = 2 + verification_attempt  # 3s, 4s, etc.
                self.logger.info(f"Pausa de {pause}s antes del siguiente intento...")
                time.sleep(pause)

        # Si llegamos aquí, todos los intentos fallaron
        final_failure_msg = "CRÍTICO: No se pudo obtener una conexión de BD válida después de múltiples intentos exhaustivos."
        self.logger.error(final_failure_msg)
        raise ConnectionError(final_failure_msg) from None

    # === PASO 3: MÉTODO DE DIAGNÓSTICO INDEPENDIENTE ===
    def diagnose_db_connection(self) -> Dict[str, Any]:
        """Método independiente para diagnosticar problemas de conexión a BD."""
        diagnostic = {
            "config_found": False,
            "config_complete": False,
            "object_created": False,
            "connection_verified": False,
            "errors": [],
            "config_details": {},
        }

        try:
            # 1. Verificar configuración
            sql_config = ConfigManager.get_sql_server_config("SQL_SAM")
            diagnostic["config_found"] = True
            diagnostic["config_details"] = {
                "server": sql_config.get("server", "NO_CONFIG"),
                "database": sql_config.get("database", "NO_CONFIG"),
                "uid": sql_config.get("uid", "NO_CONFIG"),
                "pwd_configured": bool(sql_config.get("pwd")),
            }

            # 2. Verificar completitud de config
            if all(sql_config.get(k) for k in ["server", "database", "uid", "pwd"]):
                diagnostic["config_complete"] = True
            else:
                diagnostic["errors"].append("Configuración BD incompleta")

            # 3. Intentar crear objeto
            if diagnostic["config_complete"]:
                try:
                    test_connector = DatabaseConnector(
                        servidor=sql_config["server"],
                        base_datos=sql_config["database"],
                        usuario=sql_config["uid"],
                        contrasena=sql_config["pwd"],
                    )
                    diagnostic["object_created"] = True

                    # 4. Intentar verificar conexión
                    if test_connector.verificar_conexion():
                        diagnostic["connection_verified"] = True
                    else:
                        diagnostic["errors"].append("Verificación de conexión falló")

                except Exception as e_obj:
                    diagnostic["errors"].append(f"Error creando objeto: {e_obj}")

        except Exception as e_config:
            diagnostic["errors"].append(f"Error obteniendo config: {e_config}")

        return diagnostic

    # === PASO 4: IMPLEMENTAR UN HEALTH CHECK ===
    def db_health_check(self) -> bool:
        """Health check simple para la base de datos."""
        try:
            with self._get_db_connection() as db:
                # Intentar una query muy simple
                if hasattr(db, "ejecutar_query"):
                    result = db.ejecutar_query("SELECT 1 as test")
                    return result is not None
                else:
                    return db.verificar_conexion()
        except Exception as e:
            self.logger.error(f"Health check BD falló: {e}")
            return False

    # === PASO 5: CONFIGURACIÓN DE RECONEXIÓN AUTOMÁTICA ===
    def _setup_auto_reconnection(self):
        """Configura un hilo de reconexión automática en background."""

        def reconnection_task():
            while not self._shutdown_event.is_set():
                try:
                    if not self.db_health_check():
                        self.logger.warning("Health check BD falló, intentando reconectar...")
                        self._initialize_db_connector_object()

                    # Esperar 30 segundos antes del siguiente check
                    self._shutdown_event.wait(30)

                except Exception as e:
                    self.logger.error(f"Error en tarea de reconexión: {e}")
                    self._shutdown_event.wait(60)  # Esperar más tiempo si hay error

        reconnection_thread = threading.Thread(target=reconnection_task, daemon=True)
        reconnection_thread.start()
        self.logger.info("Hilo de reconexión automática iniciado")

    def _validate_callback_payload(self, data: Dict[str, Any]) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """
        Valida el payload del callback. `botOutput` es ahora opcional.
        """
        try:
            deployment_id = data.get("deploymentId")
            status = data.get("status")
            bot_output = data.get("botOutput")  # Se obtiene, pero su ausencia no es un error.

            # Campos obligatorios
            if not deployment_id:
                return False, "Campo requerido faltante o nulo: deploymentId", None, None
            if not status:
                return False, "Campo requerido faltante o nulo: status", None, None

            # Validación de tipos para campos obligatorios
            if not isinstance(deployment_id, str) or not deployment_id.strip():
                return False, "deploymentId debe ser una cadena no vacía", None, None
            if not isinstance(status, str) or not status.strip():
                return False, "status debe ser una cadena no vacía", None, None

            # Validación para el campo opcional botOutput
            # Si existe, debe ser un diccionario. Si no existe (es None), se ignora.
            if bot_output is not None and not isinstance(bot_output, dict):
                return False, "Si se provee, botOutput debe ser un diccionario", None, None

            return True, "Válido", deployment_id.strip(), status.strip()

        except AttributeError:
            return False, "Payload de callback inválido (no es un diccionario)", None, None
        except Exception as e:
            self.logger.error(f"Excepción inesperada durante _validate_callback_payload: {e}", exc_info=True)
            return False, f"Error de validación interno: {str(e)}", None, None

    def _validate_callback_payload_old(self, data: Dict[str, Any]) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """Valida el payload del callback y extrae los campos requeridos."""
        try:
            deployment_id = data.get("deploymentId")
            status = data.get("status")
            bot_output = data.get("botOutput")

            if deployment_id is None:  # Chequear None explícitamente
                return False, "Campo requerido faltante o nulo: deploymentId", None, None

            if status is None:  # Chequear None explícitamente
                return False, "Campo requerido faltante o nulo: status", None, None

            if bot_output is None:  # Chequear None explícitamente
                return False, "Campo requerido faltante o nulo: botOutput", None, None

            # Validación adicional
            if not isinstance(deployment_id, str) or len(deployment_id.strip()) == 0:
                return False, "deploymentId debe ser una cadena no vacía", None, None

            if not isinstance(status, str) or len(status.strip()) == 0:
                return False, "status debe ser una cadena no vacía", None, None

            if not isinstance(bot_output, dict):
                return False, "botOutput debe ser un diccionario", None, None

            return True, "Válido", deployment_id.strip(), status.strip()

        except AttributeError:  # Si 'data' no es un diccionario (ej. None)
            return False, "Payload de callback inválido (no es un diccionario)", None, None
        except Exception as e:  # Otros errores inesperados durante la validación
            self.logger.error(f"Excepción inesperada durante _validate_callback_payload: {e}", exc_info=True)
            return False, f"Error de validación interno: {str(e)}", None, None

    def _process_callback(self, deployment_id: str, status: str, raw_payload: str) -> Tuple[bool, str]:
        """Procesa el callback con actualización en la base de datos."""
        try:
            with self._get_db_connection() as db:
                # Asumimos que db es un DatabaseConnector válido aquí
                if db is None:
                    self._stats["requests_failed"] += 1
                    self.logger.error("El conector de base de datos es None al intentar procesar el callback.")
                    return False, "Conector de base de datos no disponible."
                success = db.actualizar_ejecucion_desde_callback(deployment_id, status, raw_payload)
                if success:
                    self._stats["requests_processed"] += 1
                    return True, "Callback procesado y BD actualizada exitosamente"
                else:
                    self._stats["requests_failed"] += 1
                    # El logger dentro de actualizar_ejecucion_desde_callback ya debería haber logueado el fallo.
                    return False, "Falló la actualización en la base de datos (ver logs de BD para detalles)"

        except ConnectionError as e_conn:  # Captura específica si _get_db_connection falla
            self._stats["requests_failed"] += 1
            self.logger.error(
                f"Error de conexión a BD procesando callback para {deployment_id}: {e_conn}", exc_info=False
            )  # No incluir exc_info si ya se logueó antes
            return False, f"Error de conexión a BD: {str(e_conn)}"
        except Exception as e:  # Otros errores
            self._stats["requests_failed"] += 1
            self.logger.error(f"Error general procesando callback para {deployment_id}: {e}", exc_info=True)
            return False, f"Error de procesamiento general: {str(e)}"

    def _validate_http_request(self, environ: Dict[str, Any]):
        """
        Valida las propiedades de la solicitud HTTP (autorización, método, tamaño).
        Lanza RequestValidationError si alguna validación falla.
        """
        # 1. Validación de Autorización
        if self.auth_token:
            received_token_str = environ.get("HTTP_X_AUTHORIZATION")
            expected_token_bytes = self.auth_token.encode("utf-8")
            received_token_bytes = received_token_str.encode("utf-8") if received_token_str else b""

            if not hmac.compare_digest(expected_token_bytes, received_token_bytes):
                raise RequestValidationError(
                    status=HTTP.UNAUTHORIZED, internal_code=CODES.AUTH_ERROR, message="Credenciales de autorización no válidas o ausentes."
                )

        # 2. Validación del Método
        if environ.get("REQUEST_METHOD", "GET") != "POST":
            raise RequestValidationError(status=HTTP.METHOD_NOT_ALLOWED, internal_code=CODES.ERROR, message="Solo se permite el método POST.")

        # 3. Validación del Tamaño del Contenido
        try:
            content_length = int(environ.get("CONTENT_LENGTH", 0))
        except (ValueError, TypeError):
            content_length = 0

        if content_length <= 0:
            raise RequestValidationError(
                status=HTTP.BAD_REQUEST, internal_code=CODES.ERROR, message="Cuerpo de la solicitud vacío o Content-Length inválido/ausente."
            )

        if content_length > self.config.max_content_length:
            raise RequestValidationError(
                status=HTTP.PAYLOAD_TOO_LARGE,
                internal_code=CODES.ERROR,
                message=f"Payload demasiado grande (máximo {self.config.max_content_length} bytes).",
            )

    def _read_and_parse_payload(self, environ: Dict[str, Any]) -> Tuple[str, str, str]:
        """
        Lee, decodifica, parsea y valida el contenido del payload.
        Devuelve (deployment_id, status, compact_payload) si es exitoso.
        Lanza RequestValidationError si falla.
        """
        content_length = int(environ.get("CONTENT_LENGTH", 0))
        body_bytes = environ["wsgi.input"].read(content_length)

        try:
            body_str = body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise RequestValidationError(HTTP.BAD_REQUEST, CODES.ERROR, "Codificación UTF-8 inválida.")

        self._log_complete_request(environ, body_str)

        try:
            payload_data = json.loads(body_str)
        except json.JSONDecodeError:
            raise RequestValidationError(HTTP.BAD_REQUEST, CODES.ERROR, "Formato JSON inválido.")

        is_valid, msg, deployment_id, status = self._validate_callback_payload(payload_data)
        if not is_valid:
            raise RequestValidationError(HTTP.BAD_REQUEST, CODES.ERROR, msg)

        compact_payload = json.dumps(payload_data, separators=(",", ":"))
        return deployment_id, status, compact_payload

    def _generate_json_response(self, status: str, internal_code: str, message: str) -> Tuple[str, list, bytes]:
        """Genera la tupla de respuesta WSGI final en formato JSON."""
        response_data = {"status": internal_code, "message": message}
        response_body_bytes = json.dumps(response_data, ensure_ascii=False).encode("utf-8")
        headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(response_body_bytes)))]
        return status, headers, response_body_bytes

    def wsgi_application(self, environ: Dict[str, Any], start_response):
        """
        Punto de entrada WSGI. Orquesta la validación, procesamiento y respuesta.
        """
        self._stats["requests_received"] += 1

        try:
            # 1. Validar la solicitud HTTP (auth, método, tamaño)
            self._validate_http_request(environ)

            # 2. Leer, parsear y validar el contenido del payload
            deployment_id, status, compact_payload = self._read_and_parse_payload(environ)

            # 3. Procesar la lógica de negocio (actualizar BD)
            process_success, process_msg = self._process_callback(deployment_id, status, compact_payload)

            if process_success:
                # 4a. Generar respuesta de éxito
                final_status, headers, body = self._generate_json_response(
                    status=HTTP.OK, internal_code=CODES.OK, message="Callback procesado y registrado exitosamente."
                )
            else:
                # 4b. Generar respuesta de fallo de procesamiento
                final_status, headers, body = self._generate_json_response(
                    status=HTTP.INTERNAL_SERVER_ERROR, internal_code=CODES.PROCESSING_ERROR, message=process_msg
                )

        except RequestValidationError as e:
            # Captura todos los errores de validación y genera la respuesta adecuada
            self.logger.warning(f"Solicitud rechazada desde {environ.get('REMOTE_ADDR', 'Desconocida')}: {e.message}")
            final_status, headers, body = self._generate_json_response(e.status, e.internal_code, e.message)

        except Exception as e_general:
            # Captura cualquier otro error inesperado
            self.logger.critical(f"Excepción crítica no manejada en wsgi_application: {e_general}", exc_info=True)
            final_status, headers, body = self._generate_json_response(
                status=HTTP.INTERNAL_SERVER_ERROR, internal_code=CODES.SERVER_ERROR, message="Ocurrió un error interno inesperado."
            )

        # Enviar la respuesta final al servidor WSGI
        start_response(final_status, headers)
        return [body]

    def _determine_bind_address(self) -> str:
        """Determina la dirección de enlace efectiva con validación."""
        configured_host = self.config.host
        if configured_host and configured_host.strip() and configured_host not in ["0.0.0.0", "*"]:
            effective_host = configured_host.strip()
            self.logger.info(f"Usando host configurado para enlazar: '{effective_host}'")

            # Validar si el host es potencialmente resoluble (no garantiza que se pueda enlazar)
            try:
                socket.getaddrinfo(effective_host, None)
            except socket.gaierror as e:
                self.logger.warning(f"El host configurado '{effective_host}' podría no ser resoluble o válido para enlazar: {e}")

            return effective_host
        else:
            self.logger.info("Enlazando a '0.0.0.0' para escuchar en todas las interfaces de red disponibles.")
            return "0.0.0.0"

    def _setup_signal_handlers(self) -> None:
        """Configura manejadores de señales para una parada elegante."""

        def internal_signal_handler(signum, frame):
            try:
                signal_name = signal.Signals(signum).name
            except (AttributeError, ValueError):  # Para casos donde Signals(signum) no sea válido o .name no exista
                signal_name = str(signum)
            self.logger.warning(f"Recibida señal de parada '{signal_name}' (PID: {os.getpid()}). Iniciando parada del servidor...")
            self._shutdown_event.set()
            # Si estamos usando wsgiref.simple_server con handle_request en un bucle,
            # necesitamos una forma de interrumpir ese bucle.
            # Para waitress, la propia librería maneja la señal y detiene el `serve()`.
            if not WAITRESS_AVAILABLE and self.server_instance:
                # Esto es un intento, pero puede no ser suficiente para un shutdown inmediato de handle_request
                # La mejor forma es que el bucle principal de handle_request chequee self._shutdown_event.
                self.logger.info(
                    "Intentando cerrar instancia de servidor wsgiref (puede requerir una solicitud final para desbloquear handle_request)..."
                )
                # self.server_instance.shutdown() # shutdown() no funciona bien si está en handle_request

        # Intentar registrar señales comunes
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, internal_signal_handler)
            except (OSError, ValueError, AttributeError) as e:  # Algunos sistemas/contextos no permiten todas las señales
                self.logger.warning(f"No se pudo registrar el manejador para la señal {sig}: {e}")

        if hasattr(signal, "SIGBREAK"):  # SIGBREAK es específico de Windows
            try:
                signal.signal(signal.SIGBREAK, internal_signal_handler)
            except (OSError, ValueError, AttributeError) as e:
                self.logger.warning(f"No se pudo registrar el manejador para la señal SIGBREAK: {e}")

    def _log_server_stats(self) -> None:
        """Loguea las estadísticas del servidor."""
        total_uptime = time.time() - self._stats["start_time"]
        self.logger.info("=" * 70)
        self.logger.info("Estadísticas Finales del Servidor de Callbacks:")
        self.logger.info(f"  Tiempo activo total: {total_uptime:.2f} segundos")
        self.logger.info(f"  Solicitudes totales recibidas: {self._stats['requests_received']}")
        self.logger.info(f"  Solicitudes procesadas exitosamente: {self._stats['requests_processed']}")
        self.logger.info(f"  Solicitudes fallidas (procesamiento/BD): {self._stats['requests_failed']}")
        if self._stats["requests_received"] > 0:
            processing_success_rate = (self._stats["requests_processed"] / self._stats["requests_received"]) * 100
            self.logger.info(f"  Tasa de éxito de procesamiento: {processing_success_rate:.2f}%")
        self.logger.info("=" * 70)

    def start(self) -> None:
        """Inicia el servidor de callbacks."""
        effective_host = self._determine_bind_address()

        # Loguear información de inicio
        self.logger.info("=" * 80)
        self.logger.info(f" Iniciando Servidor de Callbacks SAM (PID: {os.getpid()})")
        self.logger.info(f" Escuchando en: http://{effective_host}:{self.config.port}")
        self.logger.info(
            f" Usando servidor: {'Waitress (recomendado para producción)' if WAITRESS_AVAILABLE else 'wsgiref.simple_server (solo para desarrollo)'}"
        )
        if WAITRESS_AVAILABLE:
            self.logger.info(f" Hilos configurados para Waitress: {self.config.threads}")

        # Obtener URL de callback de la configuración
        try:
            aa_config = ConfigManager.get_aa_config()
            public_callback_url = aa_config.get("url_callback", "NO CONFIGURADA EN .ENV")
            self.logger.info(f" URL pública esperada para callbacks de A360 (desde config): {public_callback_url}")
        except Exception as e_aa_config:
            self.logger.warning(f"No se pudo obtener la URL de callback desde la configuración de AA: {e_aa_config}")

        self.logger.info("=" * 80)

        server_terminated_correctly = False

        try:
            if WAITRESS_AVAILABLE:
                # Usar Waitress para producción
                serve(
                    self.wsgi_application,
                    host=effective_host,
                    port=self.config.port,
                    threads=self.config.threads,
                    channel_timeout=self.config.channel_timeout,
                    cleanup_interval=self.config.cleanup_interval,
                )
                # Si serve() retorna, es porque fue detenido (usualmente por una señal)
                server_terminated_correctly = True
            else:
                # Fallback a wsgiref para desarrollo
                self.logger.warning("Waitress no está instalado. Usando wsgiref.simple_server (NO RECOMENDADO PARA PRODUCCIÓN).")
                self.logger.warning("Para un entorno de producción, por favor instale Waitress: pip install waitress")

                self.server_instance = make_server(effective_host, self.config.port, self.wsgi_application)
                self.logger.info(f"Servidor wsgiref (desarrollo) escuchando en http://{effective_host}:{self.config.port}")

                # Bucle para manejar solicitudes y permitir parada elegante con wsgiref
                while not self._shutdown_event.is_set():
                    # handle_request() es bloqueante por una solicitud. Necesitamos un timeout
                    # o una forma de interrumpirlo. Una solución simple es un timeout corto.
                    # Sin embargo, handle_request no tiene un timeout directo.
                    # server.serve_forever() es más común pero más difícil de parar limpiamente sin hilos.
                    # Para este ejemplo, si no usamos waitress, el cierre podría no ser tan elegante.
                    # Una forma más robusta con wsgiref sería usar server_forever en un hilo y llamar a shutdown desde otro.
                    # Aquí, hacemos un bucle que podría ser menos eficiente pero más simple de parar.
                    self.server_instance.timeout = 0.5  # Poner un timeout al socket del servidor
                    try:
                        self.server_instance.handle_request()  # Manejar una solicitud
                    except socket.timeout:
                        continue  # Continuar el bucle si es solo un timeout
                    except Exception as e_handle:
                        self.logger.error(f"Error en wsgiref handle_request: {e_handle}")
                        break  # Salir del bucle en otros errores

                server_terminated_correctly = True  # Asumimos que si sale del bucle es por _shutdown_event

        except OSError as e_os:  # ej. puerto en uso
            self.logger.critical(
                f"Error de OSError al intentar iniciar el servidor (la dirección '{effective_host}:{self.config.port}' podría estar en uso): {e_os}",
                exc_info=True,
            )
        except KeyboardInterrupt:  # Capturar Ctrl+C
            self.logger.info("KeyboardInterrupt (Ctrl+C) recibido. Parando el servidor de Callbacks...")
            self._shutdown_event.set()  # Asegurar que el evento de parada esté activo
            server_terminated_correctly = True
        except SystemExit:  # Capturar SystemExit si el manejador de señales lo llama
            self.logger.info("SystemExit capturado, el servidor de callbacks está finalizando.")
            server_terminated_correctly = True
        except Exception as e_general_server:  # Cualquier otra excepción al iniciar/correr el servidor
            self.logger.critical(f"Error fatal durante la ejecución del servidor de Callbacks: {e_general_server}", exc_info=True)
        finally:
            self._cleanup_final(server_terminated_correctly)

    def _cleanup_final(self, clean_shutdown: bool = True) -> None:
        """Limpia recursos al finalizar el servidor."""
        if clean_shutdown:
            self.logger.info("Servidor de Callbacks SAM finalizando operaciones limpiamente.")
        else:
            self.logger.warning("Servidor de Callbacks SAM finalizando de forma inesperada o no pudo iniciarse.")

        # Loguear estadísticas finales
        self._log_server_stats()

        # Parar la instancia del servidor wsgiref si existe y está activa
        if self.server_instance:
            self.logger.info("Intentando cerrar la instancia del servidor wsgiref...")
            try:
                # Para wsgiref, cerrar el socket es una forma de intentar detenerlo si está en un bucle.
                if hasattr(self.server_instance, "socket") and self.server_instance.socket:
                    self.server_instance.socket.close()
                if hasattr(self.server_instance, "server_close"):
                    self.server_instance.server_close()
                self.logger.info("Instancia del servidor wsgiref cerrada (o intento realizado).")
            except Exception as e_shutdown_wsgiref:
                self.logger.error(f"Error durante el cierre del servidor wsgiref: {e_shutdown_wsgiref}", exc_info=True)

        # Cerrar conexión a base de datos
        if self.db_connector:
            self.logger.info("Cerrando conexión a la base de datos del servidor de Callbacks...")
            try:
                self.db_connector.cerrar_conexion_hilo_actual()  # Cierra la del hilo principal
                self.logger.info("Conexión a BD cerrada.")
            except Exception as e_db_close:
                self.logger.error(f"Error al cerrar la conexión a la base de datos: {e_db_close}", exc_info=True)

        # Limpiar manejadores de logging y cerrar logging
        self.logger.info("Finalizando sistema de logging del servidor de Callbacks...")
        # logging.shutdown() # Llamar a logging.shutdown() puede ser muy agresivo si hay otros loggers.
        # Es mejor limpiar los handlers del logger específico de este servidor.
        if self.logger and hasattr(self.logger, "handlers"):
            for handler_item in self.logger.handlers[:]:  # Iterar sobre una copia
                try:
                    handler_item.close()
                    self.logger.removeHandler(handler_item)
                except Exception as e_handler_close:
                    print(f"Error cerrando handler de log: {e_handler_close}", file=sys.stderr)  # Usar print si el logger ya no funciona

        print("Servidor de Callbacks SAM: Proceso de limpieza final completado.", file=sys.stderr)

    def _log_complete_request(self, environ: Dict[str, Any], body_str: str):
        """
        Registra en el log (a nivel DEBUG) los encabezados y el cuerpo de una solicitud.
        Los encabezados sensibles como la autorización son ofuscados.
        """
        try:
            # Extraer y formatear encabezados, ofuscando el de autorización
            formatted_headers = ""
            for key, value in environ.items():
                if key.startswith("HTTP_"):
                    header_name = key[5:].replace("_", "-").title()
                    if header_name.lower() == "x-authorization":
                        obfuscated_value = f"'{value[:4]}...{value[-4:]}'" if value and len(value) > 8 else "'***'"
                        formatted_headers += f"  {header_name}: {obfuscated_value}\n"
                    else:
                        formatted_headers += f"  {key[5:].replace('_', '-').title()}: {value}\n"

            # Truncar el cuerpo del log si es demasiado largo
            payload_preview = body_str[: self.config.log_payload_max_chars]
            if len(body_str) > self.config.log_payload_max_chars:
                payload_preview += "..."

            # Construir el mensaje de log final
            complete_log = (
                f"--- Inicio de Detalles de la Solicitud ---\n"
                f"Desde: {environ.get('REMOTE_ADDR', 'Desconocida')}\n"
                f"Encabezados:\n{formatted_headers.strip()}\n"
                f"Cuerpo:\n  {payload_preview}\n"
                f"--- Fin de Detalles de la Solicitud ---"
            )

            self.logger.debug(complete_log)

        except Exception as e:
            self.logger.error(f"Error al intentar registrar los detalles de la solicitud: {e}", exc_info=False)


def start_callback_server_main():
    """Punto de entrada principal para iniciar el servidor."""
    server_app = None
    try:
        server_app = CallbackServer()
        server_app.start()
    except Exception as e_fatal_start:
        # Este log podría no funcionar si el logger falló en inicializarse.
        # Usar print para asegurar visibilidad del error crítico.
        error_message = f"CRITICO: Falló el inicio del servidor de callbacks de forma fatal: {e_fatal_start}"
        print(error_message, file=sys.stderr)
        # Intentar loguear también, por si acaso
        if server_app and server_app.logger:
            server_app.logger.critical(error_message, exc_info=True)
        else:  # Logger no disponible, usar logging básico si es posible
            logging.critical(error_message, exc_info=True)
        sys.exit(1)  # Salir con código de error


if __name__ == "__main__":
    # Esto permite ejecutar el servidor directamente con: python lanzador/service/callback_server.py
    # (asumiendo que SAM_PROJECT_ROOT está en PYTHONPATH o se ejecuta desde la raíz con -m)
    start_callback_server_main()
