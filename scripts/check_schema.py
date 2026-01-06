# ruff: noqa: E402
import sys
from pathlib import Path

# Añadir src al path
src_path = str(Path(__file__).resolve().parent.parent / "src")
sys.path.insert(0, src_path)

from sam.common.config_loader import ConfigLoader
from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector


def main():
    ConfigLoader.initialize_service("schema_check")
    cfg = ConfigManager.get_sql_server_config("SQL_SAM")
    # Filtrar argumentos no soportados por DatabaseConnector
    db_args = {k: v for k, v in cfg.items() if k in ["servidor", "base_datos", "usuario", "contrasena"]}
    db = DatabaseConnector(**db_args)

    print("Columnas en dbo.Ejecuciones:")
    # Consultamos INFORMATION_SCHEMA para obtener las columnas

    print("\nColumnas en dbo.Ejecuciones_Historico:")
    schema_info_hist = db.ejecutar_consulta(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'Ejecuciones_Historico'
    """
    )
    for row in schema_info_hist:
        print(f"- {row['COLUMN_NAME']}")

    print("\nColumnas en dbo.Robots:")
    schema_info_robots = db.ejecutar_consulta(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'Robots'
    """
    )
    for row in schema_info_robots:
        print(f"- {row['COLUMN_NAME']}")

    print("\nColumnas en dbo.Equipos:")
    schema_info_equipos = db.ejecutar_consulta(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'Equipos'
    """
    )
    for row in schema_info_equipos:
        print(f"- {row['COLUMN_NAME']}")


if __name__ == "__main__":
    main()
