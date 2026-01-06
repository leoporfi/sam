# ruff: noqa: E402
import json
import sys
from pathlib import Path

# Añadir src al path
src_path = str(Path(__file__).resolve().parent.parent / "src")
sys.path.insert(0, src_path)

from sam.common.config_loader import ConfigLoader
from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector


def main():
    ConfigLoader.initialize_service("inspect_callback")
    cfg = ConfigManager.get_sql_server_config("SQL_SAM")
    # Filtrar argumentos no soportados
    db_args = {k: v for k, v in cfg.items() if k in ["servidor", "base_datos", "usuario", "contrasena"]}
    db = DatabaseConnector(**db_args)

    print("Consultando ejecuciones fallidas...")
    query = """
    SELECT TOP 5 Estado, CallbackInfo
    FROM dbo.Ejecuciones
    WHERE Estado IN ('ERROR', 'FINISHED_NOT_OK')
      AND CallbackInfo IS NOT NULL
    """
    rows = db.ejecutar_consulta(query)

    if not rows:
        print("No se encontraron ejecuciones fallidas con CallbackInfo.")

        # Intentar en histórico
        print("Consultando histórico...")
        query_hist = """
        SELECT TOP 5 Estado, CallbackInfo
        FROM dbo.Ejecuciones_Historico
        WHERE Estado IN ('ERROR', 'FINISHED_NOT_OK')
          AND CallbackInfo IS NOT NULL
        """
        rows = db.ejecutar_consulta(query_hist)

    for row in rows:
        print(f"\nEstado: {row['Estado']}")
        info = row["CallbackInfo"]
        print(f"CallbackInfo (raw): {info[:200]}...")  # Imprimir primeros 200 chars
        try:
            parsed = json.loads(info)
            print("CallbackInfo (parsed keys):", list(parsed.keys()))
            if "error" in parsed:
                print("Error field:", parsed["error"])
            if "message" in parsed:
                print("Message field:", parsed["message"])
        except json.JSONDecodeError:
            print("No se pudo parsear JSON")


if __name__ == "__main__":
    main()
