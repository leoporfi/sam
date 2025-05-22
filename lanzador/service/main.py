# SAM/Lanzador/service/main.py

import os
import sys
import time
import atexit
import signal
import logging
import threading
from threading import RLock # RLock para locks reentrantes si es necesario
from pathlib import Path
import concurrent.futures
from datetime import datetime, time as dt_time # dt_time para objetos time

import schedule # <--- IMPORTACIÓN DE SCHEDULE

# --- Configuración de Path ---
SAM_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(SAM_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SAM_PROJECT_ROOT))

from lanzador.database.sql_client import DatabaseConnector
from lanzador.clients.aa_client import AutomationAnywhereClient # O el nombre de clase que estés usando
from lanzador.utils.mail_client import EmailAlertClient
from lanzador.utils.config import setup_logging, ConfigManager
from lanzador.service.conciliador import ConciliadorImplementaciones
from typing import List, Dict, Any, Optional # Para type hints

logger = setup_logging()

class LanzadorRobots:
    def __init__(self):
        self.config_lanzador = ConfigManager.get_lanzador_config()
        
        # Leer intervalos para schedule (en segundos)
        self.intervalo_lanzador_seg = self.config_lanzador.get("intervalo_lanzador_seg", 30)
        self.intervalo_conciliador_seg = self.config_lanzador.get("intervalo_conciliador_seg", 180)
        self.intervalo_sync_tablas_seg = self.config_lanzador.get("intervalo_sync_tablas_seg", 3600)

        # Configuración de pausa
        try:
            self.pausa_inicio_str = self.config_lanzador.get("pausa_lanzamiento_inicio_hhmm", "23:00")
            self.pausa_fin_str = self.config_lanzador.get("pausa_lanzamiento_fin_hhmm", "05:00")
            self.pausa_lanzamiento_inicio = dt_time.fromisoformat(self.pausa_inicio_str)
            self.pausa_lanzamiento_fin = dt_time.fromisoformat(self.pausa_fin_str)
            self.pausa_activa_actualmente = False 
            logger.info(f"Pausa de lanzamiento configurada de {self.pausa_lanzamiento_inicio.strftime('%H:%M')} a {self.pausa_lanzamiento_fin.strftime('%H:%M')}")
        except ValueError:
            logger.error(f"Formato de PAUSA_LANZAMIENTO_INICIO_HHMM ('{self.pausa_inicio_str}') o PAUSA_LANZAMIENTO_FIN_HHMM ('{self.pausa_fin_str}') inválido. La pausa no funcionará.")
            self.pausa_lanzamiento_inicio = None
            self.pausa_lanzamiento_fin = None
        
        self._lock = RLock() # Lock general para operaciones críticas si es necesario
        self._is_shutting_down = False # Flag para indicar cierre del servicio
        self.shutdown_event = threading.Event() # Evento para señalar al bucle principal que termine

        # --- Inicialización de Clientes ---
        sql_cfg = ConfigManager.get_sql_server_config()
        db_name_lanzador = sql_cfg.get("database_sam", sql_cfg.get("database"))
        if not db_name_lanzador:
            crit_msg = "Nombre de base de datos para SAM-Lanzador no encontrado en configuración."
            logger.critical(crit_msg)
            raise ValueError(crit_msg)

        self.db_connector = DatabaseConnector(
            servidor=sql_cfg["server"],
            base_datos=db_name_lanzador,
            usuario=sql_cfg["uid"],
            contrasena=sql_cfg["pwd"],
            timeout_conexion=sql_cfg.get("timeout_conexion_inicial", 30)
        )

        aa_cfg = ConfigManager.get_aa_config()
        self.aa_client = AutomationAnywhereClient( 
            control_room_url=aa_cfg["url"],
            username=aa_cfg["user"],
            password=aa_cfg["pwd"],
            api_key=aa_cfg.get("apiKey"),
            callback_url_for_deploy=aa_cfg.get("url_callback"),
            api_timeout_seconds=self.config_lanzador.get("api_timeout_seconds", 60),
            token_refresh_buffer_sec=self.config_lanzador.get("token_ttl_refresh_buffer_sec", 1140),
            default_page_size=self.config_lanzador.get("api_default_page_size", 100),
            max_pagination_pages=self.config_lanzador.get("api_max_pagination_pages", 1000),
            logger_instance=logger
        )

        self.notificador = EmailAlertClient()
        self.conciliador = ConciliadorImplementaciones(self.db_connector, self.aa_client)

        atexit.register(self.cleanup_on_exit)
        self.configurar_tareas_programadas() # Configurar los schedules aquí
        logger.info("LanzadorRobots inicializado y tareas programadas con 'schedule'.")

    def configurar_tareas_programadas(self):
        """Configura todas las tareas periódicas usando la biblioteca schedule."""
        logger.info("Configurando tareas programadas con 'schedule'...")
        
        lanzador_interval = max(1, self.intervalo_lanzador_seg)
        schedule.every(lanzador_interval).seconds.do(self.ejecutar_ciclo_lanzamiento).tag('lanzamiento_robots')
        logger.info(f"Ciclo de lanzamiento programado para ejecutarse cada {lanzador_interval} segundos.")

        conciliador_interval = max(1, self.intervalo_conciliador_seg)
        schedule.every(conciliador_interval).seconds.do(self.ejecutar_ciclo_conciliacion).tag('conciliacion_bots')
        logger.info(f"Ciclo de conciliación programado para ejecutarse cada {conciliador_interval} segundos.")

        sync_interval = max(1, self.intervalo_sync_tablas_seg)
        schedule.every(sync_interval).seconds.do(self.ejecutar_ciclo_sincronizacion_tablas).tag('sincronizacion_tablas')
        logger.info(f"Ciclo de sincronización de tablas programado para ejecutarse cada {sync_interval} segundos.")

    def _esta_en_periodo_de_pausa(self) -> bool:
        if not self.pausa_lanzamiento_inicio or not self.pausa_lanzamiento_fin:
            return False 
        hora_actual = datetime.now().time()
        if self.pausa_lanzamiento_inicio <= self.pausa_lanzamiento_fin:
            return self.pausa_lanzamiento_inicio <= hora_actual < self.pausa_lanzamiento_fin
        else: 
            return hora_actual >= self.pausa_lanzamiento_inicio or hora_actual < self.pausa_lanzamiento_fin

    def _lanzar_robot_individualmente_y_registrar(self, robot_info_tupla: tuple, bot_input_plantilla: Optional[dict]) -> Dict[str, Any]:
        """Intenta lanzar un solo robot y registrar su ejecución. Devuelve un diccionario con el estado."""
        db_robot_id, db_equipo_id, a360_user_id, hora_programada_obj = robot_info_tupla
        robot_data_log = f"RobotID(SAM):{db_robot_id}, EquipoID(SAM):{db_equipo_id}, UserID(A360):{a360_user_id}"
        
        if self._is_shutting_down: # Chequeo al inicio de la tarea del worker
            logger.info(f"Lanzamiento para {robot_data_log} abortado (cierre solicitado).")
            return {"status": "skipped_shutdown", "error": "Servicio en cierre", "robot_info_original": robot_info_tupla}

        logger.debug(f"Procesando lanzamiento para: {robot_data_log}")
        if not all([db_robot_id is not None, db_equipo_id is not None, a360_user_id is not None]):
            msg = f"Datos insuficientes (RobotId, EquipoId o UserId faltantes), se omite: {robot_data_log}"
            logger.error(msg)
            return {"status": "failed_data", "error": msg, "robot_info_original": robot_info_tupla}

        resultado_despliegue = self.aa_client.desplegar_bot(
            file_id=db_robot_id, run_as_user_ids=[a360_user_id], bot_input=bot_input_plantilla
        )

        a360_deployment_id = resultado_despliegue.get("deploymentId")
        error_api = resultado_despliegue.get("error")
        es_reintentable_api = resultado_despliegue.get("is_retriable", False)

        if a360_deployment_id:
            try:
                self.db_connector.insertar_registro_ejecucion(
                    a360_deployment_id, db_robot_id, db_equipo_id, a360_user_id,
                    hora_programada_obj, "RUNNING" # O "PENDING_EXECUTION"
                )
                return {"status": "success", "deploymentId": a360_deployment_id, "robot_info_original": robot_info_tupla}
            except Exception as e_db:
                logger.error(f"Robot desplegado (DeploymentID: {a360_deployment_id}) pero falló el registro en BD para {robot_data_log}: {e_db}", exc_info=True)
                return {"status": "failed_db_insert", "deploymentId": a360_deployment_id, "error": str(e_db), "robot_info_original": robot_info_tupla}
        else:
            if es_reintentable_api:
                logger.warning(f"Fallo REINTENTABLE en API al desplegar {robot_data_log}. Error: {error_api}")
                return {"status": "retriable_error", "error": error_api, "robot_info_original": robot_info_tupla}
            else:
                logger.error(f"Fallo PERMANENTE en API al desplegar {robot_data_log}. Error: {error_api}")
                return {"status": "failed_api_permanent", "error": error_api, "robot_info_original": robot_info_tupla}

    def ejecutar_ciclo_lanzamiento(self):
        if self._is_shutting_down:
            logger.info("LanzadorRobots: Ciclo de lanzamiento abortado (cierre general).")
            return

        if self._esta_en_periodo_de_pausa():
            if not self.pausa_activa_actualmente:
                logger.info(f"LanzadorRobots: En período de pausa de lanzamiento ({self.pausa_lanzamiento_inicio.strftime('%H:%M')} - {self.pausa_lanzamiento_fin.strftime('%H:%M')}). No se lanzarán robots.")
                self.pausa_activa_actualmente = True
            else:
                logger.debug(f"LanzadorRobots: Ciclo de lanzamiento omitido debido a pausa programada.")
            return

        if self.pausa_activa_actualmente:
            logger.info("LanzadorRobots: Finalizado período de pausa de lanzamiento. Reanudando operaciones.")
            self.pausa_activa_actualmente = False
            
        logger.info("LanzadorRobots: Iniciando ciclo de lanzamiento de robots (concurrente)...")
        
        robots_para_lanzar_inicialmente_tuplas = []
        try:
            lista_robots_data_dict = self.db_connector.obtener_robots_ejecutables()
            if lista_robots_data_dict:
                robots_para_lanzar_inicialmente_tuplas = [
                    (r.get("RobotId"), r.get("EquipoId"), r.get("UserId"), r.get("Hora"))
                    for r in lista_robots_data_dict
                ]
                logger.info(f"LanzadorRobots: {len(robots_para_lanzar_inicialmente_tuplas)} robots obtenidos para posible ejecución.")
            else:
                logger.info("LanzadorRobots: No hay robots para ejecutar en este ciclo (según SP).")
                return
        except Exception as e_db_get:
            logger.error(f"LanzadorRobots: Error al obtener robots ejecutables de la BD: {e_db_get}", exc_info=True)
            return

        bot_input_plantilla = {"in_NumRepeticion": {"type": "NUMBER", "number": self.config_lanzador.get("vueltas", 5)}}
        robots_fallidos_para_notificar = []
        robots_para_reintentar_lista = []
        max_workers = self.config_lanzador.get("max_lanzamientos_concurrentes", 5)

        if robots_para_lanzar_inicialmente_tuplas and not self._is_shutting_down:
            logger.info(f"LanzadorRobots: Iniciando primer intento de lanzamiento para {len(robots_para_lanzar_inicialmente_tuplas)} robots usando {max_workers} hilos.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                mapa_futuro_a_robot = {
                    executor.submit(self._lanzar_robot_individualmente_y_registrar, robot_info, bot_input_plantilla): robot_info
                    for robot_info in robots_para_lanzar_inicialmente_tuplas
                }
                for futuro in concurrent.futures.as_completed(mapa_futuro_a_robot):
                    if self._is_shutting_down: break
                    robot_info_original = mapa_futuro_a_robot[futuro]
                    db_robot_id, db_equipo_id, a360_user_id, _ = robot_info_original
                    try:
                        resultado = futuro.result()
                        if resultado["status"] == "success":
                            logger.info(f"Lanzamiento concurrente exitoso para RobotID(SAM):{db_robot_id}, DeploymentID:{resultado.get('deploymentId')}")
                        elif resultado["status"] == "retriable_error":
                            robots_para_reintentar_lista.append(robot_info_original)
                        elif resultado["status"] in ["failed_api_permanent", "failed_db_insert", "failed_data"]:
                            robots_fallidos_para_notificar.append({"robot_id": db_robot_id, "equipo_id": db_equipo_id, "user_id": a360_user_id, "error": resultado.get("error", "Error desconocido")})
                    except Exception as exc_futuro:
                        logger.error(f"LanzadorRobots: Excepción al procesar futuro para RobotID(SAM):{db_robot_id}: {exc_futuro}", exc_info=True)
                        robots_fallidos_para_notificar.append({"robot_id": db_robot_id, "equipo_id": db_equipo_id, "user_id": a360_user_id, "error": f"Excepción en ThreadPool: {exc_futuro}"})
            logger.info("LanzadorRobots: Finalizado primer intento de lanzamientos concurrentes.")

        if not self._is_shutting_down and robots_para_reintentar_lista:
            delay_reintento = self.config_lanzador.get("reintento_lanzamiento_delay_seg", 10)
            logger.info(f"LanzadorRobots: {len(robots_para_reintentar_lista)} robots para reintentar. Esperando {delay_reintento} segundos...")
            if self.shutdown_event.wait(timeout=delay_reintento): # Espera interrumpible
                 logger.info("Cierre solicitado durante espera para reintentos. No se realizarán.")
            elif not self._is_shutting_down: # Re-chequear después del wait
                logger.info(f"LanzadorRobots: Iniciando SEGUNDO intento para {len(robots_para_reintentar_lista)} robots.")
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor_reintento:
                    mapa_futuro_reintento_a_robot = {
                        executor_reintento.submit(self._lanzar_robot_individualmente_y_registrar, robot_info, bot_input_plantilla): robot_info
                        for robot_info in robots_para_reintentar_lista
                    }
                    for futuro_reintento in concurrent.futures.as_completed(mapa_futuro_reintento_a_robot):
                        if self._is_shutting_down: break
                        robot_info_original_re = mapa_futuro_reintento_a_robot[futuro_reintento]
                        db_robot_id_re, db_equipo_id_re, a360_user_id_re, _ = robot_info_original_re
                        try:
                            resultado_re = futuro_reintento.result()
                            if resultado_re["status"] == "success":
                                logger.info(f"Reintento de lanzamiento concurrente exitoso para RobotID(SAM):{db_robot_id_re}, DeploymentID:{resultado_re.get('deploymentId')}")
                            else:
                                logger.error(f"Fallo en SEGUNDO intento para RobotID(SAM):{db_robot_id_re}. Error: {resultado_re.get('error')}")
                                robots_fallidos_para_notificar.append({"robot_id": db_robot_id_re, "equipo_id": db_equipo_id_re, "user_id": a360_user_id_re, "error": f"Fallo tras reintento: {resultado_re.get('error')}"})
                        except Exception as exc_futuro_re:
                            logger.error(f"LanzadorRobots: Excepción al procesar futuro de REINTENTO para RobotID(SAM):{db_robot_id_re}: {exc_futuro_re}", exc_info=True)
                            robots_fallidos_para_notificar.append({"robot_id": db_robot_id_re, "equipo_id": db_equipo_id_re, "user_id": a360_user_id_re, "error": f"Excepción en ThreadPool (Reintento): {exc_futuro_re}"})
                logger.info("LanzadorRobots: Finalizado segundo intento de lanzamientos (reintentos).")

        if robots_fallidos_para_notificar:
            self.notificar_robots_fallidos(robots_fallidos_para_notificar)
        logger.info("LanzadorRobots: Ciclo de lanzamiento (concurrente) completado.")

    def ejecutar_ciclo_conciliacion(self):
        if self._is_shutting_down:
            logger.info("LanzadorRobots: Ciclo de conciliación abortado (cierre solicitado).")
            return
        logger.info("LanzadorRobots: Iniciando ciclo de conciliación de implementaciones...")
        try:
            self.conciliador.conciliar_implementaciones()
        except Exception as e:
            logger.error(f"LanzadorRobots: Error en ciclo de conciliación: {e}", exc_info=True)
        logger.info("LanzadorRobots: Ciclo de conciliación completado.")

    def ejecutar_ciclo_sincronizacion_tablas(self):
        if self._is_shutting_down:
            logger.info("LanzadorRobots: Ciclo de sincronización de tablas abortado (cierre solicitado).")
            return
        logger.info("LanzadorRobots: Iniciando ciclo de sincronización de tablas maestras (Equipos, Robots)...")
        try:
            logger.info("Sincronizando tabla Equipos...")
            lista_devices_api = self.aa_client.obtener_devices(status_filtro="CONNECTED")
            equipos_procesados_para_merge = []
            if lista_devices_api:
                user_ids_de_devices = [dev.get("UserId") for dev in lista_devices_api if dev.get("UserId") is not None]
                mapa_usuarios_detalle = {}
                if user_ids_de_devices:
                    lista_usuarios_detalle_api = self.aa_client.obtener_usuarios_detallados(user_ids=list(set(user_ids_de_devices)))
                    mapa_usuarios_detalle = {usr.get("UserId"): usr for usr in lista_usuarios_detalle_api if usr.get("UserId") is not None}
                for device in lista_devices_api:
                    a360_user_id_en_device = device.get("UserId")
                    usuario_detalle = mapa_usuarios_detalle.get(a360_user_id_en_device) if a360_user_id_en_device else None
                    licencia_final = "NO_ASIGNADO_O_SIN_LICENCIA"; activo_calculado = True
                    if usuario_detalle:
                        licencia_final = usuario_detalle.get("Licencia", licencia_final)
                        if not usuario_detalle.get("Activo_Usuario_A360", True): activo_calculado = False
                    elif a360_user_id_en_device is not None:
                        logger.warning(f"Sincro Equipos: No se encontraron detalles para Usuario A360 ID {a360_user_id_en_device} asignado al DeviceId {device.get('EquipoId')}")
                        activo_calculado = False 
                    else: activo_calculado = False 
                    if device.get("Status_A360") != "CONNECTED": activo_calculado = False
                    equipos_procesados_para_merge.append({
                        "EquipoId": device.get("EquipoId"), "Equipo": device.get("Equipo"),
                        "UserId": a360_user_id_en_device, "UserName": device.get("UserName"),
                        "Licencia": licencia_final, "Activo_SAM": activo_calculado })
            if equipos_procesados_para_merge: self.db_connector.merge_equipos(equipos_procesados_para_merge)
            else: logger.info("Sincro Equipos: No se obtuvieron devices o usuarios válidos de la API para fusionar.")

            logger.info("Sincronizando tabla Robots...")
            lista_robots_api_filtrada = self.aa_client.obtener_robots(filtro_path_base="RPA", filtro_nombre_prefijo="P")
            if lista_robots_api_filtrada:
                robots_para_merge = [{"RobotId": bot.get("RobotId"), "Robot": bot.get("Robot"), "Descripcion": bot.get("Descripcion")} for bot in lista_robots_api_filtrada]
                self.db_connector.merge_robots(robots_para_merge)
            else: logger.info("Sincro Robots: No se obtuvieron robots (o ninguno pasó los filtros) de la API para fusionar.")
        except Exception as e:
            logger.error(f"LanzadorRobots: Error durante el ciclo de sincronización de tablas: {e}", exc_info=True)
            try:
                self.notificador.send_alert("Error CRÍTICO en Sincronización de Tablas SAM", f"Error: {e}\n\nTraceback:\n{traceback.format_exc()}", is_critical=True)
            except Exception as email_ex: logger.error(f"LanzadorRobots: Fallo también al enviar email de notificación de error de sincronización: {email_ex}")
        logger.info("LanzadorRobots: Ciclo de sincronización de tablas maestras completado.")

    def notificar_robots_fallidos(self, robots_fallidos_con_detalle: list):
        if robots_fallidos_con_detalle:
            logger.info(f"LanzadorRobots: Generando notificación para {len(robots_fallidos_con_detalle)} robots con fallos.")
            mensaje = self.db_connector.generar_mensaje_notificacion(robots_fallidos_con_detalle)
            self.notificador.send_alert(subject="Lanzador SAM: Robots con Fallo en Despliegue o Registro", message=mensaje, is_critical=False)

    def detener_tareas_programadas(self):
        logger.info("LanzadorRobots: Limpiando todas las tareas programadas con 'schedule'...")
        schedule.clear() 

    def cleanup_on_exit(self):
        logger.info("LanzadorRobots: Realizando limpieza de recursos al salir (atexit)...")
        self.finalizar_servicio()

    def finalizar_servicio(self):
        logger.info("LanzadorRobots: Iniciando proceso de finalización del servicio...")
        with self._lock:
            if self._is_shutting_down:
                logger.info("LanzadorRobots: El servicio ya está en proceso de finalización.")
                return
            self._is_shutting_down = True
        
        self.shutdown_event.set() # Señalar al bucle principal de schedule que termine
        logger.info("LanzadorRobots: Evento de cierre (shutdown_event) activado.")
        
        self.detener_tareas_programadas()
        
        # Dar un pequeño margen para que los hilos del ThreadPoolExecutor (si están activos) puedan notar el cierre
        # Esto es una heurística, un manejo más robusto de ThreadPoolExecutor implicaría .shutdown(wait=True)
        # pero debe hacerse en el lugar correcto (donde se creó y usó).
        # Por ahora, el chequeo de _is_shutting_down dentro de _lanzar_robot_individualmente_y_registrar ayuda.
        time.sleep(2) # Pequeña espera

        if self.db_connector:
            self.db_connector.cerrar_conexion_hilo_actual() # Cierra la conexión del hilo principal
        logger.info("LanzadorRobots: Finalización de servicio completada.")

