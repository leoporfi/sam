"""
Script principal para ejecutar el servicio Balanceador.

Este script configura el entorno de Python para permitir importaciones relativas
y lanza el servicio Balanceador. El Balanceador es responsable de distribuir
la carga de trabajo entre múltiples instancias del servicio Lanzador.

Autor: Equipo SAM
Fecha: 2025
"""

# SAM/balanceador/run_balanceador.py

import sys
from pathlib import Path

BALANCEADOR_MODULE_ROOT = Path(__file__).resolve().parent

SAM_PROJECT_ROOT = BALANCEADOR_MODULE_ROOT.parent

if str(SAM_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SAM_PROJECT_ROOT))

from balanceador.service.main import start_balanceador as main

if __name__ == "__main__":
    main()
