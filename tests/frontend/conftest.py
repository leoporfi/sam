# tests/frontend/conftest.py
"""
Fixtures compartidas para tests del frontend.

Este módulo proporciona fixtures para testing de componentes ReactPy,
siguiendo el principio de Inyección de Dependencias para facilitar
el testing con mocks.
"""
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from sam.web.frontend.api.api_client import APIClient


@pytest.fixture
def mock_api_client() -> APIClient:
    """
    Crea un mock de APIClient para testing.

    El mock incluye métodos async comunes que retornan datos de prueba.
    """
    mock = MagicMock(spec=APIClient)

    # Configurar métodos async comunes
    mock.get_robots = AsyncMock(
        return_value={
            "robots": [
                {"RobotId": 1, "Robot": "Robot1", "Activo": True, "EsOnline": False},
                {"RobotId": 2, "Robot": "Robot2", "Activo": False, "EsOnline": True},
            ],
            "total": 2,
        }
    )

    mock.get_equipos = AsyncMock(
        return_value={
            "equipos": [
                {"EquipoId": 1, "Equipo": "Equipo1", "ActivoSAM": True},
                {"EquipoId": 2, "Equipo": "Equipo2", "ActivoSAM": False},
            ],
            "total": 2,
        }
    )

    mock.get_pools = AsyncMock(
        return_value={
            "pools": [
                {"PoolId": 1, "Nombre": "Pool1"},
            ],
            "total": 1,
        }
    )

    mock.get_schedules = AsyncMock(
        return_value={
            "schedules": [
                {"ScheduleId": 1, "Tipo": "Diaria", "Activo": True},
            ],
            "total": 1,
        }
    )

    mock.get_mappings = AsyncMock(return_value=[])

    mock.get_sync_status = AsyncMock(return_value={"robots": "idle", "equipos": "idle"})

    mock.trigger_sync_robots = AsyncMock(return_value={"status": "started"})
    mock.trigger_sync_equipos = AsyncMock(return_value={"status": "started"})

    mock.create_robot = AsyncMock(return_value={"RobotId": 1})
    mock.update_robot = AsyncMock(return_value={"success": True})
    mock.delete_robot = AsyncMock(return_value={"success": True})

    return mock


@pytest.fixture
def mock_app_context(mock_api_client: APIClient) -> Dict[str, Any]:
    """
    Crea un contexto de aplicación mockeado para testing.

    Returns:
        Dict con las dependencias del contexto (api_client, etc.)
    """
    return {
        "api_client": mock_api_client,
    }


@pytest.fixture
def sample_robots() -> List[Dict[str, Any]]:
    """Datos de prueba para robots."""
    return [
        {"RobotId": 1, "Robot": "Robot1", "Activo": True, "EsOnline": False, "Descripcion": "Test Robot 1"},
        {"RobotId": 2, "Robot": "Robot2", "Activo": False, "EsOnline": True, "Descripcion": "Test Robot 2"},
        {"RobotId": 3, "Robot": "Robot3", "Activo": True, "EsOnline": True, "Descripcion": "Test Robot 3"},
    ]


@pytest.fixture
def sample_equipos() -> List[Dict[str, Any]]:
    """Datos de prueba para equipos."""
    return [
        {"EquipoId": 1, "Equipo": "Equipo1", "ActivoSAM": True, "PermiteBalanceo": True},
        {"EquipoId": 2, "Equipo": "Equipo2", "ActivoSAM": False, "PermiteBalanceo": False},
    ]


@pytest.fixture
def sample_pools() -> List[Dict[str, Any]]:
    """Datos de prueba para pools."""
    return [
        {"PoolId": 1, "Nombre": "Pool1", "Robots": [], "Equipos": []},
        {"PoolId": 2, "Nombre": "Pool2", "Robots": [1], "Equipos": [1]},
    ]
