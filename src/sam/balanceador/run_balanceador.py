# sam/balanceador/run_balanceador.py
"""
Punto de entrada único del servicio Balanceador.
Contiene la lógica de arranque, gestión de señales y cierre de recursos.
"""

from __future__ import annotations

import logging
import signal
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from sam.common.config_loader import ConfigLoader

# --- Añadimos src al path para ejecución directa ---
if __name__ == "__main__":
    src_path = str(Path(__file__).resolve().parent.parent.parent)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

from sam.balanceador.service.main import BalanceadorService
from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector
from sam.common.logging_setup import setup_logging
from sam.common.mail_client import EmailAlertClient

# --- Globales del Servicio ---
_service_name = "balanceador"
_shutdown_initiated = False
_service_instance: Optional[BalanceadorService] = None

# --- Dependencias Globales ---
_db_sam: Optional[DatabaseConnector] = None
_db_rpa360: Optional[DatabaseConnector] = None
_notificador: Optional[EmailAlertClient] = None


# ---------- Gestión de Cierre Ordenado (Graceful Shutdown) ----------


def _graceful_shutdown(signum: int, frame: Any) -> None:
    """Manejador de señales para un cierre ordenado."""
    global _shutdown_initiated
    if _shutdown_initiated:
        logging.warning("Señal de cierre duplicada recibida. Ya se está deteniendo.")
        return
    _shutdown_initiated = True
    logging.info(f"Señal de parada recibida (Señal: {signum}). Iniciando cierre ordenado...")

    if _service_instance:
        _service_instance.stop()
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
    """Crea y retorna las dependencias específicas del servicio."""
    global _db_sam, _db_rpa360, _notificador

    logging.info("Creando dependencias (DBs, Notificador)...")

    cfg_sql_sam = ConfigManager.get_sql_server_config("SQL_SAM")
    _db_sam = DatabaseConnector(
        servidor=cfg_sql_sam["servidor"],
        base_datos=cfg_sql_sam["base_datos"],
        usuario=cfg_sql_sam["usuario"],
        contrasena=cfg_sql_sam["contrasena"],
    )

    cfg_sql_rpa360 = ConfigManager.get_sql_server_config("SQL_RPA360")
    _db_rpa360 = DatabaseConnector(
        servidor=cfg_sql_rpa360["servidor"],
        base_datos=cfg_sql_rpa360["base_datos"],
        usuario=cfg_sql_rpa360["usuario"],
        contrasena=cfg_sql_rpa360["contrasena"],
    )

    _notificador = EmailAlertClient(service_name=_service_name)

    return {"db_sam": _db_sam, "db_rpa360": _db_rpa360, "notificador": _notificador}


def _run_service(deps: Dict[str, Any]) -> None:
    """Inicializa y ejecuta la lógica principal del servicio (síncrono)."""
    global _service_instance

    _service_instance = BalanceadorService(
        db_sam=deps["db_sam"], db_rpa360=deps["db_rpa360"], notificador=deps["notificador"]
    )

    logging.info("Iniciando el ciclo principal del servicio Balanceador...")
    _service_instance.run()


def _cleanup_resources() -> None:
    """Limpia y cierra todas las conexiones y recursos."""
    global _db_sam, _db_rpa360

    logging.info("Iniciando limpieza de recursos...")

    if _db_sam:
        try:
            _db_sam.cerrar_conexion_hilo_actual()
            logging.info("db_sam cerrado.")
        except Exception as e:
            logging.error(f"Error cerrando db_sam: {e}")

    if _db_rpa360:
        try:
            _db_rpa360.cerrar_conexion_hilo_actual()
            logging.info("db_rpa360 cerrado.")
        except Exception as e:
            logging.error(f"Error cerrando db_rpa360: {e}")

    logging.info(f"Servicio {_service_name.upper()} ha concluido y liberado recursos.")


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
        if _notificador:
            _notificador.send_alert(f"Error Crítico en {_service_name.upper()}", f"Error: {e}")
        sys.exit(1)
    finally:
        _cleanup_resources()


if __name__ == "__main__":
    """Punto de entrada para ejecución directa (python run_balanceador.py)."""
    ConfigLoader.initialize_service(_service_name)
    main(_service_name)
