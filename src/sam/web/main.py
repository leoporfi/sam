# sam/web/main.py
import logging
from pathlib import Path

from fastapi import FastAPI
from reactpy.backend.fastapi import Options, configure
from starlette.staticfiles import StaticFiles

from sam.common.database import DatabaseConnector

from .backend.api import router as api_router
from .backend.dependencies import db_dependency_provider
from .frontend.app import App, head

logger = logging.getLogger(__name__)
# ELIMINAR ESTA LÍNEA:
# app = FastAPI(title="SAM Interfaz Web API")


def create_app(db_connector: DatabaseConnector) -> FastAPI:
    """Crea y configura la aplicación FastAPI."""
    # Crear la instancia aquí
    app = FastAPI(title="SAM Interfaz Web API")

    # Inyectar la dependencia de base de datos
    db_dependency_provider.set_db_connector(db_connector)
    # Incluir las rutas de la API
    app.include_router(api_router)
    # Montar archivos estáticos si existen
    static_files_path = Path(__file__).parent / "static"
    if static_files_path.exists():
        app.mount("/static", StaticFiles(directory=static_files_path), name="static")
    # Configurar ReactPy
    configure(app, App, options=Options(head=head))

    # CRÍTICO: Registrar el evento de shutdown para liberar recursos
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cierra el pool de conexiones de forma ordenada al detener el servidor."""
        try:
            logger.info("Iniciando cierre del pool de conexiones a la base de datos...")
            db_connector.cerrar_conexiones_pool()
            logger.info("Pool de conexiones cerrado correctamente.")
        except Exception as e:
            logger.error(f"Error al cerrar el pool de conexiones: {e}", exc_info=True)

    return app
