# run_lanzador.py
"""
Script para ejecutar el lanzador manualmente
"""
import sys
import os
from pathlib import Path

# Añadir la raíz del proyecto (C:\RPA\rpa_sam) a sys.path
# __file__ es C:\RPA\rpa_sam\lanzador\run_lanzador.py
# Path(__file__).resolve() -> Path('C:/RPA/rpa_sam/lanzador/run_lanzador.py')
# .parent -> Path('C:/RPA/rpa_sam/lanzador')
# .parent -> Path('C:/RPA/rpa_sam')
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT)) # Importante insertarlo al principio

from lanzador.service.main import main_for_run_script  # Ahora puedes usar importaciones absolutas desde 'lanzador'

if __name__ == "__main__":
    main_for_run_script()