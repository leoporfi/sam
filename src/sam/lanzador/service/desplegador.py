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
        # Control para no spamear alertas de error 412 (robot error) en el mismo ciclo
        self._equipos_alertados_412 = set()
        # Control para no spamear alertas de error 500 en el mismo ciclo
        # Control para no spamear alertas de error 500 en el mismo ciclo
        self._equipos_alertados_500 = set()

        # --- PROTECCIÓN DE REBOTE (Circuit Breaker Local) ---
        # Almacena (robot_id, equipo_id) -> datetime_lanzamiento
        # Evita re-lanzar robots si la BD falló al registrar el inicio pero A360 sí lo lanzó.
        self._cooldown_despliegues: Dict[tuple, datetime] = {}

        # --- SISTEMA DE ALERTAS MEJORADO ---
        self._server_error_history: List[ServerErrorPattern] = []
        self._in_recovery_mode: bool = False
        self._system_is_down: bool = False
        self._recovery_lock = asyncio.Lock()
        self._recovery_start_time: Optional[datetime] = None
        self._alert_history: Dict[str, List[datetime]] = {}

    async def desplegar_robots_pendientes(self) -> List[Dict[str, Any]]:
        """
        Orquestación principal del despliegue:
        1. Verifica pausa.
        2. Obtiene robots de la BD.
        3. Filtra robots en cooldown (protección de rebote).
        4. Obtiene token API Gateway.
        5. Ejecuta despliegues en paralelo.
        6. Retorna resultados para que el Orquestador gestione alertas (ej. 412).
        """
        if self._esta_en_pausa():
            logger.info("Lanzador en PAUSA operativa configurada. Omitiendo ciclo.")
            return []

        # 1. Limpieza de memoria a corto plazo (Cooldowns expirados > 10 min)
        now = datetime.now()
        cooldown_minutos = 10
        self._cooldown_despliegues = {
            k: v for k, v in self._cooldown_despliegues.items() if (now - v).total_seconds() < (cooldown_minutos * 60)
        }

        logger.info("Buscando robots para ejecutar...")
        robots_raw = self._db_connector.obtener_robots_ejecutables()

        # 2. Filtrado por Cooldown (Evitar bucle zombi si falló DB)
        robots_a_ejecutar = []
        for r in robots_raw:
            key = (r.get("RobotId"), r.get("EquipoId"))
            if key in self._cooldown_despliegues:
                logger.warning(
                    f"Omitiendo Robot {r.get('Robot')} en Equipo {r.get('Equipo')} "
                    f"porque está en periodo de enfriamiento (posible fallo previo de registro en BD)."
                )
                continue
            robots_a_ejecutar.append(r)

        if not robots_a_ejecutar:
            logger.info("No hay robots para ejecutar en este ciclo.")
            # Verificar si el sistema se recuperó aunque no haya robots para lanzar
            await self._check_and_notify_system_recovery(force_health_check=True)
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

                try:
                    self._db_connector.insertar_registro_ejecucion(
                        id_despliegue=deployment_id,
                        db_robot_id=robot_id,
                        db_equipo_id=equipo_id,
                        a360_user_id=user_id,
                        marca_tiempo_programada=hora,
                        estado="DEPLOYED",
                    )

                    # Si el despliegue es exitoso, verificar si venimos de una caída del sistema
                    await self._check_and_notify_system_recovery(force_health_check=False)
                except Exception as db_e:
                    logger.error(
                        f"Error al registrar ejecución en BD para Robot {robot_id} ({robot_nombre}) "
                        f"con DeployID {deployment_id}. El robot se está ejecutando, pero SAM no lo monitoreará. "
                        f"Activando protección de rebote local. Error: {db_e}"
                    )
                    # Activar Circuit Breaker Local:
                    # Evitar que el SP nos devuelva este robot en el próximo ciclo
                    self._cooldown_despliegues[(robot_id, equipo_id)] = datetime.now()

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

                        # Solo alertar la primera vez por equipo
                        equipo_alertado_key = f"412_{equipo_id}"
                        if equipo_alertado_key not in self._equipos_alertados_412:
                            # Enviar email inmediatamente con el mensaje de error completo
                            logger.error(
                                f"Error 412 - Problema con Robot {robot_id} ({robot_nombre}) - No compatible targets. Error: {response_text_full}"
                            )
                            links = self._cfg_lanzador.get("links", {})
                            context = AlertContext(
                                alert_level=AlertLevel.CRITICAL,
                                alert_scope=AlertScope.ROBOT,
                                alert_type=AlertType.PERMANENT,
                                subject=f"Fallo de Integridad/Configuración en '{robot_nombre}' - ASIGNACIÓN ELIMINADA",
                                summary=(
                                    f"El robot '{robot_nombre}' presenta un fallo de integridad o configuración en A360 (Error 412). "
                                    "Esto puede deberse a falta de dispositivos compatibles o errores internos en el Taskbot. "
                                    "La asignación ha sido ELIMINADA de SAM para evitar reintentos fallidos."
                                ),
                                technical_details={
                                    "Robot": f"{robot_nombre} (ID: {robot_id})",
                                    "Equipo": f"{equipo_nombre} (ID: {equipo_id})",
                                    "Usuario": f"{user_nombre} (ID: {user_id})",
                                    "Error": "No compatible targets found / Code Integrity Error",
                                    "Explicación": (
                                        "Este error ocurre cuando el bot tiene configuraciones de ejecución (Run settings) "
                                        "incompatibles, o cuando el Taskbot tiene errores de integridad (paquetes o variables rotas)."
                                    ),
                                    "Documentación": links.get("aa_docs_run_settings"),
                                },
                                actions=[
                                    "1. Ingresar a A360 Control Room > Bots > " + robot_nombre,
                                    "2. Abrir el bot en el editor y verificar si hay errores de integridad (íconos rojos).",
                                    "3. En 'Run settings', asegurar que el dispositivo o el pool estén permitidos.",
                                    "4. UNA VEZ RESUELTO: Volver a asignar el equipo al robot manualmente en el panel de SAM.",
                                    "NOTA: El sistema NO volverá a intentar este lanzamiento hasta que se realice la re-asignación manual.",
                                ],
                            )
                            alert_sent = self._notificador.send_alert_v2(context)
                            if alert_sent:
                                self._equipos_alertados_412.add(equipo_alertado_key)
                            else:
                                logger.error(f"Fallo al enviar alerta de error de robot {robot_id} ({robot_nombre})")

                        # REGISTRAR FALLO EN BD para que no reintente en este ciclo/horario
                        try:
                            dummy_deploy_id = f"FAIL_412_{datetime.now().strftime('%Y%m%d%H%M%S')}_{robot_id}"
                            self._db_connector.insertar_registro_ejecucion(
                                id_despliegue=dummy_deploy_id,
                                db_robot_id=robot_id,
                                db_equipo_id=equipo_id,
                                a360_user_id=user_id,
                                marca_tiempo_programada=hora,
                                estado="DEPLOY_FAILED",
                            )
                            logger.debug(f"Fallo 412 registrado en BD para Robot {robot_id}")
                        except Exception as db_e:
                            logger.error(f"Error al registrar fallo 412 en BD: {db_e}")

                        # DESACTIVAR ASIGNACIÓN (Error permanente de configuración)
                        try:
                            self._db_connector.ejecutar_consulta(
                                "DELETE FROM dbo.Asignaciones WHERE RobotId = ? AND EquipoId = ?",
                                (robot_id, equipo_id),
                                es_select=False,
                            )
                            logger.info(
                                f"Asignación desactivada por Error 412: Robot {robot_id} ({robot_nombre}) - Equipo {equipo_id} ({equipo_nombre})"
                            )
                        except Exception as db_e:
                            logger.error(f"Error al desactivar asignación por 412: {db_e}")

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

                    # --- NUEVO: Manejo específico de "No Default Device" ---
                    elif "none of the user(s) provided have default device(s)" in error_message_lower:
                        detected_error_type = "400_no_default_device"
                        logger.warning(
                            f"Error 400 (No Default Device) Robot {robot_id} ({robot_nombre}) "
                            f"Equipo {equipo_id} ({equipo_nombre}). El usuario {user_nombre} no tiene dispositivo por defecto."
                        )

                        # Solo alertar si no está en cooldown (1 hora) para no spamear
                        alert_key = f"400_no_device_{equipo_id}"
                        if self._should_send_alert(alert_key, cooldown_min=60):
                            context = AlertContext(
                                alert_level=AlertLevel.CRITICAL,
                                alert_scope=AlertScope.DEVICE,
                                alert_type=AlertType.PERMANENT,
                                subject="Configuración Requerida en A360 - Usuario sin Dispositivo por Defecto",
                                summary=(
                                    f"El usuario '{user_nombre}' no tiene un dispositivo por defecto asignado en A360. "
                                    "Esto impide el lanzamiento automático pero la asignación en SAM se MANTENDRÁ activa."
                                ),
                                technical_details={
                                    "Robot": f"{robot_nombre} (ID: {robot_id})",
                                    "Equipo": f"{equipo_nombre} (ID: {equipo_id})",
                                    "Usuario": f"{user_nombre} (ID: {user_id})",
                                    "Error": "None of the user(s) provided have default device(s)",
                                },
                                actions=[
                                    "1. Ingresar al Control Room de A360 > Manage > Users.",
                                    f"2. Buscar y editar al usuario '{user_nombre}'.",
                                    "3. En la sección 'Device settings', seleccionar un dispositivo como 'Default Device'.",
                                    "4. Guardar los cambios.",
                                    "NOTA: El sistema volverá a intentar este lanzamiento en el próximo ciclo programado.",
                                ],
                            )
                            self._notificador.send_alert_v2(context)

                        # REGISTRAR FALLO EN BD para este ciclo
                        try:
                            dummy_deploy_id = f"FAIL_400_NODEV_{datetime.now().strftime('%Y%m%d%H%M%S')}_{robot_id}"
                            self._db_connector.insertar_registro_ejecucion(
                                id_despliegue=dummy_deploy_id,
                                db_robot_id=robot_id,
                                db_equipo_id=equipo_id,
                                a360_user_id=user_id,
                                marca_tiempo_programada=hora,
                                estado="DEPLOY_FAILED",
                            )
                        except Exception as db_e:
                            logger.error(f"Error al registrar fallo 400_no_device en BD: {db_e}")

                        break

                    else:
                        # ERROR PERMANENTE (Bad Request de configuración)
                        logger.warning(
                            f"Error 400 PERMANENTE Robot {robot_id} ({robot_nombre}) "
                            f"Equipo {equipo_id} ({equipo_nombre}) Usuario {user_id} ({user_nombre}). "
                            f"Revise configuración. Error: {response_text}"
                        )

                        # Análisis de mensaje para explicación más precisa
                        explicacion = (
                            "Este error (400 Bad Request) indica un problema de configuración o integridad en el Taskbot. "
                            "Puede deberse a paquetes inexistentes, variables mal referenciadas, parámetros inválidos o falta de licencias."
                        )
                        acciones = [
                            "1. Abrir el bot en el editor de A360 y verificar si hay errores de integridad (íconos rojos).",
                            "2. Validar que todos los paquetes (Packages) y versiones existan en el Control Room.",
                            "3. Confirmar que el usuario tenga permisos y licencias de Bot Runner disponibles.",
                            "4. Validar que el robot no haya sido movido o renombrado en A360.",
                        ]

                        if "no session found" in error_message_lower:
                            explicacion = "No se encontró una sesión activa para el usuario en el dispositivo. Problema de RDP o inicio de sesión."
                            acciones.insert(0, "Verificar configuración de RDP y credenciales del Bot Runner.")
                        elif "already logged in" in error_message_lower:
                            explicacion = (
                                "El usuario ya tiene una sesión activa en otro dispositivo o sesión de consola."
                            )
                            acciones.insert(0, "Cerrar sesiones activas del usuario en otros equipos.")

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
                                subject=f"Fallo de Integridad/Configuración en '{robot_nombre}' - ASIGNACIÓN ELIMINADA",
                                summary=(
                                    f"Fallo de configuración o integridad (400 Bad Request) al intentar desplegar en {equipo_nombre}. "
                                    "La asignación ha sido ELIMINADA de SAM para evitar reintentos fallidos. "
                                    "Se requiere revisión manual del Taskbot y re-asignación."
                                ),
                                technical_details={
                                    "Robot": f"{robot_nombre} (ID: {robot_id})",
                                    "Equipo": f"{equipo_nombre} (ID: {equipo_id})",
                                    "Usuario": f"{user_nombre} (ID: {user_id})",
                                    "Error": response_text,
                                    "Explicación": explicacion,
                                },
                                actions=acciones
                                + [
                                    "UNA VEZ RESUELTO: Volver a asignar el equipo al robot manualmente en el panel de SAM.",
                                    "NOTA: El sistema NO volverá a intentar este lanzamiento hasta que se realice la re-asignación manual.",
                                ],
                            )
                            alert_sent = self._notificador.send_alert_v2(context)
                            if alert_sent:
                                self._equipos_alertados_400.add(equipo_alertado_key)
                            else:
                                logger.error(
                                    f"Fallo al enviar alerta de error 400 para equipo {equipo_id} ({equipo_nombre})"
                                )

                        # REGISTRAR FALLO EN BD
                        try:
                            dummy_deploy_id = f"FAIL_400_{datetime.now().strftime('%Y%m%d%H%M%S')}_{robot_id}"
                            self._db_connector.insertar_registro_ejecucion(
                                id_despliegue=dummy_deploy_id,
                                db_robot_id=robot_id,
                                db_equipo_id=equipo_id,
                                a360_user_id=user_id,
                                marca_tiempo_programada=hora,
                                estado="DEPLOY_FAILED",
                            )
                            logger.debug(f"Fallo 400 registrado en BD para Robot {robot_id}")
                        except Exception as db_e:
                            logger.error(f"Error al registrar fallo 400 en BD: {db_e}")

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
                        links = self._cfg_lanzador.get("links", {})
                        alert_context = AlertContext(
                            alert_level=AlertLevel.CRITICAL,
                            alert_scope=AlertScope.SYSTEM,
                            alert_type=AlertType.PERMANENT,
                            subject="Control Room A360 Cloud - SERVICIO NO DISPONIBLE",
                            summary="El servicio A360 Cloud no se ha recuperado después de 5 minutos de inestabilidad.",
                            technical_details={
                                "Último Error": f"{status_code} - {response_text}",
                                "Tiempo Caída": "> 5 minutos",
                                "Entorno": "A360 Cloud",
                                "Explicación": (
                                    "El Control Room de Automation Anywhere está devolviendo errores internos (5xx) persistentes. "
                                    "Al ser un entorno Cloud, esto indica una degradación del servicio por parte del proveedor."
                                ),
                                "Status Page": links.get("aa_status_page"),
                            },
                            actions=[
                                f"1. Verificar el estado del servicio en: {links.get('aa_status_page')}",
                                "2. Comprobar si hay tareas de mantenimiento programadas informadas por Automation Anywhere.",
                                "3. Si el estado global es 'Operational' pero el error persiste, abrir un caso de soporte con Automation Anywhere.",
                                "4. Notificar internamente que los lanzamientos automáticos están suspendidos temporalmente.",
                            ],
                        )
                        # Salir de modo recovery pero marcar como caído para notificar cuando vuelva
                        self._in_recovery_mode = False
                        self._system_is_down = True

                    elif recovery_status == "NORMAL":
                        # Verificar salud real del servidor para distinguir caída de error aislado
                        is_server_healthy = await self._aa_client.check_health()

                        if not is_server_healthy:
                            # Servidor NO responde -> Caída de Sistema
                            if not self._in_recovery_mode:
                                self._in_recovery_mode = True
                                self._recovery_start_time = datetime.now()
                                should_alert = True
                                links = self._cfg_lanzador.get("links", {})
                                alert_context = AlertContext(
                                    alert_level=AlertLevel.CRITICAL,
                                    alert_scope=AlertScope.SYSTEM,
                                    alert_type=AlertType.RECOVERY,
                                    subject="Control Room A360 Cloud - SIN CONEXIÓN",
                                    summary="El Control Room Cloud no responde a las verificaciones de salud. Posible problema de red o caída del servicio.",
                                    technical_details={
                                        "Error Original": f"{status_code} - {response_text}",
                                        "Health Check": "Fallido (Timeout o Conexión rechazada)",
                                        "Explicación": (
                                            "SAM no puede establecer conexión con la URL de A360 Cloud. "
                                            "Esto puede deberse a un corte de internet en el servidor de SAM, un problema de DNS, "
                                            "o una caída total de la región de A360 Cloud."
                                        ),
                                    },
                                    actions=[
                                        "1. Verificar la conexión a internet y salida a sitios externos desde el servidor de SAM.",
                                        "2. Validar que la URL del Control Room sea accesible desde un navegador.",
                                        f"3. Revisar el estado de la región de A360 Cloud en la Status Page oficial: {links.get('aa_status_page')}",
                                        "4. Si el problema es local (red), contactar al equipo de Comunicaciones/Networking.",
                                    ],
                                )
                                self._system_is_down = True
                        else:
                            # Servidor SÍ responde -> Error 500 es específico de este request (Robot/Usuario)
                            equipo_alertado_key = f"{status_code}_{equipo_id}"
                            if equipo_alertado_key not in self._equipos_alertados_500:
                                should_alert = True

                                # Análisis de mensaje para explicación más precisa
                                explicacion = (
                                    "El Control Room devolvió un error interno al procesar esta solicitud específica. "
                                    "Esto suele ocurrir si el archivo del robot fue borrado, el usuario está bloqueado, "
                                    "o hay una inconsistencia en la base de datos de A360."
                                )
                                acciones = [
                                    "1. Verificar que el Robot exista y sea visible para el usuario en el Control Room.",
                                    "2. Asegurar que el usuario tenga licencias de 'Bot Runner' disponibles.",
                                ]

                                if "could not start a new session" in error_message_lower:
                                    explicacion = "Fallo al iniciar sesión de navegador o sesión de escritorio. Posible desajuste de versión de Chromedriver o extensión de A360."
                                    acciones.insert(0, "Verificar versión de Chrome y Chromedriver en el Bot Runner.")
                                elif "token that does not exist" in error_message_lower:
                                    explicacion = "Referencia a un token de sesión inexistente. Problema de persistencia de sesión en el Bot Agent."
                                    acciones.insert(
                                        0, "Reiniciar el servicio 'Automation Anywhere Bot Agent' en el equipo."
                                    )

                                alert_context = AlertContext(
                                    alert_level=AlertLevel.CRITICAL,
                                    alert_scope=AlertScope.ROBOT,
                                    alert_type=AlertType.PERMANENT,
                                    subject=f"Error 500 en '{robot_nombre}' - ASIGNACIÓN ELIMINADA",
                                    summary=(
                                        "Error 500 irreversible. El servidor está online, pero rechazó este despliegue específico. "
                                        "La asignación ha sido ELIMINADA de SAM para evitar reintentos fallidos."
                                    ),
                                    technical_details={
                                        "Robot": f"{robot_nombre} (ID: {robot_id})",
                                        "Equipo": f"{equipo_nombre} (ID: {equipo_id})",
                                        "Usuario": f"{user_nombre} (ID: {user_id})",
                                        "Error": f"{status_code} - {response_text}",
                                        "Health Check": "Exitoso (Servidor Online)",
                                        "Explicación": explicacion,
                                    },
                                    actions=acciones
                                    + [
                                        "3. UNA VEZ RESUELTO: Volver a asignar el equipo al robot manualmente en SAM.",
                                        "NOTA: El sistema NO volverá a intentar este lanzamiento hasta que se realice la re-asignación manual.",
                                    ],
                                )
                                self._equipos_alertados_500.add(equipo_alertado_key)

                                # REGISTRAR FALLO EN BD para evitar reintentos infinitos si es un error del robot/usuario
                                try:
                                    dummy_deploy_id = f"FAIL_500_{datetime.now().strftime('%Y%m%d%H%M%S')}_{robot_id}"
                                    self._db_connector.insertar_registro_ejecucion(
                                        id_despliegue=dummy_deploy_id,
                                        db_robot_id=robot_id,
                                        db_equipo_id=equipo_id,
                                        a360_user_id=user_id,
                                        marca_tiempo_programada=hora,
                                        estado="DEPLOY_FAILED",
                                    )
                                    logger.debug(f"Fallo 500 registrado en BD para Robot {robot_id}")
                                except Exception as db_e:
                                    logger.error(f"Error al registrar fallo 500 en BD: {db_e}")

                                # DESACTIVAR ASIGNACIÓN (Error irreversible)
                                try:
                                    self._db_connector.ejecutar_consulta(
                                        "DELETE FROM dbo.Asignaciones WHERE RobotId = ? AND EquipoId = ?",
                                        (robot_id, equipo_id),
                                        es_select=False,
                                    )
                                    logger.info(
                                        f"Asignación desactivada por Error 500 Irreversible: Robot {robot_id} - Equipo {equipo_id}"
                                    )
                                except Exception as db_e:
                                    logger.error(f"Error al desactivar asignación por 500: {db_e}")

                    if should_alert and alert_context:
                        # Usar tracking de frecuencia para no spamear la misma alerta de sistema
                        alert_key = f"SYSTEM_5XX_{alert_context.alert_type.value}"
                        if self._should_send_alert(alert_key, cooldown_min=15):
                            alert_context.frequency_info = self._get_frequency_info(alert_key)
                            self._notificador.send_alert_v2(alert_context)

                    # No reintentar errores del servidor, esperar al próximo ciclo
                    break
                else:
                    # OTROS ERRORES HTTP (401, 403, 404, etc.) - Probablemente permanentes
                    detected_error_type = f"{status_code}_http_error"
                    logger.error(
                        f"Error HTTP {status_code} Robot {robot_id} ({robot_nombre}) Equipo {equipo_id} ({equipo_nombre}): {response_text}"
                    )

                    # Enviar alerta para errores HTTP inesperados
                    context = AlertContext(
                        alert_level=AlertLevel.CRITICAL,
                        alert_scope=AlertScope.ROBOT,
                        alert_type=AlertType.PERMANENT,
                        subject=f"Error HTTP {status_code} en '{robot_nombre}' - ASIGNACIÓN ELIMINADA",
                        summary=(
                            f"Se recibió un error HTTP {status_code} inesperado al intentar desplegar. "
                            "La asignación ha sido ELIMINADA para evitar reintentos fallidos."
                        ),
                        technical_details={
                            "Robot": f"{robot_nombre} (ID: {robot_id})",
                            "Equipo": f"{equipo_nombre} (ID: {equipo_id})",
                            "Usuario": f"{user_nombre} (ID: {user_id})",
                            "Error": f"{status_code} - {response_text}",
                            "Explicación": (
                                "Este error (401, 403, 404) indica problemas de permisos, recursos no encontrados "
                                "o credenciales inválidas para este robot o usuario específico."
                            ),
                        },
                        actions=[
                            f"1. Verificar que el usuario '{user_nombre}' tenga permisos de ejecución en A360.",
                            "2. Confirmar que el robot y el usuario existan en el Control Room.",
                            "3. UNA VEZ RESUELTO: Volver a asignar el equipo al robot manualmente en SAM.",
                        ],
                    )
                    self._notificador.send_alert_v2(context)

                    # DESACTIVAR ASIGNACIÓN
                    try:
                        self._db_connector.ejecutar_consulta(
                            "DELETE FROM dbo.Asignaciones WHERE RobotId = ? AND EquipoId = ?",
                            (robot_id, equipo_id),
                            es_select=False,
                        )
                        logger.info(f"Asignación desactivada por Error HTTP {status_code}")
                    except Exception as db_e:
                        logger.error(f"Error al desactivar asignación por error HTTP: {db_e}")

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
                # ERRORES GENÉRICOS - Inesperados
                detected_error_type = "generic_exception"
                logger.error(
                    f"Error genérico Robot {robot_id} ({robot_nombre}) Equipo {equipo_id} ({equipo_nombre}): {e}",
                    exc_info=True,
                )

                # Alerta para errores de código o excepciones no controladas
                context = AlertContext(
                    alert_level=AlertLevel.CRITICAL,
                    alert_scope=AlertScope.SYSTEM,
                    alert_type=AlertType.PERMANENT,
                    subject=f"Excepción inesperada en despliegue de '{robot_nombre}' - ASIGNACIÓN ELIMINADA",
                    summary="Se produjo un error interno no controlado durante el despliegue. Asignación eliminada por seguridad.",
                    technical_details={
                        "Robot": f"{robot_nombre} (ID: {robot_id})",
                        "Equipo": f"{equipo_nombre} (ID: {equipo_id})",
                        "Error": str(e),
                    },
                    actions=[
                        "1. Revisar los logs del servicio Lanzador para más detalles.",
                        "2. Verificar la integridad de la base de datos y la conexión con A360.",
                        "3. UNA VEZ RESUELTO: Volver a asignar el equipo manualmente.",
                    ],
                )
                self._notificador.send_alert_v2(context)

                # DESACTIVAR ASIGNACIÓN
                try:
                    self._db_connector.ejecutar_consulta(
                        "DELETE FROM dbo.Asignaciones WHERE RobotId = ? AND EquipoId = ?",
                        (robot_id, equipo_id),
                        es_select=False,
                    )
                except Exception as db_e:
                    logger.error(f"Error al desactivar asignación por excepción: {db_e}")

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

    async def _check_and_notify_system_recovery(self, force_health_check: bool = False):
        """
        Verifica si el sistema se ha recuperado de una caída crítica y notifica.
        Se dispara ante un éxito real o periódicamente mediante health check si el sistema está caído.
        """
        if not (self._system_is_down or self._in_recovery_mode):
            return

        async with self._recovery_lock:
            # Doble chequeo dentro del lock
            if not (self._system_is_down or self._in_recovery_mode):
                return

            if force_health_check:
                # Si no hubo un éxito real (ej: ciclo sin robots), verificamos proactivamente
                logger.debug("Verificando recuperación proactiva del servidor A360...")
                is_healthy = await self._aa_client.check_health()
                if not is_healthy:
                    return

            # Si llegamos aquí, el sistema está respondiendo nuevamente
            logger.info("¡SISTEMA RECUPERADO! Enviando notificación de normalización...")

            context = AlertContext(
                alert_level=AlertLevel.MEDIUM,
                alert_scope=AlertScope.SYSTEM,
                alert_type=AlertType.RECOVERY,
                subject="Servicio de Automation Anywhere NORMALIZADO",
                summary="El servidor A360 ha vuelto a responder correctamente. Los despliegues se han reanudado.",
                technical_details={
                    "Estado": "Operativo",
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Detección": "Éxito en Despliegue" if not force_health_check else "Health Check Exitoso",
                },
                actions=[
                    "1. No se requiere acción adicional.",
                    "2. Los contadores de errores temporales de equipos han sido reseteados.",
                    "3. El sistema ha reanudado el procesamiento normal de la cola de lanzamientos.",
                ],
            )

            alert_sent = self._notificador.send_alert_v2(context)
            if alert_sent:
                # Resetear estados de falla del sistema
                self._system_is_down = False
                self._in_recovery_mode = False
                self._recovery_start_time = None
                self._server_error_history.clear()

                # Limpiar alertas de equipos para permitir nuevas notificaciones si vuelven a fallar
                self._equipos_alertados_400.clear()
                self._equipos_alertados_500.clear()

                logger.info("Notificación de normalización enviada y estados reseteados.")
            else:
                logger.error("No se pudo enviar la alerta de normalización, se reintentará en el próximo éxito.")
