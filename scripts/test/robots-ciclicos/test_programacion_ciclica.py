"""
Script de prueba para crear una programación cíclica con ventanas
Usar desde Python o adaptar para Postman/curl
"""

import json
from datetime import date, time

import requests

# Configuración
BASE_URL = "http://localhost:8000"  # Ajustar según tu configuración
API_KEY = None  # Si requiere autenticación, agregar aquí

# Ejemplo 1: Programación cíclica simple (diaria, 9 AM a 5 PM)
programacion_ciclica_1 = {
    "RobotId": 1,  # Cambiar por un RobotId válido
    "TipoProgramacion": "Diaria",
    "HoraInicio": "09:00:00",
    "HoraFin": "17:00:00",  # Nuevo campo
    "Tolerancia": 15,
    "Equipos": [1],  # Cambiar por EquipoId válido
    "EsCiclico": True,  # Nuevo campo
    "IntervaloEntreEjecuciones": 30,  # Nuevo campo: cada 30 minutos
}

# Ejemplo 2: Programación cíclica con ventana de fechas
programacion_ciclica_2 = {
    "RobotId": 1,  # Cambiar por un RobotId válido
    "TipoProgramacion": "Semanal",
    "DiasSemana": "Lun,Mar,Mie,Jue,Vie",
    "HoraInicio": "08:00:00",
    "HoraFin": "18:00:00",  # Nuevo campo
    "Tolerancia": 10,
    "Equipos": [1],  # Cambiar por EquipoId válido
    "EsCiclico": True,  # Nuevo campo
    "FechaInicioVentana": "2025-01-01",  # Nuevo campo
    "FechaFinVentana": "2025-12-31",  # Nuevo campo
    "IntervaloEntreEjecuciones": 60,  # Nuevo campo: cada hora
}

# Ejemplo 3: Programación tradicional (sin cambios, para verificar retrocompatibilidad)
programacion_tradicional = {
    "RobotId": 1,  # Cambiar por un RobotId válido
    "TipoProgramacion": "Diaria",
    "HoraInicio": "10:00:00",
    "Tolerancia": 15,
    "Equipos": [1],  # Sin nuevos campos - debe funcionar igual que antes
}


def crear_programacion(data: dict):
    """Crea una programación usando la API"""
    url = f"{BASE_URL}/api/schedules"
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        print(f"✅ Programación creada exitosamente:")
        print(f"   Respuesta: {response.json()}")
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error HTTP: {e}")
        if e.response.text:
            print(f"   Detalle: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def probar_programacion_ciclica():
    """Prueba crear una programación cíclica"""
    print("=" * 60)
    print("PRUEBA: Crear Programación Cíclica")
    print("=" * 60)
    print()

    print("Ejemplo 1: Programación cíclica diaria (9 AM - 5 PM, cada 30 min)")
    print("-" * 60)
    resultado = crear_programacion(programacion_ciclica_1)
    print()

    if resultado:
        print("✅ Prueba exitosa: La programación cíclica se creó correctamente.")
        print("   Verifica en la base de datos que los campos nuevos están poblados:")
        print("   - EsCiclico = 1")
        print("   - HoraFin = '17:00:00'")
        print("   - IntervaloEntreEjecuciones = 30")
    else:
        print("❌ Prueba fallida: Revisar errores arriba.")

    return resultado


def probar_retrocompatibilidad():
    """Prueba que las programaciones tradicionales siguen funcionando"""
    print("=" * 60)
    print("PRUEBA: Retrocompatibilidad (Programación Tradicional)")
    print("=" * 60)
    print()

    print("Creando programación sin nuevos campos...")
    resultado = crear_programacion(programacion_tradicional)
    print()

    if resultado:
        print("✅ Retrocompatibilidad verificada: Las programaciones tradicionales funcionan.")
    else:
        print("❌ Error: Las programaciones tradicionales deberían funcionar.")

    return resultado


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("SCRIPT DE PRUEBA: Robots Cíclicos con Ventanas")
    print("=" * 60)
    print()
    print("IMPORTANTE:")
    print("1. Ajustar BASE_URL si es necesario")
    print("2. Ajustar RobotId y EquipoId con valores válidos de tu BD")
    print("3. Asegurar que el servicio web esté corriendo")
    print("4. Ejecutar update_ActualizarProgramacionSimple.sql en la BD primero")
    print()

    # Descomentar para ejecutar pruebas
    # probar_programacion_ciclica()
    # print()
    # probar_retrocompatibilidad()
