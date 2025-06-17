"""
Script principal para ejecutar el servicio Lanzador.

Este script configura el entorno de Python para permitir importaciones relativas
y lanza el servicio Lanzador. El Lanzador es responsable de procesar los mensajes
asignados por el Balanceador y ejecutar las acciones necesarias.

Autor: Equipo SAM
Fecha: 2024
"""

# SAM/Lanzador/run_lanzador.py
import sys
from pathlib import Path

LANZADOR_MODULE_ROOT: Path = Path(__file__).resolve().parent
SAM_PROJECT_ROOT: Path = LANZADOR_MODULE_ROOT.parent

if str(SAM_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SAM_PROJECT_ROOT))

from lanzador.service.main import start_lanzador

if __name__ == "__main__":
    start_lanzador()
