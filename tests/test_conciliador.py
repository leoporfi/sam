import asyncio

# Asumimos que el script de test está en una carpeta 'tests/'
# y los fuentes están en 'src/', por lo que ajustamos el path.
from datetime import datetime
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import pytest

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.config_loader import ConfigLoader
from sam.common.database import DatabaseConnector

# --- Importar la clase que vamos a testear ---
# (Asegúrate de que la ruta sea correcta según tu estructura)
from sam.lanzador.service.conciliador import Conciliador


# --- Configuración de Fixtures de Pytest ---
@pytest.fixture(scope="session", autouse=True)
def setup_and_mock_config(pytestconfig):
    ConfigLoader.initialize_service("sam_test_session")

    # Mock de las configuraciones específicas
    mock_lanzador_config = {
        "conciliador_max_intentos_fallidos": 3,
        "dias_tolerancia_unknown": 90,
        "max_workers_lanzador": 10,
        "repeticiones": 1,
        "intervalo_lanzamiento": 60,
        "intervalo_sincronizacion": 300,
        "intervalo_conciliacion": 120,
    }

    with patch("sam.common.config_manager.ConfigManager.get_lanzador_config", return_value=mock_lanzador_config):
        yield


@pytest.fixture
def mock_db_connector():
    """Crea un mock para el DatabaseConnector."""
    # Usamos MagicMock para simular métodos síncronos como
    # obtener_ejecuciones_en_curso y ejecutar_consulta_multiple
    return MagicMock(spec=DatabaseConnector)


@pytest.fixture
def mock_aa_client():
    """Crea un mock para el AutomationAnywhereClient."""
    # Usamos AsyncMock porque sus métodos (ej. obtener_detalles) son async
    return AsyncMock(spec=AutomationAnywhereClient)


@pytest.fixture
def conciliador_service(mock_db_connector, mock_aa_client):
    """
    Crea una instancia del Conciliador con sus dependencias mockeadas.
    Usamos un umbral de 3 intentos para simular un entorno real.
    """
    return Conciliador(db_connector=mock_db_connector, aa_client=mock_aa_client, config={"dias_tolerancia_unknown": 90})


# --- Pruebas (Tests) ---


@pytest.mark.asyncio
async def test_conciliar_sin_bots_activos_no_hace_nada(conciliador_service, mock_db_connector, mock_aa_client):
    """
    Prueba que si la base de datos no devuelve bots en curso,
    el conciliador termina limpiamente sin llamar a la API.
    """
    # Arrange: La base de datos no devuelve ejecuciones
    mock_db_connector.obtener_ejecuciones_en_curso.return_value = []

    # Act: Ejecutamos el conciliador
    await conciliador_service.conciliar_ejecuciones()

    # Assert: Verificamos que solo se llamó a la BD
    mock_db_connector.obtener_ejecuciones_en_curso.assert_called_once()
    # NUNCA se debe llamar a la API de A360
    mock_aa_client.obtener_detalles_por_deployment_ids.assert_not_called()
    # NUNCA se debe llamar a ninguna consulta de actualización
    mock_db_connector.ejecutar_consulta.assert_not_called()
    mock_db_connector.ejecutar_consulta_multiple.assert_not_called()


@pytest.mark.asyncio
async def test_conciliar_bot_completado_actualiza_estado(conciliador_service, mock_db_connector, mock_aa_client):
    """
    Prueba el "Happy Path": un bot en 'RUNNING' es reportado como
    'COMPLETED' por la API y se actualiza en la BD.
    """
    # Arrange: Un bot en curso en la BD
    BOT_EN_CURSO = {"EjecucionId": 100, "DeploymentId": "dep-123"}
    mock_db_connector.obtener_ejecuciones_en_curso.return_value = [BOT_EN_CURSO]

    # La API de A360 devuelve que el bot ha completado
    API_RESPONSE = [{"deploymentId": "dep-123", "status": "COMPLETED", "endDateTime": "2025-11-11T14:00:00Z"}]
    mock_aa_client.obtener_detalles_por_deployment_ids.return_value = API_RESPONSE

    # Mockeamos la conversión de fecha para simplicidad
    # (Si no, tendríamos que mockear pytz y dateutil)
    with patch.object(
        conciliador_service, "_convertir_utc_a_local_sam", return_value=datetime(2025, 11, 11, 11, 0, 0)
    ) as mock_convertir_fecha:
        await conciliador_service.conciliar_ejecuciones()

        # Assert
        mock_db_connector.obtener_ejecuciones_en_curso.assert_called_once()
        mock_aa_client.obtener_detalles_por_deployment_ids.assert_called_with(["dep-123"])
        mock_convertir_fecha.assert_called_with("2025-11-11T14:00:00Z")
        mock_db_connector.ejecutar_consulta_multiple.assert_called_once()

        # Verificamos los parámetros de la actualización
        call_args = mock_db_connector.ejecutar_consulta_multiple.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "UPDATE dbo.Ejecuciones" in query
        assert "SET Estado = ?" in query
        assert "IntentosConciliadorFallidos = 0" in query  # Valida que resetea el contador
        assert "WHERE EjecucionId = ?" in query

        # Validamos los datos pasados
        assert params[0][0] == "COMPLETED"  # Estado
        assert params[0][2] == 100  # EjecucionId

        # 5. NO se llamó a la lógica de "perdidos" o "unknown de API"
        mock_db_connector.ejecutar_consulta.assert_not_called()


