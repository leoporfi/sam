from unittest.mock import MagicMock, patch

import pytest

from sam.common.config_manager import ConfigManager


@pytest.fixture
def local_mock_db():
    # Crear el mock del conector de BD
    db = MagicMock()

    # Configurar el comportamiento de ejecutar_consulta
    # Debe devolver una lista de diccionarios con Clave y Valor
    mock_data = [
        {"Clave": "LANZADOR_INTERVALO_LANZAMIENTO_SEG", "Valor": "30"},
        {"Clave": "LANZADOR_HABILITAR_SINCRONIZACION", "Valor": "False"},
        {"Clave": "BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO", "Valor": "True"},
        {"Clave": "INTERFAZ_WEB_SESSION_TIMEOUT_MIN", "Valor": "45"},
        {"Clave": "LANZADOR_PARAMETROS_PREDETERMINADOS_JSON", "Valor": "{}"},
    ]
    db.ejecutar_consulta.return_value = mock_data

    # Inyectar el mock en ConfigManager
    ConfigManager.set_db_connector(db)
    ConfigManager._config_cache = {}  # Limpiar caché
    ConfigManager._last_cache_update = 0

    yield db

    # Teardown (opcional, pero buena práctica)
    ConfigManager.set_db_connector(None)
    ConfigManager._config_cache = {}


def test_config_manager_db_priority(local_mock_db):
    """Verifica que el valor de BD tenga prioridad sobre ENV y Default."""
    # Mockear _get_env_with_warning para que devuelva 15
    with patch.object(ConfigManager, "_get_env_with_warning", return_value="15"):
        # En BD es 30, en ENV es 15. Debe ganar BD.
        val = ConfigManager._get_config_value("LANZADOR_INTERVALO_LANZAMIENTO_SEG", "10")
        assert val == "30"


def test_config_manager_fallback_to_env(local_mock_db):
    """Verifica que si no está en BD, usa la variable de entorno."""
    # Mockear _get_env_with_warning para que devuelva env_val
    with patch.object(ConfigManager, "_get_env_with_warning", return_value="env_val"):
        val = ConfigManager._get_config_value("VARIABLE_SOLO_ENV", "default")
        assert val == "env_val"


def test_config_manager_fallback_to_default(local_mock_db):
    """Verifica que si no está en BD ni en ENV, usa el default."""

    def side_effect(key, default=None, warning_msg=None):
        return default

    with patch.object(ConfigManager, "_get_env_with_warning", side_effect=side_effect):
        val = ConfigManager._get_config_value("VARIABLE_INEXISTENTE", "default_val")
        assert val == "default_val"


def test_config_manager_boolean_consistency(local_mock_db):
    """Verifica que los booleanos se interpreten correctamente independientemente del caso."""
    # LANZADOR_HABILITAR_SINCRONIZACION es "False" en mock_db
    config = ConfigManager.get_lanzador_config()
    assert config["habilitar_sync"] is False

    # BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO es "True" en mock_db
    config_bal = ConfigManager.get_balanceador_config()
    assert config_bal["aislamiento_estricto_pool"] is True


def test_config_manager_fallback_mechanism(local_mock_db):
    """Verifica que el mecanismo de fallback (nuevo -> antiguo) funcione."""
    # Limpiar caché para forzar lectura
    ConfigManager._config_cache = {}

    # Caso 1: Solo existe la clave antigua
    mock_data = [{"Clave": "LANZADOR_BOT_INPUT_VUELTAS", "Valor": "5"}]
    local_mock_db.ejecutar_consulta.return_value = mock_data

    val = ConfigManager._get_with_fallback("LANZADOR_REPETICIONES_ROBOT", "LANZADOR_BOT_INPUT_VUELTAS", "3")
    assert val == "5"

    # Caso 2: Existen ambas, debe ganar la nueva
    ConfigManager._config_cache = {}
    mock_data = [
        {"Clave": "LANZADOR_REPETICIONES_ROBOT", "Valor": "10"},
        {"Clave": "LANZADOR_BOT_INPUT_VUELTAS", "Valor": "5"},
    ]
    local_mock_db.ejecutar_consulta.return_value = mock_data

    val = ConfigManager._get_with_fallback("LANZADOR_REPETICIONES_ROBOT", "LANZADOR_BOT_INPUT_VUELTAS", "3")
    assert val == "10"
