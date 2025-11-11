# sam/lanzador/run_lanzador.py
"""
Punto de entrada único del servicio Lanzador.
Contiene la lógica de arranque, gestión de señales y cierre de recursos.
"""

from __future__ import annotations

import asyncio
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

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.apigw_client import ApiGatewayClient
from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector
from sam.common.logging_setup import setup_logging
from sam.common.mail_client import EmailAlertClient
from sam.lanzador.service.conciliador import Conciliador
from sam.lanzador.service.desplegador import Desplegador
from sam.lanzador.service.main import LanzadorService
from sam.lanzador.service.sincronizador import Sincronizador

# --- Globales del Servicio ---
_service_name = "lanzador"
_shutdown_initiated = False
_service_instance: Optional[LanzadorService] = None

# --- Dependencias Globales ---
_db_connector: Optional[DatabaseConnector] = None
_aa_client: Optional[AutomationAnywhereClient] = None
_gateway_client: Optional[ApiGatewayClient] = None
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
        if hasattr(_service_instance, "_shutdown_event"):
            logging.info("Notificando a las tareas asíncronas que deben detenerse...")
            _service_instance._shutdown_event.set()
        else:
            # Fallback por si el service_instance no es el esperado
            _service_instance.stop()
    else:
        # Si el servicio aún no se ha inicializado, forzar la salida en el main
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
    global _db_connector, _aa_client, _gateway_client, _notificador

    logging.info("Creando dependencias (DB, Clientes API)...")

    cfg_sql_sam = ConfigManager.get_sql_server_config("SQL_SAM")
    _db_connector = DatabaseConnector(
        servidor=cfg_sql_sam["servidor"],
        base_datos=cfg_sql_sam["base_datos"],
        usuario=cfg_sql_sam["usuario"],
        contrasena=cfg_sql_sam["contrasena"],
    )

    cfg_aa = ConfigManager.get_aa360_config()
    _aa_client = AutomationAnywhereClient(
        cr_url=cfg_aa["cr_url"],
        cr_user=cfg_aa["cr_user"],
        cr_pwd=cfg_aa.get("cr_pwd"),
        cr_api_key=cfg_aa["cr_api_key"],
        cr_api_timeout=cfg_aa["api_timeout_seconds"],
        callback_url_deploy=cfg_aa.get("callback_url_deploy"),
    )

    cfg_apigw = ConfigManager.get_apigw_config()
    _gateway_client = ApiGatewayClient(cfg_apigw)

    _notificador = EmailAlertClient(service_name=_service_name)

    return {
        "db_connector": _db_connector,
        "aa_client": _aa_client,
        "gateway_client": _gateway_client,
        "notificador": _notificador,
    }


async def _run_service(deps: Dict[str, Any]) -> None:
    """Inicializa y ejecuta la lógica principal del servicio (asíncrono)."""
    global _service_instance

    cfg_lanzador = ConfigManager.get_lanzador_config()
    callback_token = ConfigManager.get_callback_server_config().get("token")

    sincronizador = Sincronizador(deps["db_connector"], deps["aa_client"])
    desplegador = Desplegador(
        deps["db_connector"],
        deps["aa_client"],
        deps["gateway_client"],
        cfg_lanzador,
        callback_token,
    )
    conciliador = Conciliador(deps["db_connector"], deps["aa_client"], cfg_lanzador)
    sync_enabled = cfg_lanzador.get("habilitar_sync", False)

    _service_instance = LanzadorService(
        sincronizador,
        desplegador,
        conciliador,
        deps["notificador"],
        cfg_lanzador,
        sync_enabled,
    )

    logging.info("Iniciando los ciclos de tareas asíncronas...")
    await _service_instance.run()


async def _cleanup_resources() -> None:
    """Limpia y cierra todas las conexiones y recursos."""
    global _db_connector, _aa_client, _gateway_client, _notificador

    logging.info("Iniciando limpieza de recursos...")

    cfg_lanzador = ConfigManager.get_lanzador_config()
    shutdown_timeout = cfg_lanzador.get("shutdown_timeout_seg", 60)

    # 1. Esperar a que las tareas asíncronas terminen
    if _service_instance and hasattr(_service_instance, "_tasks") and _service_instance._tasks:
        logging.info(f"Esperando a que las tareas finalicen (máx {shutdown_timeout} segundos)...")
        try:
            if hasattr(_service_instance, "_shutdown_event"):
                _service_instance._shutdown_event.set()

            results = await asyncio.wait_for(
                asyncio.gather(*_service_instance._tasks, return_exceptions=True), timeout=float(shutdown_timeout)
            )
            for i, result in enumerate(results):
                if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                    logging.warning(f"Tarea {i} terminó con excepción durante el cierre: {result}")
            logging.info("Todas las tareas asíncronas finalizaron.")
        except asyncio.TimeoutError:
            logging.warning(f"Timeout ({shutdown_timeout}s) esperando tareas. Forzando cancelación...")
            for task in _service_instance._tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*_service_instance._tasks, return_exceptions=True)
        except Exception as e:
            logging.error(f"Error durante el gather de tareas en el cierre: {e}", exc_info=True)

    # 2. Cerrar clientes HTTP (asíncronos)
    if _gateway_client:
        try:
            await _gateway_client.close()
            logging.info("gateway_client cerrado.")
        except Exception as e:
            logging.error(f"Error cerrando gateway_client: {e}")
    if _aa_client:
        try:
            await _aa_client.close()
            logging.info("aa_client cerrado.")
        except Exception as e:
            logging.error(f"Error cerrando aa_client: {e}")

    # 3. Cerrar BD
    if _db_connector:
        try:
            _db_connector.cerrar_conexion_hilo_actual()
            logging.info("db_connector cerrado.")
        except Exception as e:
            logging.error(f"Error cerrando db_connector: {e}")

    logging.info(f"Servicio {_service_name.upper()} ha concluido y liberado recursos.")


# ---------- Punto de Entrada Principal ----------


async def _main_async() -> None:
    """Función principal asíncrona que envuelve el ciclo de vida."""
    deps = {}
    try:
        deps = _setup_dependencies()
        await _run_service(deps)
    except asyncio.CancelledError:
        logging.warning("El bucle principal de asyncio fue cancelado (esperado durante el cierre).")
    except Exception as e:
        logging.critical(f"Error crítico no controlado en _main_async: {e}", exc_info=True)
        if _notificador:
            _notificador.send_alert(f"Error Crítico en {_service_name.upper()}", f"Error: {e}")
        sys.exit(1)
    finally:
        await _cleanup_resources()


def main(service_name: str) -> None:
    """Punto de entrada síncrono llamado por __main__.py."""
    global _service_name
    _service_name = service_name

    setup_logging(service_name=_service_name)
    logging.info(f"Iniciando el servicio: {_service_name.capitalize()}...")

    _setup_signals()

    try:
        asyncio.run(_main_async())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Servicio detenido por el usuario o el sistema (KeyboardInterrupt/SystemExit).")
    except Exception as e:
        logging.critical(f"Error fatal no capturado en el nivel superior de asyncio.run: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    """Punto de entrada para ejecución directa (python run_lanzador.py)."""
    ConfigLoader.initialize_service(_service_name)
    main(_service_name)
