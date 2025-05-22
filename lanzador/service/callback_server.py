# SAM/Lanzador/service/callback_server.py
import json
import logging
from logging.handlers import TimedRotatingFileHandler # Para el logger dedicado
import os
import socket # Para autodetección de IP y validación de host
import signal
import sys
from wsgiref.simple_server import make_server # Fallback si waitress no está
# from waitress import serve # Descomentar para producción

# --- Configuración de Path ---
from pathlib import Path
SAM_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(SAM_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SAM_PROJECT_ROOT))

from lanzador.utils.config import ConfigManager # Solo para leer la config de BD y del propio callback server
from lanzador.database.sql_client import DatabaseConnector
from typing import Optional, List, Dict, Any # Para type hints

# --- CONFIGURACIÓN DE LOGGING ESPECÍFICA PARA EL CALLBACK SERVER ---
def setup_callback_logging(
        log_directory_base: str = "C:/RPA/Logs/SAM_Lanzador", # Debería leerse de config si es posible
        log_filename: str = "sam_callback_server.log",
        log_level_str: str = "INFO",
        backup_count: int = 7,
        log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
        date_fmt: str = "%Y-%m-%d %H:%M:%S"
    ) -> logging.Logger:
    """Configura un logger dedicado para el callback_server."""
    
    logger_name = "SAMCallbackServer"
    cb_logger = logging.getLogger(logger_name)
    
    # Evitar añadir handlers múltiples si el logger ya está configurado (ej. si se llama múltiples veces)
    if cb_logger.hasHandlers():
        # Podríamos optar por limpiar handlers existentes: cb_logger.handlers.clear()
        # o simplemente no añadir más si ya los tiene.
        # Por ahora, si ya tiene, asumimos que está bien o que fue configurado por el mismo código.
        # Si queremos asegurar una reconfiguración, limpiar primero:
        # cb_logger.handlers.clear()
        pass # No añadir handlers duplicados

    cb_logger.setLevel(getattr(logging, log_level_str.upper(), logging.INFO))
    cb_logger.propagate = False # Evitar que los logs se propaguen al logger raíz si éste tiene otra config

    # Crear directorio si no existe, dentro de un subdirectorio "callbacks"
    callback_log_dir = os.path.join(log_directory_base, "callbacks")
    try:
        os.makedirs(callback_log_dir, exist_ok=True)
    except OSError as e_os:
        # Si no podemos crear el directorio de logs, es un problema serio.
        # Imprimir en consola y re-levantar o salir.
        print(f"Error CRÍTICO: No se pudo crear el directorio de logs '{callback_log_dir}': {e_os}", file=sys.stderr)
        # Podríamos usar un handler de consola como fallback aquí o simplemente fallar.
        # Por ahora, si esto falla, el logging a archivo no funcionará.
        # Considerar añadir un StreamHandler si el FileHandler falla.
        
    log_file_path = os.path.join(callback_log_dir, log_filename)

    # Añadir handlers solo si no los tiene (o si se limpiaron arriba)
    if not cb_logger.handlers:
        try:
            file_handler = TimedRotatingFileHandler(
                log_file_path, 
                when="midnight", 
                interval=1, 
                backupCount=backup_count,
                encoding="utf-8"
            )
            formatter = logging.Formatter(fmt=log_format, datefmt=date_fmt)
            file_handler.setFormatter(formatter)
            cb_logger.addHandler(file_handler)
        except Exception as e_fh:
            print(f"Error CRÍTICO: No se pudo crear FileHandler para '{log_file_path}': {e_fh}", file=sys.stderr)


        # Handler para consola (útil para debugging y si el logging a archivo falla)
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(fmt=log_format, datefmt=date_fmt) # Puede tener su propio formato
        console_handler.setFormatter(console_formatter)
        cb_logger.addHandler(console_handler)
            
    return cb_logger

