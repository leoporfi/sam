# src/interfaz_web/main.py (Refactorizado)
from pathlib import Path

from fastapi import FastAPI
from reactpy.backend.fastapi import Options, configure
from starlette.staticfiles import StaticFiles

# 1. Importar los routers de la API desde el paquete 'api'
from .api import asignaciones_router, equipos_router, programaciones_router, robots_router

# 2. Importar el componente raíz de ReactPy y la cabecera HTML
from .app_component import App, head

# 3. Crear la instancia principal de la aplicación FastAPI
app = FastAPI()

# --- Montaje de Middleware y Rutas Estáticas ---

# Montamos la carpeta 'static' para que los archivos CSS y JS sean accesibles
static_files_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_files_path), name="static")


# --- Inclusión de Routers de la API ---
# Registramos todos los endpoints de la API que hemos modularizado.
# La aplicación principal delega el manejo de estas rutas a los routers específicos.
app.include_router(robots_router)
app.include_router(asignaciones_router)
app.include_router(programaciones_router)
app.include_router(equipos_router)


# --- Configuración del Frontend (ReactPy) ---

# Le decimos a ReactPy que se encargue de la ruta raíz ("/") y que renderice
# el componente 'App', inyectando nuestro 'head' personalizado en el HTML.
configure(
    app,
    App,
    options=Options(head=head),
)

# Nota: La inicialización de la base de datos ahora vive en 'dependencies.py'
# y se inyecta en los endpoints de la API donde se necesita.
# El archivo 'main.py' ya no se preocupa por la conexión a la DB.
