# sam/lanzador/service/desplegador.py
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import pytz

from sam.common.a360_client import AutomationAnywhereClient
from sam.common.alert_types import AlertContext, AlertLevel, AlertScope, AlertType, ServerErrorPattern
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
        # Control para no spamear alertas de error 500 en el mismo ciclo
        self._equipos_alertados_500 = set()

        # --- SISTEMA DE ALERTAS MEJORADO ---
        self._server_error_history: List[ServerErrorPattern] = []
        self._in_recovery_mode: bool = False
        self._recovery_start_time: Optional[datetime] = None
        self._alert_history: Dict[str, List[datetime]] = {}

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
        robot_nombre = robot_info.get("Robot")
        user_id = robot_info.get("UserId")
        user_nombre = robot_info.get("UserName")
        equipo_id = robot_info.get("EquipoId")
        equipo_nombre = robot_info.get("Equipo")
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
                    logger.error(f"Respuesta inválida de A360 para Robot {robot_id} ({robot_nombre}): {error_msg}")
                    return {"status": "fallido", "robot_id": robot_id}

                deployment_id = deployment_result["deploymentId"]

                # 2. ÉXITO - Registrar en BD
                logger.debug(
                    f"Robot {robot_id} ({robot_nombre}) desplegado con ID: {deployment_id} "
                    f"en Equipo {equipo_id} ({equipo_nombre}) (Intento {intento}/{max_intentos})"
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
                            f"Error 412 - Problema con Robot {robot_id} ({robot_nombre}) - No compatible targets. Error: {response_text_full}"
                        )
                        context = AlertContext(
                            alert_level=AlertLevel.CRITICAL,
                            alert_scope=AlertScope.ROBOT,
                            alert_type=AlertType.PERMANENT,
                            subject=f"Robot '{robot_nombre}' no configurable",
                            summary=f"El robot '{robot_nombre}' no tiene dispositivos compatibles asignados en A360.",
                            technical_details={
                                "Robot": f"{robot_nombre} (ID: {robot_id})",
                                "Equipo": f"{equipo_nombre} (ID: {equipo_id})",
                                "Usuario": f"{user_nombre} (ID: {user_id})",
                                "Error": "No compatible targets found",
                            },
                            actions=[
                                f"Ingresar a A360 Control Room > Bots > {robot_nombre}",
                                "Editar el bot y verificar la pestaña 'Run settings'",
                                "Asegurar que haya al menos un dispositivo en 'Run with these devices'",
                            ],
                        )
                        alert_sent = self._notificador.send_alert_v2(context)
                        if not alert_sent:
                            logger.error(f"Fallo al enviar alerta de error de robot {robot_id} ({robot_nombre})")

                        # No reintentar, es un error permanente del robot
                        break

                    # Si no es error del robot, tratarlo como error temporal (Device Offline)
                    if not is_robot_error:
                        if intento < max_intentos:
                            logger.warning(
                                f"Error 412 (Device Offline) Robot {robot_id} ({robot_nombre}) "
                                f"Equipo {equipo_id} ({equipo_nombre}). "
                                f"Reintentando ({intento + 1}/{max_intentos}) en {delay_seg}s..."
                            )
                            await asyncio.sleep(delay_seg)
                            continue
                        else:
                            logger.warning(
                                f"Error 412 persistente Robot {robot_id} ({robot_nombre}) "
                                f"Equipo {equipo_id} ({equipo_nombre}) después de {max_intentos} intentos. "
                                f"Dispositivo offline."
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
                                f"Error 400 (Device Offline) Robot {robot_id} ({robot_nombre}) "
                                f"Equipo {equipo_id} ({equipo_nombre}). "
                                f"Reintentando ({intento + 1}/{max_intentos}) en {delay_seg}s... "
                                f"Error: {response_text}"
                            )
                            await asyncio.sleep(delay_seg)
                            continue
                        else:
                            logger.warning(
                                f"Error 400 persistente (Device Offline) Robot {robot_id} ({robot_nombre}) "
                                f"Equipo {equipo_id} ({equipo_nombre}) "
                                f"después de {max_intentos} intentos. Dispositivo no disponible."
                            )
                            # No desasignar, solo reportar el fallo
                            break
                    else:
                        # ERROR PERMANENTE (Bad Request de configuración)
                        logger.warning(
                            f"Error 400 PERMANENTE Robot {robot_id} ({robot_nombre}) "
                            f"Equipo {equipo_id} ({equipo_nombre}) Usuario {user_id} ({user_nombre}). "
                            f"Revise configuración. Error: {response_text}"
                        )

                        # Solo alertar la primera vez por equipo
                        equipo_alertado_key = f"400_{equipo_id}"
                        if equipo_alertado_key not in self._equipos_alertados_400:
                            logger.debug(
                                f"Intentando enviar alerta para error 400 en equipo {equipo_id} ({equipo_nombre})"
                            )
                            context = AlertContext(
                                alert_level=AlertLevel.CRITICAL,
                                alert_scope=AlertScope.ROBOT,
                                alert_type=AlertType.PERMANENT,
                                subject=f"Error de configuración en despliegue de '{robot_nombre}'",
                                summary=f"Fallo de configuración (400 Bad Request) al intentar desplegar en {equipo_nombre}.",
                                technical_details={
                                    "Robot": f"{robot_nombre} (ID: {robot_id})",
                                    "Equipo": f"{equipo_nombre} (ID: {equipo_id})",
                                    "Usuario": f"{user_nombre} (ID: {user_id})",
                                    "Error": response_text,
                                },
                                actions=[
                                    f"Verificar que el usuario '{user_nombre}' tenga permisos sobre el robot",
                                    "Confirmar que haya licencias disponibles en A360",
                                    "Validar que el robot exista en el Control Room",
                                ],
                            )
                            alert_sent = self._notificador.send_alert_v2(context)
                            if alert_sent:
                                self._equipos_alertados_400.add(equipo_alertado_key)
                            else:
                                logger.error(
                                    f"Fallo al enviar alerta de error 400 para equipo {equipo_id} ({equipo_nombre})"
                                )

                        # Desactivar asignación problemática
                        try:
                            self._db_connector.ejecutar_consulta(
                                "DELETE FROM dbo.Asignaciones WHERE RobotId = ? AND EquipoId = ?",
                                (robot_id, equipo_id),
                                es_select=False,
                            )
                            logger.debug(
                                f"Asignación desactivada: Robot {robot_id} ({robot_nombre}) - Equipo {equipo_id} ({equipo_nombre})"
                            )
                        except Exception as db_e:
                            logger.error(f"Error al desactivar asignación: {db_e}")

                        break

                elif status_code >= 500:
                    # ERRORES DEL SERVIDOR (5xx) - Error crítico del servidor A360
                    detected_error_type = f"{status_code}_server_error"
                    logger.error(
                        f"Error HTTP {status_code} (Server Error) Robot {robot_id} ({robot_nombre}) Equipo {equipo_id} ({equipo_nombre}): {response_text}"
                    )

                    # --- LÓGICA DE DETECCIÓN DE REINICIO A360 ---
                    self._track_server_error(status_code)
                    recovery_status = self._check_recovery_window()

                    should_alert = False
                    alert_context = None

                    if recovery_status == "RECOVERY":
                        logger.info(f"Suprimiendo alerta 5xx (Modo Recuperación Activo). Status: {status_code}")

                    elif recovery_status == "TIMEOUT":
                        # Fallo persistente tras ventana de recuperación
                        should_alert = True
                        alert_context = AlertContext(
                            alert_level=AlertLevel.CRITICAL,
                            alert_scope=AlertScope.SYSTEM,
                            alert_type=AlertType.PERMANENT,
                            subject="Control Room A360 caído persistentemente",
                            summary="El servidor A360 no se ha recuperado después de 5 minutos de inestabilidad.",
                            technical_details={
                                "Último Error": f"{status_code} - {response_text}",
                                "Tiempo Caída": "> 5 minutos",
                            },
                            actions=[
                                "Contactar a Soporte de Infraestructura AHORA",
                                "Verificar servicios de A360 en el servidor",
                            ],
                        )
                        # Salir de modo recovery para permitir futuras alertas si esto persiste
                        self._in_recovery_mode = False

                    elif recovery_status == "NORMAL":
                        if self._is_potential_recovery():
                            # Detectado patrón de reinicio -> Entrar en modo recovery
                            self._in_recovery_mode = True
                            self._recovery_start_time = datetime.now()
                            should_alert = True
                            alert_context = AlertContext(
                                alert_level=AlertLevel.MEDIUM,
                                alert_scope=AlertScope.SYSTEM,
                                alert_type=AlertType.RECOVERY,
                                subject="Control Room A360 posiblemente reiniciándose",
                                summary="Se han detectado múltiples errores 5xx en corto tiempo. Posible reinicio en curso.",
                                technical_details={
                                    "Patrón": "Múltiples 5xx en < 3 min",
                                    "Errores recientes": str([p.status_code for p in self._server_error_history[-3:]]),
                                },
                                actions=[
                                    "Esperar 5 minutos a que el servicio se estabilice",
                                    "No reiniciar servicios manualmente aún",
                                ],
                            )
                        else:
                            # Error 5xx aislado o inicial -> Alerta estándar pero CRITICAL
                            # Solo alertar si no se ha alertado recientemente para este equipo (evitar spam local)
                            equipo_alertado_key = f"{status_code}_{equipo_id}"
                            if equipo_alertado_key not in self._equipos_alertados_500:
                                should_alert = True
                                alert_context = AlertContext(
                                    alert_level=AlertLevel.CRITICAL,
                                    alert_scope=AlertScope.ROBOT,
                                    alert_type=AlertType.PERMANENT,
                                    subject=f"Error 500 en Despliegue de '{robot_nombre}'",
                                    summary="Error 500 irreversible al intentar desplegar. Posible ID de archivo o usuario inválido.",
                                    technical_details={
                                        "Robot": f"{robot_nombre} (ID: {robot_id})",
                                        "Equipo": f"{equipo_nombre} (ID: {equipo_id})",
                                        "Usuario": f"{user_nombre} (ID: {user_id})",
                                        "Error": f"{status_code} - {response_text}",
                                    },
                                    actions=[
                                        "Verificar que el FileId del robot exista en A360",
                                        "Verificar que el UserId del usuario exista en A360",
                                        "Si el error persiste, contactar soporte de A360",
                                    ],
                                )
                                self._equipos_alertados_500.add(equipo_alertado_key)

                    if should_alert and alert_context:
                        # Usar tracking de frecuencia para no spamear la misma alerta de sistema
                        alert_key = f"SYSTEM_5XX_{alert_context.alert_type.value}"
                        if self._should_send_alert(alert_key, cooldown_min=15):
                            alert_context.frequency_info = self._get_frequency_info(alert_key)
                            self._notificador.send_alert_v2(alert_context)

                    # No reintentar errores del servidor, esperar al próximo ciclo
                    break
                else:
                    # OTROS ERRORES HTTP (401, 403, 404, etc.)
                    detected_error_type = f"{status_code}_http_error"
                    logger.error(
                        f"Error HTTP {status_code} Robot {robot_id} ({robot_nombre}) Equipo {equipo_id} ({equipo_nombre}): {response_text}"
                    )
                    break

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                # ERRORES DE RED/TIMEOUT
                if intento < max_intentos:
                    logger.warning(
                        f"Error de Red ({type(e).__name__}) Robot {robot_id} ({robot_nombre}) "
                        f"Equipo {equipo_id} ({equipo_nombre}). "
                        f"Reintentando ({intento + 1}/{max_intentos}) en {delay_seg}s..."
                    )
                    await asyncio.sleep(delay_seg)
                    continue
                else:
                    logger.error(
                        f"Error de Red persistente Robot {robot_id} ({robot_nombre}) Equipo {equipo_id} ({equipo_nombre}). Fallo definitivo."
                    )
                    break

            except Exception as e:
                # ERRORES GENÉRICOS
                logger.error(
                    f"Error genérico Robot {robot_id} ({robot_nombre}) Equipo {equipo_id} ({equipo_nombre}): {e}",
                    exc_info=True,
                )
                break

        # Fallo después de todos los intentos
        logger.error(
            f"Fallo definitivo Robot {robot_id} ({robot_nombre}) Equipo {equipo_id} ({equipo_nombre}) después de {intento} intentos."
        )
        return {
            "status": "fallido",
            "robot_id": robot_id,
            "equipo_id": equipo_id,  # <--- IMPORTANTE: Necesario para la alerta
            "equipo_nombre": equipo_nombre,  # <--- Agregar nombre del equipo para mejor contexto
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

    # --- MÉTODOS DE SOPORTE PARA ALERTAS MEJORADAS ---

    def _track_server_error(self, status_code: int) -> None:
        """Registra un error 5xx para detección de patrones."""
        now = datetime.now()
        # Limpiar historial antiguo (> 10 min)
        self._server_error_history = [
            p for p in self._server_error_history if (now - p.timestamp).total_seconds() < 600
        ]
        self._server_error_history.append(ServerErrorPattern(status_code, now))

    def _is_potential_recovery(self) -> bool:
        """
        Detecta si hay un patrón de reinicio:
        Al menos 2 errores 5xx diferentes en los últimos 3 minutos.
        """
        now = datetime.now()
        recent_errors = [p for p in self._server_error_history if (now - p.timestamp).total_seconds() < 180]

        if len(recent_errors) < 2:
            return False

        # Verificar si hay códigos de estado diferentes (ej: 500 y 502)
        unique_codes = {p.status_code for p in recent_errors}
        return len(unique_codes) >= 2 or len(recent_errors) >= 3

    def _check_recovery_window(self) -> str:
        """
        Verifica el estado de la ventana de recuperación.
        Returns: 'NORMAL', 'RECOVERY', 'TIMEOUT'
        """
        if not self._in_recovery_mode:
            return "NORMAL"

        if not self._recovery_start_time:
            self._in_recovery_mode = False
            return "NORMAL"

        elapsed = (datetime.now() - self._recovery_start_time).total_seconds()

        # Ventana de 5 minutos (300s)
        if elapsed > 300:
            return "TIMEOUT"

        return "RECOVERY"

    def _should_send_alert(self, alert_key: str, cooldown_min: int = 30) -> bool:
        """
        Determina si se debe enviar una alerta basado en cooldown.
        """
        now = datetime.now()
        history = self._alert_history.get(alert_key, [])

        if not history:
            self._alert_history[alert_key] = [now]
            return True

        last_sent = history[-1]
        if (now - last_sent).total_seconds() < (cooldown_min * 60):
            return False

        history.append(now)
        # Mantener solo las últimas 10 ocurrencias
        self._alert_history[alert_key] = history[-10:]
        return True

    def _get_frequency_info(self, alert_key: str) -> str:
        """Genera texto informativo sobre la frecuencia de la alerta."""
        history = self._alert_history.get(alert_key, [])
        count = len(history)
        if count <= 1:
            return "Primera ocurrencia registrada."

        last = history[-2] if count >= 2 else history[0]
        diff_min = int((datetime.now() - last).total_seconds() / 60)
        return f"Esta alerta se ha disparado {count} veces. Última vez hace {diff_min} minutos."