# Inicializar logger dedicado
# Idealmente, los parámetros de setup_callback_logging vendrían de ConfigManager
try:
    log_cfg = ConfigManager.get_log_config() # Asumiendo que esto devuelve un dict
    logger = setup_callback_logging(
        log_directory_base=log_cfg.get("directory", "C:/RPA/Logs/SAM_Lanzador"),
        log_filename=log_cfg.get("callback_log_filename", "sam_callback_server.log"),
        log_level_str=log_cfg.get("level_str", "INFO"), # Asumiendo que tienes "level_str" en log_config
        backup_count=log_cfg.get("backupCount", 7),
        log_format=log_cfg.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"),
        date_fmt=log_cfg.get("datefmt", "%Y-%m-%d %H:%M:%S")
    )
except Exception as e_log_init:
    # Fallback a un logger de consola muy básico si la configuración de logging falla
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - SAMCallbackServer - %(levelname)s - %(message)s')
    logger = logging.getLogger("SAMCallbackServer_Fallback")
    logger.critical(f"Fallo al inicializar logging desde ConfigManager, usando fallback: {e_log_init}", exc_info=True)


# --- Variables Globales para el Servidor (se cargarán desde ConfigManager) ---
CALLBACK_SERVER_HOST = "0.0.0.0"
CALLBACK_SERVER_PORT = 8008
CALLBACK_SERVER_THREADS = 8 # Para Waitress

db_connector_instance: Optional[DatabaseConnector] = None

def initialize_db_connector():
    """Inicializa el conector de base de datos para el servidor de callbacks."""
    global db_connector_instance
    if db_connector_instance is None or not db_connector_instance.verificar_conexion():
        logger.info("Inicializando o reconectando DatabaseConnector para Callback Server...")
        try:
            sql_cfg = ConfigManager.get_sql_server_config()
            # El db_name para el lanzador y el callback server debe ser el mismo (SAM.dbo.Ejecuciones)
            db_name_sam = sql_cfg.get("database_sam", sql_cfg.get("database")) 
            if not db_name_sam:
                 raise ValueError("Nombre de BD para SAM no encontrado en config para Callback Server.")

            # Usar un timeout de conexión diferente/más corto para el callback server si se desea
            timeout_cb_db_conn = sql_cfg.get("timeout_conexion_inicial_callback", 15)

            db_connector_instance = DatabaseConnector(
                servidor=sql_cfg["server"],
                base_datos=db_name_sam,
                usuario=sql_cfg["uid"],
                contrasena=sql_cfg["pwd"],
                timeout_conexion=timeout_cb_db_conn 
            )
            logger.info("DatabaseConnector (re)inicializado exitosamente para Callback Server.")
        except Exception as e:
            logger.critical(f"Error CRÍTICO al (re)inicializar DatabaseConnector para Callback Server: {e}", exc_info=True)
            db_connector_instance = None
    return db_connector_instance


