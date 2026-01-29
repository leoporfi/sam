from unittest.mock import MagicMock, patch

import pytest

# Esta importación es necesaria para que la fixture de configuración funcione.
from sam.common.config_loader import ConfigLoader


@pytest.fixture(scope="session", autouse=True)
def setup_and_mock_config():
    """
    Se ejecuta una sola vez por sesión para asegurar que la configuración
    esté 'mockeada' antes de que cualquier prueba se ejecute.
    Esto previene que los tests intenten leer archivos .env.
    """
    # Inicializa el cargador para asegurar que sys.path sea correcto.
    ConfigLoader.initialize_service("sam_test_session")

    # Usamos patch para interceptar las llamadas al ConfigManager.
    # Esto reemplaza la necesidad de un archivo .env durante las pruebas.
    mock_settings = {
        "CALLBACK_TOKEN": "test_token_123",
        "AA_CR_URL": "https://test.a360.com",
        "AA_CR_API_KEY": "test-key",
        "AA_CR_USER": "test-user",
        "SQL_SAM_HOST": "test_server",
        "SQL_SAM_DB_NAME": "test-db",
        "SQL_SAM_UID": "test-user",
        "SQL_SAM_PWD": "test-password",
    }

    # Creamos un 'side effect' para simular la obtención de valores.
    def mock_get(key, default=None, warning_msg=None):
        return mock_settings.get(key, default)

    # Aplicamos el patch al método interno que usa ConfigManager
    patch("sam.common.config_manager.ConfigManager._get_env_with_warning", side_effect=mock_get).start()


@pytest.fixture
def mock_db_connector():
    """
    Crea un mock autocontenido del DatabaseConnector para inyectar en los tests.
    """
    connector = MagicMock()
    # Usamos AsyncMock para los métodos que son `async`
    connector.connect = MagicMock()
    connector.close = MagicMock()
    connector.fetch_all = MagicMock(return_value=[])
    connector.fetch_one = MagicMock(return_value=None)
    connector.execute = MagicMock(return_value=None)
    return connector
