# SAM/src/callback/service/main.py
import hmac
import json
import logging
from typing import Any, Dict, Optional, Tuple
from wsgiref.simple_server import make_server

try:
    from waitress import serve

    WAITRESS_AVAILABLE = True
except ImportError:
    WAITRESS_AVAILABLE = False

from src.common.database.sql_client import DatabaseConnector
from src.common.utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class CallbackService:
    """
    Encapsula toda la lógica del servidor de Callbacks.
    """

    def __init__(self):
        """Inicializa el servidor de Callbacks."""
        logger.info("Inicializando CallbackService...")
        self._load_configuration()
        self._initialize_db_connector()

    def _load_configuration(self):
        """Carga la configuración desde el ConfigManager."""
        cb_config = ConfigManager.get_callback_server_config()
        self.host = cb_config.get("host", "0.0.0.0")
        self.port = cb_config.get("port", 8008)
        self.threads = cb_config.get("threads", 8)
        self.auth_token = cb_config.get("callback_token")

        # Nueva configuración para el modo de autenticación
        # 'strict' para producción (requiere token), 'optional' para desarrollo.
        self.auth_mode = cb_config.get("auth_mode", "optional").lower()

        # Asegurarse de que la ruta siempre empiece con una barra '/'.
        path_from_config = cb_config.get("endpoint_path", "/").strip()
        if not path_from_config.startswith("/"):
            path_from_config = "/" + path_from_config
        self.endpoint_path = path_from_config
        logger.info(f"Endpoint configurado en la ruta: {self.endpoint_path}")

        if self.auth_mode == "strict":
            if not self.auth_token:
                logger.critical("Error de configuración: El modo de autenticación es 'strict' pero no se ha definido un CALLBACK_TOKEN.")
                # En un caso real, podría ser buena idea salir del programa si la configuración es inconsistente.
                # sys.exit(1)
            else:
                logger.info("Servidor en modo de autenticación ESTRICTO. Todas las peticiones requieren un token válido.")
        else:
            logger.info("Servidor en modo de autenticación OPCIONAL. Ideal para desarrollo.")

    def _initialize_db_connector(self):
        """Inicializa el conector a la base de datos."""
        try:
            sql_config = ConfigManager.get_sql_server_config("SQL_SAM")
            self.db_connector = DatabaseConnector(
                servidor=sql_config["server"], base_datos=sql_config["database"], usuario=sql_config["uid"], contrasena=sql_config["pwd"]
            )
            logger.info("Conector de base de datos inicializado.")
        except Exception as e:
            logger.critical(f"No se pudo inicializar el conector de la base de datos: {e}", exc_info=True)
            self.db_connector = None

    def _validate_request(self, environ: Dict[str, Any]) -> Tuple[bool, str, str]:
        """Valida el método, token y cuerpo de la petición."""
        # 0. Validar ruta del endpoint
        path = environ.get("PATH_INFO", "")
        if path != self.endpoint_path:
            logger.warning(f"Petición rechazada a ruta no válida: {path}. Ruta esperada: {self.endpoint_path}")
            return False, "404 Not Found", f"La ruta '{path}' no existe. El endpoint correcto es '{self.endpoint_path}'."

        # 1. Validar método
        if environ.get("REQUEST_METHOD", "GET") != "POST":
            return False, "405 Method Not Allowed", "Método no permitido. Solo se acepta POST."

        # 2. Validar token según el modo
        if self.auth_mode == "strict":
            # En modo estricto, el token debe estar configurado y la petición debe tenerlo.
            if not self.auth_token:
                # Esto indica una mala configuración del servidor.
                return False, "500 Internal Server Error", "Servidor no configurado para validar tokens."

            received_token = environ.get("HTTP_X_AUTHORIZATION", "")
            if not hmac.compare_digest(self.auth_token, received_token):
                logger.warning(f"Intento de acceso no autorizado. Token recibido: '{received_token[:10]}...'")
                return False, "401 Unauthorized", "Token de autorización inválido o ausente."
        elif self.auth_token:
            # En modo opcional, si el token está configurado, se valida si se recibe.
            # Si no se recibe el header, se permite el paso.
            received_token = environ.get("HTTP_X_AUTHORIZATION")
            if received_token is not None and not hmac.compare_digest(self.auth_token, received_token):
                return False, "401 Unauthorized", "Token de autorización inválido."

        # 3. Validar Content-Length
        try:
            content_length = int(environ.get("CONTENT_LENGTH", 0))
            if content_length <= 0:
                return False, "400 Bad Request", "Cuerpo de la petición vacío o Content-Length ausente."
        except (ValueError, TypeError):
            return False, "400 Bad Request", "Content-Length inválido."

        return True, "", ""

    def _process_payload(self, body: bytes) -> Tuple[bool, str]:
        """Parsea el payload y lo procesa en la base de datos."""
        try:
            payload_str = body.decode("utf-8")
            data = json.loads(payload_str)

            deployment_id = data.get("deploymentId")
            status = data.get("status")

            if not deployment_id or not status:
                return False, "Faltan 'deploymentId' o 'status' en el payload."

            if not self.db_connector:
                logger.error("No se puede procesar el callback porque el conector de BD no está disponible.")
                return False, "Error interno del servidor: Conexión a BD no disponible."

            # El método actualizar_ejecucion_desde_callback ya almacena el payload completo (payload_str)
            # por lo que los campos opcionales como deviceId, userId y botOutput quedan registrados.
            success = self.db_connector.actualizar_ejecucion_desde_callback(deployment_id, status, payload_str)
            return success, "Callback procesado." if success else "Error al actualizar la base de datos."

        except json.JSONDecodeError:
            return False, "Payload no es un JSON válido."
        except UnicodeDecodeError:
            return False, "Payload no está en formato UTF-8 válido."
        except Exception as e:
            logger.error(f"Error inesperado procesando el payload: {e}", exc_info=True)
            return False, "Error interno del servidor durante el procesamiento."

    def wsgi_app(self, environ: Dict[str, Any], start_response):
        """Aplicación WSGI que maneja las peticiones entrantes."""
        is_valid, status, message = self._validate_request(environ)
        if not is_valid:
            response_body = json.dumps({"status": "ERROR", "message": message}).encode("utf-8")
            headers = [("Content-Type", "application/json"), ("Content-Length", str(len(response_body)))]
            start_response(status, headers)
            return [response_body]

        content_length = int(environ.get("CONTENT_LENGTH", 0))
        request_body = environ["wsgi.input"].read(content_length)

        success, message = self._process_payload(request_body)

        if success:
            response_status = "200 OK"
            response_json = {"status": "OK", "message": message}
        else:
            response_status = "500 Internal Server Error"
            response_json = {"status": "ERROR", "message": message}

        response_body = json.dumps(response_json).encode("utf-8")
        headers = [("Content-Type", "application/json"), ("Content-Length", str(len(response_body)))]
        start_response(response_status, headers)
        return [response_body]

    def start(self):
        """Inicia el servidor WSGI."""
        logger.info(f"Servidor de Callbacks iniciando en http://{self.host}:{self.port}")

        if WAITRESS_AVAILABLE:
            logger.info(f"Usando servidor Waitress con {self.threads} hilos (recomendado para producción).")
            serve(self.wsgi_app, host=self.host, port=self.port, threads=self.threads)
        else:
            logger.warning("Waitress no encontrado. Usando wsgiref.simple_server (solo para desarrollo).")
            httpd = make_server(self.host, self.port, self.wsgi_app)
            httpd.serve_forever()


#
