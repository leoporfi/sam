# SAM/Lanzador/tests/test_sql_client_merge_methods.py (Nuevo archivo)

import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import datetime # Para el objeto time

# --- Configuración de Path para encontrar los módulos de SAM ---
SAM_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(SAM_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SAM_PROJECT_ROOT))

# --- Importar el DatabaseConnector y ConfigManager ---
from lanzador.database.sql_client import DatabaseConnector
from lanzador.utils.config import ConfigManager, setup_logging

# --- Configurar Logging Básico para la Prueba ---
logger = setup_logging() # Usa el logger configurado por SAM
logger.setLevel(logging.DEBUG) # Poner en DEBUG para ver más detalle de las operaciones SQL

def pretty_print_sql_params(params_list: List[tuple]):
    print("Datos para MERGE:")
    if not params_list:
        print("  (Lista vacía)")
        return
    for i, params_tuple in enumerate(params_list):
        print(f"  Registro {i+1}: {params_tuple}")

def run_merge_tests():
    logger.info("--- Iniciando Prueba de Métodos MERGE en DatabaseConnector ---")

    # --- Cargar Configuración Real de BD desde .env usando ConfigManager ---
    try:
        sql_cfg = ConfigManager.get_sql_server_config()
        # Asegúrate que tu .env esté configurado para la BD SAM que usa el Lanzador
        db_name_for_lanzador = sql_cfg.get("database_sam") # O "database" si solo hay una para el lanzador
        if not db_name_for_lanzador:
            db_name_for_lanzador = sql_cfg.get("database") # Fallback al nombre genérico
            if not db_name_for_lanzador:
                logger.error("No se encontró el nombre de la base de datos para SAM Lanzador en la configuración.")
                return
        
        db_connector = DatabaseConnector(
            servidor=sql_cfg["server"],
            base_datos=db_name_for_lanzador, 
            usuario=sql_cfg["uid"],
            contrasena=sql_cfg["pwd"]
        )
        logger.info(f"Conectado a la base de datos: {db_name_for_lanzador}")
    except Exception as e:
        logger.error(f"Error conectando a la base de datos o cargando configuración: {e}", exc_info=True)
        return

    # --- Prueba para merge_equipos_sam ---
    print("\n--- Prueba: merge_equipos_sam ---")
    # Datos ficticios simulando lo que vendría de AutomationAnywhereClient.obtener_devices_para_sam
    # y posterior enriquecimiento.
    # Campos clave: "EquipoId" (A360 DeviceID), "Equipo", "UserId" (A360 UserID), "UserName", "Licencia", "Activo_SAM"
    lista_equipos_ficticios: List[Dict[str, Any]] = [
        { # Caso 1: Equipo existente que podría necesitar actualización
            "EquipoId": 101, "Equipo": "RPA-VM01-PROD-ACTUALIZADO", "UserId": 701, 
            "UserName": "runner01prod", "Licencia": "Unattended", "Activo_SAM": True 
        },
        { # Caso 2: Nuevo equipo para insertar
            "EquipoId": 105, "Equipo": "RPA-VM05-NUEVO", "UserId": 705, 
            "UserName": "runner05new", "Licencia": "Attended", "Activo_SAM": True
        },
        { # Caso 3: Equipo existente, pero ahora inactivo
            "EquipoId": 102, "Equipo": "RPA-VM02-AHORA-INACTIVO", "UserId": 702,
            "UserName": "runner02off", "Licencia": "Unattended", "Activo_SAM": False # Asumiendo que la columna Activo existe
        },
        { # Caso 4: Device sin usuario asignado
            "EquipoId": 106, "Equipo": "RPA-VM06-SIN-USUARIO", "UserId": None, 
            "UserName": None, "Licencia": "NO_APLICA", "Activo_SAM": False
        },
        { # Caso 5: Mismo EquipoId que el caso 1, para ver si actualiza (el último debería ganar si hay duplicados en la lista)
          # Esto prueba la lógica del MERGE, no la deduplicación en la lista de entrada, que debe hacerse antes.
          # En una lista real, no debería haber EquipoId duplicados.
            "EquipoId": 101, "Equipo": "RPA-VM01-PROD-FINAL", "UserId": 701, 
            "UserName": "runner01final", "Licencia": "SuperUnattended", "Activo_SAM": True 
        }
    ]
    
    # Antes de ejecutar, podrías querer insertar/actualizar manualmente algunos registros en tu BD SAM
    # para verificar los casos de MATCHED e INSERT.
    # Por ejemplo, asegúrate que un Equipo con EquipoId=101 exista, y uno con EquipoId=105 no.
    input("PREPARACIÓN: Asegúrate que tu tabla dbo.Equipos esté lista para probar el MERGE (ej. EquipoId 101 existe, 105 no). Presiona Enter para continuar...")

    try:
        logger.info(f"Llamando a merge_equipos_sam con {len(lista_equipos_ficticios)} registros ficticios.")
        # La función merge_equipos_sam en sql_client.py ya prepara los parámetros para la query.
        filas_afectadas_eq = db_connector.merge_equipos_sam(lista_equipos_ficticios)
        logger.info(f"merge_equipos_sam ejecutado. Filas afectadas/procesadas aprox: {filas_afectadas_eq}")
        print(f"Resultado merge_equipos_sam (filas afectadas aprox): {filas_afectadas_eq}")
        print("Verifica la tabla dbo.Equipos en tu base de datos SAM.")
    except Exception as e:
        logger.error(f"Error durante la prueba de merge_equipos_sam: {e}", exc_info=True)
        print(f"ERROR en merge_equipos_sam: {e}")


    # --- Prueba para merge_robots_sam ---
    print("\n--- Prueba: merge_robots_sam ---")
    # Datos ficticios simulando lo que vendría de AutomationAnywhereClient.obtener_robots_para_sam
    # Campos clave: "RobotId" (A360 FileID), "Robot" (nombre), "Descripcion", "EsOnline_SAM", "Activo_SAM"
    lista_robots_ficticios: List[Dict[str, Any]] = [
        { # Caso 1: Robot existente que necesita actualización de nombre/desc
            "RobotId": 2001, "Robot": "P001_Facturacion_V2", "Descripcion": "Proceso de facturación mensual actualizado",
            "EsOnline_SAM": False, "Activo_SAM": True
        },
        { # Caso 2: Nuevo robot para insertar
            "RobotId": 2005, "Robot": "P005_ReportesDiarios", "Descripcion": "Genera reportes diarios de ventas",
            "EsOnline_SAM": True, "Activo_SAM": True
        },
        { # Caso 3: Robot existente, pero ahora inactivo
            "RobotId": 2002, "Robot": "P002_Conciliaciones_OLD", "Descripcion": "Conciliaciones bancarias (versión antigua)",
            "EsOnline_SAM": False, "Activo_SAM": False # Marcar como inactivo
        },
        { # Caso 4: Robot sin descripción
            "RobotId": 2006, "Robot": "P006_UtilitarioSimple", "Descripcion": None,
            "EsOnline_SAM": True, "Activo_SAM": True
        }
    ]

    input("PREPARACIÓN: Asegúrate que tu tabla dbo.Robots esté lista para probar el MERGE (ej. RobotId 2001 existe, 2005 no). Presiona Enter para continuar...")

    try:
        logger.info(f"Llamando a merge_robots_sam con {len(lista_robots_ficticios)} registros ficticios.")
        filas_afectadas_rb = db_connector.merge_robots_sam(lista_robots_ficticios)
        logger.info(f"merge_robots_sam ejecutado. Filas afectadas/procesadas aprox: {filas_afectadas_rb}")
        print(f"Resultado merge_robots_sam (filas afectadas aprox): {filas_afectadas_rb}")
        print("Verifica la tabla dbo.Robots en tu base de datos SAM.")
    except Exception as e:
        logger.error(f"Error durante la prueba de merge_robots_sam: {e}", exc_info=True)
        print(f"ERROR en merge_robots_sam: {e}")

    # --- Limpieza ---
    try:
        db_connector.cerrar_conexion()
    except Exception as e:
        logger.error(f"Error cerrando la conexión de BD al final de la prueba: {e}")

    logger.info("--- Prueba de Métodos MERGE Finalizada ---")

if __name__ == "__main__":
    # --- MUY IMPORTANTE: Configura tu archivo .env para la BD de SAM ---
    # SQL_SERVER_HOST=tu_servidor_sql
    # SQL_SERVER_DB_SAM=SAM # O el nombre de tu BD SAM para el Lanzador
    # SQL_SERVER_UID=tu_usuario_sql
    # SQL_SERVER_PWD=tu_contraseña_sql
    
    print("**************************************************************************")
    print("ATENCIÓN: Esta prueba realizará operaciones MERGE en tu base de datos SAM.")
    print(f"Asegúrate de que la configuración en .env apunte a una BD DE PRUEBAS.")
    print("Se recomienda tener un backup si trabajas sobre datos importantes.")
    print("**************************************************************************")
    confirm = input("¿Estás seguro de que quieres continuar con la prueba de MERGE? (s/N): ")
    if confirm.lower() == 's':
        run_merge_tests()
    else:
        print("Prueba de MERGE cancelada por el usuario.")