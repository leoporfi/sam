# interfaz_web/run_interfaz_web.py

import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from reactpy.backend.fastapi import configure

# Añadir la raíz del proyecto al sys.path para permitir importaciones relativas
WEB_MODULE_ROOT = Path(__file__).resolve().parent
SAM_PROJECT_ROOT = WEB_MODULE_ROOT.parent

if str(SAM_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SAM_PROJECT_ROOT))

# Importar el componente principal de la aplicación desde su nueva ubicación
from interfaz_web.service.main import App

# Configuración del servidor web usando FastAPI como backend
app = FastAPI()
configure(app, App)

if __name__ == "__main__":
    print("Iniciando servidor web de SAM en http://127.0.0.1:8000")
    # uvicorn es ideal para desarrollo.
    uvicorn.run(app, host="0.0.0.0", port=8000)
