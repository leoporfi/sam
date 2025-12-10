# src/interfaz_web/dependencies.py
from typing import Optional

from fastapi import HTTPException

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.database import DatabaseConnector


# --- Proveedor de BD ---
class DBDependencyProvider:
    """
    Clase que actúa como un contenedor para nuestra dependencia de base de datos.
    Esto resuelve el problema de cómo pasar la instancia creada en run_web.py
    a los endpoints de la API que la necesitan a través de FastAPI `Depends`.
    """

    def __init__(self):
        self._db_connector: Optional[DatabaseConnector] = None

    def set_db_connector(self, db_connector: DatabaseConnector):
        """Este método es llamado una vez al inicio desde run_web.py."""
        self._db_connector = db_connector

    def get_db_connector(self) -> DatabaseConnector:
        """Esta es la función que FastAPI usará con `Depends`."""
        if self._db_connector is None:
            raise HTTPException(status_code=503, detail="Conexión BD no disponible.")
        return self._db_connector


db_dependency_provider = DBDependencyProvider()
get_db = db_dependency_provider.get_db_connector


# --- Proveedor de Cliente A360 ---
class AAClientDependencyProvider:
    def __init__(self):
        self._aa_client: Optional[AutomationAnywhereClient] = None

    def set_aa_client(self, aa_client: AutomationAnywhereClient):
        self._aa_client = aa_client

    def get_aa_client(self) -> AutomationAnywhereClient:
        if self._aa_client is None:
            raise HTTPException(status_code=503, detail="Cliente A360 no disponible.")
        return self._aa_client


aa_client_provider = AAClientDependencyProvider()
get_aa_client = aa_client_provider.get_aa_client