def callback_receiver_app(environ: Dict[str, Any], start_response):
    """Punto de entrada WSGI para cada petición de callback de A360."""
    status_http = "200 OK"
    # Especificar charset para asegurar correcta codificación de tildes, etc.
    response_headers = [("Content-type", "application/json; charset=utf-8")]
    response_body_dict = {"estado": "OK", "mensaje": "Callback recibido y procesado por SAM."}
    body_bytes = b'' # Para el logging en caso de error de parseo JSON

    try:
        request_method = environ.get("REQUEST_METHOD", "GET")
        path_info = environ.get("PATH_INFO", "/")
        remote_addr = environ.get('REMOTE_ADDR', 'Desconocida')
        logger.info(f"Callback entrante: {request_method} {path_info} desde {remote_addr}")

        if request_method != "POST":
            logger.warning(f"Método no permitido: {request_method}. Se esperaba POST.")
            status_http = "405 Method Not Allowed"
            response_body_dict = {"estado": "ERROR", "mensaje": "Método no permitido. Por favor, use POST."}
            start_response(status_http, response_headers + [('Allow', 'POST')])
            # ensure_ascii=False para que json.dumps respete los caracteres no ASCII
            return [json.dumps(response_body_dict, ensure_ascii=False).encode('utf-8')]

        content_length = int(environ.get("CONTENT_LENGTH", 0))
        if content_length <= 0:
            logger.warning("Callback POST sin cuerpo (Content-Length 0 o ausente).")
            status_http = "400 Bad Request"
            response_body_dict = {"estado": "ERROR", "mensaje": "El cuerpo de la solicitud está vacío o falta Content-Length."}
        else:
            try:
                body_bytes = environ["wsgi.input"].read(content_length)
                body_str = body_bytes.decode("utf-8") # Asumir UTF-8
                logger.debug(f"Callback POST payload (raw): {body_str[:1000]}...") # Loguear más del payload
                
                data_json = json.loads(body_str)
                
                deployment_id = data_json.get("deploymentId")
                status_from_a360 = data_json.get("status")
                # Opcional: extraer otros campos si son útiles para loguear o debuggear
                # a360_user_id_cb = data_json.get("userId")
                # a360_device_id_cb = data_json.get("deviceId")
                # bot_output_cb = data_json.get("botOutput")

                logger.info(f"Callback procesando: DeploymentId='{deployment_id}', Estado A360='{status_from_a360}'")

                if deployment_id and status_from_a360:
                    # Asegurar que db_connector_instance esté inicializado (debería estarlo si el server arrancó)
                    if db_connector_instance or initialize_db_connector():
                        actualizado_ok = db_connector_instance.actualizar_ejecucion_desde_callback(
                            deployment_id, status_from_a360, body_str # Guardar el payload completo
                        )
                        if not actualizado_ok:
                            status_http = "500 Internal Server Error"
                            response_body_dict = {"estado": "ERROR", "mensaje": "Fallo al actualizar la base de datos desde el callback."}
                            logger.error(f"Fallo al actualizar BD para DeploymentId {deployment_id} desde callback.")
                    else:
                        logger.critical("Callback NO PUDO PROCESARSE: db_connector_instance no está inicializado después de intento.")
                        status_http = "500 Internal Server Error"
                        response_body_dict = {"estado": "ERROR", "mensaje": "El conector de base de datos del servidor de Callbacks no está disponible."}
                else:
                    logger.warning(f"Callback recibido con JSON incompleto: Falta deploymentId o status. Payload: {str(data_json)[:500]}")
                    status_http = "400 Bad Request"
                    response_body_dict = {"estado": "ERROR", "mensaje": "Payload JSON inválido: deploymentId y status son requeridos."}

            except json.JSONDecodeError as e_json:
                logger.error(f"Error decodificando JSON del callback: {e_json}. Body (bytes): {body_bytes[:200]}...", exc_info=True)
                status_http = "400 Bad Request"
                response_body_dict = {"estado": "ERROR", "mensaje": "Formato JSON inválido en el cuerpo de la solicitud."}
            except Exception as e_proc_body: # Cualquier otro error procesando el cuerpo
                logger.error(f"Error procesando cuerpo del request del callback: {e_proc_body}", exc_info=True)
                status_http = "500 Internal Server Error"
                response_body_dict = {"estado": "ERROR", "mensaje": "Error interno procesando el cuerpo de la solicitud."}
    
    except Exception as e_general_cb: # Error muy general en la app WSGI
        logger.critical(f"Excepción crítica no manejada en callback_receiver_app: {e_general_cb}", exc_info=True)
        status_http = "500 Internal Server Error"
        response_body_dict = {"estado": "ERROR", "mensaje": "Ocurrió un error interno inesperado en la aplicación de callbacks."}

    response_body_bytes = json.dumps(response_body_dict, ensure_ascii=False).encode('utf-8')
    response_headers.append(('Content-Length', str(len(response_body_bytes))))
    start_response(status_http, response_headers)
    return [response_body_bytes]


