# src/web/main.py

from pathlib import Path

from fastapi import FastAPI
from reactpy.backend.fastapi import Options, configure
from starlette.staticfiles import StaticFiles

# Importa el router de la API
from .backend.api import router as api_router

# Importa el componente raíz y la cabecera desde su nueva ubicación
from .frontend.app import App, head

# Crea la aplicación FastAPI
app = FastAPI()

# Monta las rutas de la API
app.include_router(api_router)

# Monta los archivos estáticos
static_files_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_files_path), name="static")

# Configura ReactPy para renderizar el componente App en la raíz
configure(app, App, options=Options(head=head))
