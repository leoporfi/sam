#!/usr/bin/env python3
"""
Script para aplicar el Stored Procedure de Análisis de Utilización de Recursos.
"""

import sys
from pathlib import Path

# Añadir src al path
src_path = str(Path(__file__).resolve().parent.parent / "src")
sys.path.insert(0, src_path)

from sam.common.config_loader import ConfigLoader  # noqa: E402
from sam.common.config_manager import ConfigManager  # noqa: E402
from sam.common.database import DatabaseConnector  # noqa: E402
from sam.common.logging_setup import setup_logging  # noqa: E402


def main():
    # Inicializar configuración
    SERVICE_NAME = "apply_sp_utilizacion"
    ConfigLoader.initialize_service(SERVICE_NAME)
    setup_logging(service_name=SERVICE_NAME)

    print("=" * 60)
    print("APLICANDO SP: AnalisisUtilizacionRecursos")
    print("=" * 60)

    # Crear conector DB
    cfg_sql = ConfigManager.get_sql_server_config("SQL_SAM")
    db_connector = DatabaseConnector(
        servidor=cfg_sql["servidor"],
        base_datos=cfg_sql["base_datos"],
        usuario=cfg_sql["usuario"],
        contrasena=cfg_sql["contrasena"],
    )

    # Leer archivo SQL
    sql_path = (
        Path(__file__).resolve().parent.parent / "database" / "procedures" / "dbo_AnalisisUtilizacionRecursos.sql"
    )

    if not sql_path.exists():
        print(f"ERROR: No se encontró el archivo SQL en: {sql_path}")
        return

    try:
        print(f"Leyendo archivo SQL: {sql_path}")
        with open(sql_path, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Eliminar líneas que solo contienen GO (case insensitive)
        sql_statements = []
        current_statement = []

        for line in sql_content.splitlines():
            if line.strip().upper() == "GO":
                if current_statement:
                    sql_statements.append("\n".join(current_statement))
                    current_statement = []
            else:
                current_statement.append(line)

        if current_statement:
            sql_statements.append("\n".join(current_statement))

        print(f"Se encontraron {len(sql_statements)} bloques de ejecución.")

        with db_connector.obtener_cursor() as cursor:
            for i, statement in enumerate(sql_statements):
                if not statement.strip():
                    continue
                print(f"Ejecutando bloque {i + 1}...")
                cursor.execute(statement)

        print("\n✓ Stored Procedure aplicado exitosamente.")

    except Exception as e:
        print(f"\n✗ Error aplicando el SP: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db_connector.cerrar_conexion_hilo_actual()
        print("\nConexión cerrada.")


if __name__ == "__main__":
    main()