def determine_effective_host(configured_host: str, logger_instance: logging.Logger) -> str:
    """Determina el host efectivo para el servidor."""
    if configured_host and configured_host.strip() and configured_host not in ["0.0.0.0", "*"]:
        effective_host = configured_host.strip()
        logger_instance.info(f"Usando host especificado en config: '{effective_host}'")
        try:
            socket.getaddrinfo(effective_host, None) 
        except socket.gaierror:
            logger_instance.warning(f"Host configurado '{effective_host}' no parece ser resoluble o es inválido. Verifica la configuración.")
        return effective_host
    else: 
        logger_instance.info(f"Host no especificado o como '0.0.0.0'/'*'. Usando '0.0.0.0' para escuchar en todas las interfaces.")
        return "0.0.0.0"

http_server_global_ref = None # Para poder cerrarlo desde el signal_handler si es wsgiref

def signal_handler_callbacks(signum, frame):
    global http_server_global_ref
    logger.warning(f"Señal de cierre {signal.Signals(signum).name} recibida por SAM Callback Server (PID: {os.getpid()}).")
    
    if db_connector_instance:
        logger.info("Cerrando conexión de BD del Callback Server...")
        db_connector_instance.cerrar_conexion_hilo_actual() # Cierra la del hilo actual (principal)
    
    if http_server_global_ref and hasattr(http_server_global_ref, 'shutdown'): # Si es wsgiref
        logger.info("Intentando detener servidor wsgiref...")
        # Shutdown para wsgiref necesita ser llamado desde otro hilo, o no funcionará bien con serve_forever
        # Una forma más simple es simplemente salir del proceso, y el finally lo manejará.
        # threading.Thread(target=http_server_global_ref.shutdown).start() # Esto podría ser necesario para wsgiref
        # O simplemente dejar que el script termine y el finally se ejecute.
        pass # Dejar que el finally principal maneje esto.
    
    logger.info("Waitress (o wsgiref) debería manejar el cierre del servidor. El script finalizará después de que el servidor se detenga.")
    # No llamar a sys.exit() aquí, permitir que el servidor WSGI se detenga y el script termine naturalmente.

