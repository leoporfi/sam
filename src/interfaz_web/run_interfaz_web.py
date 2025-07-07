# SAM/src/interfaz_web/run_interfaz_web.py (Archivo Nuevo)
"""
Script principal para ejecutar el servicio de Interfaz Web SAM.

Este script configura el entorno y lanza el servidor web FastAPI/Uvicorn.
"""

import sys
from pathlib import Path

# === INICIALIZACIÓN DE CONFIGURACIÓN (DEBE SER LO PRIMERO) ===
# Se añade 'src' al path temporalmente para poder importar 'common.utils.config_loader'.
SAM_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = SAM_PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


# --- AÑADIR ESTA LÍNEA PARA ACTIVAR EL MODO DEBUG ---
# import reactpy

# reactpy.config.REACTPY_DEBUG_MODE.current = True

from common.utils.config_loader import ConfigLoader

# Ahora se importa y utiliza ConfigLoader.
# Inicializa el servicio 'interfaz_web'.
ConfigLoader.initialize_service("interfaz_web", __file__)


# === IMPORTS DE MÓDULOS (DESPUÉS DE LA CONFIGURACIÓN) ===
# Importamos uvicorn para iniciar el servidor y ConfigManager para leer la config.
import uvicorn

from common.utils.config_manager import ConfigManager

# === EJECUCIÓN DEL SERVICIO ===
if __name__ == "__main__":
    # Opcional: Imprime un resumen de la configuración para verificar los valores.
    # print("--- Resumen de Configuración para 'Interfaz Web' ---")
    # ConfigManager.print_config_summary("interfaz_web")
    # print("-------------------------------------------------")

    # Obtenemos la configuración del servidor web desde ConfigManager.
    # Esto permite controlar el host, puerto y modo debug/reload desde los archivos .env.
    web_config = ConfigManager.get_interfaz_web_config()

    host = web_config.get("host", "127.0.0.1")
    port = web_config.get("port", 8000)
    # El modo 'reload' es ideal para desarrollo y se activa con INTERFAZ_WEB_DEBUG=true
    reload = web_config.get("debug", False)

    print(f"Iniciando servidor Uvicorn en http://{host}:{port} (Reload: {reload})")

    # Ejecutamos el servidor uvicorn programáticamente.
    # Apunta a la instancia 'app' dentro del módulo 'interfaz_web.main'.
    uvicorn.run("interfaz_web.main:app", host=host, port=port, reload=reload, log_level="info")
