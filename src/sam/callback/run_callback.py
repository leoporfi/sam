# sam/callback/run_callback.py
"""
Punto de entrada único del servicio Callback (Servidor Uvicorn).
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
from sam.common.logging_setup import setup_logging

# --- Globales del Servicio ---
_service_name = "callback"
_shutdown_initiated = False
_server_instance: Optional[uvicorn.Server] = None
# (Este servicio no crea dependencias en el run_*.py, FastAPI las maneja)


# ---------- Gestión de Cierre Ordenado (Graceful Shutdown) ----------


def _graceful_shutdown(signum: int, frame: Any) -> None:
    """Manejador de señales para un cierre ordenado."""
    global _shutdown_initiated
    if _shutdown_initiated:
        logging.warning("Señal de cierre duplicada recibida. Ya se está deteniendo.")
        return
    _shutdown_initiated = True
    logging.debug(f"Señal de parada recibida (Señal: {signum}). Iniciando cierre ordenado...")

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
    """El servicio Callback no tiene dependencias pre-inicializadas en el runner."""
    logging.debug("Las dependencias de Callback son gestionadas por FastAPI (lifespan).")
    return {}


def _run_service(deps: Dict[str, Any]) -> None:
    """Inicializa y ejecuta el servidor Uvicorn."""
    global _server_instance

    server_config = ConfigManager.get_callback_server_config()
    log_config = ConfigManager.get_log_config()

    host = server_config.get("host", "0.0.0.0")
    port = server_config.get("port", 8008)
    workers = server_config.get("threads", 1)
    log_level = log_config.get("level_str", "info").lower()

    logging.debug(f"Configuración del servidor: http://{host}:{port} con {workers} worker(s)...")

    config = uvicorn.Config(
        "sam.callback.service.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level=log_level,
    )
    _server_instance = uvicorn.Server(config)

    logging.debug("Servidor Uvicorn iniciado correctamente.")
    _server_instance.run()


def _cleanup_resources() -> None:
    """Uvicorn maneja su propia limpieza."""
    logging.debug(f"Servidor Uvicorn detenido. Servicio {_service_name.upper()} ha concluido.")


# ---------- Punto de Entrada Principal ----------


def main(service_name: str) -> None:
    """Punto de entrada síncrono llamado por __main__.py."""
    global _service_name
    _service_name = service_name

    setup_logging(service_name=_service_name)
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
    """Punto de entrada para ejecución directa (python run_callback.py)."""
    ConfigLoader.initialize_service(_service_name)
    main(_service_name)
