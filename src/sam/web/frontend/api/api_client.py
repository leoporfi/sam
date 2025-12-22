# sam/web/frontend/api/api_client.py
"""
Cliente HTTP centralizado para comunicación con FastAPI backend.

Este módulo proporciona un cliente HTTP que sigue el principio de Inyección
de Dependencias de la Guía General de SAM. Las instancias deben crearse
y ser inyectadas a través del contexto de la aplicación, no usando el
patrón singleton.

Uso:
    # Crear instancia (en app.py o punto de inyección)
    api_client = APIClient(base_url="http://127.0.0.1:8000")

    # Inyectar en contexto
    context_value = {"api_client": api_client}

    # Usar en hooks
    api_client = use_app_context()["api_client"]
    data = await api_client.get("/api/robots")
"""

import asyncio
import warnings
from typing import Any, Dict, List, Optional

import httpx

from ...backend.schemas import Robot
from ..utils.exceptions import APIException, ValidationException
from ..utils.validation import validate_robot_data


# Cliente HTTP centralizado para comunicación con FastAPI backend
class APIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self._client = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0, headers={"Content-Type": "application/json"})
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            # if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0, headers={"Content-Type": "application/json"})
        return self._client

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retries: int = 3,
    ) -> Any:
        """Método interno para realizar requests HTTP con reintentos."""
        client = self._get_client()
        for attempt in range(retries):
            try:
                response = await client.request(method=method, url=endpoint, params=params, json=json_data)
                if response.status_code >= 400:
                    error_detail = "Error desconocido"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", str(error_data))
                    except Exception:
                        error_detail = response.text or f"Error HTTP {response.status_code}"
                    raise APIException(message=f"Error en la API: {error_detail}", status_code=response.status_code)
                try:
                    return response.json()
                except Exception:
                    return response.text
            except httpx.RequestError as e:
                if attempt == retries - 1:
                    raise APIException(f"Error de conexión: {str(e)}")
                await asyncio.sleep(2**attempt)
            except APIException:
                raise

    # ============================================================================
    # MÉTODOS GENÉRICOS (según estándar)
    # ============================================================================

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """
        GET request con manejo de errores centralizado.

        Args:
            endpoint: Ruta del endpoint (ej: "/api/robots")
            params: Parámetros de query string

        Returns:
            Respuesta JSON parseada

        Raises:
            APIException: Si hay error en la petición
        """
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, data: Dict) -> Any:
        """
        POST request con manejo de errores.

        Args:
            endpoint: Ruta del endpoint
            data: Datos a enviar en el body (se serializan a JSON)

        Returns:
            Respuesta JSON parseada

        Raises:
            APIException: Si hay error en la petición
        """
        return await self._request("POST", endpoint, json_data=data)

    async def put(self, endpoint: str, data: Dict) -> Any:
        """
        PUT request con manejo de errores.

        Args:
            endpoint: Ruta del endpoint
            data: Datos a enviar en el body

        Returns:
            Respuesta JSON parseada

        Raises:
            APIException: Si hay error en la petición
        """
        return await self._request("PUT", endpoint, json_data=data)

    async def delete(self, endpoint: str) -> Any:
        """
        DELETE request con manejo de errores.

        Args:
            endpoint: Ruta del endpoint

        Returns:
            Respuesta JSON parseada

        Raises:
            APIException: Si hay error en la petición
        """
        return await self._request("DELETE", endpoint)

    # MÉTODOS PARA ROBOTS
    async def get_robots(self, params: Optional[Dict] = None) -> Dict:
        try:
            data = await self._request("GET", "/api/robots", params=params)
            if not isinstance(data, dict):
                error_preview = str(data)[:200]
                raise APIException(f"La respuesta del servidor no es un JSON válido. Contenido: '{error_preview}...'")
            return {"robots": data.get("robots", []), "total_count": data.get("total_count", 0)}
        except Exception as e:
            raise APIException(f"Error al obtener robots: {str(e)}")

    async def create_robot(self, robot_data: Dict) -> Robot:
        validation_result = validate_robot_data(robot_data)
        if not validation_result.is_valid:
            raise ValidationException("Datos inválidos", validation_result.errors)
        return await self._request("POST", "/api/robots", json_data=robot_data)

    async def update_robot(self, robot_id: int, robot_data: Dict) -> Robot:
        validation_result = validate_robot_data(robot_data, is_update=True)
        if not validation_result.is_valid:
            raise ValidationException("Datos inválidos", validation_result.errors)
        return await self._request("PUT", f"/api/robots/{robot_id}", json_data=robot_data)

    async def update_robot_status(self, robot_id: int, status_data: Dict[str, bool]) -> Dict:
        return await self._request("PATCH", f"/api/robots/{robot_id}", json_data=status_data)

    async def delete_robot(self, robot_id: int) -> Dict:
        return await self._request("DELETE", f"/api/robots/{robot_id}")

    # MÉTODOS PARA ASIGNACIONES
    async def get_robot_assignments(self, robot_id: int) -> List[Dict]:
        return await self._request("GET", f"/api/robots/{robot_id}/asignaciones")

    async def get_available_devices(self, robot_id: int) -> List[Dict]:
        return await self._request("GET", f"/api/equipos/disponibles/{robot_id}")

    async def update_robot_assignments(self, robot_id: int, assign_ids: List[int], unassign_ids: List[int]) -> Dict:
        data = {"asignar_equipo_ids": assign_ids, "desasignar_equipo_ids": unassign_ids}
        return await self._request("POST", f"/api/robots/{robot_id}/asignaciones", json_data=data)

    # MÉTODOS PARA PROGRAMACIONES (SCHEDULES)
    async def get_schedules(self, params: Optional[Dict] = None) -> Dict:
        """
        Obtiene la lista paginada de programaciones con validación y compatibilidad.
        """
        try:
            data = await self._request("GET", "/api/schedules", params=params)

            if not isinstance(data, dict):
                error_preview = str(data)[:200]
                raise APIException(f"Respuesta inválida (no es JSON válido). Inicio: '{error_preview}...'")

            return {"schedules": data.get("schedules", []), "total_count": data.get("total_count", 0)}

        except Exception as e:
            # Si es una excepción nuestra la dejamos pasar, sino la envolvemos
            if isinstance(e, APIException):
                raise e
            raise APIException(f"Error al obtener programaciones: {str(e)}")

    async def toggle_schedule_status(self, schedule_id: int, activo: bool) -> Dict:
        """
        Cambia el estado 'Activo' de una programación.
        """
        payload = {"Activo": activo}
        return await self._request("PATCH", f"/api/schedules/{schedule_id}/status", json_data=payload)

    async def get_all_schedules_legacy(self) -> List[Dict]:
        return await self._request("GET", "/api/schedules/all")

    async def get_all_schedules(self) -> List[Dict]:
        return await self._request("GET", "/api/schedules")

    async def get_robot_schedules(self, robot_id: int) -> List[Dict]:
        return await self._request("GET", f"/api/schedules/robot/{robot_id}")

    async def create_schedule(self, schedule_data: Dict) -> Dict:
        return await self._request("POST", "/api/schedules", json_data=schedule_data)

    async def update_schedule(self, schedule_id: int, schedule_data: Dict) -> Dict:
        """
        Actualiza una programación completa.
        """
        return await self._request("PUT", f"/api/schedules/{schedule_id}", json_data=schedule_data)

    async def update_schedule_details(self, schedule_id: int, data: dict) -> Dict:
        """
        Usa el endpoint 'details' que no requiere el campo 'Equipos'.
        Usado por la página de Programaciones.
        """
        return await self._request("PUT", f"/api/schedules/{schedule_id}/details", json_data=data)

    async def delete_schedule(self, schedule_id: int, robot_id: int) -> Dict:
        return await self._request("DELETE", f"/api/schedules/{schedule_id}/robot/{robot_id}")

    # --- Métodos para Asignaciones de Programaciones (NUEVOS) ---

    async def get_schedule_devices(self, schedule_id: int) -> Dict:
        """
        Obtiene los equipos asignados y disponibles para una programación específica.
        Endpoint: GET /api/schedules/{id}/devices
        """
        return await self._request("GET", f"/api/schedules/{schedule_id}/devices")

    async def update_schedule_devices(self, schedule_id: int, device_ids: List[int]):
        """
        Actualiza la lista de equipos asignados a una programación.
        Endpoint: PUT /api/schedules/{id}/devices
        """
        return await self._request("PUT", f"/api/schedules/{schedule_id}/devices", json_data=device_ids)

    # MÉTODOS PARA POOLS
    async def get_pools(self) -> List[Dict]:
        return await self._request("GET", "/api/pools")

    async def create_pool(self, pool_data: Dict) -> Dict:
        return await self._request("POST", "/api/pools", json_data=pool_data)

    async def update_pool(self, pool_id: int, pool_data: Dict) -> Dict:
        return await self._request("PUT", f"/api/pools/{pool_id}", json_data=pool_data)

    async def delete_pool(self, pool_id: int) -> None:
        await self._request("DELETE", f"/api/pools/{pool_id}")

    async def get_pool_assignments(self, pool_id: int) -> Dict:
        return await self._request("GET", f"/api/pools/{pool_id}/asignaciones")

    async def update_pool_assignments(self, pool_id: int, robot_ids: List[int], equipo_ids: List[int]) -> Dict:
        # RFR-34: Se estandariza el nombre del parámetro y del campo a 'equipo_ids'.
        payload = {"robot_ids": robot_ids, "equipo_ids": equipo_ids}
        return await self._request("PUT", f"/api/pools/{pool_id}/asignaciones", json_data=payload)

    async def get_equipos(self, params: Optional[Dict] = None) -> Dict:
        return await self._request("GET", "/api/equipos", params=params)

    async def update_equipo_status(self, equipo_id: int, status_data: Dict[str, Any]) -> Dict:
        return await self._request("PATCH", f"/api/equipos/{equipo_id}", json_data=status_data)

    async def create_equipo(self, equipo_data: Dict) -> Dict:
        """Crea un nuevo equipo manualmente."""
        # Podríamos añadir validación Pydantic aquí si quisiéramos
        # Opcional: Validar equipo_data contra EquipoCreateRequest aquí antes de enviar
        return await self._request("POST", "/api/equipos", json_data=equipo_data)

    # MÉTODOS UTILITARIOS
    async def get_sync_status(self) -> Dict:
        """Consulta el estado de las tareas de sincronización del backend."""
        return await self._request("GET", "/api/sync/status")

    async def trigger_sync_robots(self) -> Dict:
        """Sincroniza solo robots desde A360."""
        return await self._request("POST", "/api/sync/robots")

    async def trigger_sync_equipos(self) -> Dict:
        """Sincroniza solo equipos desde A360."""
        return await self._request("POST", "/api/sync/equipos")

    async def trigger_sync(self) -> Dict:
        """Sincroniza robots y equipos desde A360 (legacy)."""
        return await self._request("POST", "/api/sync")

    # MÉTODOS DE CONFIGURACIÓN DEL SISTEMA
    async def get_preemption_mode(self) -> Dict:
        """Obtiene el estado actual del modo Prioridad Estricta."""
        return await self._request("GET", "/api/config/preemption")

    async def set_preemption_mode(self, enabled: bool) -> Dict:
        """Activa o desactiva el modo Prioridad Estricta."""
        # El backend espera un JSON con la clave "enabled"
        return await self._request("PUT", "/api/config/preemption", json_data={"enabled": enabled})

    async def get_isolation_mode(self) -> Dict:
        return await self._request("GET", "/api/config/isolation")

    async def set_isolation_mode(self, enabled: bool) -> Dict:
        return await self._request("PUT", "/api/config/isolation", json_data={"enabled": enabled})

    #
    async def get_mappings(self) -> List[Dict]:
        return await self._request("GET", "/api/mappings")

    async def create_mapping(self, data: Dict) -> Dict:
        return await self._request("POST", "/api/mappings", json_data=data)

    async def delete_mapping(self, mapeo_id: int) -> Dict:
        return await self._request("DELETE", f"/api/mappings/{mapeo_id}")

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# ============================================================================
# COMPATIBILIDAD TEMPORAL (DEPRECATED)
# ============================================================================
# Esta función se mantiene temporalmente para no romper código existente.
# Se eliminará en una fase posterior cuando todos los hooks usen DI.

_api_client_instance = None


def get_api_client() -> APIClient:
    """
    ⚠️ DEPRECATED: Esta función usa patrón singleton y será eliminada.

    Usa inyección de dependencias a través del contexto en su lugar:

    # ❌ NO USAR (deprecated):
    api_client = get_api_client()

    # ✅ USAR (recomendado):
    from sam.web.frontend.state.app_context import use_app_context
    api_client = use_app_context()["api_client"]

    Returns:
        Instancia singleton de APIClient (temporal, para compatibilidad)
    """
    global _api_client_instance
    warnings.warn(
        "get_api_client() está deprecated. Usa inyección de dependencias a través de use_app_context()['api_client'] en su lugar.",
        DeprecationWarning,
        stacklevel=2,
    )
    if _api_client_instance is None:
        _api_client_instance = APIClient()
    return _api_client_instance


# Alias para compatibilidad con código que importa ApiClient
ApiClient = APIClient  # type: ignore
