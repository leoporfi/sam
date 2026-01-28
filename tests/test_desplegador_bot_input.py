"""
Tests para la funcionalidad de parámetros personalizados de bot_input en el Desplegador.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.apigw_client import ApiGatewayClient
from sam.common.database import DatabaseConnector
from sam.common.mail_client import EmailAlertClient
from sam.lanzador.service.desplegador import Desplegador

# Marcamos todas las pruebas en este módulo para que usen asyncio.
pytestmark = pytest.mark.asyncio


# Sobrescribir el fixture problemático del conftest.py principal
@pytest.fixture(scope="session", autouse=True)
def setup_and_mock_config(pytestconfig):
    """Fixture vacío que sobrescribe el del conftest.py principal."""
    # No hacer nada - estos tests no necesitan mockear ConfigManager
    yield


@pytest.fixture
def mock_db_connector():
    """Crea un mock del DatabaseConnector."""
    connector = MagicMock(spec=DatabaseConnector)
    connector.ejecutar_consulta = MagicMock(return_value=[])
    connector.obtener_robots_ejecutables = MagicMock(return_value=[])
    connector.insertar_registro_ejecucion = MagicMock()
    return connector


@pytest.fixture
def mock_aa_client():
    """Crea un mock del AutomationAnywhereClient."""
    client = AsyncMock(spec=AutomationAnywhereClient)
    client.desplegar_bot_v4 = AsyncMock(return_value={"deploymentId": "test-deployment-123"})
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_api_gateway_client():
    """Crea un mock del ApiGatewayClient."""
    client = AsyncMock(spec=ApiGatewayClient)
    client.get_auth_header = AsyncMock(return_value={"Authorization": "Bearer test-token"})
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_email_client():
    """Crea un mock del EmailAlertClient."""
    client = MagicMock(spec=EmailAlertClient)
    client.send_alert = MagicMock()
    return client


@pytest.fixture
def default_config():
    """Configuración por defecto del lanzador."""
    return {
        "repeticiones": 3,
        "max_workers_lanzador": 10,
        "max_reintentos_deploy": 2,
        "delay_reintentos_deploy_seg": 5,
        "pausa_lanzamiento": (None, None),
    }


@pytest.fixture
def desplegador(mock_db_connector, mock_aa_client, mock_api_gateway_client, mock_email_client, default_config):
    """Crea una instancia del Desplegador con mocks."""
    return Desplegador(
        db_connector=mock_db_connector,
        aa_client=mock_aa_client,
        api_gateway_client=mock_api_gateway_client,
        notificador=mock_email_client,
        cfg_lanzador=default_config,
        callback_token="test-callback-token",
    )


class TestObtenerBotInputRobot:
    """Tests para el método _obtener_bot_input_robot."""

    async def test_usar_parametros_personalizados_cuando_existen(self, desplegador, mock_db_connector):
        """Verifica que se usan los parámetros personalizados cuando el robot los tiene configurados."""
        # Arrange
        robot_id = 123
        parametros_personalizados = {"in_NumRepeticion": {"type": "NUMBER", "number": "5"}}
        mock_db_connector.ejecutar_consulta.return_value = [{"Parametros": json.dumps(parametros_personalizados)}]

        default_bot_input = {"in_NumRepeticion": {"type": "NUMBER", "number": "3"}}

        # Act
        result = desplegador._obtener_bot_input_robot(robot_id, default_bot_input)

        # Assert
        assert result == parametros_personalizados
        assert result["in_NumRepeticion"]["number"] == "5"
        mock_db_connector.ejecutar_consulta.assert_called_once_with(
            "SELECT Parametros FROM dbo.Robots WHERE RobotId = ?", (robot_id,), es_select=True
        )

    async def test_usar_valor_por_defecto_cuando_no_hay_parametros(self, desplegador, mock_db_connector):
        """Verifica que se usa el valor por defecto cuando el robot no tiene parámetros configurados."""
        # Arrange
        robot_id = 456
        mock_db_connector.ejecutar_consulta.return_value = [{"Parametros": None}]

        default_bot_input = {"in_NumRepeticion": {"type": "NUMBER", "number": "3"}}

        # Act
        result = desplegador._obtener_bot_input_robot(robot_id, default_bot_input)

        # Assert
        assert result == default_bot_input
        assert result["in_NumRepeticion"]["number"] == "3"

    async def test_usar_valor_por_defecto_cuando_parametros_esta_vacio(self, desplegador, mock_db_connector):
        """Verifica que se usa el valor por defecto cuando el campo Parametros está vacío."""
        # Arrange
        robot_id = 789
        mock_db_connector.ejecutar_consulta.return_value = [{"Parametros": ""}]

        default_bot_input = {"in_NumRepeticion": {"type": "NUMBER", "number": "3"}}

        # Act
        result = desplegador._obtener_bot_input_robot(robot_id, default_bot_input)

        # Assert
        assert result == default_bot_input

    async def test_usar_valor_por_defecto_cuando_json_invalido(self, desplegador, mock_db_connector):
        """Verifica que se usa el valor por defecto cuando el JSON de parámetros es inválido."""
        # Arrange
        robot_id = 999
        mock_db_connector.ejecutar_consulta.return_value = [{"Parametros": "{invalid json"}]

        default_bot_input = {"in_NumRepeticion": {"type": "NUMBER", "number": "3"}}

        # Act
        result = desplegador._obtener_bot_input_robot(robot_id, default_bot_input)

        # Assert
        assert result == default_bot_input

    async def test_usar_valor_por_defecto_cuando_json_no_es_dict(self, desplegador, mock_db_connector):
        """Verifica que se usa el valor por defecto cuando el JSON no es un diccionario."""
        # Arrange
        robot_id = 111
        mock_db_connector.ejecutar_consulta.return_value = [{"Parametros": '["not", "a", "dict"]'}]

        default_bot_input = {"in_NumRepeticion": {"type": "NUMBER", "number": "3"}}

        # Act
        result = desplegador._obtener_bot_input_robot(robot_id, default_bot_input)

        # Assert
        assert result == default_bot_input

    async def test_usar_valor_por_defecto_cuando_error_en_consulta(self, desplegador, mock_db_connector):
        """Verifica que se usa el valor por defecto cuando hay un error al consultar la BD."""
        # Arrange
        robot_id = 222
        mock_db_connector.ejecutar_consulta.side_effect = Exception("Error de conexión")

        default_bot_input = {"in_NumRepeticion": {"type": "NUMBER", "number": "3"}}

        # Act
        result = desplegador._obtener_bot_input_robot(robot_id, default_bot_input)

        # Assert
        assert result == default_bot_input

    async def test_usar_valor_por_defecto_cuando_robot_no_existe(self, desplegador, mock_db_connector):
        """Verifica que se usa el valor por defecto cuando el robot no existe en la BD."""
        # Arrange
        robot_id = 333
        mock_db_connector.ejecutar_consulta.return_value = []

        default_bot_input = {"in_NumRepeticion": {"type": "NUMBER", "number": "3"}}

        # Act
        result = desplegador._obtener_bot_input_robot(robot_id, default_bot_input)

        # Assert
        assert result == default_bot_input


class TestDesplegarRobotsConParametros:
    """Tests para el despliegue de robots con parámetros personalizados."""

    async def test_desplegar_robot_con_parametros_personalizados(
        self, desplegador, mock_db_connector, mock_aa_client, mock_api_gateway_client
    ):
        """Verifica que se usan los parámetros personalizados al desplegar un robot."""
        # Arrange
        robot_info = {
            "RobotId": 123,
            "UserId": 456,
            "EquipoId": 789,
            "Hora": "09:00:00",
        }

        parametros_personalizados = {"in_NumRepeticion": {"type": "NUMBER", "number": "7"}}
        mock_db_connector.ejecutar_consulta.return_value = [{"Parametros": json.dumps(parametros_personalizados)}]
        mock_db_connector.obtener_robots_ejecutables.return_value = [robot_info]
        mock_api_gateway_client.get_auth_header.return_value = {"Authorization": "Bearer test-token"}

        # Act
        await desplegador.desplegar_robots_pendientes()

        # Assert
        # Verificar que se consultó la BD para obtener los parámetros
        mock_db_connector.ejecutar_consulta.assert_any_call(
            "SELECT Parametros FROM dbo.Robots WHERE RobotId = ?", (123,), es_select=True
        )

        # Verificar que se llamó a desplegar_bot_v4 con los parámetros personalizados
        mock_aa_client.desplegar_bot_v4.assert_called_once()
        call_args = mock_aa_client.desplegar_bot_v4.call_args

        assert call_args.kwargs["file_id"] == 123
        assert call_args.kwargs["user_ids"] == [456]
        assert call_args.kwargs["bot_input"] == parametros_personalizados
        assert call_args.kwargs["bot_input"]["in_NumRepeticion"]["number"] == "7"

    async def test_desplegar_robot_sin_parametros_usar_default(
        self, desplegador, mock_db_connector, mock_aa_client, mock_api_gateway_client
    ):
        """Verifica que se usa el valor por defecto cuando el robot no tiene parámetros."""
        # Arrange
        robot_info = {
            "RobotId": 456,
            "UserId": 789,
            "EquipoId": 101,
            "Hora": "10:00:00",
        }

        mock_db_connector.ejecutar_consulta.return_value = [{"Parametros": None}]
        mock_db_connector.obtener_robots_ejecutables.return_value = [robot_info]
        mock_api_gateway_client.get_auth_header.return_value = {"Authorization": "Bearer test-token"}

        # Act
        await desplegador.desplegar_robots_pendientes()

        # Assert
        # Verificar que se llamó a desplegar_bot_v4 con el valor por defecto
        mock_aa_client.desplegar_bot_v4.assert_called_once()
        call_args = mock_aa_client.desplegar_bot_v4.call_args

        assert call_args.kwargs["bot_input"]["in_NumRepeticion"]["number"] == "3"  # Valor por defecto de la config

    async def test_desplegar_multiples_robots_con_diferentes_parametros(
        self, desplegador, mock_db_connector, mock_aa_client, mock_api_gateway_client
    ):
        """Verifica que cada robot usa sus propios parámetros al desplegar múltiples robots."""
        # Arrange
        robot_1 = {"RobotId": 1, "UserId": 100, "EquipoId": 200, "Hora": "09:00:00"}
        robot_2 = {"RobotId": 2, "UserId": 101, "EquipoId": 201, "Hora": "10:00:00"}

        parametros_robot_1 = {"in_NumRepeticion": {"type": "NUMBER", "number": "5"}}
        parametros_robot_2 = {"in_NumRepeticion": {"type": "NUMBER", "number": "10"}}

        # Configurar mocks para devolver diferentes parámetros según el robot
        def mock_ejecutar_consulta(query, params, es_select):
            robot_id = params[0]
            if robot_id == 1:
                return [{"Parametros": json.dumps(parametros_robot_1)}]
            elif robot_id == 2:
                return [{"Parametros": json.dumps(parametros_robot_2)}]
            return [{"Parametros": None}]

        mock_db_connector.ejecutar_consulta.side_effect = mock_ejecutar_consulta
        mock_db_connector.obtener_robots_ejecutables.return_value = [robot_1, robot_2]
        mock_api_gateway_client.get_auth_header.return_value = {"Authorization": "Bearer test-token"}

        # Act
        await desplegador.desplegar_robots_pendientes()

        # Assert
        # Verificar que se llamó dos veces (una por cada robot)
        assert mock_aa_client.desplegar_bot_v4.call_count == 2

        # Verificar que cada robot usó sus propios parámetros
        calls = mock_aa_client.desplegar_bot_v4.call_args_list

        # Primera llamada (robot 1)
        assert calls[0].kwargs["file_id"] == 1
        assert calls[0].kwargs["bot_input"]["in_NumRepeticion"]["number"] == "5"

        # Segunda llamada (robot 2)
        assert calls[1].kwargs["file_id"] == 2
        assert calls[1].kwargs["bot_input"]["in_NumRepeticion"]["number"] == "10"
