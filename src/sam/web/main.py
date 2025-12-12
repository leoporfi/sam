# sam/web/main.py
import asyncio
import platform

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from reactpy.backend.fastapi import Options, configure
from starlette.staticfiles import StaticFiles

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector

from .backend.api import router as api_router
from .backend.dependencies import aa_client_provider, db_dependency_provider
from .frontend.app import App, head

#  Asegurar política también aquí
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = logging.getLogger(__name__)


# --- Gestor de ciclo de vida (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando aplicación y recursos...")

    # Solo verificamos que esté listo
    if not aa_client_provider.get_aa_client():
        logger.warning("El cliente AA no fue inyectado correctamente desde run_web.py")

    # Inicializa el diccionario de estado
    app.state.sync_status = {"robots": "idle", "equipos": "idle", "global": "idle"}
    # Un Lock evita que dos peticiones cambien el estado al mismo tiempo
    app.state.sync_lock = asyncio.Lock()

    yield  # La aplicación se ejecuta aquí

    logger.info("Iniciando cierre ordenado de recursos...")
    if aa_client_provider.get_aa_client():
        await aa_client_provider.get_aa_client().close()
        logger.info("Cliente A360 cerrado.")

    try:
        logger.info("Cerrando pool de conexiones de base de datos...")
        db_dependency_provider.get_db_connector().cerrar_conexiones_pool()
        logger.info("Pool de conexiones de BD cerrado.")
    except Exception as e:
        logger.error(f"Error al cerrar el pool de conexiones: {e}", exc_info=True)


def create_app(db_connector: DatabaseConnector) -> FastAPI:
    """Crea y configura la aplicación FastAPI."""

    # Pasar el lifespan a FastAPI
    app = FastAPI(title="SAM Interfaz Web API", lifespan=lifespan)

    # Inyectar la dependencia de base de datos
    db_dependency_provider.set_db_connector(db_connector)

    # Incluir las rutas de la API
    app.include_router(api_router)

    # Montar archivos estáticos
    static_files_path = Path(__file__).parent / "static"
    if static_files_path.exists():
        app.mount("/static", StaticFiles(directory=static_files_path), name="static")

    # Configurar ReactPy
    configure(app, App, options=Options(head=head))

    return app
