# SAM/Lanzador/clients/aa_client.py
import requests
import urllib3
import logging
import threading
import time # Necesario para el sleep opcional en paginación
import re

from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta

# Este logger será el del módulo. Si una aplicación que usa esta clase
# quiere pasar su propio logger, el __init__ lo asignará.
logger = logging.getLogger(__name__) # Logger específico del módulo
# La configuración del logger (handlers, level) la debe hacer la aplicación principal.
# Si este módulo se usa como biblioteca, no debe configurar el logging raíz.

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class AutomationAnywhereClient: # Nombre original de tu clase en SAM
    """
    Cliente para interactuar con la API de Automation Anywhere A360.
    Diseñado para ser reutilizable, independiente de la configuración directa,
    con gestión de token robusta y paginación completa.
    """
    # Endpoints comunes de la API (ajusta versiones si es necesario)
    _ENDPOINT_AUTH_V2 = "/v2/authentication"
    _ENDPOINT_ACTIVITY_LIST_V3 = "/v3/activity/list"
    _ENDPOINT_AUTOMATIONS_DEPLOY_V3 = "/v3/automations/deploy"
    # Usar V2 para Users y Files/Robots si es posible, ya que es más reciente
    _ENDPOINT_USERS_LIST_V2 = "/v2/usermanagement/users/list"
    _ENDPOINT_DEVICES_LIST_V2 = "/v2/devices/list"
    _ENDPOINT_FILES_LIST_V2 = "/v2/repository/workspaces/public/files/list" # Asume workspace público

    # Constantes para campos comunes de la API
    _FIELD_TOKEN = "token"
    _FIELD_FILTER = "filter"
    _FIELD_OPERATOR = "operator"
    _FIELD_OPERANDS = "operands"
    _FIELD_FIELD = "field"
    _FIELD_VALUE = "value"
    _FIELD_SORT = "sort"
    _FIELD_DIRECTION = "direction"
    _FIELD_PAGE = "page"
    _FIELD_OFFSET = "offset"
    _FIELD_LENGTH = "length"
    _FIELD_LIST = "list"
    _FIELD_ID = "id"

    def __init__(self, control_room_url: str, username: str, password: str,
                api_key: Optional[str] = None,
                callback_url_for_deploy: Optional[str] = None,
                api_timeout_seconds: int = 60,
                token_refresh_buffer_sec: int = 1140,
                default_page_size: int = 100,
                max_pagination_pages: int = 1000, # Salvaguarda para paginación
                logger_instance: Optional[logging.Logger] = None):

        if logger_instance:
            global logger # Usa el logger pasado por la aplicación
            logger = logger_instance

        self.url_base = control_room_url.strip('/')
        self.username = username
        self.password = password
        self.api_key = api_key
        self.callback_url_for_deploy = callback_url_for_deploy

        self._timeout_requests = api_timeout_seconds
        self._token_refresh_buffer_seconds = token_refresh_buffer_sec
        self._default_page_size = default_page_size
        self._max_pagination_pages = max_pagination_pages # Límite de páginas a solicitar

        self.session = requests.Session()
        self.session.verify = False

        self._token_auth: Optional[str] = None
        self._ts_inicio_token: Optional[datetime] = None
        self._token_lock = threading.Lock()

        logger.info(f"Cliente API ({type(self).__name__}) inicializado para CR: {self.url_base}, Usuario: {self.username}")

    def _manejar_excepcion_api(self, error: requests.exceptions.RequestException,
                               response_obj: Optional[requests.Response] = None, request_data=None):
        """Maneja excepciones de requests y errores HTTP, levantando una excepción formateada."""
        error_message = ""
        status_code_str = str(response_obj.status_code) if response_obj is not None else "N/A"
        api_details = ""

        if response_obj is not None:
            try:
                error_data = response_obj.json()
                api_message = error_data.get("message", response_obj.text[:250]) # Más contexto del error
                api_code = error_data.get("code", "")
                api_details = f"API Response (Status {status_code_str}): Code='{api_code}', Message='{api_message}'"
            except ValueError:
                api_details = f"API Response (Status {status_code_str}, Not JSON): {response_obj.text[:250]}"
        else:
             api_details = "No response object from API (network issue or timeout before response)."

        req_data_summary = str(request_data)[:250] if request_data else "N/A" # Más contexto del request

        if isinstance(error, requests.exceptions.Timeout):
            error_message = f"API request timed out after {self._timeout_requests}s. {api_details}"
            logger.error(f"{error_message} Request Data: {req_data_summary}")
            raise TimeoutError(error_message) from error
        elif isinstance(error, requests.exceptions.ConnectionError):
            error_message = f"API connection error. {api_details} Original error: {error}"
            logger.error(f"{error_message} Request Data: {req_data_summary}")
            raise ConnectionError(error_message) from error
        else:
            error_message = f"API request failed. Error: {error}. {api_details}"
            logger.error(f"{error_message} Request Data: {req_data_summary}")
            raise Exception(error_message) from error

    def _obtener_token(self) -> Optional[str]:
        """Obtiene un nuevo token de autenticación. Debe ser llamado bajo _token_lock."""
        logger.info(f"Intentando obtener nuevo token para usuario '{self.username}'.")
        url = f"{self.url_base}{self._ENDPOINT_AUTH_V2}"
        payload = {
            "username": self.username,
            "password": self.password,
            "multiLogin": True, # Basado en tu uso previo
        }
        if self.api_key:
            payload["apiKey"] = self.api_key

        response_obj = None
        try:
            response_obj = self.session.post(url, json=payload, timeout=self._timeout_requests)
            response_obj.raise_for_status()
            data_respuesta = response_obj.json()
            self._token_auth = data_respuesta.get(self._FIELD_TOKEN)
            if self._token_auth:
                self._ts_inicio_token = datetime.now()
                self.session.headers.update({"X-Authorization": self._token_auth})
                logger.info(f"Nuevo token obtenido exitosamente para '{self.username}'.")
                return self._token_auth
            else:
                logger.error(f"Autenticación exitosa para '{self.username}' pero no se recibió token. Respuesta: {str(data_respuesta)[:500]}")
                self._token_auth = None
                self._ts_inicio_token = None
                if "X-Authorization" in self.session.headers:
                    del self.session.headers["X-Authorization"]
                return None
        except requests.exceptions.RequestException as e:
            self._manejar_excepcion_api(e, response_obj, payload)
            return None # No se alcanza si _manejar_excepcion_api siempre relanza

    def _is_token_still_valid_by_time(self) -> bool:
        """Verifica si el token actual es probablemente válido según su tiempo de vida."""
        if not self._token_auth or not self._ts_inicio_token:
            return False
        elapsed_time = (datetime.now() - self._ts_inicio_token).total_seconds()
        if elapsed_time < self._token_refresh_buffer_seconds:
            logger.debug("Token existente es válido por tiempo.")
            return True
        else:
            logger.info("Token existente ha superado el buffer de refresco por tiempo. Necesita ser renovado.")
            return False

    def _ensure_token_valid(self) -> None:
        """Asegura que haya un token válido. Obtiene/refresca si es necesario."""
        with self._token_lock:
            if self._is_token_still_valid_by_time():
                return
            logger.info("Token no válido o necesita refresco. Obteniendo nuevo token (dentro de lock)...")
            if not self._obtener_token():
                raise Exception(f"No se pudo obtener un token de autenticación válido para el usuario '{self.username}' después del intento.")

    def _realizar_peticion_api(self, method: str, endpoint: str,
                               params_query: Optional[Dict] = None,
                               json_payload: Optional[Dict] = None,
                               data_payload: Any = None,
                               headers_extra: Optional[Dict] = None) -> Dict[str, Any]:
        """Método centralizado para realizar peticiones API."""
        self._ensure_token_valid()
        url = f"{self.url_base}{endpoint}"
        final_headers = {}
        if json_payload is not None and (method.upper() in ["POST", "PUT", "PATCH"]):
             final_headers["Content-Type"] = "application/json"

        if headers_extra:
            final_headers.update(headers_extra)

        request_kwargs = {
            "params": params_query, "json": json_payload, "data": data_payload,
            "timeout": self._timeout_requests
        }
        if final_headers: request_kwargs["headers"] = final_headers

        response_obj = None
        try:
            payload_summary = str(json_payload or data_payload)[:250] # Un poco más de info
            logger.debug(f"API Call: {method} {url} | Payload: {payload_summary}")
            response_obj = self.session.request(method, url, **request_kwargs)
            response_obj.raise_for_status()

            if response_obj.content and response_obj.text.strip():
                try:
                    return response_obj.json()
                except requests.exceptions.JSONDecodeError as json_err:
                    err_msg = f"Respuesta de {method} {url} no pudo ser decodificada como JSON. Status: {response_obj.status_code}. Content: {response_obj.text[:250]}"
                    logger.error(err_msg)
                    raise Exception(err_msg) from json_err
            else:
                logger.debug(f"Respuesta de {method} {url} (Status {response_obj.status_code}) sin contenido JSON parseable.")
                return {}
        except requests.exceptions.RequestException as e:
            self._manejar_excepcion_api(e, response_obj, json_payload or data_payload)
            raise # Asegurar que la excepción se propague

    def _obtener_lista_paginada_entidades(self, endpoint: str, payload_base: dict,
                                       campos_api_a_extraer: List[str],
                                       limite_por_pagina: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Función genérica para obtener todas las entidades de un endpoint que soporta paginación,
        usando page.totalFilter o page.total para un control robusto del bucle.
        """
        lista_completa = []
        offset_actual = 0
        page_size = limite_por_pagina if limite_por_pagina is not None else self._default_page_size
        total_entidades_esperadas = -1 # -1 indica que aún no lo sabemos de la API
        primera_pagina_procesada = False
        paginas_intentadas = 0

        payload_base_actual = payload_base.copy()
        if self._FIELD_PAGE not in payload_base_actual:
            payload_base_actual[self._FIELD_PAGE] = {}
        payload_base_actual[self._FIELD_PAGE][self._FIELD_LENGTH] = page_size

        while paginas_intentadas < self._max_pagination_pages:
            paginas_intentadas += 1
            payload_base_actual[self._FIELD_PAGE][self._FIELD_OFFSET] = offset_actual
            
            try:
                logger.debug(f"Paginación: Solicitando página {paginas_intentadas}, endpoint: {endpoint}, offset: {offset_actual}, page_size: {page_size}")
                respuesta_api = self._realizar_peticion_api("POST", endpoint, json_payload=payload_base_actual)
                entidades_pagina_api = respuesta_api.get(self._FIELD_LIST, [])
                
                if not primera_pagina_procesada:
                    page_info_respuesta = respuesta_api.get(self._FIELD_PAGE)
                    logger.debug(f"PAGINACIÓN - INFO DE PÁGINA DEVUELTA POR API (1ra vez): {page_info_respuesta}")
                    if page_info_respuesta:
                        if isinstance(page_info_respuesta.get("totalFilter"), int):
                            total_entidades_esperadas = page_info_respuesta["totalFilter"]
                        elif isinstance(page_info_respuesta.get("total"), int): # Fallback a 'total'
                            total_entidades_esperadas = page_info_respuesta["total"]
                        
                        if total_entidades_esperadas == 0 and entidades_pagina_api:
                            logger.warning(f"Paginación: API reportó totalFilter/total de 0 para {endpoint} pero la primera página devolvió {len(entidades_pagina_api)} resultados. Se ignorará el total reportado y se usará el conteo de ítems por página.")
                            total_entidades_esperadas = -1 
                    logger.info(f"Paginación: Total de entidades esperadas (según API): {total_entidades_esperadas if total_entidades_esperadas != -1 else 'No disponible o inconsistente'}")
                    primera_pagina_procesada = True

                if not entidades_pagina_api:
                    logger.info(f"Paginación: No se obtuvieron más entidades de {endpoint} en offset {offset_actual} (lista vacía). Finalizando paginación.")
                    break 
                
                for entidad_api in entidades_pagina_api:
                    data_entidad = {campo: entidad_api.get(campo) for campo in campos_api_a_extraer}
                    lista_completa.append(data_entidad)

                logger.debug(f"Paginación: Obtenidos {len(entidades_pagina_api)} entidades en esta página. Total acumulado: {len(lista_completa)}.")

                if total_entidades_esperadas != -1 and len(lista_completa) >= total_entidades_esperadas:
                    logger.info(f"Paginación: Se han obtenido todas las {len(lista_completa)} entidades esperadas (totalFilter/total: {total_entidades_esperadas}). Finalizando.")
                    break

                if len(entidades_pagina_api) < page_size:
                    logger.info(f"Paginación: Última página obtenida (recibidos {len(entidades_pagina_api)} < page_size {page_size}). Finalizando.")
                    break 
                
                offset_actual += page_size
                # time.sleep(0.05) # Pequeña pausa opcional para no sobrecargar la API en ráfagas rápidas

            except Exception as e:
                logger.error(f"Paginación: Error obteniendo página {paginas_intentadas} de {endpoint} en offset {offset_actual}: {e}", exc_info=True)
                break
        
        if paginas_intentadas >= self._max_pagination_pages:
            logger.warning(f"Paginación: Se alcanzó el límite máximo de {self._max_pagination_pages} páginas para {endpoint}. Resultados podrían estar incompletos (obtenidos: {len(lista_completa)}).")

        logger.info(f"Paginación: Total final de {len(lista_completa)} entidades obtenidas de {endpoint}.")
        return lista_completa

    # --- Métodos Públicos ---
    def desplegar_bot(self, file_id: int, run_as_user_ids: List[int], bot_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Despliega un bot y devuelve un diccionario con el resultado.
        Resultado: {"deploymentId": str_or_none, "error": str_or_none, "is_retriable": bool, "status_code": int_or_none }
        """
        payload = {
            "fileId": file_id,
            "runAsUserIds": run_as_user_ids,
        }
        if self.callback_url_for_deploy:
            payload["callbackInfo"] = {"url": self.callback_url_for_deploy}
        if bot_input and isinstance(bot_input, dict):
            payload["botInput"] = bot_input
            
        logger.debug(f"Preparando despliegue de bot con payload: {payload}")
        resultado = {"deploymentId": None, "error": None, "is_retriable": False, "status_code": None}
        
        try:
            datos_respuesta = self._realizar_peticion_api("POST", self._ENDPOINT_AUTOMATIONS_DEPLOY_V3, json_payload=payload)
            deployment_id = datos_respuesta.get("deploymentId")
            if not deployment_id:
                logger.warning(f"API de despliegue no devolvió deploymentId. Payload: {payload}, Respuesta: {str(datos_respuesta)[:500]}")
                resultado["error"] = "No se obtuvo deploymentId"
                return resultado
            logger.info(f"Bot (FileID: {file_id}) desplegado exitosamente. DeploymentId: {deployment_id}")
            resultado["deploymentId"] = deployment_id
            return resultado
        except Exception as e:
            logger.error(f"Fallo en el intento de desplegar bot (FileID: {file_id}, Usuarios: {run_as_user_ids}). Error: {e}", exc_info=True)
            resultado["error"] = str(e)
            # Intentar obtener el status_code si la excepción es de requests
            if hasattr(e, 'response') and e.response is not None:
                resultado["status_code"] = e.response.status_code
            error_lower = str(e).lower()
            # Errores comunes de A360 que podrían ser reintentables (ej. device ocupado, problema temporal de licencia)
            # El error "INVALID_ARGUMENT: Some or all users provided are either deleted or disabled" NO es reintentable.
            # Pero un "400 Client Error: Bad Request" genérico, o un "412 Precondition Failed" (que a veces usa A360)
            # podrían serlo si el problema es un estado temporal del dispositivo.
            if "device is busy" in error_lower or \
               ("400 client error" in error_lower and "invalid_argument" not in error_lower and "user" not in error_lower and "deleted" not in error_lower and "disabled" not in error_lower) or \
               "412 client error" in error_lower or \
               isinstance(e, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)): # Errores de red son reintentables
                resultado["is_retriable"] = True
            logger.debug(f"Resultado completo del despliegue: {resultado}")
            return resultado
                
    def desplegar_bot_old(self, file_id: int, run_as_user_ids: List[int], bot_input: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Despliega un bot y devuelve el deploymentId."""
        payload = {
            "fileId": file_id,
            "runAsUserIds": run_as_user_ids,
        }
        if self.callback_url_for_deploy:
             payload["callbackInfo"] = {"url": self.callback_url_for_deploy}
        if bot_input and isinstance(bot_input, dict): # Solo añadir si es un dict y no está vacío
            payload["botInput"] = bot_input
        
        try:
            datos_respuesta = self._realizar_peticion_api("POST", self._ENDPOINT_AUTOMATIONS_DEPLOY_V3, json_payload=payload)
            deployment_id = datos_respuesta.get("deploymentId")
            if not deployment_id:
                logger.warning(f"API de despliegue no devolvió deploymentId. Payload: {payload}, Respuesta: {str(datos_respuesta)[:500]}")
                return None
            logger.info(f"Bot (FileID: {file_id}) desplegado exitosamente. DeploymentId: {deployment_id}")
            return deployment_id
        except Exception as e:
            logger.error(f"Fallo en el intento de desplegar bot (FileID: {file_id}, Usuarios: {run_as_user_ids}). Error: {e}")
            return None

    def _crear_filtro_deployment_ids(self, deployment_ids: List[str], operador: str = "or") -> Dict[str, Any]:
        """Crea el payload de filtro para buscar por deployment IDs."""
        return {
            self._FIELD_SORT: [{"field": "startDateTime", "direction": "desc"}],
            self._FIELD_FILTER: {
                self._FIELD_OPERATOR: operador,
                self._FIELD_OPERANDS: [{"operator": "eq", "field": "deploymentId", "value": valor} for valor in deployment_ids],
            },
        }

    def obtener_detalles_por_deployment_ids(self, deployment_ids: List[str]) -> List[Dict[str, Any]]:
        """Obtiene detalles de múltiples deployments."""
        if not deployment_ids:
            return []
        payload_filtro = self._crear_filtro_deployment_ids(deployment_ids, operador="or")
        campos_api_a_extraer = ["status", "progress", "endDateTime", "deploymentId", "userId", "message", "fileName", "automationName"]
        
        try:
            respuesta_json = self._realizar_peticion_api("POST", self._ENDPOINT_ACTIVITY_LIST_V3, json_payload=payload_filtro)
            actividad_lista_api = respuesta_json.get(self._FIELD_LIST, [])
            
            if not actividad_lista_api:
                logger.info(f"No se encontraron detalles de actividad para los deployment IDs: {deployment_ids}")
                return []

            resultados_filtrados = []
            for item_api in actividad_lista_api:
                detalle = {campo: item_api.get(campo) for campo in campos_api_a_extraer}
                if detalle.get("userId") is not None:
                    try:
                        detalle["userId"] = int(str(detalle["userId"]))
                    except ValueError:
                        logger.warning(f"No se pudo convertir userId '{detalle['userId']}' a entero para deploymentId '{detalle.get('deploymentId')}'.")
                resultados_filtrados.append(detalle)
            return resultados_filtrados
        except Exception as e:
            logger.error(f"Error al obtener detalles para deployment IDs {str(deployment_ids)[:100]}: {e}", exc_info=True)
            return []

    def obtener_devices(self, status_filtro: Optional[str] = "CONNECTED") -> List[Dict[str, Any]]:
        """Obtiene la lista de devices (runners) de A360, con paginación."""
        logger.info(f"Obteniendo devices de A360 (status: '{status_filtro}')...")
        endpoint = self._ENDPOINT_DEVICES_LIST_V2
        
        payload_base = {
            self._FIELD_PAGE: {},
            self._FIELD_SORT: [{"field": "hostName", "direction": "asc"}],
            self._FIELD_FILTER: { self._FIELD_OPERATOR: "and", self._FIELD_OPERANDS: [] }
        }
        if status_filtro:
             payload_base[self._FIELD_FILTER][self._FIELD_OPERANDS].append({
                self._FIELD_OPERATOR: "eq", self._FIELD_FIELD: "status", self._FIELD_VALUE: status_filtro.upper()
            })
        # Si _FIELD_OPERANDS está vacío, algunas APIs podrían rechazarlo.
        # Si es el único filtro posible y es opcional, se puede omitir "filter" si no hay operandos.
        if not payload_base[self._FIELD_FILTER][self._FIELD_OPERANDS]:
            del payload_base[self._FIELD_FILTER] # Eliminar filtro si no hay condiciones

        campos_api_a_extraer = [self._FIELD_ID, "hostName", "status", "defaultUsers"]
        
        devices_api_bruto = self._obtener_lista_paginada_entidades(endpoint, payload_base, campos_api_a_extraer)
        
        devices_mapeados = []
        for dev_api in devices_api_bruto:
            a360_user_id = None
            a360_username = None
            if dev_api.get("defaultUsers") and isinstance(dev_api["defaultUsers"], list) and dev_api["defaultUsers"]:
                default_user = dev_api["defaultUsers"][0]
                a360_user_id = default_user.get(self._FIELD_ID)
                a360_username = default_user.get("username")
            
            devices_mapeados.append({
                "EquipoId": dev_api.get(self._FIELD_ID),
                "Equipo": dev_api.get("hostName"),
                "UserId": a360_user_id,
                "UserName": a360_username,
                "Status_A360": dev_api.get("status"),
            })
        return devices_mapeados

    def obtener_usuarios_detallados(self, filtro_descripcion_contiene: Optional[str] = None, user_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Obtiene detalles de usuarios de A360, con paginación y opción de filtrar por IDs."""
        logger.info(f"Obteniendo usuarios detallados (desc: '{filtro_descripcion_contiene}', user_ids: {str(user_ids)[:50] if user_ids else 'Todos'})...")
        endpoint = self._ENDPOINT_USERS_LIST_V2

        payload_base = {
            self._FIELD_PAGE: {},
            self._FIELD_SORT: [{"field": "username", "direction": "asc"}]
        }
        
        operands = []
        if filtro_descripcion_contiene:
            operands.append({
                self._FIELD_OPERATOR: "substring", self._FIELD_FIELD: "description", 
                self._FIELD_VALUE: filtro_descripcion_contiene
            })
        if user_ids:
            operands.append({
                self._FIELD_OPERATOR: "or",
                self._FIELD_OPERANDS: [{self._FIELD_OPERATOR: "eq", self._FIELD_FIELD: self._FIELD_ID, self._FIELD_VALUE: uid} for uid in user_ids]
            })
        
        if operands:
            payload_base[self._FIELD_FILTER] = { self._FIELD_OPERATOR: "and", self._FIELD_OPERANDS: operands }
            if len(operands) == 1: payload_base[self._FIELD_FILTER] = operands[0]

        campos_api_a_extraer = [self._FIELD_ID, "username", "description", "licenseFeatures", "disabled", "email", "firstName", "lastName", "roleIds"]
        
        usuarios_api_bruto = self._obtener_lista_paginada_entidades(endpoint, payload_base, campos_api_a_extraer)
        
        usuarios_mapeados = []
        for usr_api in usuarios_api_bruto:
            licencia_str = "SIN_LICENCIA"
            if usr_api.get("licenseFeatures"):
                features = usr_api["licenseFeatures"]
                if isinstance(features, list) and features: licencia_str = features[0] 
                elif isinstance(features, str): licencia_str = features
            
            usuarios_mapeados.append({
                "UserId": usr_api.get(self._FIELD_ID),
                "UserName": usr_api.get("username"),
                "Descripcion_Usuario_A360": usr_api.get("description"),
                "Licencia": licencia_str,
                "Email": usr_api.get("email"),
                "FirstName": usr_api.get("firstName"),
                "LastName": usr_api.get("lastName"),
                "RoleIds_A360": usr_api.get("roleIds", []),
                "Activo_Usuario_A360": not usr_api.get("disabled", False)
            })
        return usuarios_mapeados

    def obtener_robots(self, 
                            filtro_path_base: str = "RPA", # Filtro para path que contenga "RPA"
                            filtro_nombre_prefijo: str = "P" # Filtro para nombre que empiece con "P"
                            ) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de robots (taskbots) de A360, con paginación y filtros específicos.
        Mapea campos para la tabla dbo.Robots de SAM.
        """
        logger.info(f"Obteniendo robots de A360 (path base: '{filtro_path_base}', prefijo nombre: '{filtro_nombre_prefijo}')...")
        endpoint = self._ENDPOINT_FILES_LIST_V2
        
        operands_list = [
            {self._FIELD_OPERATOR: "eq", self._FIELD_FIELD: "type", self._FIELD_VALUE: "application/vnd.aa.taskbot"}
        ]

        if filtro_path_base:
            operands_list.append({
                self._FIELD_OPERATOR: "substring", self._FIELD_FIELD: "path", self._FIELD_VALUE: filtro_path_base
            })
        
        if filtro_nombre_prefijo:
            operands_list.append({
                self._FIELD_OPERATOR: "substring", self._FIELD_FIELD: "name", self._FIELD_VALUE: filtro_nombre_prefijo 
                # Usar substring para "empieza con". Si la API soporta "startsWith", sería mejor.
                # Algunas APIs de A360 usan "startswith" como operador. Si no, "substring" con el prefijo
                # es lo más cercano, y luego filtramos más en Python.
            })

        payload_base = {
            self._FIELD_PAGE: {}, # Se llenará en _obtener_lista_paginada_entidades
            self._FIELD_SORT: [{"field": "name", "direction": "asc"}],
            self._FIELD_FILTER: { 
                self._FIELD_OPERATOR: "and", 
                self._FIELD_OPERANDS: operands_list
            }
        }
        # Si solo hay un operando (ej. solo el de type), el "and" es innecesario pero usualmente inofensivo.
        # Si operands_list queda solo con el de "type", se podría simplificar el filtro:
        if len(operands_list) == 1:
            payload_base[self._FIELD_FILTER] = operands_list[0]
        elif not operands_list: # No debería pasar si siempre filtramos por type
             del payload_base[self._FIELD_FILTER]


        campos_api_a_extraer = [self._FIELD_ID, "name", "path", "description", "version", "locked", "parentId"]
        
        robots_api_bruto = self._obtener_lista_paginada_entidades(
            endpoint, payload_base, campos_api_a_extraer
        )
        
        robots_mapeados_y_filtrados = []
        # Expresión regular para el patrón de nombre: "P" seguido de cualquier cosa hasta un número, luego "_", luego cualquier cosa.
        # Ajustada para ser más precisa: P, luego opcionalmente letras, luego números, luego _, luego cualquier cosa.
        # P[A-Z]*[0-9]+_.*
        # P      -> Literal "P"
        # [A-Z]* -> Cero o más letras mayúsculas (ej. en P008DA, la "DA")
        # [0-9]+ -> Uno o más dígitos
        # _      -> Literal "_"
        # .* -> Cualquier caracter, cero o más veces
        patron_nombre_robot = re.compile(r"^P[A-Z]*[0-9]+_.*") 
        # Si la "P" puede ser seguida inmediatamente por números:
        # patron_nombre_robot = re.compile(r"^P[0-9]+_.*") si es P directamente seguido de números
        # Para cubrir ambos P<letras><numeros>_ y P<numeros>_ :
        # patron_nombre_robot = re.compile(r"^P([A-Z]*[0-9]+|[0-9]+)_.*")

        # De tu lista, parece que el formato es P<LETRAS_OPCIONALES_MAYUSCULAS><NUMEROS>_<DESCRIPCION>
        # O P<NUMEROS>_<DESCRIPCION>
        # Ejemplo: P568235_CambioPlanWhatsApp (P + 6 digitos + _)
        # Ejemplo: P008DA_Descarga Facturas CEVIGE (P + 3 digitos + 2 letras + _)
        # Un patrón más general que cubra esto: ^P[A-Z0-9]*[0-9]+[A-Z0-9]*_.*
        # Simplificando basado en la estructura más común P<NUMEROS>... o P<LETRAS><NUMEROS>...
        # patron_nombre_robot = re.compile(r"^P([A-Z0-9]*[0-9]+|[0-9]+[A-Z0-9]*)[_].*")
        # O más simple si siempre hay un número después de P (con o sin letras en medio):
        patron_nombre_robot_sam = re.compile(r"^P[A-Z0-9]*[0-9].*_.*")


        for bot_api in robots_api_bruto:
            nombre_bot = bot_api.get("name")
            # Aplicar filtro de nombre con expresión regular
            if nombre_bot and patron_nombre_robot_sam.match(nombre_bot):
                robots_mapeados_y_filtrados.append({
                    "RobotId": bot_api.get(self._FIELD_ID),
                    "Robot": nombre_bot,
                    "Descripcion": bot_api.get("description"),
                    "Path_A360": bot_api.get("path"),
                    "Version_A360": bot_api.get("version"),
                    "Locked_A360": bot_api.get("locked"),
                    "ParentId_A360": bot_api.get("parentId")
                    # Los campos "Parametros", "EsOnline_SAM", "Activo_SAM" para tu tabla dbo.Robots
                    # se determinarán/asignarán en la lógica de SAM, no vienen directamente así de la API.
                })
            elif nombre_bot and filtro_nombre_prefijo and nombre_bot.startswith(filtro_nombre_prefijo) and not patron_nombre_robot_sam.match(nombre_bot):
                # Loguear los que empiezan con "P" pero no cumplen el patrón regex completo, para depuración.
                logger.debug(f"Robot '{nombre_bot}' comienza con '{filtro_nombre_prefijo}' pero no coincide con el patrón regex detallado. Se omite.")

        logger.info(f"Total de {len(robots_mapeados_y_filtrados)} robots obtenidos y filtrados de A360.")
        return robots_mapeados_y_filtrados
