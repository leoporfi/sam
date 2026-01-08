import os
import sys
from typing import Any

from dotenv import load_dotenv

# Ensure the src directory is in the python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from sam.web.backend.database import ConfigManager, DatabaseConnector  # noqa: E402


def get_db_connector() -> DatabaseConnector:
    """
    Creates and returns a DatabaseConnector instance using the SQL_SAM configuration.
    Ensures .env is loaded.
    """
    load_dotenv()
    config = ConfigManager.get_sql_server_config("SQL_SAM")
    return DatabaseConnector(
        servidor=config["servidor"],
        base_datos=config["base_datos"],
        usuario=config["usuario"],
        contrasena=config["contrasena"],
    )


def run_query(query: str, params: tuple = None, es_select: bool = True) -> Any:
    """
    Helper to run a query quickly.
    """
    db = get_db_connector()
    return db.ejecutar_consulta(query, params, es_select)


if __name__ == "__main__":
    # Example usage / test
    try:
        print("Testing connection...")
        res = run_query("SELECT @@VERSION as Version")
        print(f"Connection successful. Version: {res[0]['Version'][:50]}...")
    except Exception as e:
        print(f"Connection failed: {e}")
