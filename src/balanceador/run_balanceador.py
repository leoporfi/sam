# SAM/src/balanceador/run_balanceador.py
"""
Script principal para ejecutar el servicio Balanceador.

Este script configura el entorno de Python para permitir importaciones relativas
y lanza el servicio Balanceador. El Balanceador es responsable de distribuir
la carga de trabajo entre los equipos disponibles.

Autor: Equipo SAM
Fecha: 2025
"""

import sys
from pathlib import Path

# === INICIALIZACIÓN DE CONFIGURACIÓN (DEBE SER LO PRIMERO) ===
SAM_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = SAM_PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Ahora se importa y utiliza ConfigLoader.
from common.utils.config_loader import ConfigLoader

# Inicializa el servicio 'balanceador'. ConfigLoader se encarga de:
# 1. Determinar las rutas del proyecto.
# 2. Modificar sys.path para la ejecución actual.
# 3. Cargar los archivos .env en el orden correcto de precedencia.
ConfigLoader.initialize_service("balanceador", __file__)


# === IMPORTS DE MÓDULOS (DESPUÉS DE LA CONFIGURACIÓN) ===
# Con sys.path ya configurado, se pueden importar los módulos del servicio.
from balanceador.service.main import start_balanceador
from common.utils.config_manager import ConfigManager  # Opcional, para depuración

# === EJECUCIÓN DEL SERVICIO ===
if __name__ == "__main__":
    # Opcional: Imprime un resumen de la configuración para verificar los valores cargados.
    print("--- Resumen de Configuración para 'Balanceador' ---")
    ConfigManager.print_config_summary("balanceador")
    print("--------------------------------------------------")

    # Llama a la función que inicia la lógica del servicio Balanceador.
    start_balanceador()
