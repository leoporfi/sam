# common/clients/aa_client.py (Con Refresco de Token)
import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

import httpx
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


class AutomationAnywhereClient:
    _ENDPOINT_AUTH_V2 = "/v2/authentication"
    _ENDPOINT_ACTIVITY_LIST_V3 = "/v3/activity/list"
    _ENDPOINT_AUTOMATIONS_DEPLOY_V3 = "/v3/automations/deploy"
    _ENDPOINT_USERS_LIST_V2 = "/v2/usermanagement/users/list"
    _ENDPOINT_DEVICES_LIST_V2 = "/v2/devices/list"
    _ENDPOINT_FILES_LIST_V2 = "/v2/repository/workspaces/public/files/list"

    def __init__(self, control_room_url: str, username: str, password: str, **kwargs):
        self.url_base = control_room_url.strip("/")
        self.username = username
        self.password = password
        self.api_key = kwargs.get("api_key")
        self.api_timeout = kwargs.get("api_timeout_seconds", 60)
        self.callback_url_deploy = kwargs.get("callback_url_deploy")

        self._token: Optional[str] = None
        self._token_lock = asyncio.Lock()

        self._client = httpx.AsyncClient(base_url=self.url_base, verify=False, timeout=self.api_timeout)
        logger.info(f"Cliente API Asíncrono inicializado para CR: {self.url_base}")

    # --- Métodos Internos: Gestión de Token y Peticiones ---

    async def _obtener_token(self, is_retry: bool = False):
        """Obtiene un nuevo token de autenticación."""
        # Este método se ejecuta dentro de un lock, por lo que es seguro.
        if is_retry:
            logger.warning("Intentando obtener un nuevo token de A360...")
        else:
            logger.info("Obteniendo token de A360...")

        payload = {"username": self.username, "password": self.password}
        if self.api_key:
            payload["apiKey"] = self.api_key

        response = await self._client.post(self._ENDPOINT_AUTH_V2, json=payload)
        response.raise_for_status()

        self._token = response.json().get("token")
        if self._token:
            self._client.headers["X-Authorization"] = self._token
            logger.info("Token de A360 obtenido/refrescado exitosamente.")
        else:
            logger.error("La autenticación fue exitosa pero no se recibió un token.")
            raise ValueError("No se recibió un token de la API de A360.")

    async def _asegurar_validez_del_token(self, is_retry: bool = False):
        """Asegura que tenemos un token. Se llama solo si no hay token o si ha expirado."""
        async with self._token_lock:
            # Doble chequeo para evitar que múltiples corutinas pidan token a la vez
            if not self._token or is_retry:
                await self._obtener_token(is_retry=is_retry)

    async def _realizar_peticion_api(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Realiza una petición a la API, manejando la obtención y refresco del token.
        """
        # Asegurarse de tener un token inicial si es la primera vez
        if not self._token:
            await self._asegurar_validez_del_token()

        try:
            # Primer intento de la petición
            response = await self._client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}

        except httpx.HTTPStatusError as e:
            # --- LÓGICA DE REFRESCO DE TOKEN ---
            # Si el error es 401 (No Autorizado), el token probablemente expiró.
            if e.response.status_code == 401:
                logger.warning("Recibido error 401 (No Autorizado). El token puede haber expirado. Intentando reautenticar...")

                # Forzar la obtención de un nuevo token
                await self._asegurar_validez_del_token(is_retry=True)

                # Reintentar la petición original UNA VEZ MÁS con el nuevo token
                logger.info(f"Reintentando la petición a {endpoint} con el nuevo token...")
                response_retry = await self._client.request(method, endpoint, **kwargs)
                response_retry.raise_for_status()
                return response_retry.json() if response_retry.content else {}
            else:
                # Si es otro error HTTP, simplemente lo relanzamos
                raise

    async def _obtener_lista_paginada_entidades(self, endpoint: str, payload: Dict) -> List[Dict]:
        """
        Obtiene todas las entidades de un endpoint que soporta paginación.
        """
        lista_completa = []
        offset = 0
        page_size = 100

        if "page" not in payload:
            payload["page"] = {}

        while True:
            payload["page"]["offset"] = offset
            payload["page"]["length"] = page_size

            response_json = await self._realizar_peticion_api("POST", endpoint, json=payload)
            entidades_pagina = response_json.get("list", [])

            if not entidades_pagina:
                break

            lista_completa.extend(entidades_pagina)

            if len(entidades_pagina) < page_size:
                break

            offset += page_size

        logger.info(f"Paginación: Se obtuvieron un total de {len(lista_completa)} entidades de {endpoint}.")
        return lista_completa

    def _crear_filtro_deployment_ids(self, deployment_ids: List[str]) -> Dict:
        """Crea el payload de filtro para buscar por deployment IDs."""
        return {
            "sort": [{"field": "startDateTime", "direction": "desc"}],
            "filter": {
                "operator": "or",
                "operands": [{"operator": "eq", "field": "deploymentId", "value": dep_id} for dep_id in deployment_ids],
            },
        }

    # --- Métodos Públicos Asíncronos ---

    async def obtener_devices(self) -> List[Dict]:
        logger.info("Obteniendo devices de A360...")
        payload = {"filter": {"operator": "eq", "field": "status", "value": "CONNECTED"}}
        devices_api = await self._obtener_lista_paginada_entidades(self._ENDPOINT_DEVICES_LIST_V2, payload)

        devices_mapeados = []
        for device in devices_api:
            user_info = device.get("defaultUsers", [{}])[0]
            devices_mapeados.append(
                {
                    "EquipoId": device.get("id"),
                    "Equipo": device.get("hostName"),
                    "UserId": user_info.get("id"),
                    "UserName": user_info.get("username"),
                }
            )
        logger.info(f"Se encontraron {len(devices_mapeados)} devices conectados.")
        return devices_mapeados

    async def obtener_usuarios_detallados(self) -> List[Dict]:
        logger.info("Obteniendo usuarios detallados de A360...")
        usuarios_api = await self._obtener_lista_paginada_entidades(self._ENDPOINT_USERS_LIST_V2, {})

        usuarios_mapeados = []
        for user in usuarios_api:
            licencia = "SIN_LICENCIA"
            if user.get("licenseFeatures"):
                licencia = user["licenseFeatures"][0]
            usuarios_mapeados.append(
                {
                    "UserId": user.get("id"),
                    "UserName": user.get("username"),
                    "Licencia": licencia,
                }
            )
        logger.info(f"Se encontraron {len(usuarios_mapeados)} usuarios.")
        return usuarios_mapeados

    async def obtener_robots(self) -> List[Dict]:
        logger.info("Obteniendo robots de A360...")
        payload = {
            "filter": {
                "operator": "and",
                "operands": [
                    {"operator": "substring", "field": "path", "value": "RPA"},
                    {"operator": "eq", "field": "type", "value": "application/vnd.aa.taskbot"},
                ],
            }
        }
        robots_api = await self._obtener_lista_paginada_entidades(self._ENDPOINT_FILES_LIST_V2, payload)

        patron_nombre = re.compile(r"^P[A-Z0-9]*[0-9].*_.*")
        robots_mapeados = []
        for bot in robots_api:
            nombre = bot.get("name")
            if nombre and patron_nombre.match(nombre):
                robots_mapeados.append({"RobotId": bot.get("id"), "Robot": nombre, "Descripcion": bot.get("description")})

        logger.info(f"Se encontraron y filtraron {len(robots_mapeados)} robots.")
        return robots_mapeados

    async def obtener_detalles_por_deployment_ids(self, deployment_ids: List[str]) -> List[Dict]:
        if not deployment_ids:
            return []
        logger.info(f"Obteniendo detalles de {len(deployment_ids)} deployments...")
        payload = self._crear_filtro_deployment_ids(deployment_ids)
        response_json = await self._realizar_peticion_api("POST", self._ENDPOINT_ACTIVITY_LIST_V3, json=payload)
        return response_json.get("list", [])

    async def desplegar_bot(self, file_id: int, user_ids: List[int], bot_input: Optional[Dict] = None) -> Dict:
        logger.info(f"Desplegando bot con FileID: {file_id} en UserIDs: {user_ids}")
        payload = {"fileId": file_id, "runAsUserIds": user_ids}
        if bot_input:
            payload["botInput"] = bot_input
        if self.callback_url_deploy:
            payload["callbackInfo"] = {"url": self.callback_url_deploy}

        try:
            logger.debug(f"Payload de despliegue: {payload}")
            response = await self._realizar_peticion_api("POST", self._ENDPOINT_AUTOMATIONS_DEPLOY_V3, json=payload)
            logger.info(f"Bot desplegado exitosamente. DeploymentId: {response.get('deploymentId')}")
            return response
        except Exception as e:
            logger.error(f"Fallo en el despliegue del bot {file_id}: {e}", exc_info=True)
            return {"error": str(e)}

    async def close(self):
        """Cierra la sesión del cliente httpx de forma segura."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("Cliente API de A360 cerrado.")
