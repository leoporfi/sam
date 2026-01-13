import sys
from pathlib import Path

# Ensure the scripts directory is in the python path to import db_tools
scripts_path = str(Path(__file__).resolve().parent / "scripts")
if scripts_path not in sys.path:
    sys.path.append(scripts_path)

from db_tools import get_db_connector


def apply_sp():
    db = get_db_connector()

    sql_file = Path(r"c:\Users\lporfiri\RPA\sam\database\procedures\dbo_ObtenerEjecucionesRecientes.sql")
    with open(sql_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split by GO
    commands = sql_content.split("GO")

    try:
        with db.obtener_cursor() as cursor:
            for cmd in commands:
                if cmd.strip():
                    cursor.execute(cmd)
        print("SP applied successfully using db_tools")
    except Exception as e:
        print(f"Error applying SP: {e}")


if __name__ == "__main__":
    apply_sp()
