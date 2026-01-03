"""
Script para debuggear create_schedule y ver exactamente qué se está enviando
"""

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent
src_dir = root_dir / "src"
sys.path.insert(0, str(src_dir))

# Inicializar ConfigLoader antes de usar ConfigManager (igual que en los servicios)
from sam.common.config_loader import ConfigLoader  # noqa: E402
from sam.common.logging_setup import setup_logging  # noqa: E402

# Inicializar el servicio (necesario para cargar .env y configuración)
SERVICE_NAME = "debug_create_schedule"
ConfigLoader.initialize_service(SERVICE_NAME)
setup_logging(service_name=SERVICE_NAME)

from sam.common.config_manager import ConfigManager  # noqa: E402
from sam.common.database import DatabaseConnector  # noqa: E402


def debug_create_schedule():
    """Debug de create_schedule para ver qué se envía"""

    print("=" * 60)
    print("DEBUG: create_schedule")
    print("=" * 60)
    print()

    # Obtener configuración
    try:
        config = ConfigManager.get_sql_server_config("SQL_SAM")
        db = DatabaseConnector(
            servidor=config["servidor"],
            base_datos=config["base_datos"],
            usuario=config["usuario"],
            contrasena=config["contrasena"],
        )
    except Exception as e:
        print(f"[ERROR] No se pudo conectar: {e}")
        return

    try:
        # Obtener robot y equipo
        robots = db.ejecutar_consulta("SELECT TOP 1 RobotId, Robot FROM dbo.Robots WHERE Activo = 1", es_select=True)
        if not robots:
            print("[ERROR] No hay robots")
            return

        robot = robots[0]
        robot_id = robot["RobotId"]
        robot_nombre = robot["Robot"]

        equipos = db.ejecutar_consulta(
            "SELECT TOP 1 EquipoId, Equipo FROM dbo.Equipos WHERE Activo_SAM = 1", es_select=True
        )
        if not equipos:
            print("[ERROR] No hay equipos")
            return

        equipo = equipos[0]
        equipo_id = equipo["EquipoId"]
        equipo_nombre = equipo["Equipo"]

        print(f"Robot: {robot_nombre} (ID: {robot_id})")
        print(f"Equipo: {equipo_nombre} (ID: {equipo_id})")
        print()

        # Simular lo que hace create_schedule
        print("1. Obteniendo nombre del robot...")
        robot_nombre_result = db.ejecutar_consulta(
            "SELECT Robot FROM dbo.Robots WHERE RobotId = ?", (robot_id,), es_select=True
        )
        robot_str = robot_nombre_result[0]["Robot"]
        print(f"   robot_str = '{robot_str}'")
        print()

        print("2. Obteniendo nombres de equipos...")
        equipos_str = ""
        equipos_ids = [equipo_id]
        if equipos_ids:
            placeholders = ",".join("?" for _ in equipos_ids)
            equipos_nombres_result = db.ejecutar_consulta(
                f"SELECT STRING_AGG(CAST(Equipo AS NVARCHAR(MAX)), ',') AS Nombres FROM dbo.Equipos WHERE EquipoId IN ({placeholders})",
                tuple(equipos_ids),
                es_select=True,
            )
            if equipos_nombres_result and equipos_nombres_result[0]["Nombres"]:
                equipos_str = equipos_nombres_result[0]["Nombres"]
        print(f"   equipos_str = '{equipos_str}'")
        print()

        print("3. Construyendo query y parámetros...")
        # Usar sintaxis EXEC con parámetros nombrados (igual que en database.py)
        query = "EXEC dbo.CrearProgramacion @Robot=?, @Equipos=?, @TipoProgramacion=?, @HoraInicio=?, @Tolerancia=?, @DiasSemana=?, @DiaDelMes=?, @FechaEspecifica=?, @DiaInicioMes=?, @DiaFinMes=?, @UltimosDiasMes=?, @UsuarioCrea=?, @EsCiclico=?, @HoraFin=?, @FechaInicioVentana=?, @FechaFinVentana=?, @IntervaloEntreEjecuciones=?"

        # Contar parámetros en query
        param_count_query = query.count("?")
        print(f"   Parámetros en query: {param_count_query}")
        print()

        # Simular datos como vendrían del frontend
        dia_inicio = None
        dia_fin = None

        params = (
            robot_str,
            equipos_str,
            "Diaria",
            "09:00:00",
            60,
            None,  # DiasSemana
            None,  # DiaDelMes
            None,  # FechaEspecifica
            dia_inicio,
            dia_fin,
            None,  # UltimosDiasMes
            "WebApp_Creation",
            False,  # EsCiclico
            None,  # HoraFin
            None,  # FechaInicioVentana
            None,  # FechaFinVentana
            None,  # IntervaloEntreEjecuciones
        )

        param_count_params = len(params)
        print(f"   Parámetros en tuple: {param_count_params}")
        print()

        if param_count_query != param_count_params:
            print(
                f"[ERROR] Desajuste: query tiene {param_count_query} parámetros, pero tuple tiene {param_count_params}"
            )
        else:
            print("[OK] Número de parámetros coincide")
        print()

        print("4. Detalle de parámetros:")
        param_names = [
            "@Robot",
            "@Equipos",
            "@TipoProgramacion",
            "@HoraInicio",
            "@Tolerancia",
            "@DiasSemana",
            "@DiaDelMes",
            "@FechaEspecifica",
            "@DiaInicioMes",
            "@DiaFinMes",
            "@UltimosDiasMes",
            "@UsuarioCrea",
            "@EsCiclico",
            "@HoraFin",
            "@FechaInicioVentana",
            "@FechaFinVentana",
            "@IntervaloEntreEjecuciones",
        ]

        for i, (name, value) in enumerate(zip(param_names, params), 1):
            value_str = str(value) if value is not None else "None"
            value_type = type(value).__name__
            print(f"   {i:2d}. {name:25s} = {value_str:30s} ({value_type})")
        print()

        print("5. Ejecutando SP...")
        try:
            db.ejecutar_consulta(query, params, es_select=False)
            print("[OK] SP ejecutado exitosamente")
        except Exception as e:
            print("[ERROR] Error al ejecutar SP:")
            print(f"   Tipo: {type(e).__name__}")
            print(f"   Mensaje: {str(e)}")
            if hasattr(e, "args") and len(e.args) > 0:
                print(f"   Detalle: {e.args[0]}")

    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.cerrar_conexiones_pool()


if __name__ == "__main__":
    debug_create_schedule()
