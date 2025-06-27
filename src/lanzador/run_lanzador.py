# SAM/src/Lanzador/run_lanzador.py
"""
Script principal para ejecutar el servicio Lanzador.

Este script configura el entorno de Python para permitir importaciones relativas
y lanza el servicio Lanzador. El Lanzador es responsable de procesar los mensajes
asignados por el Balanceador y ejecutar las acciones necesarias.

Autor: Equipo SAM
Fecha: 2024
"""

import sys
from pathlib import Path

# === INICIALIZACIÓN DE CONFIGURACIÓN (DEBE SER LO PRIMERO) ===
SAM_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = SAM_PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Ahora podemos importar y usar ConfigLoader de forma segura
from common.utils.config_loader import ConfigLoader

# Inicializa el servicio. ConfigLoader se encarga de:
# 1. Determinar las rutas del proyecto.
# 2. Modificar sys.path permanentemente para esta ejecución.
# 3. Cargar los archivos .env en el orden correcto de precedencia.
ConfigLoader.initialize_service("lanzador", __file__)


# === IMPORTS DE MÓDULOS (DESPUÉS DE LA CONFIGURACIÓN) ===
from common.utils.config_manager import ConfigManager  # Opcional, para debug
from lanzador.service.main import start_lanzador

# === EJECUCIÓN DEL SERVICIO ===
if __name__ == "__main__":
    # Opcional: Imprimir un resumen de la configuración cargada para este servicio.
    print("--- Resumen de Configuración para 'Lanzador' ---")
    ConfigManager.print_config_summary("lanzador")
    print("-------------------------------------------------")

    # Llama a la función que inicia toda la lógica del servicio Lanzador.
    start_lanzador()
