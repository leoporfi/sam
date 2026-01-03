"""
Script SIMPLE para probar robots cíclicos
Ejecutar: python probar_ciclicos.py
"""

import os
import sys

# Agregar el path del proyecto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sam.common.config_manager import ConfigManager  # noqa: E402
from sam.common.database import DatabaseConnector  # noqa: E402
from sam.web.backend.schemas import ScheduleData  # noqa: E402


def obtener_ids_validos(db: DatabaseConnector):
    """Obtiene un RobotId y EquipoId válidos de la BD"""
    print("Obteniendo RobotId y EquipoId válidos...")

    # Obtener un robot activo
    robot_result = db.ejecutar_consulta(
        "SELECT TOP 1 RobotId, Robot FROM dbo.Robots WHERE Activo = 1 ORDER BY RobotId", es_select=True
    )

    # Obtener un equipo activo
    equipo_result = db.ejecutar_consulta(
        "SELECT TOP 1 EquipoId, Equipo FROM dbo.Equipos WHERE Activo_SAM = 1 ORDER BY EquipoId", es_select=True
    )

    if not robot_result:
        raise ValueError("[ERROR] No hay robots activos en la BD")
    if not equipo_result:
        raise ValueError("[ERROR] No hay equipos activos en la BD")

    robot_id = robot_result[0]["RobotId"]
    robot_nombre = robot_result[0]["Robot"]
    equipo_id = equipo_result[0]["EquipoId"]
    equipo_nombre = equipo_result[0]["Equipo"]

    print(f"   [OK] RobotId: {robot_id} ({robot_nombre})")
    print(f"   [OK] EquipoId: {equipo_id} ({equipo_nombre})")
    print()

    return robot_id, equipo_id


def verificar_programacion_creada(db: DatabaseConnector, robot_id: int):
    """Verifica que la programación se creó correctamente con los campos nuevos"""
    print("Verificando programación creada...")

    resultado = db.ejecutar_consulta(
        """
        SELECT TOP 1
            ProgramacionId,
            EsCiclico,
            HoraInicio,
            HoraFin,
            FechaInicioVentana,
            FechaFinVentana,
            IntervaloEntreEjecuciones,
            TipoProgramacion
        FROM dbo.Programaciones
        WHERE RobotId = ?
        ORDER BY ProgramacionId DESC
        """,
        (robot_id,),
        es_select=True,
    )

    if resultado:
        prog = resultado[0]
        print(f"   [OK] ProgramacionId: {prog['ProgramacionId']}")
        print(f"   [OK] EsCiclico: {prog['EsCiclico']}")
        print(f"   [OK] HoraInicio: {prog['HoraInicio']}")
        print(f"   [OK] HoraFin: {prog['HoraFin']}")
        print(f"   [OK] IntervaloEntreEjecuciones: {prog['IntervaloEntreEjecuciones']}")
        print()

        # Verificar que los campos nuevos están poblados
        if prog["EsCiclico"] == 1 and prog["HoraFin"] and prog["IntervaloEntreEjecuciones"]:
            print("   [OK] Todos los campos nuevos estan correctamente poblados!")
            return True
        else:
            print("   [WARN] Algunos campos nuevos no estan poblados correctamente")
            return False
    else:
        print("   [ERROR] No se encontro la programacion")
        return False


