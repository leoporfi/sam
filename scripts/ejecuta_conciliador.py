#!/usr/bin/env python3
"""
Script manual para probar el Conciliador de forma aislada.
Ejecutar: python test_conciliador_manual.py
"""

import asyncio
import sys
from pathlib import Path

# Añadir src al path
src_path = str(Path(__file__).resolve().parent.parent / "src")
sys.path.insert(0, src_path)

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.config_loader import ConfigLoader
from sam.common.config_manager import ConfigManager
from sam.common.database import DatabaseConnector
from sam.common.logging_setup import setup_logging
from sam.lanzador.service.conciliador import Conciliador


async def main():
    # Inicializar configuración
    SERVICE_NAME = "test_conciliador"
    ConfigLoader.initialize_service(SERVICE_NAME)
    setup_logging(service_name=SERVICE_NAME)

    print("=" * 60)
    print("TEST MANUAL DEL CONCILIADOR")
    print("=" * 60)

    # Crear dependencias
    cfg_sql = ConfigManager.get_sql_server_config("SQL_SAM")
    db_connector = DatabaseConnector(
        servidor=cfg_sql["servidor"],
        base_datos=cfg_sql["base_datos"],
        usuario=cfg_sql["usuario"],
        contrasena=cfg_sql["contrasena"],
    )

    cfg_aa = ConfigManager.get_aa360_config()
    aa_client = AutomationAnywhereClient(
        cr_url=cfg_aa["cr_url"],
        cr_user="lporfiri",
        cr_pwd="",
        cr_api_key="QBZV@{fS@`39R}tOmGD2cpAP5uCAC2r45JbG4XtG",
        cr_api_timeout=cfg_aa["api_timeout_seconds"],
    )

    cfg_lanzador = ConfigManager.get_lanzador_config()

    # Crear conciliador
    conciliador = Conciliador(db_connector=db_connector, aa_client=aa_client, config=cfg_lanzador)

    # Ejecutar ciclo de conciliación
    print("\nIniciando ciclo de conciliación...\n")
    try:
        await conciliador.conciliar_ejecuciones()
        print("\n✓ Conciliación completada exitosamente")
    except Exception as e:
        print(f"\n✗ Error durante la conciliación: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Limpiar recursos
        await aa_client.close()
        db_connector.cerrar_conexion_hilo_actual()
        print("\nRecursos liberados")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
