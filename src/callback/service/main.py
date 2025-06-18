# SAM/src/callback/service/main.py
"""
Servidor de callbacks optimizado para SAM - Recibe callbacks de Automation Anywhere A360.

Este script implementa un servidor WSGI que escucha callbacks de A360 y actualiza la base de datos SAM.
Incluye manejo robusto de errores, validación de payloads y logging detallado.
"""

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

from dotenv import load_dotenv

try:
    from waitress import serve

    WAITRESS_DISPONIBLE = True
except ImportError:
    WAITRESS_DISPONIBLE = False


# --- Configuración de constantes ---
@dataclass
class ConfiguracionServidorCallback:
    """Clase de datos para la configuración del servidor de callbacks."""

    host: str = "0.0.0.0"
    puerto: int = 8008
    hilos: int = 8  # threads
    tiempo_espera_canal: int = 120  # timeout (para waitress channel_timeout)
    intervalo_limpieza_waitress: int = 30  # cleanup_interval (para waitress)
    longitud_max_contenido: int = 1024 * 1024  # Límite de 1MB
    log_payload_max_caracteres: int = 1000


@dataclass
class ConfiguracionLog:
    """Clase de datos para la configuración de logging."""

    directorio: str = "C:/RPA/Logs/SAM"
    nombre_archivo: str = "sam_callback_server.log"  # filename
    nivel: str = "INFO"  # level
    num_respaldos: int = 7  # backup_count
    formato: str = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"  # format
    formato_fecha: str = "%Y-%m-%d %H:%M:%S"  # date_format


# --- Carga optimizada de configuración ---
def cargar_configuracion_entorno() -> None:
    """Carga la configuración del entorno con manejo de errores adecuado."""
    raiz_proyecto_sam = Path(__file__).resolve().parent.parent.parent
    ruta_env: Path = raiz_proyecto_sam / ".env"

    if ruta_env.exists():
        print(f"SERVIDOR_CALLBACK: Cargando .env desde {ruta_env}", file=sys.stderr)
        load_dotenv(dotenv_path=ruta_env, override=True)
    else:
        print(f"SERVIDOR_CALLBACK: No se encontró .env en {ruta_env}, usando defaults del sistema", file=sys.stderr)
        load_dotenv()


# Cargar configuración temprano
cargar_configuracion_entorno()

# Imports que dependen de la configuración
try:
    from common.database.sql_client import DatabaseConnector
    from common.utils.config_manager import ConfigManager
    from common.utils.logging_setup import RobustTimedRotatingFileHandler
except ImportError as e:
    print(f"CRITICO: No se pueden importar los módulos requeridos: {e}", file=sys.stderr)
    sys.exit(1)