def probar_crear_programacion_ciclica():
    """Prueba crear una programación cíclica"""
    print("=" * 60)
    print("PRUEBA 1: Crear Programación Cíclica")
    print("=" * 60)
    print()

    try:
        # Conectar a la BD
        print("Conectando a la base de datos...")
        sql_config = ConfigManager.get_sql_server_config("SQL_SAM")
        db = DatabaseConnector(
            servidor=sql_config["servidor"],
            base_datos=sql_config["base_datos"],
            usuario=sql_config["usuario"],
            contrasena=sql_config["contrasena"],
        )
        print("   [OK] Conectado")
        print()

        # Obtener IDs válidos
        robot_id, equipo_id = obtener_ids_validos(db)

        # Crear programación cíclica
        print("Creando programación cíclica...")
        print("   Tipo: Diaria")
        print("   Horario: 09:00:00 - 17:00:00")
        print("   EsCiclico: True")
        print("   Intervalo: 30 minutos")
        print()

        schedule_data = ScheduleData(
            RobotId=robot_id,
            TipoProgramacion="Diaria",
            HoraInicio="09:00:00",
            HoraFin="17:00:00",
            Tolerancia=15,
            Equipos=[equipo_id],
            EsCiclico=True,
            IntervaloEntreEjecuciones=30,
        )

        from sam.web.backend import database as db_service

        db_service.create_schedule(db, schedule_data)

        print("   [OK] Programacion creada exitosamente!")
        print()

        # Verificar
        return verificar_programacion_creada(db, robot_id)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


def probar_retrocompatibilidad():
    """Prueba que las programaciones tradicionales siguen funcionando"""
    print("=" * 60)
    print("PRUEBA 2: Retrocompatibilidad")
    print("=" * 60)
    print()

    try:
        sql_config = ConfigManager.get_sql_server_config("SQL_SAM")
        db = DatabaseConnector(
            servidor=sql_config["servidor"],
            base_datos=sql_config["base_datos"],
            usuario=sql_config["usuario"],
            contrasena=sql_config["contrasena"],
        )

        robot_id, equipo_id = obtener_ids_validos(db)

        print("Creando programación tradicional (sin nuevos campos)...")
        print("   Tipo: Diaria")
        print("   HoraInicio: 10:00:00")
        print("   Sin EsCiclico, HoraFin, etc.")
        print()

        schedule_data = ScheduleData(
            RobotId=robot_id,
            TipoProgramacion="Diaria",
            HoraInicio="10:00:00",
            Tolerancia=15,
            Equipos=[equipo_id],
            # Sin EsCiclico, HoraFin, etc.
        )

        from sam.web.backend import database as db_service

        db_service.create_schedule(db, schedule_data)

        print("   [OK] Programacion tradicional creada exitosamente!")
        print()

        # Verificar que EsCiclico es NULL o 0
        resultado = db.ejecutar_consulta(
            """
            SELECT TOP 1 EsCiclico, HoraFin
            FROM dbo.Programaciones
            WHERE RobotId = ?
            ORDER BY ProgramacionId DESC
            """,
            (robot_id,),
            es_select=True,
        )

        if resultado:
            prog = resultado[0]
            if prog["EsCiclico"] is None or prog["EsCiclico"] == 0:
                print("   [OK] Retrocompatibilidad verificada: EsCiclico es NULL/0")
                return True
            else:
                print("   [WARN] EsCiclico deberia ser NULL/0 para programaciones tradicionales")
                return False
        else:
            print("   [ERROR] No se encontro la programacion")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("SCRIPT DE PRUEBA: Robots Cíclicos con Ventanas")
    print("=" * 60)
    print()

    # Prueba 1: Programación cíclica
    resultado1 = probar_crear_programacion_ciclica()
    print()

    # Prueba 2: Retrocompatibilidad
    resultado2 = probar_retrocompatibilidad()
    print()

    # Resumen
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    if resultado1 and resultado2:
        print("[OK] Todas las pruebas pasaron exitosamente!")
        print()
        print("Los robots ciclicos con ventanas estan funcionando correctamente.")
    else:
        print("[ERROR] Algunas pruebas fallaron. Revisar errores arriba.")
        print()
        print("Posibles causas:")
        print("  - Los SPs no tienen los nuevos parámetros (ejecutar update_stored_procedures_ciclicos.sql)")
        print("  - Error de conexión a la BD")
        print("  - No hay robots/equipos activos en la BD")
    print()
