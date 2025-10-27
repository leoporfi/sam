# sam/web/main.py
from pathlib import Path

from fastapi import FastAPI
from reactpy.backend.fastapi import Options, configure
from starlette.staticfiles import StaticFiles

from sam.common.database import DatabaseConnector

from .backend.api import router as api_router
from .backend.dependencies import db_dependency_provider
from .frontend.app import App, head

# ELIMINAR ESTA LÍNEA:
# app = FastAPI(title="SAM Interfaz Web API")


def create_app(db_connector: DatabaseConnector) -> FastAPI:
    """Crea y configura la aplicación FastAPI."""
    # Crear la instancia aquí
    app = FastAPI(title="SAM Interfaz Web API")

    db_dependency_provider.set_db_connector(db_connector)
    app.include_router(api_router)

    static_files_path = Path(__file__).parent / "static"
    if static_files_path.exists():
        app.mount("/static", StaticFiles(directory=static_files_path), name="static")

    configure(app, App, options=Options(head=head))
    return app
