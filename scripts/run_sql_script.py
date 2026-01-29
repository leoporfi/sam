import sys
from pathlib import Path

# Add src to python path BEFORE importing sam modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Now we can import sam modules
from sam.common.config_manager import ConfigManager  # noqa: E402
from sam.common.database import DatabaseConnector  # noqa: E402


def run_script(script_path):
    print(f"Executing script: {script_path}")

    try:
        sql_config = ConfigManager.get_sql_server_config("SQL_SAM")
        db = DatabaseConnector(
            servidor=sql_config["servidor"],
            base_datos=sql_config["base_datos"],
            usuario=sql_config["usuario"],
            contrasena=sql_config["contrasena"],
            db_config_prefix="SQL_SAM",
        )

        with open(script_path, encoding="utf-8") as f:
            sql_content = f.read()

        # Split by GO if necessary
        batches = [b.strip() for b in sql_content.split("GO") if b.strip()]

        for i, batch in enumerate(batches):
            print(f"Executing batch {i + 1}/{len(batches)}...")
            db.ejecutar_consulta(batch, es_select=False)

        print("Script executed successfully.")

    except Exception as e:
        print(f"Error executing script: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_sql_script.py <path_to_sql_file>")
        sys.exit(1)

    run_script(sys.argv[1])
