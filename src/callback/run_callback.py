# SAM/src/callback/run_callback.py
"""
Script principal para ejecutar el servicio Callback.

Este script configura el entorno de Python para permitir importaciones relativas
y lanza el servidor de Callbacks, que escucha las notificaciones de A360.
"""

import sys
from pathlib import Path

# === INICIALIZACIÓN DE CONFIGURACIÓN (DEBE SER LO PRIMERO) ===
# Añadimos 'src' al path temporalmente para poder importar 'common.utils.config_loader'.
SAM_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = SAM_PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Ahora importamos y usamos ConfigLoader.
from common.utils.config_loader import ConfigLoader

# Inicializa el servicio 'callback'. ConfigLoader se encarga de:
# 1. Determinar las rutas del proyecto.
# 2. Modificar sys.path para la ejecución actual.
# 3. Cargar los archivos .env en el orden correcto de precedencia.
ConfigLoader.initialize_service("callback", __file__)


# === IMPORTS DE MÓDULOS (DESPUÉS DE LA CONFIGURACIÓN) ===
# Con sys.path ya configurado, podemos importar el punto de entrada del servicio.
from callback.service.main import start_callback_server_main
from common.utils.config_manager import ConfigManager  # Opcional, para depuración

# === EJECUCIÓN DEL SERVICIO ===
if __name__ == "__main__":
    # Opcional: Imprime un resumen de la configuración para verificar los valores.
    print("--- Resumen de Configuración para 'Callback' ---")
    ConfigManager.print_config_summary("callback")
    print("-------------------------------------------------")

    # Llama a la función que inicia el servidor de callbacks.
    start_callback_server_main()