# --- Funciones de Nivel de Módulo para el Punto de Entrada ---
app_instance: Optional[LanzadorRobots] = None

def main_service_logic():
    global app_instance
    app_instance = LanzadorRobots()
    # configurar_tareas_programadas() ya se llama en __init__ de LanzadorRobots

    logger.info("LanzadorRobots: Ejecutando tareas iniciales una vez (si no está en cierre)...")
    if not app_instance.shutdown_event.is_set(): app_instance.ejecutar_ciclo_sincronizacion_tablas() 
    if not app_instance.shutdown_event.is_set(): app_instance.ejecutar_ciclo_conciliacion()
    if not app_instance.shutdown_event.is_set(): app_instance.ejecutar_ciclo_lanzamiento()

    logger.info("LanzadorRobots: Iniciando bucle principal de 'schedule'. El servicio está corriendo.")
    while not app_instance.shutdown_event.is_set():
        schedule.run_pending()
        app_instance.shutdown_event.wait(timeout=1) # Espera interrumpible de 1 segundo
    logger.info("LanzadorRobots: Bucle principal de 'schedule' terminado.")

def signal_handler_main(sig, frame):
    logger.warning(f"Señal de terminación {signal.Signals(sig).name} recibida. Cerrando LanzadorRobots...")
    if app_instance:
        app_instance.finalizar_servicio() # Esto setea _is_shutting_down y shutdown_event

def main_for_run_script():
    signal.signal(signal.SIGINT, signal_handler_main)
    signal.signal(signal.SIGTERM, signal_handler_main)
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler_main)

    try:
        main_service_logic()
    except Exception as e:
        logger.critical(f"Error fatal en la lógica principal del servicio Lanzador: {e}", exc_info=True)
        if app_instance: # Intentar limpiar si la instancia existe
            app_instance.finalizar_servicio()
    finally:
        logger.info("LanzadorRobots: Script principal (main_for_run_script) ha finalizado.")

if __name__ == "__main__":
    logger.info("Ejecutando service/main.py directamente para pruebas...")
    main_for_run_script()