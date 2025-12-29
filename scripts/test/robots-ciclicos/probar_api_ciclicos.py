"""
Script para probar la API de programaciones cíclicas
Ejecutar: python probar_api_ciclicos.py
"""

import json
import sys

import requests

# Configuración
BASE_URL = "http://localhost:8000"  # Ajustar si es necesario
API_KEY = None  # Si requiere autenticación, agregar aquí


def obtener_robots_disponibles():
    """Obtiene la lista de robots disponibles desde la API"""
    try:
        url = f"{BASE_URL}/api/robots"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # La respuesta puede ser una lista o un dict con 'robots'
        if isinstance(data, list):
            robots = data
        elif isinstance(data, dict) and "robots" in data:
            robots = data["robots"]
        else:
            robots = []

        return robots
    except Exception as e:
        print(f"[ERROR] No se pudo obtener robots: {e}")
        return []


def obtener_equipos_disponibles():
    """Obtiene la lista de equipos disponibles desde la API"""
    try:
        url = f"{BASE_URL}/api/devices"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # La respuesta puede ser una lista o un dict con 'devices'
        if isinstance(data, list):
            equipos = data
        elif isinstance(data, dict) and "devices" in data:
            equipos = data["devices"]
        else:
            equipos = []

        return equipos
    except Exception as e:
        print(f"[ERROR] No se pudo obtener equipos: {e}")
        return []


def crear_programacion_ciclica(data: dict):
    """Crea una programación cíclica usando la API"""
    url = f"{BASE_URL}/api/schedules"
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    try:
        print(f"Enviando request a: {url}")
        print(f"Payload: {json.dumps(data, indent=2)}")
        print()

        response = requests.post(url, json=data, headers=headers, timeout=30)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200 or response.status_code == 201:
            print("[OK] Programacion creada exitosamente!")
            try:
                result = response.json()
                print(f"Respuesta: {json.dumps(result, indent=2)}")
            except:
                print(f"Respuesta: {response.text}")
            return True
        else:
            print(f"[ERROR] Status Code: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"[ERROR] No se pudo conectar al servidor en {BASE_URL}")
        print("Verifica que el servicio web esté corriendo.")
        return False
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout al conectar con {BASE_URL}")
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        import traceback

        traceback.print_exc()
        return False


def probar_programacion_ciclica_simple():
    """Prueba crear una programación cíclica simple"""
    print("=" * 60)
    print("PRUEBA 1: Programación Cíclica Simple")
    print("=" * 60)
    print()

    # Obtener IDs válidos
    print("Obteniendo robots y equipos disponibles...")
    robots = obtener_robots_disponibles()
    equipos = obtener_equipos_disponibles()

    if not robots:
        print("[ERROR] No hay robots disponibles. Usando valores por defecto.")
        robot_id = 1
    else:
        robot_id = robots[0].get("RobotId", robots[0].get("robotId", 1))
        print(f"[OK] Usando RobotId: {robot_id}")

    if not equipos:
        print("[ERROR] No hay equipos disponibles. Usando valores por defecto.")
        equipo_id = 1
    else:
        equipo_id = equipos[0].get("EquipoId", equipos[0].get("equipoId", 1))
        print(f"[OK] Usando EquipoId: {equipo_id}")

    print()

    # Crear programación cíclica
    data = {
        "RobotId": robot_id,
        "TipoProgramacion": "Diaria",
        "HoraInicio": "09:00:00",
        "HoraFin": "17:00:00",
        "Tolerancia": 15,
        "Equipos": [equipo_id],
        "EsCiclico": True,
        "IntervaloEntreEjecuciones": 30,
    }

    return crear_programacion_ciclica(data)


def probar_programacion_ciclica_con_fechas():
    """Prueba crear una programación cíclica con ventana de fechas"""
    print()
    print("=" * 60)
    print("PRUEBA 2: Programación Cíclica con Ventana de Fechas")
    print("=" * 60)
    print()

    # Obtener IDs válidos
    robots = obtener_robots_disponibles()
    equipos = obtener_equipos_disponibles()

    robot_id = robots[0].get("RobotId", robots[0].get("robotId", 1)) if robots else 1
    equipo_id = equipos[0].get("EquipoId", equipos[0].get("equipoId", 1)) if equipos else 1

    # Crear programación cíclica con fechas
    data = {
        "RobotId": robot_id,
        "TipoProgramacion": "Semanal",
        "DiasSemana": "Lun,Mar,Mie,Jue,Vie",
        "HoraInicio": "08:00:00",
        "HoraFin": "18:00:00",
        "Tolerancia": 10,
        "Equipos": [equipo_id],
        "EsCiclico": True,
        "FechaInicioVentana": "2025-01-01",
        "FechaFinVentana": "2025-12-31",
        "IntervaloEntreEjecuciones": 60,
    }

    return crear_programacion_ciclica(data)


def probar_retrocompatibilidad():
    """Prueba que las programaciones tradicionales siguen funcionando"""
    print()
    print("=" * 60)
    print("PRUEBA 3: Retrocompatibilidad (Programación Tradicional)")
    print("=" * 60)
    print()

    # Obtener IDs válidos
    robots = obtener_robots_disponibles()
    equipos = obtener_equipos_disponibles()

    robot_id = robots[0].get("RobotId", robots[0].get("robotId", 1)) if robots else 1
    equipo_id = equipos[0].get("EquipoId", equipos[0].get("equipoId", 1)) if equipos else 1

    # Crear programación tradicional (sin nuevos campos)
    data = {
        "RobotId": robot_id,
        "TipoProgramacion": "Diaria",
        "HoraInicio": "10:00:00",
        "Tolerancia": 15,
        "Equipos": [equipo_id],
        # Sin EsCiclico, HoraFin, etc.
    }

    return crear_programacion_ciclica(data)


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("PRUEBA DE API: Robots Cíclicos con Ventanas")
    print("=" * 60)
    print()
    print(f"URL Base: {BASE_URL}")
    print()

    # Verificar que el servidor esté disponible
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        print("[OK] Servidor web disponible")
    except:
        print(f"[ADVERTENCIA] No se pudo conectar a {BASE_URL}")
        print("Asegurate de que el servicio web esté corriendo.")
        print()

    print()

    # Ejecutar pruebas
    resultado1 = probar_programacion_ciclica_simple()
    print()

    resultado2 = probar_programacion_ciclica_con_fechas()
    print()

    resultado3 = probar_retrocompatibilidad()
    print()

    # Resumen
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    if resultado1 and resultado2 and resultado3:
        print("[OK] Todas las pruebas pasaron exitosamente!")
    else:
        print("[ERROR] Algunas pruebas fallaron. Revisar errores arriba.")
    print()
