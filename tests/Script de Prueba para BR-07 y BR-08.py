import logging

# Configuración básica de logging para ver los mensajes del script
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# Mock de las clases de dependencia para poder instanciar SincronizadorComun
class MockDbConnector:
    def merge_robots(self, *args, **kwargs):
        pass

    def merge_equipos(self, *args, **kwargs):
        pass


class MockAaClient:
    async def obtener_robots(self):
        return []

    async def obtener_devices(self):
        return []

    async def obtener_usuarios_detallados(self):
        return []


# Importamos la clase a probar DESPUÉS de los mocks si es necesario
from sam.common.sincronizador_comun import SincronizadorComun

# --- Datos de Prueba ---
mock_users_api = [
    {"id": 101, "username": "user_attended", "licenseFeatures": ["ATTENDEDRUNTIME"]},
    {"id": 102, "username": "user_runtime", "licenseFeatures": ["RUNTIME", "some_other_license"]},
    {"id": 103, "username": "user_unattended", "licenseFeatures": ["UNATTENDEDRUNTIME"]},
    {"id": 104, "username": "user_no_license", "licenseFeatures": []},
    {"id": 105, "username": "user_missing_key"},
    {"id": 106, "username": "user_valid_secondary", "licenseFeatures": ["RUNTIME"]},
]

mock_devices_api = [
    # Caso 1: Válido, usuario único con ATTENDEDRUNTIME
    {"id": 201, "hostName": "Device-01", "status": "CONNECTED", "defaultUsers": [{"id": 101}]},
    # Caso 2: Válido, usuario único con RUNTIME
    {"id": 202, "hostName": "Device-02", "status": "CONNECTED", "defaultUsers": [{"id": 102}]},
    # <<-- NUEVO CASO DE PRUEBA -->>
    # Caso 7: Válido, el primer usuario no tiene licencia válida, pero el segundo sí.
    # Debe tomar los datos del usuario 106.
    {
        "id": 207,
        "hostName": "Device-07-MultiUser",
        "status": "CONNECTED",
        "defaultUsers": [{"id": 103, "username": "user_unattended"}, {"id": 106, "username": "user_valid_secondary"}],
    },
    # --- Casos inválidos ---
    {"id": 203, "hostName": "Device-03", "status": "CONNECTED", "defaultUsers": [{"id": 103}]},
    {"id": 204, "hostName": "Device-04", "status": "CONNECTED", "defaultUsers": [{"id": 104}]},
    {"id": 205, "hostName": "Device-05", "status": "CONNECTED", "defaultUsers": [{"id": 999}]},
    {"id": 206, "hostName": "Device-06", "status": "CONNECTED", "defaultUsers": []},
    # <<-- NUEVO CASO DE PRUEBA -->>
    # Caso 8: Inválido, ambos usuarios tienen licencias no válidas.
    {
        "id": 208,
        "hostName": "Device-08-MultiUser-Invalid",
        "status": "CONNECTED",
        "defaultUsers": [{"id": 103, "username": "user_unattended"}, {"id": 104, "username": "user_no_license"}],
    },
]


def run_test():
    """
    Ejecuta la prueba de la lógica de filtrado de licencias, ahora con casos multi-usuario.
    """
    print("--- 1. Ejecutando prueba para BR-07 y BR-08 (con escenario multi-usuario) ---")

    sincronizador = SincronizadorComun(MockDbConnector(), MockAaClient())

    resultado = sincronizador._procesar_y_mapear_equipos(mock_devices_api, mock_users_api)

    print(f"\nSe procesaron {len(mock_devices_api)} dispositivos y se obtuvieron {len(resultado)} equipos válidos.")

    print("\n--- 2. Verificación de Resultados ---")

    ids_resultado = {item["EquipoId"] for item in resultado}
    ids_esperados = {201, 202, 207}  # Ahora esperamos que el dispositivo 207 sea incluido

    print(f"IDs obtenidos: {ids_resultado if ids_resultado else '{}'}")
    print(f"IDs esperados: {ids_esperados}")

    # Verificación de correctitud
    is_ok = True
    error_msgs = []

    if ids_resultado != ids_esperados:
        is_ok = False
        if not ids_esperados.issubset(ids_resultado):
            error_msgs.append(f"   - Faltan equipos que deberían estar: {ids_esperados - ids_resultado}")
        if not ids_resultado.issubset(ids_esperados):
            error_msgs.append(f"   - Se incluyeron equipos que no deberían estar: {ids_resultado - ids_esperados}")

    # Verificación específica para el caso multi-usuario (Device 207)
    device_207_data = next((item for item in resultado if item["EquipoId"] == 207), None)
    if device_207_data:
        if device_207_data["UserId"] != 106:
            is_ok = False
            error_msgs.append(
                f"   - ERROR: El dispositivo 207 se asoció al usuario incorrecto (ID: {device_207_data['UserId']}). Debió ser el 106."
            )
    elif 207 in ids_esperados:
        is_ok = False
        error_msgs.append("   - ERROR: El dispositivo 207 (multi-usuario válido) no fue incluido en el resultado.")

    if is_ok:
        print(
            "\n=> RESULTADO: ÉXITO. El filtro de licencias funciona como se esperaba, incluyendo el caso multi-usuario."
        )
        print(
            "   - Se seleccionó correctamente el primer usuario con licencia válida en un dispositivo con múltiples usuarios."
        )
    else:
        print("\n=> RESULTADO: ERROR. La lógica de procesamiento no es correcta.")
        for msg in error_msgs:
            print(msg)


if __name__ == "__main__":
    run_test()
