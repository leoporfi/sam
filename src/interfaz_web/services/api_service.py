# interfaz_web/services/api_service.py

import asyncio
import os
from typing import Any, Dict, List, Optional

import httpx

from ..config.settings import Settings
from ..schemas.robot_types import Robot, RobotFilters, RobotUpdateData
from ..utils.exceptions import APIException, ValidationException
from ..utils.validation import validate_robot_data


class APIService:
    """Servicio centralizado para todas las llamadas a la API"""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url or Settings.API_BASE_URL
        self.timeout = timeout
        self._client = None

    async def __aenter__(self):
        """Context manager para uso con async with"""
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, headers={"Content-Type": "application/json"})
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cierra el cliente al salir del context manager"""
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        """Obtiene el cliente HTTP, creándolo si es necesario"""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, headers={"Content-Type": "application/json"})
        return self._client

    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None, retries: int = 3) -> Any:
        """
        Realiza una petición HTTP con reintentos y manejo de errores
        """
        client = self._get_client()

        for attempt in range(retries):
            try:
                response = await client.request(method=method, url=endpoint, params=params, json=json_data)

                # Verificar código de estado
                if response.status_code >= 400:
                    error_detail = "Error desconocido"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", str(error_data))
                    except:
                        error_detail = response.text or f"Error HTTP {response.status_code}"

                    raise APIException(message=f"Error en la API: {error_detail}", status_code=response.status_code)

                # Intentar parsear JSON, devolver texto si falla
                try:
                    return response.json()
                except:
                    return response.text

            except httpx.RequestError as e:
                if attempt == retries - 1:  # Último intento
                    raise APIException(f"Error de conexión: {str(e)}")

                # Esperar antes del siguiente intento (exponential backoff)
                await asyncio.sleep(2**attempt)

            except APIException:
                # Re-lanzar errores de API sin reintentar
                raise

    # =========================
    # MÉTODOS PARA ROBOTS
    # =========================

    async def get_robots(self, filters: Optional[RobotFilters] = None) -> Dict[str, Any]:
        """
        Obtiene la lista de robots con filtros opcionales
        Retorna: {"robots": List[Robot], "total_count": int}
        """
        params = {}

        if filters:
            if filters.get("name"):
                params["name"] = filters.get("name")
            if filters.get("active") is not None:
                params["active"] = filters.get("active")
            if filters.get("online") is not None:
                params["online"] = filters.get("online")
            if filters.get("page"):
                params["page"] = filters.get("page")
            if filters.get("size"):
                params["size"] = filters.get("size")

        try:
            data = await self._make_request("GET", "/api/robots", params=params)

            # Si la API devuelve directamente la lista (compatibilidad hacia atrás)
            if isinstance(data, list):
                return {"robots": data, "total_count": len(data), "page": 1, "size": len(data)}

            # Si la API devuelve un objeto con metadatos
            return {"robots": data.get("robots", []), "total_count": data.get("total_count", 0), "page": data.get("page", 1), "size": data.get("size", 20)}

        except Exception as e:
            raise APIException(f"Error al obtener robots: {str(e)}")

    async def get_robot(self, robot_id: int) -> Robot:
        """Obtiene un robot específico por ID"""
        try:
            return await self._make_request("GET", f"/api/robots/{robot_id}")
        except Exception as e:
            raise APIException(f"Error al obtener robot {robot_id}: {str(e)}")

    async def create_robot(self, robot_data: Dict[str, Any]) -> Robot:
        """Crea un nuevo robot"""
        # Validar datos antes de enviar
        validation_result = validate_robot_data(robot_data)
        if not validation_result.is_valid:
            raise ValidationException("Datos inválidos", validation_result.errors)

        try:
            return await self._make_request("POST", "/api/robots", json_data=robot_data)
        except Exception as e:
            raise APIException(f"Error al crear robot: {str(e)}")

    async def update_robot(self, robot_id: int, robot_data: Dict[str, Any]) -> Robot:
        """Actualiza un robot existente"""
        # Validar datos antes de enviar
        validation_result = validate_robot_data(robot_data, is_update=True)
        if not validation_result.is_valid:
            raise ValidationException("Datos inválidos", validation_result.errors)

        try:
            return await self._make_request("PUT", f"/api/robots/{robot_id}", json_data=robot_data)
        except Exception as e:
            raise APIException(f"Error al actualizar robot {robot_id}: {str(e)}")

    async def update_robot_status(self, robot_id: int, status_data: Dict[str, bool]) -> Dict[str, str]:
        """Actualiza el estado de un robot (Activo/Online)"""
        try:
            return await self._make_request("PATCH", f"/api/robots/{robot_id}", json_data=status_data)
        except Exception as e:
            raise APIException(f"Error al actualizar estado del robot {robot_id}: {str(e)}")

    async def delete_robot(self, robot_id: int) -> Dict[str, str]:
        """Elimina un robot"""
        try:
            return await self._make_request("DELETE", f"/api/robots/{robot_id}")
        except Exception as e:
            raise APIException(f"Error al eliminar robot {robot_id}: {str(e)}")

    # =========================
    # MÉTODOS PARA ASIGNACIONES
    # =========================

    async def get_robot_assignments(self, robot_id: int) -> List[Dict[str, Any]]:
        """Obtiene las asignaciones de un robot"""
        try:
            return await self._make_request("GET", f"/api/robots/{robot_id}/asignaciones")
        except Exception as e:
            raise APIException(f"Error al obtener asignaciones del robot {robot_id}: {str(e)}")

    async def get_available_teams(self, robot_id: int) -> List[Dict[str, Any]]:
        """Obtiene los equipos disponibles para asignar a un robot"""
        try:
            return await self._make_request("GET", f"/api/equipos/disponibles/{robot_id}")
        except Exception as e:
            raise APIException(f"Error al obtener equipos disponibles: {str(e)}")

    async def update_robot_assignments(self, robot_id: int, assign_team_ids: List[int], unassign_team_ids: List[int]) -> Dict[str, str]:
        """Actualiza las asignaciones de un robot"""
        try:
            data = {"assign_team_ids": assign_team_ids, "unassign_team_ids": unassign_team_ids}
            return await self._make_request("POST", f"/api/robots/{robot_id}/asignaciones", json_data=data)
        except Exception as e:
            raise APIException(f"Error al actualizar asignaciones del robot {robot_id}: {str(e)}")

    # =========================
    # MÉTODOS PARA PROGRAMACIONES
    # =========================

    async def get_robot_schedules(self, robot_id: int) -> List[Dict[str, Any]]:
        """Obtiene las programaciones de un robot"""
        try:
            return await self._make_request("GET", f"/api/robots/{robot_id}/programaciones")
        except Exception as e:
            raise APIException(f"Error al obtener programaciones del robot {robot_id}: {str(e)}")

    async def create_schedule(self, schedule_data: Dict[str, Any]) -> Dict[str, str]:
        """Crea una nueva programación"""
        try:
            return await self._make_request("POST", "/api/programaciones", json_data=schedule_data)
        except Exception as e:
            raise APIException(f"Error al crear programación: {str(e)}")

    async def update_schedule(self, schedule_id: int, schedule_data: Dict[str, Any]) -> Dict[str, str]:
        """Actualiza una programación existente"""
        try:
            return await self._make_request("PUT", f"/api/programaciones/{schedule_id}", json_data=schedule_data)
        except Exception as e:
            raise APIException(f"Error al actualizar programación {schedule_id}: {str(e)}")

    async def delete_schedule(self, robot_id: int, schedule_id: int) -> Dict[str, str]:
        """Elimina una programación"""
        try:
            return await self._make_request("DELETE", f"/api/robots/{robot_id}/programaciones/{schedule_id}")
        except Exception as e:
            raise APIException(f"Error al eliminar programación {schedule_id}: {str(e)}")

    # =========================
    # MÉTODOS UTILITARIOS
    # =========================

    async def health_check(self) -> Dict[str, Any]:
        """Verifica el estado de la API"""
        try:
            return await self._make_request("GET", "/health")
        except Exception as e:
            raise APIException(f"Error en health check: {str(e)}")

    async def close(self):
        """Cierra el cliente HTTP"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Instancia global del servicio (singleton)
_api_service_instance = None


def get_api_service() -> APIService:
    """Factory function para obtener la instancia del servicio API"""
    global _api_service_instance
    if _api_service_instance is None:
        _api_service_instance = APIService()
    return _api_service_instance
