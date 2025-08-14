# SAM/src/callback/service/main.py (Refactorizado)
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

        if not self.auth_token:
            logger.warning("No se ha configurado un CALLBACK_TOKEN. El servidor no validará las peticiones.")
        else:
            logger.info("CALLBACK_TOKEN cargado. El servidor validará el encabezado 'X-Authorization'.")

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
        # Validar método
        if environ.get("REQUEST_METHOD", "GET") != "POST":
            return False, "405 Method Not Allowed", "Método no permitido. Solo se acepta POST."

        # Validar token
        if self.auth_token:
            received_token = environ.get("HTTP_X_AUTHORIZATION", "")
            if not hmac.compare_digest(self.auth_token, received_token):
                return False, "401 Unauthorized", "Token de autorización inválido."

        # Validar Content-Length
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

            # El campo botOutput es opcional, por lo que no se valida su presencia.
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