#!/usr/bin/env python3
"""
Script para verificar la integración del Dashboard de Tiempos de Ejecución.
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
from sam.web.backend.database import get_tiempos_ejecucion_dashboard  # noqa: E402


def main():
    # Inicializar configuración
    SERVICE_NAME = "verify_tiempos"
    ConfigLoader.initialize_service(SERVICE_NAME)
    setup_logging(service_name=SERVICE_NAME)

    print("=" * 60)
    print("VERIFICANDO BACKEND: get_tiempos_ejecucion_dashboard")
    print("=" * 60)

    # Crear conector DB
    cfg_sql = ConfigManager.get_sql_server_config("SQL_SAM")
    db_connector = DatabaseConnector(
        servidor=cfg_sql["servidor"],
        base_datos=cfg_sql["base_datos"],
        usuario=cfg_sql["usuario"],
        contrasena=cfg_sql["contrasena"],
    )

    try:
        print("Llamando a get_tiempos_ejecucion_dashboard()...")
        # Llamada con parámetros por defecto
        data = get_tiempos_ejecucion_dashboard(db_connector)

        print(f"\n✓ Llamada exitosa. Se obtuvieron {len(data)} registros.")

        if data:
            print("\nPrimer registro de muestra:")
            first = data[0]
            for k, v in first.items():
                print(f"  - {k}: {v}")
        else:
            print("\nNo hay datos para mostrar (posiblemente no hay ejecuciones recientes o completadas).")

    except Exception as e:
        print(f"\n✗ Error en la verificación: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db_connector.cerrar_conexion_hilo_actual()
        print("\nConexión cerrada.")


if __name__ == "__main__":
    main()
