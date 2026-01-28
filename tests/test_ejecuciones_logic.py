from unittest.mock import MagicMock, patch

from sam.web.backend.database import get_recent_executions


@patch("sam.web.backend.database.ejecutar_sp_multiple_result_sets")
@patch("sam.common.config_manager.ConfigManager.get_lanzador_config")
def test_get_recent_executions_passes_default_repeticiones(mock_get_config, mock_ejecutar_sp):
    db = MagicMock()
    mock_get_config.return_value = {"repeticiones": 5}
    mock_ejecutar_sp.return_value = [[], []]
    get_recent_executions(db)
    args, kwargs = mock_ejecutar_sp.call_args
    params = args[2]
    assert params["DefaultRepeticiones"] == 5


@patch("sam.web.backend.database.ejecutar_sp_multiple_result_sets")
@patch("sam.common.config_manager.ConfigManager.get_lanzador_config")
def test_get_recent_executions_returns_correct_structure(mock_get_config, mock_ejecutar_sp):
    db = MagicMock()
    mock_get_config.return_value = {"repeticiones": 1}
    mock_ejecutar_sp.return_value = [
        [{"Id": 1, "Robot": "Bot1", "TipoCritico": "Fallo"}],
        [{"Id": 2, "Robot": "Bot2", "TipoCritico": "Demorada"}],
    ]
    result = get_recent_executions(db)
    assert "fallos" in result
    assert "demoras" in result
    assert len(result["fallos"]) == 1
    assert len(result["demoras"]) == 1