# --- Clase principal del servidor ---
class ServidorCallback:  # CallbackServer
    """Clase principal del servidor de callbacks con gestión de recursos mejorada."""

    def __init__(self):
        self.config = ConfiguracionServidorCallback()
        self.config_log = ConfiguracionLog()
        self.logger = self._configurar_logging()  # _setup_logging
        self.conector_bd: Optional[DatabaseConnector] = None  # db_connector
        self.instancia_servidor = None  # server_instance
        self._evento_parada = threading.Event()  # _shutdown_event
        self._estadisticas = {  # _stats
            "solicitudes_recibidas": 0,
            "solicitudes_procesadas": 0,
            "solicitudes_fallidas": 0,
            "tiempo_inicio": time.time(),
        }

        # Cargar configuración
        self._cargar_configuracion()  # _load_configuration

        # Inicializar conexión a base de datos (no crítico para el inicio del servidor)
        bd_inicializada = self._inicializar_objeto_conector_bd()  # db_initialized, _initialize_database
        if not bd_inicializada:
            self.logger.warning("Base de datos no inicializada al arrancar - se intentará conexión en la primera solicitud")

        # Configurar manejadores de señales
        self._configurar_signal_handlers()  # _setup_signal_handlers

    def _configurar_logging(self) -> logging.Logger:  # _setup_logging
        """Configura un logging dedicado para el servidor de callbacks."""
        nombre_logger = "SAMServidorCallback"  # logger_name
        logger = logging.getLogger(nombre_logger)

        if logger.hasHandlers():  # Si ya tiene manejadores, no añadir más
            return logger

        logger.setLevel(getattr(logging, self.config_log.nivel.upper(), logging.INFO))
        logger.propagate = False  # No propagar al logger raíz

        # Crear directorio de log si no existe
        log_dir = Path(self.config_log.directorio)  # log_dir
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e_os:
            print(f"ERROR CRITICO: No se pudo crear el directorio de logs '{log_dir}': {e_os}", file=sys.stderr)

        log_file_path: Path = log_dir / self.config_log.nombre_archivo  # log_file_path

        formateador = logging.Formatter(  # formatter
            fmt=self.config_log.formato,
            datefmt=self.config_log.formato_fecha,
        )

        try:
            # Manejador de archivo
            file_handler = RobustTimedRotatingFileHandler(  # file_handler
                str(log_file_path),
                when="midnight",
                interval=1,
                backupCount=self.config_log.num_respaldos,
                encoding="utf-8",
                max_retries=3,
                retry_delay=0.5,
            )
            file_handler.setFormatter(formateador)
            logger.addHandler(file_handler)

        except Exception as e:
            # Si falla el manejador de archivo, al menos el de consola (añadido después) debería funcionar.
            print(f"ERROR: No se pudo crear el manejador de archivo para '{log_file_path}': {e}", file=sys.stderr)

        # Manejador de consola (siempre añadir)
        console_handler = logging.StreamHandler(sys.stdout)  # console_handler
        console_handler.setFormatter(formateador)
        logger.addHandler(console_handler)

        return logger

    def _cargar_configuracion(self):  # _load_configuration
        """Carga la configuración desde ConfigManager con valores por defecto."""
        try:
            # Cargar configuración del servidor de callbacks
            cb_config = ConfigManager.get_callback_server_config()  # cb_config
            self.config.host = cb_config.get("host", self.config.host)
            self.config.puerto = cb_config.get("port", self.config.puerto)
            self.config.hilos = cb_config.get("threads", self.config.hilos)

            # Cargar configuración de log (usando ConfigManager)
            cfg_log_global = ConfigManager.get_log_config()  # log_config
            self.config_log.directorio = cfg_log_global.get("directory", self.config_log.directorio)
            self.config_log.nombre_archivo = cfg_log_global.get("callback_log_filename", self.config_log.nombre_archivo)
            self.config_log.nivel = cfg_log_global.get("level_str", self.config_log.nivel)
            self.config_log.formato = cfg_log_global.get("format", self.config_log.formato)
            self.config_log.formato_fecha = cfg_log_global.get("datefmt", self.config_log.formato_fecha)
            self.config_log.num_respaldos = cfg_log_global.get("backupCount", self.config_log.num_respaldos)

            # Re-configurar el logger si los valores de config_log cambiaron
            self.logger = self._configurar_logging()

            self.logger.info("Configuración cargada/recargada exitosamente")

        except Exception as e:
            self.logger.error(f"Error cargando configuración, usando valores por defecto: {e}", exc_info=True)

    def _inicializar_objeto_conector_bd_old(self) -> bool:  # Renombrado para claridad
        """
        Intenta crear o recrear la instancia de DatabaseConnector.

        Retorna True si el objeto fue creado, False si la creación del objeto falló.
        No garantiza que la conexión esté viva, solo que el objeto existe.
        """
        max_reintentos = 2
        retraso_reintento_seg = 2

        # Si ya existe un conector, intentar cerrarlo antes de crear uno nuevo.
        if self.conector_bd and hasattr(self.conector_bd, "cerrar_conexion_hilo_actual"):
            try:
                self.conector_bd.cerrar_conexion_hilo_actual()
            except Exception as e_close:
                self.logger.debug(f"Error menor al cerrar conector BD previo: {e_close}")
        self.conector_bd = None  # Asegurar que empezamos desde None para recrear

        for intento in range(1, max_reintentos + 1):
            try:
                cfg_sql = ConfigManager.get_sql_server_config("SQL_SAM")
                nombre_bd_sam = cfg_sql.get("database")

                if not nombre_bd_sam:
                    self.logger.error("Config BD: 'database' (SQL_SAM_DB_NAME) no encontrada.")
                    return False  # No se puede crear sin nombre de BD
                if not all(cfg_sql.get(k) for k in ["server", "uid", "pwd"]):
                    self.logger.error("Config BD incompleta (falta server, uid o pwd para SQL_SAM).")
                    return False

                self.conector_bd = DatabaseConnector(  # Crea la nueva instancia
                    servidor=cfg_sql["server"], base_datos=nombre_bd_sam, usuario=cfg_sql["uid"], contrasena=cfg_sql["pwd"]
                )
                self.logger.info(f"Objeto DatabaseConnector (re)creado exitosamente (intento {intento}).")
                return True  # Objeto creado
            except Exception as e_init_obj:
                self.logger.warning(f"Intento {intento}/{max_reintentos} de creación de objeto DatabaseConnector fallido: {e_init_obj}")
                if intento < max_reintentos:
                    time.sleep(retraso_reintento_seg)
                else:
                    self.logger.error("Falló la creación del objeto DatabaseConnector después de todos los reintentos.")
                    self.conector_bd = None
                    return False
        return False  # No debería llegar si el bucle se completa

    @contextmanager
    def _obtener_conexion_bd_old(self):
        """
        Gestor de contexto que asegura que self.conector_bd exista y tenga una conexión verificada.

        Lanza ConnectionError si no se puede establecer una conexión válida.
        """
        # Paso 1: Asegurar que el objeto self.conector_bd exista.
        if not self.conector_bd:
            self.logger.info("Objeto conector BD es None. Intentando creación inicial del objeto.")
            if not self._inicializar_objeto_conector_bd():
                self.logger.error("Fallo crítico: No se pudo crear el objeto DatabaseConnector.")
                raise ConnectionError("Fallo crítico al crear el objeto DatabaseConnector.")

        # Paso 2: Verificar la conexión del objeto existente. Reintentar si falla.
        # Permitimos un número limitado de reintentos de verificación/recreación aquí.
        max_intentos_verificacion = 2
        for intento_verif in range(1, max_intentos_verificacion + 1):
            try:
                if self.conector_bd and self.conector_bd.verificar_conexion():
                    self.logger.debug("Conexión BD verificada exitosamente en _obtener_conexion_bd.")
                    yield self.conector_bd  # Conexión buena, ceder el conector.
                    return  # Salir del generador y del bucle.
                else:
                    self.logger.warning(f"Verificación de conexión BD falló para el hilo actual (intento {intento_verif}). Intentando conectar...")
                    try:
                        self.conector_bd.conectar_base_datos()  # Conectar para el hilo actual usando el objeto existente
                        # Si tiene éxito, el siguiente loop de verificación debería pasar.
                    except Exception as e_conn_thread:
                        self.logger.error(f"Error al intentar conectar para el hilo actual: {e_conn_thread}", exc_info=True)
                        # Si falla la conexión aquí, podría ser necesario recrear el objeto o fallar la solicitud.
            except Exception as e_verif_reint:
                self.logger.error(f"Excepción durante intento {intento_verif} de conexión/verificación BD: {e_verif_reint}", exc_info=True)
                # Si hay una excepción, también es una falla. Intentar recrear el objeto por si acaso.
                if not self._inicializar_objeto_conector_bd():
                    msg_error = "Fallo crítico al recrear objeto DB tras excepción en verificación."
                    self.logger.error(msg_error)
                    raise ConnectionError(msg_error) from e_verif_reint

            if intento_verif < max_intentos_verificacion:
                self.logger.info("Pausa antes del siguiente intento de verificación/recreación de conexión BD.")
                time.sleep(1 + intento_verif)  # Pequeña pausa incremental

        # Si el bucle termina, todos los intentos de obtener una conexión verificada fallaron.
        msg_final_fallo = "No se pudo obtener una conexión de BD válida después de múltiples intentos y recreaciones."
        self.logger.error(msg_final_fallo)
        raise ConnectionError(msg_final_fallo) from None

    # === PASO 1: DIAGNÓSTICO DETALLADO ===
    # 1.1 Añadir logging más específico en _inicializar_objeto_conector_bd
    def _inicializar_objeto_conector_bd(self) -> bool:
        """
        Intenta crear o recrear la instancia de DatabaseConnector.

        VERSIÓN CON DIAGNÓSTICO MEJORADO.
        """
        max_reintentos = 2
        retraso_reintento_seg = 2

        # Si ya existe un conector, intentar cerrarlo antes de crear uno nuevo.
        if self.conector_bd and hasattr(self.conector_bd, "cerrar_conexion_hilo_actual"):
            try:
                self.conector_bd.cerrar_conexion_hilo_actual()
            except Exception as e_close:
                self.logger.debug(f"Error menor al cerrar conector BD previo: {e_close}")
        self.conector_bd = None

        for intento in range(1, max_reintentos + 1):
            try:
                cfg_sql = ConfigManager.get_sql_server_config("SQL_SAM")
                nombre_bd_sam = cfg_sql.get("database")

                # DIAGNÓSTICO DETALLADO DE CONFIGURACIÓN
                self.logger.debug(f"=== DIAGNÓSTICO BD (Intento {intento}) ===")
                self.logger.debug(f"Server: {cfg_sql.get('server', 'NO_CONFIG')}")
                self.logger.debug(f"Database: {nombre_bd_sam or 'NO_CONFIG'}")
                self.logger.debug(f"User: {cfg_sql.get('uid', 'NO_CONFIG')}")
                self.logger.debug(f"Password configured: {'YES' if cfg_sql.get('pwd') else 'NO'}")

                if not nombre_bd_sam:
                    self.logger.error("Config BD: 'database' (SQL_SAM_DB_NAME) no encontrada.")
                    return False
                if not all(cfg_sql.get(k) for k in ["server", "uid", "pwd"]):
                    self.logger.error("Config BD incompleta (falta server, uid o pwd para SQL_SAM).")
                    return False

                self.conector_bd = DatabaseConnector(
                    servidor=cfg_sql["server"], base_datos=nombre_bd_sam, usuario=cfg_sql["uid"], contrasena=cfg_sql["pwd"]
                )

                # VERIFICACIÓN INMEDIATA TRAS CREACIÓN
                self.logger.debug("Objeto DatabaseConnector creado. Verificando conexión inmediatamente...")
                try:
                    # Intentar establecer la conexión. conectar_base_datos()
                    # guardará la conexión en el hilo local y la devolverá,
                    # o levantará una excepción si falla.
                    connection = self.conector_bd.conectar_base_datos()  # <--- AÑADIR ESTA LLAMADA
                    if connection:  # Si conectar_base_datos() es exitoso y devuelve la conexión
                        self.logger.debug(f"Conexión BD establecida y verificada exitosamente tras creación (intento {intento})")
                        # Opcionalmente, podrías incluso llamar a self.conector_bd.verificar_conexion() aquí si quieres la doble verificación,
                        # pero el éxito de conectar_base_datos() ya es una buena señal.
                        return True
                    else:
                        # Este caso es menos probable si conectar_base_datos está bien implementado
                        # (debería levantar excepción en fallo, no devolver None silenciosamente)
                        self.logger.warning(f"Conexión a BD no establecida tras creación (intento {intento}), conectar_base_datos devolvió None.")

                except pyodbc.Error as e_db_connect:  # type: ignore # Capturar específicamente errores de pyodbc  # noqa: F821
                    self.logger.error(f"Error de PyODBC al intentar conectar inmediatamente: {e_db_connect}", exc_info=True)
                except Exception as e_connect_inmediata:  # Capturar otras excepciones
                    self.logger.error(f"Excepción al intentar conectar inmediatamente: {e_connect_inmediata}", exc_info=True)

            except Exception as e_init_obj:
                self.logger.warning(
                    f"Intento {intento}/{max_reintentos} de creación de objeto DatabaseConnector fallido: {e_init_obj}", exc_info=True
                )

            if intento < max_reintentos:
                self.logger.info(f"Esperando {retraso_reintento_seg}s antes del siguiente intento...")
                time.sleep(retraso_reintento_seg)
            else:
                self.logger.error("Falló la creación/verificación del objeto DatabaseConnector después de todos los reintentos.")
                self.conector_bd = None
                return False
        return False

    # === PASO 2: MEJORAR EL MÉTODO _obtener_conexion_bd ===
    @contextmanager
    def _obtener_conexion_bd(self):
        """VERSIÓN MEJORADA con más diagnóstico y reintentos inteligentes."""
        # Paso 1: Asegurar que el objeto self.conector_bd exista.
        if not self.conector_bd:
            self.logger.debug("bjeto conector BD es None. Intentando creación inicial del objeto.")
            if not self._inicializar_objeto_conector_bd():
                self.logger.error("CRÍTICO: No se pudo crear el objeto DatabaseConnector.")
                raise ConnectionError("Fallo crítico al crear el objeto DatabaseConnector.")

        # Paso 2: Verificar la conexión con diagnóstico mejorado
        max_intentos_verificacion = 3  # Aumentado de 2 a 3
        for intento_verif in range(1, max_intentos_verificacion + 1):
            try:
                self.logger.debug(f"Verificando conexión BD (intento {intento_verif}/{max_intentos_verificacion})")

                # DIAGNÓSTICO: Verificar si el objeto existe y tiene los métodos esperados
                if not self.conector_bd:
                    self.logger.error("self.conector_bd es None durante verificación")
                    raise ConnectionError("Conector BD es None")

                if not hasattr(self.conector_bd, "verificar_conexion"):
                    self.logger.error("El objeto conector_bd no tiene método 'verificar_conexion'")
                    raise ConnectionError("Objeto DatabaseConnector inválido")

                # Intentar verificación con timeout si es posible
                conexion_ok = self.conector_bd.verificar_conexion()

                if conexion_ok:
                    self.logger.debug(f"Conexión BD verificada exitosamente (intento {intento_verif})")
                    yield self.conector_bd
                    return
                else:
                    self.logger.warning(f"Verificación de conexión BD falló (intento {intento_verif}/{max_intentos_verificacion})")

                    # DIAGNÓSTICO ADICIONAL: Intentar obtener más información del error
                    try:
                        # Si tu DatabaseConnector tiene un método para obtener el último error
                        if hasattr(self.conector_bd, "ultimo_error"):
                            self.logger.error(f"Último error de BD: {self.conector_bd.ultimo_error}")

                        # Intentar una operación simple para diagnóstico
                        if hasattr(self.conector_bd, "obtener_conexion"):
                            conn = self.conector_bd.obtener_conexion()
                            if conn:
                                self.logger.debug("obtener_conexion() retornó un objeto de conexión")
                                # Intentar un query simple
                                cursor = conn.cursor()
                                cursor.execute("SELECT 1")
                                resultado = cursor.fetchone()
                                cursor.close()
                                self.logger.debug(f"Query de prueba exitoso: {resultado}")
                            else:
                                self.logger.error("obtener_conexion() retornó None")
                    except Exception as e_diag:
                        self.logger.error(f"Error durante diagnóstico adicional: {e_diag}")

                    # Recrear el objeto si no es el último intento
                    if intento_verif < max_intentos_verificacion:
                        self.logger.info("Recreando objeto DatabaseConnector...")
                        if not self._inicializar_objeto_conector_bd():
                            msg_error = "Fallo crítico al recrear objeto DB tras falla de verificación."
                            self.logger.error(msg_error)
                            raise ConnectionError(msg_error) from None

            except Exception as e_verif_reint:
                self.logger.error(f"Excepción durante intento {intento_verif} de conexión/verificación BD: {e_verif_reint}", exc_info=True)

                # Solo recrear si no es el último intento
                if intento_verif < max_intentos_verificacion:
                    self.logger.info("Recreando objeto tras excepción...")
                    if not self._inicializar_objeto_conector_bd():
                        msg_error = "Fallo crítico al recrear objeto DB tras excepción."
                        self.logger.error(msg_error)
                        raise ConnectionError(msg_error) from None

            # Pausa incremental entre intentos
            if intento_verif < max_intentos_verificacion:
                pausa = 2 + intento_verif  # 3s, 4s, etc.
                self.logger.info(f"Pausa de {pausa}s antes del siguiente intento...")
                time.sleep(pausa)

        # Si llegamos aquí, todos los intentos fallaron
        msg_final_fallo = "CRÍTICO: No se pudo obtener una conexión de BD válida después de múltiples intentos exhaustivos."
        self.logger.error(msg_final_fallo)
        raise ConnectionError(msg_final_fallo) from None

    # === PASO 3: MÉTODO DE DIAGNÓSTICO INDEPENDIENTE ===
    def diagnosticar_conexion_bd(self) -> Dict[str, Any]:
        """Método independiente para diagnosticar problemas de conexión a BD."""
        diagnostico = {
            "config_encontrada": False,
            "config_completa": False,
            "objeto_creado": False,
            "conexion_verificada": False,
            "errores": [],
            "config_details": {},
        }

        try:
            # 1. Verificar configuración
            cfg_sql = ConfigManager.get_sql_server_config("SQL_SAM")
            diagnostico["config_encontrada"] = True
            diagnostico["config_details"] = {
                "server": cfg_sql.get("server", "NO_CONFIG"),
                "database": cfg_sql.get("database", "NO_CONFIG"),
                "uid": cfg_sql.get("uid", "NO_CONFIG"),
                "pwd_configured": bool(cfg_sql.get("pwd")),
            }

            # 2. Verificar completitud de config
            if all(cfg_sql.get(k) for k in ["server", "database", "uid", "pwd"]):
                diagnostico["config_completa"] = True
            else:
                diagnostico["errores"].append("Configuración BD incompleta")

            # 3. Intentar crear objeto
            if diagnostico["config_completa"]:
                try:
                    conector_test = DatabaseConnector(
                        servidor=cfg_sql["server"],
                        base_datos=cfg_sql["database"],
                        usuario=cfg_sql["uid"],
                        contrasena=cfg_sql["pwd"],
                    )
                    diagnostico["objeto_creado"] = True

                    # 4. Intentar verificar conexión
                    if conector_test.verificar_conexion():
                        diagnostico["conexion_verificada"] = True
                    else:
                        diagnostico["errores"].append("Verificación de conexión falló")

                except Exception as e_obj:
                    diagnostico["errores"].append(f"Error creando objeto: {e_obj}")

        except Exception as e_config:
            diagnostico["errores"].append(f"Error obteniendo config: {e_config}")

        return diagnostico

    # === PASO 4: IMPLEMENTAR UN HEALTH CHECK ===
    def health_check_bd(self) -> bool:
        """Health check simple para la base de datos."""
        try:
            with self._obtener_conexion_bd() as bd:
                # Intentar una query muy simple
                if hasattr(bd, "ejecutar_query"):
                    resultado = bd.ejecutar_query("SELECT 1 as test")
                    return resultado is not None
                else:
                    return bd.verificar_conexion()
        except Exception as e:
            self.logger.error(f"Health check BD falló: {e}")
            return False

    # === PASO 5: CONFIGURACIÓN DE RECONEXIÓN AUTOMÁTICA ===
    def _configurar_reconexion_automatica(self):
        """Configura un hilo de reconexión automática en background."""

        def tarea_reconexion():
            while not self._evento_parada.is_set():
                try:
                    if not self.health_check_bd():
                        self.logger.warning("Health check BD falló, intentando reconectar...")
                        self._inicializar_objeto_conector_bd()

                    # Esperar 30 segundos antes del siguiente check
                    self._evento_parada.wait(30)

                except Exception as e:
                    self.logger.error(f"Error en tarea de reconexión: {e}")
                    self._evento_parada.wait(60)  # Esperar más tiempo si hay error

        hilo_reconexion = threading.Thread(target=tarea_reconexion, daemon=True)
        hilo_reconexion.start()
        self.logger.info("Hilo de reconexión automática iniciado")

    def _validar_payload_callback(self, datos: Dict[str, Any]) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """Valida el payload del callback y extrae los campos requeridos."""
        try:
            id_despliegue = datos.get("deploymentId")  # deployment_id
            estado = datos.get("status")  # status

            if id_despliegue is None:  # Chequear None explícitamente
                return False, "Campo requerido faltante o nulo: deploymentId", None, None

            if estado is None:  # Chequear None explícitamente
                return False, "Campo requerido faltante o nulo: status", None, None

            # Validación adicional
            if not isinstance(id_despliegue, str) or len(id_despliegue.strip()) == 0:
                return False, "deploymentId debe ser una cadena no vacía", None, None

            if not isinstance(estado, str) or len(estado.strip()) == 0:
                return False, "status debe ser una cadena no vacía", None, None

            return True, "Válido", id_despliegue.strip(), estado.strip()

        except AttributeError:  # Si 'datos' no es un diccionario (ej. None)
            return False, "Payload de callback inválido (no es un diccionario)", None, None
        except Exception as e:  # Otros errores inesperados durante la validación
            self.logger.error(f"Excepción inesperada durante _validar_payload_callback: {e}", exc_info=True)
            return False, f"Error de validación interno: {str(e)}", None, None

    def _procesar_callback(self, id_despliegue: str, estado: str, payload_crudo: str) -> Tuple[bool, str]:  # _process_callback, raw_payload
        """Procesa el callback con actualización en la base de datos."""
        try:
            with self._obtener_conexion_bd() as bd:  # db
                # Asumimos que bd es un DatabaseConnector válido aquí
                if bd is None:
                    self._estadisticas["solicitudes_fallidas"] += 1
                    self.logger.error("El conector de base de datos es None al intentar procesar el callback.")
                    return False, "Conector de base de datos no disponible."
                exito = bd.actualizar_ejecucion_desde_callback(id_despliegue, estado, payload_crudo)  # success
                if exito:
                    self._estadisticas["solicitudes_procesadas"] += 1
                    return True, "Callback procesado y BD actualizada exitosamente"
                else:
                    self._estadisticas["solicitudes_fallidas"] += 1
                    # El logger dentro de actualizar_ejecucion_desde_callback ya debería haber logueado el fallo.
                    return False, "Falló la actualización en la base de datos (ver logs de BD para detalles)"

        except ConnectionError as e_conn:  # Captura específica si _obtener_conexion_bd falla
            self._estadisticas["solicitudes_fallidas"] += 1
            self.logger.error(
                f"Error de conexión a BD procesando callback para {id_despliegue}: {e_conn}", exc_info=False
            )  # No incluir exc_info si ya se logueó antes
            return False, f"Error de conexión a BD: {str(e_conn)}"
        except Exception as e:  # Otros errores
            self._estadisticas["solicitudes_fallidas"] += 1
            self.logger.error(f"Error general procesando callback para {id_despliegue}: {e}", exc_info=True)
            return False, f"Error de procesamiento general: {str(e)}"

    def aplicacion_wsgi(self, entorno: Dict[str, Any], iniciar_respuesta):  # wsgi_application, environ, start_response
        """Aplicación WSGI con manejo de errores y validación mejorados."""
        self._estadisticas["solicitudes_recibidas"] += 1

        # Respuesta por defecto
        status = "200 OK"  # status
        cabeceras = [("Content-Type", "application/json; charset=utf-8")]  # headers
        response_data = {"estado": "OK", "mensaje": "Callback recibido y en procesamiento."}  # response_data

        try:
            metodo = entorno.get("REQUEST_METHOD", "GET")  # method
            ruta = entorno.get("PATH_INFO", "/")  # path
            direccion_remota = entorno.get("REMOTE_ADDR", "Desconocida")  # remote_addr

            self.logger.info(f"Solicitud entrante: {metodo} {ruta} desde {direccion_remota}")

            # Validación del método
            if metodo != "POST":
                status = "405 Method Not Allowed"
                cabeceras.append(("Allow", "POST"))
                response_data = {"estado": "ERROR", "mensaje": "Solo se permite el método POST."}
                self.logger.warning(f"Método no permitido recibido: {metodo} desde {direccion_remota} para {ruta}.")

            else:  # Método es POST
                # Validación de longitud de contenido
                try:
                    longitud_contenido = int(entorno.get("CONTENT_LENGTH", 0))  # content_length
                except (ValueError, TypeError):
                    longitud_contenido = 0
                    self.logger.warning(f"Content-Length inválido o ausente: {entorno.get('CONTENT_LENGTH')}")

                if longitud_contenido <= 0:
                    status = "400 Bad Request"
                    response_data = {"estado": "ERROR", "mensaje": "Cuerpo de la solicitud vacío o Content-Length inválido/ausente."}
                    self.logger.warning("Solicitud POST con cuerpo vacío o Content-Length problemático.")

                elif longitud_contenido > self.config.longitud_max_contenido:
                    status = "413 Payload Too Large"
                    response_data = {"estado": "ERROR", "mensaje": f"Payload demasiado grande (máximo {self.config.longitud_max_contenido} bytes)."}
                    self.logger.warning(f"Solicitud POST con payload demasiado grande: {longitud_contenido} bytes.")

                else:  # Payload con tamaño aceptable
                    # Leer y procesar payload
                    try:
                        bytes_cuerpo = entorno["wsgi.input"].read(longitud_contenido)  # body_bytes
                        try:
                            body_str = bytes_cuerpo.decode("utf-8")  # body_str
                        except UnicodeDecodeError as e_unicode:
                            self.logger.error(
                                f"Error de decodificación UTF-8 del payload: {e_unicode}. Bytes (primeros 200): {bytes_cuerpo[:200]}", exc_info=True
                            )
                            status = "400 Bad Request"
                            response_data = {"estado": "ERROR", "mensaje": "Codificación UTF-8 inválida en el cuerpo de la solicitud."}
                            # Salir del else anidado, ya que no podemos procesar más.
                            raise StopIteration()  # Usar una excepción para romper el flujo normal

                        # Loguear payload (truncado por seguridad)
                        vista_previa_payload = body_str[: self.config.log_payload_max_caracteres]  # payload_preview
                        if len(body_str) > self.config.log_payload_max_caracteres:
                            vista_previa_payload += "..."
                        self.logger.debug(f"Payload recibido: {vista_previa_payload}")

                        # Parsear JSON
                        try:
                            datos_payload = json.loads(body_str)  # payload_data
                        except json.JSONDecodeError as e_json:
                            self.logger.error(
                                f"Error de decodificación JSON del payload: {e_json}. Payload (str preview): {vista_previa_payload}", exc_info=True
                            )
                            status = "400 Bad Request"
                            response_data = {"estado": "ERROR", "mensaje": "Formato JSON inválido en el cuerpo de la solicitud."}
                            raise StopIteration()  # Romper flujo

                        # Validar payload parseado
                        es_valido, msg_validacion, deployment_id, callback_status = self._validar_payload_callback(
                            datos_payload
                        )  # is_valid, validation_msg, deployment_id, callback_status

                        if not es_valido:
                            status = "400 Bad Request"
                            response_data = {"estado": "ERROR", "mensaje": msg_validacion}
                            self.logger.warning(f"Payload de callback inválido: {msg_validacion}. Payload: {datos_payload}")
                        elif deployment_id is None or callback_status is None:
                            status = "400 Bad Request"
                            response_data = {"estado": "ERROR", "mensaje": "deploymentId o status no pueden ser None."}
                            self.logger.error(f"deploymentId o status son None tras validación. Payload: {datos_payload}")
                        else:
                            # Procesar callback (esta es la ruta de éxito principal)
                            self.logger.info(f"Procesando callback validado: DeploymentId='{deployment_id}', Status='{callback_status}'")
                            # RE-SERIALIZAR EL PAYLOAD A UN STRING COMPACTO ANTES DE GUARDARLO
                            payload_compacto = json.dumps(datos_payload, separators=(",", ":"))
                            exito_proceso, msg_proceso_final = self._procesar_callback(
                                deployment_id, callback_status, payload_compacto
                            )  # success, process_msg

                            if not exito_proceso:
                                status = "500 Internal Server Error"  # Podría ser 202 Accepted si el procesamiento es asíncrono y solo falló la BD
                                response_data = {"estado": "ERROR_PROCESAMIENTO", "mensaje": msg_proceso_final}
                                self.logger.error(f"Fallo en el procesamiento del callback para DeploymentId {deployment_id}: {msg_proceso_final}")
                            else:
                                # Si _procesar_callback fue exitoso, el estado_http 200 OK y mensaje por defecto son apropiados.
                                response_data = {"estado": "OK", "mensaje": "Callback procesado y registrado exitosamente."}
                                self.logger.info(f"Callback procesado y registrado exitosamente para DeploymentId: {deployment_id}")

                    except StopIteration:  # Para manejar las salidas tempranas por errores de decodificación/parseo
                        pass  # El estado_http y datos_respuesta ya están seteados.
                    except Exception as e_lectura_payload:
                        self.logger.error(f"Error leyendo o procesando el cuerpo del payload: {e_lectura_payload}", exc_info=True)
                        status = "500 Internal Server Error"
                        response_data = {"estado": "ERROR", "mensaje": "Error interno al procesar el cuerpo de la solicitud."}

        except Exception as e_general_wsgi:  # Error muy general en la app WSGI
            status = "500 Internal Server Error"
            response_data = {"estado": "ERROR", "mensaje": "Ocurrió un error interno inesperado en la aplicación de callbacks."}
            self.logger.critical(f"Excepción crítica no manejada en aplicacion_wsgi: {e_general_wsgi}", exc_info=True)

        # Preparar respuesta final
        try:
            cuerpo_respuesta_bytes = json.dumps(response_data, ensure_ascii=False).encode("utf-8")  # response_body_bytes
        except Exception as e_json_dump:
            self.logger.critical(f"Error al convertir la respuesta a JSON: {e_json_dump}. Respuesta original: {response_data}", exc_info=True)
            status = "500 Internal Server Error"
            error_response = {"estado": "ERROR_SERVIDOR", "mensaje": "Error generando respuesta JSON."}
            cuerpo_respuesta_bytes = json.dumps(error_response, ensure_ascii=False).encode("utf-8")

        cabeceras.append(("Content-Length", str(len(cuerpo_respuesta_bytes))))

        iniciar_respuesta(status, cabeceras)
        return [cuerpo_respuesta_bytes]

    def _determinar_direccion_enlace(self) -> str:  # _determine_bind_address
        """Determina la dirección de enlace efectiva con validación."""
        host_cfg = self.config.host  # host_configurado
        if host_cfg and host_cfg.strip() and host_cfg not in ["0.0.0.0", "*"]:
            host_efectivo = host_cfg.strip()  # effective_host
            self.logger.info(f"Usando host configurado para enlazar: '{host_efectivo}'")

            # Validar si el host es potencialmente resoluble (no garantiza que se pueda enlazar)
            try:
                socket.getaddrinfo(host_efectivo, None)
            except socket.gaierror as e:
                self.logger.warning(f"El host configurado '{host_efectivo}' podría no ser resoluble o válido para enlazar: {e}")

            return host_efectivo
        else:
            self.logger.info("Enlazando a '0.0.0.0' para escuchar en todas las interfaces de red disponibles.")
            return "0.0.0.0"

    def _configurar_signal_handlers(self) -> None:  # _setup_signal_handlers
        """Configura manejadores de señales para una parada elegante."""

        def manejador_signal_interno(signum, frame):  # signal_handler_internal
            try:
                nombre_signal = signal.Signals(signum).name  # signal_name
            except (AttributeError, ValueError):  # Para casos donde Signals(signum) no sea válido o .name no exista
                nombre_signal = str(signum)
            self.logger.warning(f"Recibida señal de parada '{nombre_signal}' (PID: {os.getpid()}). Iniciando parada del servidor...")
            self._evento_parada.set()
            # Si estamos usando wsgiref.simple_server con handle_request en un bucle,
            # necesitamos una forma de interrumpir ese bucle.
            # Para waitress, la propia librería maneja la señal y detiene el `serve()`.
            if not WAITRESS_DISPONIBLE and self.instancia_servidor:
                # Esto es un intento, pero puede no ser suficiente para un shutdown inmediato de handle_request
                # La mejor forma es que el bucle principal de handle_request chequee self._evento_parada.
                self.logger.info(
                    "Intentando cerrar instancia de servidor wsgiref (puede requerir una solicitud final para desbloquear handle_request)..."
                )
                # self.instancia_servidor.shutdown() # shutdown() no funciona bien si está en handle_request

        # Intentar registrar señales comunes
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, manejador_signal_interno)
            except (OSError, ValueError, AttributeError) as e:  # Algunos sistemas/contextos no permiten todas las señales
                self.logger.warning(f"No se pudo registrar el manejador para la señal {sig}: {e}")

        if hasattr(signal, "SIGBREAK"):  # SIGBREAK es específico de Windows
            try:
                signal.signal(signal.SIGBREAK, manejador_signal_interno)
            except (OSError, ValueError, AttributeError) as e:
                self.logger.warning(f"No se pudo registrar el manejador para la señal SIGBREAK: {e}")

    def _log_estadisticas_servidor(self) -> None:  # _log_server_stats
        """Loguea las estadísticas del servidor."""
        tiempo_activo_total = time.time() - self._estadisticas["tiempo_inicio"]  # total_uptime
        self.logger.info("=" * 70)
        self.logger.info("Estadísticas Finales del Servidor de Callbacks:")
        self.logger.info(f"  Tiempo activo total: {tiempo_activo_total:.2f} segundos")
        self.logger.info(f"  Solicitudes totales recibidas: {self._estadisticas['solicitudes_recibidas']}")
        self.logger.info(f"  Solicitudes procesadas exitosamente: {self._estadisticas['solicitudes_procesadas']}")
        self.logger.info(f"  Solicitudes fallidas (procesamiento/BD): {self._estadisticas['solicitudes_fallidas']}")
        if self._estadisticas["solicitudes_recibidas"] > 0:
            tasa_exito_proc = (
                self._estadisticas["solicitudes_procesadas"] / self._estadisticas["solicitudes_recibidas"]
            ) * 100  # processing_success_rate
            self.logger.info(f"  Tasa de éxito de procesamiento: {tasa_exito_proc:.2f}%")
        self.logger.info("=" * 70)

    def iniciar(self) -> None:  # start
        """Inicia el servidor de callbacks."""
        host_efectivo = self._determinar_direccion_enlace()  # effective_host

        # Loguear información de inicio
        self.logger.info("=" * 80)
        self.logger.info(f" Iniciando Servidor de Callbacks SAM (PID: {os.getpid()})")
        self.logger.info(f" Escuchando en: http://{host_efectivo}:{self.config.puerto}")
        self.logger.info(
            f" Usando servidor: {'Waitress (recomendado para producción)' if WAITRESS_DISPONIBLE else 'wsgiref.simple_server (solo para desarrollo)'}"
        )
        if WAITRESS_DISPONIBLE:
            self.logger.info(f" Hilos configurados para Waitress: {self.config.hilos}")

        # Obtener URL de callback de la configuración
        try:
            cfg_aa = ConfigManager.get_aa_config()  # aa_config
            url_callback_publica = cfg_aa.get("url_callback", "NO CONFIGURADA EN .ENV")  # public_callback_url
            self.logger.info(f" URL pública esperada para callbacks de A360 (desde config): {url_callback_publica}")
        except Exception as e_cfg_aa:
            self.logger.warning(f"No se pudo obtener la URL de callback desde la configuración de AA: {e_cfg_aa}")

        self.logger.info("=" * 80)

        servidor_termino_correctamente = False  # server_terminated_correctly

        try:
            if WAITRESS_DISPONIBLE:
                # Usar Waitress para producción
                serve(
                    self.aplicacion_wsgi,
                    host=host_efectivo,
                    port=self.config.puerto,
                    threads=self.config.hilos,
                    channel_timeout=self.config.tiempo_espera_canal,
                    cleanup_interval=self.config.intervalo_limpieza_waitress,
                )
                # Si serve() retorna, es porque fue detenido (usualmente por una señal)
                servidor_termino_correctamente = True
            else:
                # Fallback a wsgiref para desarrollo
                self.logger.warning("Waitress no está instalado. Usando wsgiref.simple_server (NO RECOMENDADO PARA PRODUCCIÓN).")
                self.logger.warning("Para un entorno de producción, por favor instale Waitress: pip install waitress")

                self.instancia_servidor = make_server(host_efectivo, self.config.puerto, self.aplicacion_wsgi)
                self.logger.info(f"Servidor wsgiref (desarrollo) escuchando en http://{host_efectivo}:{self.config.puerto}")

                # Bucle para manejar solicitudes y permitir parada elegante con wsgiref
                while not self._evento_parada.is_set():
                    # handle_request() es bloqueante por una solicitud. Necesitamos un timeout
                    # o una forma de interrumpirlo. Una solución simple es un timeout corto.
                    # Sin embargo, handle_request no tiene un timeout directo.
                    # server.serve_forever() es más común pero más difícil de parar limpiamente sin hilos.
                    # Para este ejemplo, si no usamos waitress, el cierre podría no ser tan elegante.
                    # Una forma más robusta con wsgiref sería usar server_forever en un hilo y llamar a shutdown desde otro.
                    # Aquí, hacemos un bucle que podría ser menos eficiente pero más simple de parar.
                    self.instancia_servidor.timeout = 0.5  # Poner un timeout al socket del servidor
                    try:
                        self.instancia_servidor.handle_request()  # Manejar una solicitud
                    except socket.timeout:
                        continue  # Continuar el bucle si es solo un timeout
                    except Exception as e_handle:
                        self.logger.error(f"Error en wsgiref handle_request: {e_handle}")
                        break  # Salir del bucle en otros errores

                servidor_termino_correctamente = True  # Asumimos que si sale del bucle es por _evento_parada

        except OSError as e_os:  # ej. puerto en uso
            self.logger.critical(
                f"Error de OSError al intentar iniciar el servidor (la dirección '{host_efectivo}:{self.config.puerto}' podría estar en uso): {e_os}",
                exc_info=True,
            )
        except KeyboardInterrupt:  # Capturar Ctrl+C
            self.logger.info("KeyboardInterrupt (Ctrl+C) recibido. Parando el servidor de Callbacks...")
            self._evento_parada.set()  # Asegurar que el evento de parada esté activo
            servidor_termino_correctamente = True
        except SystemExit:  # Capturar SystemExit si el manejador de señales lo llama
            self.logger.info("SystemExit capturado, el servidor de callbacks está finalizando.")
            servidor_termino_correctamente = True
        except Exception as e_general_servidor:  # Cualquier otra excepción al iniciar/correr el servidor
            self.logger.critical(f"Error fatal durante la ejecución del servidor de Callbacks: {e_general_servidor}", exc_info=True)
        finally:
            self._limpiar_recursos_final(servidor_termino_correctamente)  # _cleanup_final

    def _limpiar_recursos_final(self, termino_limpiamente: bool = True) -> None:  # _cleanup_final, clean_shutdown
        """Limpia recursos al finalizar el servidor."""
        if termino_limpiamente:
            self.logger.info("Servidor de Callbacks SAM finalizando operaciones limpiamente.")
        else:
            self.logger.warning("Servidor de Callbacks SAM finalizando de forma inesperada o no pudo iniciarse.")

        # Loguear estadísticas finales
        self._log_estadisticas_servidor()

        # Parar la instancia del servidor wsgiref si existe y está activa
        if self.instancia_servidor:
            self.logger.info("Intentando cerrar la instancia del servidor wsgiref...")
            try:
                # Para wsgiref, cerrar el socket es una forma de intentar detenerlo si está en un bucle.
                if hasattr(self.instancia_servidor, "socket") and self.instancia_servidor.socket:
                    self.instancia_servidor.socket.close()
                if hasattr(self.instancia_servidor, "server_close"):
                    self.instancia_servidor.server_close()
                self.logger.info("Instancia del servidor wsgiref cerrada (o intento realizado).")
            except Exception as e_shutdown_wsgiref:
                self.logger.error(f"Error durante el cierre del servidor wsgiref: {e_shutdown_wsgiref}", exc_info=True)

        # Cerrar conexión a base de datos
        if self.conector_bd:
            self.logger.info("Cerrando conexión a la base de datos del servidor de Callbacks...")
            try:
                self.conector_bd.cerrar_conexion_hilo_actual()  # Cierra la del hilo principal
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


def start_callback_server_main():  # main_entry_point
    """Punto de entrada principal para iniciar el servidor."""
    servidor_app = None
    try:
        servidor_app = ServidorCallback()
        servidor_app.iniciar()
    except Exception as e_inicio_fatal:
        # Este log podría no funcionar si el logger falló en inicializarse.
        # Usar print para asegurar visibilidad del error crítico.
        mensaje_error = f"CRITICO: Falló el inicio del servidor de callbacks de forma fatal: {e_inicio_fatal}"
        print(mensaje_error, file=sys.stderr)
        # Intentar loguear también, por si acaso
        if servidor_app and servidor_app.logger:
            servidor_app.logger.critical(mensaje_error, exc_info=True)
        else:  # Logger no disponible, usar logging básico si es posible
            logging.critical(mensaje_error, exc_info=True)
        sys.exit(1)  # Salir con código de error


if __name__ == "__main__":
    # Esto permite ejecutar el servidor directamente con: python lanzador/service/callback_server.py
    # (asumiendo que SAM_PROJECT_ROOT está en PYTHONPATH o se ejecuta desde la raíz con -m)
    start_callback_server_main()
