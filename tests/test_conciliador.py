# Asumimos que el script de test está en una carpeta 'tests/'
# y los fuentes están en 'src/', por lo que ajustamos el path.
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.config_loader import ConfigLoader
from sam.common.database import DatabaseConnector

# --- Importar la clase que vamos a testear ---
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
        "conciliador_max_intentos_inferencia": 5,
    }

    with patch("sam.common.config_manager.ConfigManager.get_lanzador_config", return_value=mock_lanzador_config):
        yield


@pytest.fixture
def mock_db_connector():
    """Crea un mock para el DatabaseConnector."""
    return MagicMock(spec=DatabaseConnector)


@pytest.fixture
def mock_aa_client():
    """Crea un mock para el AutomationAnywhereClient."""
    return AsyncMock(spec=AutomationAnywhereClient)


@pytest.fixture
def conciliador_service(mock_db_connector, mock_aa_client):
    """
    Crea una instancia del Conciliador con sus dependencias mockeadas.
    """
    return Conciliador(
        db_connector=mock_db_connector, aa_client=mock_aa_client, config={"conciliador_max_intentos_inferencia": 5}
    )


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
    mock_aa_client.obtener_ejecuciones_activas.assert_not_called()


@pytest.mark.asyncio
async def test_conciliar_bot_completado_actualiza_estado(conciliador_service, mock_db_connector, mock_aa_client):
    """
    Prueba el "Happy Path": un bot en 'RUNNING' es reportado como
    'COMPLETED' por la API y se actualiza en la BD.
    """
    # Arrange: Un bot en curso en la BD
    BOT_EN_CURSO = {"EjecucionId": 100, "DeploymentId": "dep-123"}
    mock_db_connector.obtener_ejecuciones_en_curso.return_value = [BOT_EN_CURSO]

    # La API de A360 devuelve que el bot ha completado (no está en activas, pero sí en detalles)
    mock_aa_client.obtener_ejecuciones_activas.return_value = []
    API_RESPONSE = [
        {
            "deploymentId": "dep-123",
            "status": "COMPLETED",
            "endDateTime": "2025-11-11T14:00:00Z",
            "startDateTime": "2025-11-11T13:00:00Z",
        }
    ]
    mock_aa_client.obtener_detalles_por_deployment_ids.return_value = API_RESPONSE

    # Mockeamos la conversión de fecha para simplicidad
    with patch.object(
        conciliador_service,
        "_convertir_utc_a_local_sam",
        side_effect=[datetime(2025, 11, 11, 11, 0, 0), datetime(2025, 11, 11, 10, 0, 0)],
    ):
        await conciliador_service.conciliar_ejecuciones()

        # Assert
        mock_db_connector.obtener_ejecuciones_en_curso.assert_called_once()
        mock_aa_client.obtener_ejecuciones_activas.assert_called_once()
        mock_aa_client.obtener_detalles_por_deployment_ids.assert_called_with(["dep-123"])

        # Verificamos los parámetros de la actualización
        # Se llama a ejecutar_consulta_multiple para actualizar el estado final
        assert mock_db_connector.ejecutar_consulta_multiple.call_count >= 1

        # Buscar la llamada que actualiza el estado a COMPLETED
        found_update = False
        for call in mock_db_connector.ejecutar_consulta_multiple.call_args_list:
            query = call[0][0]
            params = call[0][1]
            if "UPDATE dbo.Ejecuciones" in query and "SET Estado = ?" in query and params[0][0] == "COMPLETED":
                found_update = True
                assert params[0][3] == 100  # EjecucionId
                break
        assert found_update


@pytest.mark.asyncio
async def test_conciliar_bot_perdido_incrementa_contador(conciliador_service, mock_db_connector, mock_aa_client):
    """
    Prueba que si un bot desaparece de la lista de activos y la API no devuelve detalles,
    se incrementa el contador de intentos fallidos.
    """
    # Arrange: Un bot en curso en la BD
    BOT_PERDIDO = {"EjecucionId": 200, "DeploymentId": "dep-456", "IntentosConciliadorFallidos": 0}
    mock_db_connector.obtener_ejecuciones_en_curso.return_value = [BOT_PERDIDO]

    # La API de A360 devuelve listas VACÍAS
    mock_aa_client.obtener_ejecuciones_activas.return_value = []
    mock_aa_client.obtener_detalles_por_deployment_ids.return_value = []

    # Act
    await conciliador_service.conciliar_ejecuciones()

    # Assert
    mock_db_connector.obtener_ejecuciones_en_curso.assert_called_once()
    mock_aa_client.obtener_ejecuciones_activas.assert_called_once()
    mock_aa_client.obtener_detalles_por_deployment_ids.assert_called_with(["dep-456"])

    # Se debe llamar a ejecutar_consulta_multiple para incrementar el contador
    found_inc = False
    for call in mock_db_connector.ejecutar_consulta_multiple.call_args_list:
        query = call[0][0]
        params = call[0][1]
        if "SET IntentosConciliadorFallidos = ISNULL(IntentosConciliadorFallidos, 0) + 1" in query:
            found_inc = True
            assert params == [(200,)]
            break
    assert found_inc


@pytest.mark.asyncio
async def test_conciliar_bot_perdido_max_intentos_infiere_finalizacion(
    conciliador_service, mock_db_connector, mock_aa_client
):
    """
    Prueba que si un bot perdido supera el máximo de intentos, se infiere su finalización.
    """
    # Arrange: Un bot con 4 intentos fallidos (límite es 5)
    BOT_LIMITE = {"EjecucionId": 300, "DeploymentId": "dep-789", "IntentosConciliadorFallidos": 4}
    mock_db_connector.obtener_ejecuciones_en_curso.return_value = [BOT_LIMITE]

    mock_aa_client.obtener_ejecuciones_activas.return_value = []
    mock_aa_client.obtener_detalles_por_deployment_ids.return_value = []

    # Act
    await conciliador_service.conciliar_ejecuciones()

    # Assert
    found_infer = False
    for call in mock_db_connector.ejecutar_consulta_multiple.call_args_list:
        query = call[0][0]
        params = call[0][1]
        if "SET Estado = ?" in query and params[0][0] == "COMPLETED_INFERRED":
            found_infer = True
            assert params[0][2] == 300  # EjecucionId
            break
    assert found_infer


@pytest.mark.asyncio
async def test_conciliar_bot_api_reporta_unknown_INCREMENTA_contador(
    conciliador_service, mock_db_connector, mock_aa_client
):
    """
    Prueba que si la API reporta "UNKNOWN", el sistema actualiza el estado e incrementa el contador.
    """
    # Arrange: Un bot en curso en la BD
    BOT_EN_CURSO = {"EjecucionId": 400, "DeploymentId": "dep-999"}
    mock_db_connector.obtener_ejecuciones_en_curso.return_value = [BOT_EN_CURSO]

    # La API de A360 devuelve que el bot está "UNKNOWN" en la lista de activos
    API_RESPONSE = [{"deploymentId": "dep-999", "status": "UNKNOWN"}]
    mock_aa_client.obtener_ejecuciones_activas.return_value = API_RESPONSE

    # Act
    await conciliador_service.conciliar_ejecuciones()

    # Assert
    found_unknown = False
    for call in mock_db_connector.ejecutar_consulta_multiple.call_args_list:
        query = call[0][0]
        params = call[0][1]
        if (
            "SET Estado = 'UNKNOWN'" in query
            and "IntentosConciliadorFallidos = IntentosConciliadorFallidos + 1" in query
        ):
            found_unknown = True
            assert params == [(400,)]
            break
    assert found_unknown