def start_callback_server_main():
    global CALLBACK_SERVER_HOST, CALLBACK_SERVER_PORT, CALLBACK_SERVER_THREADS
    global http_server_global_ref # Para wsgiref

    try:
        # Cargar configuración del callback server
        cfg_cb_server = ConfigManager.get_callback_server_config()
        CALLBACK_SERVER_HOST = cfg_cb_server.get("host", "0.0.0.0")
        CALLBACK_SERVER_PORT = cfg_cb_server.get("port", 8008)
        CALLBACK_SERVER_THREADS = cfg_cb_server.get("threads", 8)
        
        # Cargar configuración de logging (opcional, si setup_callback_logging no lo hace desde config)
        # log_cfg = ConfigManager.get_log_config()
        # logger = setup_callback_logging(log_filename=log_cfg.get("callback_log_filename", "sam_callback_server.log"))

    except Exception as e_cfg:
        logger.critical(f"Error fatal leyendo configuración para Callback Server: {e_cfg}. Usando defaults.", exc_info=True)

    if not initialize_db_connector(): # Intenta inicializar/reconectar la BD
        logger.critical("No se pudo inicializar el conector de BD. El servidor de Callbacks no se iniciará.")
        return 

    effective_host = determine_effective_host(CALLBACK_SERVER_HOST, logger)
    
    # Registrar manejadores de señales
    signal.signal(signal.SIGTERM, signal_handler_callbacks)
    signal.signal(signal.SIGINT, signal_handler_callbacks)
    if hasattr(signal, 'SIGBREAK'): 
        signal.signal(signal.SIGBREAK, signal_handler_callbacks)

    logger.info(f"====================================================================")
    logger.info(f" Iniciando Servidor de Callbacks SAM (PID: {os.getpid()})")
    logger.info(f" Escuchando en: http://{effective_host}:{CALLBACK_SERVER_PORT}")
    logger.info(f" Usando Waitress con {CALLBACK_SERVER_THREADS} threads (si está instalada).")
    logger.info(f" URL pública para callbacks de A360 (configurada en AA_URL_CALLBACK): {ConfigManager.get_aa_config().get('url_callback', 'NO CONFIGURADA')}")
    logger.info(f"====================================================================")
    
    server_stopped_cleanly = False
    try:
        # Dar prioridad a Waitress para producción
        from waitress import serve
        serve(
            callback_receiver_app,
            host=effective_host,
            port=CALLBACK_SERVER_PORT,
            threads=CALLBACK_SERVER_THREADS,
            channel_timeout=120, 
            cleanup_interval=30  
        )
        server_stopped_cleanly = True # Si serve() retorna, es un cierre normal (ej. por señal)
    except ImportError:
        logger.warning("Waitress no está instalado. Iniciando con wsgiref.simple_server (SOLO PARA DESARROLLO).")
        logger.warning("Para producción, por favor instale waitress: pip install waitress")
        try:
            http_server_global_ref = make_server(effective_host, CALLBACK_SERVER_PORT, callback_receiver_app)
            logger.info(f"Servidor de Callbacks (wsgiref) escuchando en http://{effective_host}:{CALLBACK_SERVER_PORT}")
            http_server_global_ref.serve_forever() # Bloqueante
            server_stopped_cleanly = True # Si serve_forever es interrumpido por KeyboardInterrupt y manejado
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt (Ctrl+C) recibido por wsgiref. Cerrando servidor...")
            server_stopped_cleanly = True
        except Exception as e_wsgiref:
            logger.critical(f"Error fatal al intentar iniciar servidor wsgiref: {e_wsgiref}", exc_info=True)
    except OSError as e_os_serve: # Ej. puerto en uso
        logger.critical(
            f"OSError al intentar iniciar el servidor (la dirección '{effective_host}:{CALLBACK_SERVER_PORT}' podría estar en uso): {e_os_serve}",
            exc_info=True)
    except SystemExit: # Capturar SystemExit si el signal handler lo llama
        logger.info("SystemExit capturado, el servidor de callbacks está finalizando.")
        server_stopped_cleanly = True
    except Exception as e_serve: # Cualquier otra excepción al iniciar/correr el servidor
        logger.critical(f"Error fatal durante la ejecución del servidor de Callbacks: {e_serve}", exc_info=True)
    finally:
        if server_stopped_cleanly:
            logger.info("Servidor de Callbacks SAM ha finalizado limpiamente.")
        else:
            logger.warning("Servidor de Callbacks SAM ha finalizado de forma inesperada o no pudo iniciarse.")

        # Intentar cerrar el servidor wsgiref si fue usado y no se detuvo por KeyboardInterrupt
        if http_server_global_ref and hasattr(http_server_global_ref, '_BaseServer__is_shut_down') and \
           not http_server_global_ref._BaseServer__is_shut_down.is_set(): # Chequeo interno de wsgiref
            try:
                logger.info("Intentando shutdown final para servidor wsgiref...")
                http_server_global_ref.shutdown()
            except Exception as e_shutdown_final:
                 logger.error(f"Error en el shutdown final del servidor wsgiref: {e_shutdown_final}")
        
        # La conexión del hilo principal ya debería estar cerrada por el signal_handler o si el server terminó.
        # Pero como doble chequeo:
        if db_connector_instance:
            db_connector_instance.cerrar_conexion_hilo_actual()
        
        logging.shutdown() # Limpiar todos los handlers de logging al final del todo

if __name__ == "__main__":
    start_callback_server_main()