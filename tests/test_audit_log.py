"""Tests para la funcionalidad de log de auditoría."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sam.web.backend.dependencies import aa_client_provider, apigw_client_provider
from sam.web.main import create_app


@pytest.fixture
def client(mock_db_connector):
    """Cliente de prueba de FastAPI para la interfaz web."""
    # Mock de clientes para evitar errores en lifespan
    aa_client_provider.set_aa_client(AsyncMock())
    apigw_client_provider.set_apigw_client(MagicMock())

    # Creamos la app inyectando el mock
    app = create_app(mock_db_connector)
    with TestClient(app) as test_client:
        yield test_client


class TestAuditLog:
    def test_robot_status_update_logs_audit(self, client: TestClient, mock_db_connector):
        """Verifica que el cambio de estado de un robot genera un log de auditoría."""
        # Mock para update_robot_status (devuelve 1 fila afectada)
        mock_db_connector.ejecutar_consulta.return_value = 1

        response = client.patch("/api/robots/1", json={"Activo": False})

        assert response.status_code == 200

        # Verificar que se llamó a RegistrarAuditoria
        # La primera llamada es para update_robot_status, la segunda para log_audit
        calls = mock_db_connector.ejecutar_consulta.call_args_list
        audit_call = next((c for c in calls if "dbo.RegistrarAuditoria" in str(c)), None)

        assert audit_call is not None
        args, kwargs = audit_call
        query = args[0]
        params = args[1]

        assert "dbo.RegistrarAuditoria" in query
        assert params[0] == "UPDATE_STATUS"
        assert params[1] == "Robot"
        assert params[2] == "1"
        assert "Cambio en Activo a False" in params[3]
        # El host debería ser testclient (por defecto en TestClient)
        assert params[4] == "testclient"

    def test_create_pool_logs_audit(self, client: TestClient, mock_db_connector):
        """Verifica que la creación de un pool genera un log de auditoría."""
        # Mock para create_pool (devuelve el pool creado)
        mock_db_connector.ejecutar_consulta.return_value = [{"PoolId": 10, "Nombre": "TestPool"}]

        response = client.post("/api/pools", json={"Nombre": "TestPool", "Descripcion": "Test"})

        assert response.status_code == 201

        calls = mock_db_connector.ejecutar_consulta.call_args_list
        audit_call = next((c for c in calls if "dbo.RegistrarAuditoria" in str(c)), None)

        assert audit_call is not None
        params = audit_call[0][1]
        assert params[0] == "CREATE"
        assert params[1] == "Pool"
        assert params[2] == "10"
        assert "TestPool" in params[3]

    def test_unlock_execution_logs_audit(self, client: TestClient, mock_db_connector):
        """Verifica que destrabar una ejecución genera un log de auditoría."""
        # Mock para obtener_info_ejecucion
        mock_db_connector.ejecutar_consulta.return_value = [{"EquipoId": 1, "UserId": 1}]

        # Mock para apigw_client.notificar_callback (necesitamos parcharlo)
        with patch("sam.web.backend.api.ApiGatewayClient.notificar_callback", return_value=True):
            response = client.post("/api/executions/DEP-123/unlock")

        assert response.status_code == 200

        calls = mock_db_connector.ejecutar_consulta.call_args_list
        audit_call = next((c for c in calls if "dbo.RegistrarAuditoria" in str(c)), None)

        assert audit_call is not None
        params = audit_call[0][1]
        assert params[0] == "UNLOCK"
        assert params[1] == "Ejecucion"
        assert params[2] == "DEP-123"
        assert "Destrabado manual" in params[3]

    def test_update_robot_details_logs_audit(self, client: TestClient, mock_db_connector):
        """Verifica que la actualización de detalles de un robot genera un log de auditoría."""
        # Mock para update_robot_details (devuelve True)
        mock_db_connector.ejecutar_consulta.return_value = 1

        robot_data = {
            "Robot": "UpdatedBot",
            "Descripcion": "Test description",
            "MinEquipos": 1,
            "MaxEquipos": 2,
            "PrioridadBalanceo": 10,
            "TicketsPorEquipoAdicional": 5,
            "Parametros": "{}",
        }

        response = client.put("/api/robots/1", json=robot_data)

        assert response.status_code == 200

        calls = mock_db_connector.ejecutar_consulta.call_args_list
        audit_call = next((c for c in calls if "dbo.RegistrarAuditoria" in str(c)), None)

        assert audit_call is not None
        params = audit_call[0][1]
        assert params[0] == "UPDATE"
        assert params[1] == "Robot"
        assert params[2] == "1"
        assert "UpdatedBot" in params[3]

    def test_log_audit_resolves_hostname(self, mock_db_connector):
        """Verifica que log_audit intenta resolver el hostname."""
        from sam.web.backend.database import log_audit

        with patch("socket.gethostbyaddr", return_value=("ResolvedPC", [], ["127.0.0.1"])):
            log_audit(
                mock_db_connector,
                accion="TEST",
                entidad="Test",
                entidad_id="1",
                detalle="Test detail",
                host="127.0.0.1",
            )

        calls = mock_db_connector.ejecutar_consulta.call_args_list
        audit_call = next((c for c in calls if "dbo.RegistrarAuditoria" in str(c)), None)

        assert audit_call is not None
        params = audit_call[0][1]
        assert params[4] == "ResolvedPC"
