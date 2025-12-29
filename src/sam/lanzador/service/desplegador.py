# sam/lanzador/service/desplegador.py
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import httpx
import pytz

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.apigw_client import ApiGatewayClient
from sam.common.database import DatabaseConnector
from sam.common.mail_client import EmailAlertClient

logger = logging.getLogger(__name__)


class Desplegador:
    """
    Componente 'cerebro' responsable de la lógica de despliegue de robots.
    Recibe sus dependencias y configuración, y su única misión es ejecutar
    el ciclo de lanzamiento cuando se le indica.
    """

    def __init__(
        self,
        db_connector: DatabaseConnector,
        aa_client: AutomationAnywhereClient,
        api_gateway_client: ApiGatewayClient,
        notificador: EmailAlertClient,
        cfg_lanzador: Dict[str, Any],
        callback_token: str,
    ):
        """
        Inicializa el Desplegador con sus dependencias.

        Args:
            db_connector: Conector a la base de datos de SAM.
            aa_client: Cliente para la API de Automation Anywhere.
            api_gateway_client: Cliente para el API Gateway.
            lanzador_config: Diccionario con la configuración específica del lanzador.
            callback_token: Token estático para la autenticación del callback.
        """
        self._db_connector = db_connector
        self._aa_client = aa_client
        self._api_gateway_client = api_gateway_client
        self._notificador = notificador
        self._cfg_lanzador = cfg_lanzador
        self._static_callback_api_key = callback_token

        # Control para no spamear alertas de error 400 en el mismo ciclo
        self._equipos_alertados_400 = set()

    async def desplegar_robots_pendientes(self) -> List[Dict[str, Any]]:
        """
        Orquestación principal del despliegue:
        1. Verifica pausa.
        2. Obtiene robots de la BD.
        3. Obtiene token API Gateway.
        4. Ejecuta despliegues en paralelo.
        5. Retorna resultados para que el Orquestador gestione alertas (ej. 412).
        """
        if self._esta_en_pausa():
            logger.info("Lanzador en PAUSA operativa configurada. Omitiendo ciclo.")
            return []

        logger.info("Buscando robots para ejecutar...")
        robots_a_ejecutar = self._db_connector.obtener_robots_ejecutables()

        if not robots_a_ejecutar:
            logger.info("No hay robots para ejecutar en este ciclo.")
            return

        # Bot input por defecto (valor de configuración)
        default_bot_input = {
            "in_NumRepeticion": {"type": "NUMBER", "number": str(self._cfg_lanzador.get("repeticiones", 1))}
        }
        max_workers = self._cfg_lanzador.get("max_workers_lanzador", 10)
        auth_headers = await self._preparar_cabeceras_callback()

        logger.info(f"{len(robots_a_ejecutar)} robots encontrados. Desplegando en paralelo (límite: {max_workers})...")

        tasks = [
            asyncio.create_task(self._desplegar_y_registrar_robot(robot_info, default_bot_input, auth_headers))
            for robot_info in robots_a_ejecutar
        ]

        successful_deploys = 0
        failed_deploys = 0
        all_results = []

        for i in range(0, len(tasks), max_workers):
            batch = tasks[i : i + max_workers]
            results = await asyncio.gather(*batch)
            all_results.extend(results)  # <--- 2. Guardar resultados del lote actual

            successful_deploys += sum(1 for r in results if r.get("status") == "exitoso")
            failed_deploys += sum(1 for r in results if r.get("status") == "fallido")

        logger.info(f"Ciclo de despliegue completado. Exitosos: {successful_deploys}, Fallidos: {failed_deploys}.")

        return all_results

    def _obtener_bot_input_robot(self, robot_id: int, default_bot_input: dict) -> dict:
        """
        Obtiene los parámetros de bot_input configurados para un robot específico.
        Si el robot tiene parámetros configurados en la BD, los usa; caso contrario usa el valor por defecto.
        """
        try:
            query = "SELECT Parametros FROM dbo.Robots WHERE RobotId = ?"
            result = self._db_connector.ejecutar_consulta(query, (robot_id,), es_select=True)

            if result and result[0].get("Parametros"):
                try:
                    # Intentar parsear el JSON de Parametros
                    parametros_json = json.loads(result[0]["Parametros"])
                    if parametros_json and isinstance(parametros_json, dict):
                        logger.debug(f"Robot {robot_id} tiene parámetros personalizados: {parametros_json}")
                        return parametros_json
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Error al parsear Parametros del Robot {robot_id}: {e}. Usando valor por defecto.")

            # Si no hay parámetros o hay error, usar el valor por defecto
            logger.debug(f"Robot {robot_id} usando parámetros por defecto")
            return default_bot_input
        except Exception as e:
            logger.error(
                f"Error al obtener parámetros del Robot {robot_id}: {e}. Usando valor por defecto.", exc_info=True
            )
            return default_bot_input

    async def _desplegar_y_registrar_robot(
        self, robot_info: dict, default_bot_input: dict, cabeceras_callback: dict
    ) -> Dict[str, Any]:
        """
        Intenta desplegar un robot, manejando errores 412 con reintentos
        y errores 400 como permanentes + alerta.
        """
        robot_id = robot_info.get("RobotId")
        user_id = robot_info.get("UserId")
        equipo_id = robot_info.get("EquipoId")
        hora = robot_info.get("Hora")

        # Obtener bot_input específico del robot o usar el valor por defecto
        bot_input = self._obtener_bot_input_robot(robot_id, default_bot_input)

        detected_error_type = None

        # Configuración de reintentos
        max_intentos = self._cfg_lanzador.get("max_reintentos_deploy", 2)
        delay_seg = self._cfg_lanzador.get("delay_reintentos_deploy_seg", 5)
        intento = 0
        for intento in range(1, max_intentos + 1):
            try:
                # 1. INTENTAR DESPLEGAR
                deployment_result = await self._aa_client.desplegar_bot_v4(
                    file_id=robot_id,
                    user_ids=[user_id],
                    bot_input=bot_input,
                    callback_auth_headers=cabeceras_callback,
                )

                # Validar respuesta
                if not deployment_result or "deploymentId" not in deployment_result:
                    error_msg = deployment_result.get("error", "No se recibió deploymentId")
                    logger.error(f"Respuesta inválida de A360 para Robot {robot_id}: {error_msg}")
                    return {"status": "fallido", "robot_id": robot_id}

                deployment_id = deployment_result["deploymentId"]

                # 2. ÉXITO - Registrar en BD
                logger.debug(
                    f"Robot {robot_id} desplegado con ID: {deployment_id} en Equipo {equipo_id} (Intento {intento}/{max_intentos})"
                )

                self._db_connector.insertar_registro_ejecucion(
                    id_despliegue=deployment_id,
                    db_robot_id=robot_id,
                    db_equipo_id=equipo_id,
                    a360_user_id=user_id,
                    marca_tiempo_programada=hora,
                    estado="DEPLOYED",
                )

                return {"status": "exitoso", "robot_id": robot_id, "equipo_id": equipo_id}

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                response_text_full = e.response.text  # Mensaje completo para análisis
                response_text = response_text_full[:200]  # Limitar para logs

                if status_code == 412:
                    detected_error_type = "412"

                    # Verificar si es un error del robot (no compatible targets)
                    # Este error indica un problema con el robot, no con el device
                    is_robot_error = False
                    error_message_lower = response_text_full.lower()

                    # Buscar el mensaje de error en el texto (puede venir en JSON o texto plano)
                    error_message_to_check = error_message_lower
                    try:
                        # Intentar parsear como JSON para extraer el mensaje
                        error_json = json.loads(response_text_full)
                        if isinstance(error_json, dict) and "message" in error_json:
                            error_message_to_check = error_json["message"].lower()
                    except (json.JSONDecodeError, TypeError):
                        # Si no es JSON, usar el texto completo
                        pass

                    # Verificar si contiene el mensaje de error de targets no compatibles
                    if "no compatible targets found in automation" in error_message_to_check:
                        is_robot_error = True
                        detected_error_type = "412_robot_error"  # Marcar como error del robot

                        # Enviar email inmediatamente con el mensaje de error completo
                        logger.error(
                            f"Error 412 - Problema con Robot {robot_id} (no es problema del device). "
                            f"Error: {response_text_full}"
                        )
                        try:
                            self._notificador.send_alert(
                                subject=f"[SAM CRÍTICO] Error en Robot {robot_id} - No Compatible Targets",
                                message=(
                                    f"Error al desplegar robot (Error 412 - Problema con el robot, NO con el device):\n\n"
                                    f"• RobotId: {robot_id}\n"
                                    f"• EquipoId: {equipo_id}\n"
                                    f"• UserId: {user_id}\n\n"
                                    f"Mensaje de error completo:\n{response_text_full}\n\n"
                                    f"Acción requerida: Revisar la configuración del robot en A360. "
                                    f"El robot no tiene targets compatibles configurados."
                                ),
                            )
                        except Exception as mail_e:
                            logger.error(f"Fallo al enviar alerta de error de robot: {mail_e}")

                        # No reintentar, es un error permanente del robot
                        break

                    # Si no es error del robot, tratarlo como error temporal (Device Offline)
                    if not is_robot_error:
                        if intento < max_intentos:
                            logger.warning(
                                f"Error 412 (Device Offline) Robot {robot_id} Equipo {equipo_id}. "
                                f"Reintentando ({intento + 1}/{max_intentos}) en {delay_seg}s..."
                            )
                            await asyncio.sleep(delay_seg)
                            continue
                        else:
                            logger.warning(
                                f"Error 412 persistente Robot {robot_id} Equipo {equipo_id} después de {max_intentos} intentos. Dispositivo offline."
                            )
                            break
                elif status_code == 400:
                    detected_error_type = "400"

                    # Verificar si es un error temporal de dispositivo offline
                    is_device_offline = False
                    error_message_lower = response_text_full.lower()

                    # Patrones que indican que el dispositivo está offline (error temporal)
                    device_offline_patterns = [
                        "are not active",
                        "not connected",
                        "device is offline",
                        "device(s) are not active",
                        "device(s) not connected",
                    ]

                    for pattern in device_offline_patterns:
                        if pattern in error_message_lower:
                            is_device_offline = True
                            break

                    if is_device_offline:
                        # ERROR TEMPORAL - Dispositivo offline, reintentar
                        detected_error_type = "400_device_offline"

                        if intento < max_intentos:
                            logger.warning(
                                f"Error 400 (Device Offline) Robot {robot_id} Equipo {equipo_id}. "
                                f"Reintentando ({intento + 1}/{max_intentos}) en {delay_seg}s... "
                                f"Error: {response_text}"
                            )
                            await asyncio.sleep(delay_seg)
                            continue
                        else:
                            logger.warning(
                                f"Error 400 persistente (Device Offline) Robot {robot_id} Equipo {equipo_id} "
                                f"después de {max_intentos} intentos. Dispositivo no disponible."
                            )
                            # No desasignar, solo reportar el fallo
                            break
                    else:
                        # ERROR PERMANENTE (Bad Request de configuración)
                        logger.warning(
                            f"Error 400 PERMANENTE Robot {robot_id} Equipo {equipo_id} Usuario {user_id}. "
                            f"Revise configuración. Error: {response_text}"
                        )

                        # Solo alertar la primera vez por equipo
                        equipo_alertado_key = f"400_{equipo_id}"
                        if equipo_alertado_key not in self._equipos_alertados_400:
                            logger.debug(f"Intentando enviar alerta para error 400 en equipo {equipo_id}")
                            try:
                                self._notificador.send_alert(
                                    subject=f"[SAM CRÍTICO] Error 400 Equipo {equipo_id}",
                                    message=(
                                        f"Error de Configuración (400 Bad Request) al desplegar:\n\n"
                                        f"• RobotId: {robot_id}\n"
                                        f"• EquipoId: {equipo_id}\n"
                                        f"• UserId: {user_id}\n\n"
                                        f"Causa: {response_text}\n\n"
                                        f"Acción requerida: Verificar permisos, licencias o existencia del bot en A360."
                                    ),
                                )
                                self._equipos_alertados_400.add(equipo_alertado_key)
                            except Exception as mail_e:
                                logger.error(f"Fallo al enviar alerta: {mail_e}")

                        # Desactivar asignación problemática
                        try:
                            self._db_connector.ejecutar_consulta(
                                "DELETE FROM dbo.Asignaciones WHERE RobotId = ? AND EquipoId = ?",
                                (robot_id, equipo_id),
                                es_select=False,
                            )
                            logger.debug(f"Asignación desactivada: Robot {robot_id} - Equipo {equipo_id}")
                        except Exception as db_e:
                            logger.error(f"Error al desactivar asignación: {db_e}")

                        break

                else:
                    # OTROS ERRORES HTTP
                    logger.error(f"Error HTTP {status_code} Robot {robot_id} Equipo {equipo_id}: {response_text}")
                    break

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                # ERRORES DE RED/TIMEOUT
                if intento < max_intentos:
                    logger.warning(
                        f"Error de Red ({type(e).__name__}) Robot {robot_id} Equipo {equipo_id}. "
                        f"Reintentando ({intento + 1}/{max_intentos}) en {delay_seg}s..."
                    )
                    await asyncio.sleep(delay_seg)
                    continue
                else:
                    logger.error(f"Error de Red persistente Robot {robot_id} Equipo {equipo_id}. Fallo definitivo.")
                    break

            except Exception as e:
                # ERRORES GENÉRICOS
                logger.error(f"Error genérico Robot {robot_id} Equipo {equipo_id}: {e}", exc_info=True)
                break

        # Fallo después de todos los intentos
        logger.error(f"Fallo definitivo Robot {robot_id} Equipo {equipo_id} después de {intento} intentos.")
        return {
            "status": "fallido",
            "robot_id": robot_id,
            "equipo_id": equipo_id,  # <--- IMPORTANTE: Necesario para la alerta
            "error_type": detected_error_type,  # <--- IMPORTANTE: Pasa "412" si ocurrió
        }

    async def _preparar_cabeceras_callback(self) -> Dict[str, str]:
        """Obtiene y combina las cabeceras de autorización para el callback."""
        combined_headers = {}
        try:
            logger.debug("Obteniendo token dinámico del API Gateway...")
            gateway_headers = await self._api_gateway_client.get_auth_header()
            if gateway_headers:
                combined_headers.update(gateway_headers)
            else:
                logger.warning("No se pudo obtener token del API Gateway.")
        except Exception as token_error:
            logger.error(f"Excepción al obtener token del API Gateway: {token_error}.", exc_info=True)

        if self._static_callback_api_key:
            logger.debug("Añadiendo ApiKey estática (X-Authorization) a las cabeceras del callback.")
            combined_headers["X-Authorization"] = self._static_callback_api_key
        else:
            logger.warning("La ApiKey estática (CALLBACK_TOKEN) no está configurada.")

        return combined_headers

    def _esta_en_pausa(self) -> bool:
        """Verifica si la hora actual está dentro de la ventana de pausa operacional."""
        start_str, end_str = self._cfg_lanzador.get("pausa_lanzamiento", (None, None))
        if not start_str or not end_str:
            return False
        try:
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
            tz = pytz.timezone("America/Argentina/Buenos_Aires")
            current_time = datetime.now(tz).time()

            if start_time > end_time:
                return current_time >= start_time or current_time < end_time
            else:
                return start_time <= current_time < end_time
        except (ValueError, pytz.exceptions.UnknownTimeZoneError) as e:
            logger.error(f"Error al procesar la ventana de pausa. Verifique el formato HH:MM. Error: {e}")
            return False
