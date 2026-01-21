import asyncio
from typing import Any, Dict, List
from unittest import IsolatedAsyncioTestCase, mock

import httpx

# --- MOCKS DE INFRAESTRUCTURA ---


class MockDatabaseConnector:
    def obtener_robots_ejecutables(self, *args, **kwargs) -> List[Dict[str, Any]]:
        # AJUSTE: Usamos "UserId" en lugar de "UsuarioId" para coincidir con tu desplegador.py
        return [
            {"AsignacionId": 1, "RobotId": "Bot_001", "EquipoId": "PC_001", "UserId": "user_test", "Hora": "10:00:00"}
        ]

    def cerrar_asignacion_fallida(self, *args, **kwargs):
        pass

    def ejecutar_consulta(self, *args, **kwargs):
        pass

    def insertar_registro_ejecucion(self, *args, **kwargs):
        pass


class MockApiGatewayClient:
    async def get_auth_header(self) -> Dict[str, str]:
        return {"Authorization": "Bearer mock_token"}


class MockEmailAlertClient:
    def send_alert(self, *args, **kwargs):
        pass


class MockAAClient:
    def __init__(self, expected_status_code: int, response_text: str = ""):
        self.expected_status_code = expected_status_code
        self.response_text = response_text

    async def desplegar_bot_v4(self, *args, **kwargs):
        # Simula la respuesta de la API v4
        if self.expected_status_code == 200:
            return {"deploymentId": "dep_12345"}
        else:
            # Generamos el error HTTP real que espera tu código
            request = httpx.Request("POST", "https://mock.url/v4/automations/deploy")
            response = httpx.Response(status_code=self.expected_status_code, text=self.response_text, request=request)
            raise httpx.HTTPStatusError(
                message=f"Mock Error {self.expected_status_code}", request=request, response=response
            )


class TestAlertaDespliegue(IsolatedAsyncioTestCase):
    @mock.patch("sam.lanzador.service.desplegador.logger")
    @mock.patch("sam.lanzador.service.main.logger")
    async def test_alerta_400_envio_inmediato(self, main_logger, desplegador_logger):
        """Prueba que el error 400 envíe alerta inmediata."""

        mock_notificador = MockEmailAlertClient()
        mock_notificador.send_alert = mock.MagicMock()

        mock_aa_client = MockAAClient(expected_status_code=400, response_text="Invalid Input Data")

        from sam.lanzador.service.desplegador import Desplegador

        # AJUSTE: Usamos las claves de configuración correctas para tu código
        cfg_test = {"max_workers_lanzador": 1, "max_reintentos_deploy": 1, "repeticiones": 1}

        desplegador = Desplegador(
            db_connector=MockDatabaseConnector(),
            aa_client=mock_aa_client,
            api_gateway_client=MockApiGatewayClient(),
            notificador=mock_notificador,
            cfg_lanzador=cfg_test,
            callback_token="mock_token",
        )

        await desplegador.desplegar_robots_pendientes()

        # Verificación
        self.assertEqual(mock_notificador.send_alert.call_count, 1, "Se esperaba 1 alerta por error 400")
        _, kwargs = mock_notificador.send_alert.call_args
        subject_enviado = kwargs.get("subject", "")
        self.assertIn("[SAM CRÍTICO]", subject_enviado)

    @mock.patch("sam.lanzador.service.desplegador.logger")
    @mock.patch("sam.lanzador.service.main.logger")
    async def test_alerta_412_acumulada(self, main_logger, desplegador_logger):
        """Prueba que el error 412 acumule fallos y alerte tras el umbral."""

        mock_notificador = MockEmailAlertClient()
        mock_notificador.send_alert = mock.MagicMock()

        UMBRAL_412 = 3

        cfg_lanzador_completa = {
            "umbral_alertas_412": UMBRAL_412,
            "intervalo_lanzamiento": 10,
            "intervalo_sincronizacion": 60,
            "intervalo_conciliacion": 60,
            # AJUSTE: Claves correctas
            "max_workers_lanzador": 1,
            "max_reintentos_deploy": 1,
        }

        from sam.lanzador.service.conciliador import Conciliador
        from sam.lanzador.service.desplegador import Desplegador
        from sam.lanzador.service.main import LanzadorService
        from sam.lanzador.service.sincronizador import Sincronizador

        mock_aa_client = MockAAClient(expected_status_code=412, response_text="Device offline")

        desplegador = Desplegador(
            db_connector=MockDatabaseConnector(),
            aa_client=mock_aa_client,
            api_gateway_client=MockApiGatewayClient(),
            notificador=mock_notificador,
            cfg_lanzador=cfg_lanzador_completa,
            callback_token="mock_token",
        )

        lanzador = LanzadorService(
            sincronizador=mock.Mock(spec=Sincronizador),
            desplegador=desplegador,
            conciliador=mock.Mock(spec=Conciliador),
            notificador=mock_notificador,
            cfg_lanzador=cfg_lanzador_completa,
            sync_enabled=False,
        )

        # Simular ciclos
        # Ciclo 1 y 2 -> No alerta
        for i in range(1, UMBRAL_412):
            results = await lanzador._desplegador.desplegar_robots_pendientes()
            lanzador._procesar_resultados_despliegue(results)
            self.assertEqual(mock_notificador.send_alert.call_count, 0, f"Ciclo {i} no debería alertar")

        # Ciclo 3 -> Alerta
        results = await lanzador._desplegador.desplegar_robots_pendientes()
        lanzador._procesar_resultados_despliegue(results)

        self.assertEqual(mock_notificador.send_alert.call_count, 1, "Se esperaba alerta tras alcanzar umbral 412")


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    asyncio.run(TestAlertaDespliegue().run_tests())
