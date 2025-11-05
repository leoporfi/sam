# sam/web/run_web.py
"""
Punto de entrada único del servicio Web (Servidor Uvicorn).
"""

from __future__ import annotations

import logging
import signal
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn

# --- Añadimos src al path para ejecución directa ---
if __name__ == "__main__":
    src_path = str(Path(__file__).resolve().parent.parent.parent)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

from sam.common.config_loader import ConfigLoader
from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector
from sam.common.logging_setup import setup_logging
from sam.web.main import create_app

# --- Globales del Servicio ---
_service_name = "web"
_shutdown_initiated = False
_server_instance: Optional[uvicorn.Server] = None

# --- Dependencias Globales ---
_db_connector: Optional[DatabaseConnector] = None


# ---------- Gestión de Cierre Ordenado (Graceful Shutdown) ----------


def _graceful_shutdown(signum: int, frame: Any) -> None:
    """Manejador de señales para un cierre ordenado."""
    global _shutdown_initiated
    if _shutdown_initiated:
        logging.warning("Señal de cierre duplicada recibida. Ya se está deteniendo.")
        return
    _shutdown_initiated = True
    logging.info(f"Señal de parada recibida (Señal: {signum}). Iniciando cierre ordenado...")

    if _server_instance:
        _server_instance.should_exit = True
    else:
        sys.exit(0)


def _setup_signals() -> None:
    """Configura los manejadores de señales para Windows y Unix."""
    if sys.platform == "win32":
        logging.info("Plataforma Windows detectada. Registrando SIGINT y SIGBREAK.")
        signal.signal(signal.SIGINT, _graceful_shutdown)
        try:
            signal.signal(signal.SIGBREAK, _graceful_shutdown)
        except AttributeError:
            logging.warning("signal.SIGBREAK no está disponible.")
    else:
        logging.info("Plataforma No-Windows detectada. Registrando SIGINT y SIGTERM.")
        signal.signal(signal.SIGINT, _graceful_shutdown)
        signal.signal(signal.SIGTERM, _graceful_shutdown)


# ---------- Lógica del Servicio ----------


def _setup_dependencies() -> Dict[str, Any]:
    """Crea y retorna las dependencias específicas del servicio (la BD)."""
    global _db_connector

    logging.info("Creando dependencia DatabaseConnector...")

    cfg_sql_sam = ConfigManager.get_sql_server_config("SQL_SAM")
    _db_connector = DatabaseConnector(
        servidor=cfg_sql_sam["servidor"],
        base_datos=cfg_sql_sam["base_datos"],
        usuario=cfg_sql_sam["usuario"],
        contrasena=cfg_sql_sam["contrasena"],
    )
    return {"db_connector": _db_connector}


def _run_service(deps: Dict[str, Any]) -> None:
    """Inicializa y ejecuta el servidor Uvicorn."""
    global _server_instance

    db_conn = deps.get("db_connector")
    if not db_conn:
        logging.critical("No se pudo inicializar DatabaseConnector. Abortando.")
        sys.exit(1)

    # Crear la App FastAPI (inyectando la dependencia)
    app = create_app(db_connector=db_conn)

    web_config = ConfigManager.get_interfaz_web_config()
    host = web_config.get("host", "127.0.0.1")
    port = web_config.get("port", 8000)
    reload = web_config.get("debug", False)

    logging.info(f"Configuración del servidor: http://{host}:{port} (Reload: {reload})")

    config = uvicorn.Config(app, host=host, port=port, reload=reload)
    _server_instance = uvicorn.Server(config)

    logging.info("Servidor Uvicorn iniciado correctamente.")
    _server_instance.run()


def _cleanup_resources() -> None:
    """Limpia la conexión a BD."""
    global _db_connector

    logging.info("Iniciando limpieza de recursos...")

    if _db_connector:
        try:
            _db_connector.cerrar_conexion_hilo_actual()
            logging.info("db_connector cerrado.")
        except Exception as e:
            logging.error(f"Error cerrando db_connector: {e}")

    logging.info(f"Servicio {_service_name.upper()} ha concluido y liberado recursos.")


# ---------- Punto de Entrada Principal ----------


def main(service_name: str) -> None:
    """Punto de entrada síncrono llamado por __main__.py."""
    global _service_name

    # Estandarizar el nombre del servicio
    _service_name = "web" if service_name == "interfaz_web" else service_name

    # El logging se debe iniciar *antes* que nada
    setup_logging(service_name="interfaz_web")  # Usar nombre de archivo de log esperado
    logging.info(f"Iniciando el servicio: {_service_name.capitalize()}...")

    _setup_signals()

    try:
        deps = _setup_dependencies()
        _run_service(deps)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Servicio detenido por el usuario o el sistema.")
    except Exception as e:
        logging.critical(f"Error crítico no controlado en main: {e}", exc_info=True)
        sys.exit(1)
    finally:
        _cleanup_resources()


if __name__ == "__main__":
    """Punto de entrada para ejecución directa (python run_web.py)."""
    # El SERVICE_NAME de ConfigLoader debe coincidir con el log
    ConfigLoader.initialize_service("interfaz_web")
    main("web")
