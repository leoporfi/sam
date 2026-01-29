import sys
from pathlib import Path

# Add src to sys.path
project_root = Path(__file__).resolve().parent.parent
src_path = str(project_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# ruff: noqa: E402
from sam.common.config_loader import ConfigLoader
from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector


def apply_migration():
    print("Initializing ConfigLoader...")
    ConfigLoader.initialize_service("lanzador")  # Use any service to load env

    print("Connecting to database...")
    # We need to get credentials manually or use ConfigManager if it works
    # ConfigManager depends on ConfigLoader which we just initialized

    # Get DB config prefix
    db_prefix = "SQL_SAM"

    config = ConfigManager.get_sql_server_config(db_prefix)

    db = DatabaseConnector(
        servidor=config["servidor"],
        base_datos=config["base_datos"],
        usuario=config["usuario"],
        contrasena=config["contrasena"],
        db_config_prefix=db_prefix,
    )

    # Read seed_config.sql
    seed_file = project_root / "database" / "scripts" / "seed_config.sql"
    print(f"Reading {seed_file}...")

    with open(seed_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split by GO
    batches = sql_content.split("GO")

    print(f"Found {len(batches)} batches to execute.")

    for i, batch in enumerate(batches):
        batch = batch.strip()
        if not batch:
            continue

        print(f"Executing batch {i + 1}...")
        try:
            # We use execute_consulta with es_select=False.
            # Note: DatabaseConnector might not handle raw SQL blocks with variables well if not parameterized,
            # but this script is simple T-SQL.
            # However, DatabaseConnector.ejecutar_consulta expects a query string.
            # We might need to use the cursor directly for DDL/mixed batches if the wrapper is too strict.

            with db.obtener_cursor() as cursor:
                cursor.execute(batch)

            print(f"Batch {i + 1} executed successfully.")
        except Exception as e:
            print(f"Error executing batch {i + 1}: {e}")
            # Don't stop, try next batches (idempotency)

    print("Migration completed.")


if __name__ == "__main__":
    apply_migration()
