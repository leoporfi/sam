"""
Script SIMPLE para probar creación de programación cíclica
Ejecutar: python probar_programacion_ciclica_simple.py
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
    # Obtener un robot activo
    robot_result = db.ejecutar_consulta(
        "SELECT TOP 1 RobotId, Robot FROM dbo.Robots WHERE Activo = 1 ORDER BY RobotId", es_select=True
    )

    # Obtener un equipo activo
    equipo_result = db.ejecutar_consulta(
        "SELECT TOP 1 EquipoId, Equipo FROM dbo.Equipos WHERE Activo_SAM = 1 ORDER BY EquipoId", es_select=True
    )

    if not robot_result:
        raise ValueError("No hay robots activos en la BD")
    if not equipo_result:
        raise ValueError("No hay equipos activos en la BD")

    return robot_result[0]["RobotId"], equipo_result[0]["EquipoId"]


def probar_crear_programacion_ciclica():
    """Prueba crear una programación cíclica"""
    print("=" * 60)
    print("PRUEBA: Crear Programación Cíclica")
    print("=" * 60)
    print()

    try:
        # Conectar a la BD
        config = ConfigManager()
        db = DatabaseConnector(
            servidor=config.get("SQL_SAM_SERVIDOR"),
            base_datos=config.get("SQL_SAM_BASE_DATOS"),
            usuario=config.get("SQL_SAM_USUARIO"),
            contrasena=config.get("SQL_SAM_CONTRASENA"),
        )

        # Obtener IDs válidos
        print("Obteniendo RobotId y EquipoId válidos...")
        robot_id, equipo_id = obtener_ids_validos(db)
        print(f"   RobotId: {robot_id}")
        print(f"   EquipoId: {equipo_id}")
        print()

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

        print("✅ Programación cíclica creada exitosamente!")
        print()
        print("Verificar en la BD:")
        print("   SELECT TOP 1 ProgramacionId, EsCiclico, HoraFin, IntervaloEntreEjecuciones")
        print("   FROM Programaciones")
        print("   ORDER BY ProgramacionId DESC")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def probar_retrocompatibilidad():
    """Prueba que las programaciones tradicionales siguen funcionando"""
    print("=" * 60)
    print("PRUEBA: Retrocompatibilidad")
    print("=" * 60)
    print()

    try:
        config = ConfigManager()
        db = DatabaseConnector(
            servidor=config.get("SQL_SAM_SERVIDOR"),
            base_datos=config.get("SQL_SAM_BASE_DATOS"),
            usuario=config.get("SQL_SAM_USUARIO"),
            contrasena=config.get("SQL_SAM_CONTRASENA"),
        )

        robot_id, equipo_id = obtener_ids_validos(db)

        print("Creando programación tradicional (sin nuevos campos)...")

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

        print("✅ Retrocompatibilidad verificada: Las programaciones tradicionales funcionan.")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
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
        print("✅ Todas las pruebas pasaron exitosamente!")
    else:
        print("❌ Algunas pruebas fallaron. Revisar errores arriba.")
    print()