@pytest.mark.asyncio
async def test_conciliar_bot_perdido_NO_marca_unknown_Y_NO_incrementa_contador(
    conciliador_service, mock_db_connector, mock_aa_client
):
    """
    *** TEST CRÍTICO PARA LA NUEVA LÓGICA ***
    Prueba que si un bot en 'RUNNING' NO es devuelto por la API
    (es un "deployment perdido"), el sistema NO lo marca como UNKNOWN
    y NO incrementa su contador de intentos.
    """
    # Arrange: Un bot en curso en la BD
    BOT_PERDIDO = {"EjecucionId": 200, "DeploymentId": "dep-456"}
    mock_db_connector.obtener_ejecuciones_en_curso.return_value = [BOT_PERDIDO]

    # La API de A360 devuelve una lista VACÍA
    API_RESPONSE = []
    mock_aa_client.obtener_detalles_por_deployment_ids.return_value = API_RESPONSE

    # Act
    await conciliador_service.conciliar_ejecuciones()

    # Assert
    # 1. Se buscaron los bots
    mock_db_connector.obtener_ejecuciones_en_curso.assert_called_once()
    # 2. Se consultó a la API
    mock_aa_client.obtener_detalles_por_deployment_ids.assert_called_with(["dep-456"])

    # 3. *** ASSERT CLAVE ***
    # NO se debe llamar a NINGUNA consulta de actualización.
    # Ni para actualizar estado final (no hay)
    # Ni para incrementar contador (lógica eliminada)
    # Ni para marcar como UNKNOWN (lógica eliminada)
    mock_db_connector.ejecutar_consulta_multiple.assert_not_called()
    mock_db_connector.ejecutar_consulta.assert_not_called()

    # El bot simplemente se reintentará en el próximo ciclo.


@pytest.mark.asyncio
async def test_conciliar_bot_api_reporta_unknown_INCREMENTA_contador_y_actualiza_timestamp(
    conciliador_service, mock_db_connector, mock_aa_client
):
    """
    Prueba que si la API reporta "UNKNOWN", el sistema actualiza el estado,
    INCREMENTA el contador de fallos y actualiza FechaUltimoUNKNOWN,
    pero NO establece FechaFin.
    """
    # Arrange: Un bot en curso en la BD
    BOT_EN_CURSO = {"EjecucionId": 300, "DeploymentId": "dep-789"}
    mock_db_connector.obtener_ejecuciones_en_curso.return_value = [BOT_EN_CURSO]

    # La API de A360 devuelve que el bot está "UNKNOWN"
    API_RESPONSE = [
        {
            "deploymentId": "dep-789",
            "status": "UNKNOWN",
            "endDateTime": None,  # Importante: no hay fecha fin
        }
    ]
    mock_aa_client.obtener_detalles_por_deployment_ids.return_value = API_RESPONSE

    # Act
    await conciliador_service.conciliar_ejecuciones()

    # Assert
    # 1. Se buscaron los bots y se llamó a la API
    mock_db_connector.obtener_ejecuciones_en_curso.assert_called_once()
    mock_aa_client.obtener_detalles_por_deployment_ids.assert_called_with(["dep-789"])

    # 2. Se debe llamar a la consulta MÚLTIPLE (para la query_unknown)
    mock_db_connector.ejecutar_consulta_multiple.assert_called_once()

    # 3. Verificamos los argumentos de esa llamada
    call_args = mock_db_connector.ejecutar_consulta_multiple.call_args
    query = call_args[0][0]  # La query SQL
    params = call_args[0][1]  # Los parámetros

    # 4. Validamos la QUERY
    # El estado se setea directamente en la query
    assert "SET Estado = 'UNKNOWN'" in query
    # Se actualiza el timestamp
    assert "FechaUltimoUNKNOWN = GETDATE()" in query
    # Se INCREMENTA el contador
    assert "IntentosConciliadorFallidos = IntentosConciliadorFallidos + 1" in query
    # NO se debe setear FechaFin
    assert "FechaFin = ?" not in query
    assert "FechaFin = GETDATE()" not in query

    # 5. Validamos los PARÁMETROS
    # La query_unknown solo espera el EjecucionId
    assert params == [(300,)]  # Lista de tuplas -> [(EjecucionId,)]
