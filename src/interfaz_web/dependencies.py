# src/interfaz_web/dependencies.py
from fastapi import HTTPException

from common.database.sql_client import DatabaseConnector
from common.utils.config_manager import ConfigManager

# --- Instancia Única del Conector de Base de Datos ---
# Esto asegura que solo haya una conexión (o pool) para toda la aplicación,
# lo cual es más eficiente.

try:
    db_config = ConfigManager.get_sql_server_config("SQL_SAM")
    db_connector = DatabaseConnector(
        servidor=db_config.get("server"),
        base_datos=db_config.get("database"),
        usuario=db_config.get("uid"),
        contrasena=db_config.get("pwd")
    )
except Exception as e:
    # Si la configuración de la DB falla al inicio, la app no puede funcionar.
    # Es mejor lanzar un error aquí para que el problema sea obvio.
    raise RuntimeError(f"No se pudo inicializar la conexión a la base de datos: {e}") from e

def get_db_connector() -> DatabaseConnector:
    """
    Función de dependencia de FastAPI para inyectar el conector de base de datos.

    Simplemente devuelve la instancia global 'db_connector'. FastAPI se encarga
    de pasarla a los endpoints que la requieran con Depends().
    """
    if not db_connector:
        raise HTTPException(
            status_code=503, 
            detail="La conexión a la base de datos no está disponible."
        )
    return db_connector
