# SAM/balanceador/service/balanceo.py

import math
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from balanceador.database.historico_client import HistoricoBalanceoClient
from balanceador.service.cooling_manager import CoolingManager

logger = logging.getLogger("SAM.Balanceador.Balanceo")

class Balanceo:
    """
    Implementación del algoritmo de balanceo con protección contra thrashing,
    sistema de prioridades y registro histórico.
    """
    
    def __init__(self, balanceador_instance):
        """
        Inicializa el módulo de balanceo.
        
        Args:
            balanceador_instance: Instancia del Balanceador principal
        """
        self.balanceador = balanceador_instance
        
        # Acceder a los conectores de base de datos
        if hasattr(balanceador_instance, 'db_sam'):
            self.db_sam = balanceador_instance.db_sam
        else:
            raise AttributeError("El balanceador no tiene el atributo 'db_sam'")
            
        if hasattr(balanceador_instance, 'db_rpa360'):
            self.db_rpa360 = balanceador_instance.db_rpa360
        else:
            raise AttributeError("El balanceador no tiene el atributo 'db_rpa360'")
            
        if hasattr(balanceador_instance, 'mysql_clouders'):
            self.mysql_clouders = balanceador_instance.mysql_clouders
        else:
            raise AttributeError("El balanceador no tiene el atributo 'mysql_clouders'")
        
        # Acceder a la configuración
        if hasattr(balanceador_instance, 'cfg_balanceador_specifics'):
            self.cfg_balanceador_specifics = balanceador_instance.cfg_balanceador_specifics
        else:
            raise AttributeError("El balanceador no tiene el atributo 'cfg_balanceador_specifics'")
        
        # Crear cliente para histórico de balanceo
        self.historico_client = HistoricoBalanceoClient(self.db_sam)
        
        # Crear gestor de enfriamiento
        cooling_period = self.cfg_balanceador_specifics.get("cooling_period_seg", 300)
        self.cooling_manager = CoolingManager(cooling_period_seconds=cooling_period)
        
        # Configuración de concurrencia
        self.max_workers = self.cfg_balanceador_specifics.get("max_workers_balanceo", 4)
        self._lock = threading.RLock()
    
    def ejecutar_balanceo(self):
        """
        Ejecuta el ciclo de balanceo con protección contra thrashing,
        sistema de prioridades y registro histórico.
        """
        # Verificar si el balanceador está en proceso de cierre
        if hasattr(self.balanceador, '_is_shutting_down') and self.balanceador._is_shutting_down:
            logger.info("SAM Balanceador: Ciclo abortado (cierre general).")
            return
        
        logger.info("SAM Balanceador: Iniciando ciclo de balanceo...")
        
        with self._lock:
            # Verificar nuevamente si está en cierre
            if hasattr(self.balanceador, '_is_shutting_down') and self.balanceador._is_shutting_down: 
                return
            
            try:
                # Paso A: Obtener pool dinámico disponible
                if hasattr(self.balanceador, '_obtener_pool_dinamico_disponible'):
                    pool_dinamico_disponible = self.balanceador._obtener_pool_dinamico_disponible()
                else:
                    logger.error("El método '_obtener_pool_dinamico_disponible' no existe en el balanceador")
                    return
                    
                logger.debug(f"Pool dinámico inicial: {len(pool_dinamico_disponible)} equipos.")
                
                # Paso B: Obtener carga de trabajo
                if hasattr(self.balanceador, '_obtener_carga_de_trabajo_consolidada'):
                    carga_trabajo_por_robot = self.balanceador._obtener_carga_de_trabajo_consolidada()
                else:
                    logger.error("El método '_obtener_carga_de_trabajo_consolidada' no existe en el balanceador")
                    return
                
                # Obtener configuración y asignaciones actuales de todos los robots activos y online
                query_robots_activos = """
                SELECT RobotId, Robot, MinEquipos, MaxEquipos, PrioridadBalanceo, 
                       TicketsPorEquipoAdicional 
                FROM dbo.Robots 
                WHERE Activo = 1
                  AND EsOnline = 1
                ORDER BY PrioridadBalanceo DESC, RobotId;
                """
                todos_los_robots_config_list = self.db_sam.ejecutar_consulta(query_robots_activos, es_select=True) or []
                
                mapa_config_robots = {r["RobotId"]: r for r in todos_los_robots_config_list}
                
                query_asignaciones = """
                SELECT RobotId, EquipoId, Reservado, EsProgramado 
                FROM dbo.Asignaciones;
                """
                mapa_asignaciones_por_robot: Dict[int, List[Dict[str, Any]]] = {}
                mapa_equipos_asignados_dinamicamente: Dict[int, List[int]] = {}  # RobotId -> [EquipoId]
                
                for asignacion in (self.db_sam.ejecutar_consulta(query_asignaciones, es_select=True) or []):
                    mapa_asignaciones_por_robot.setdefault(asignacion["RobotId"], []).append(asignacion)
                    # Considerar como dinámica si NO está reservada Y NO es programada
                    if not asignacion.get("Reservado") and not asignacion.get("EsProgramado"):
                        mapa_equipos_asignados_dinamicamente.setdefault(asignacion["RobotId"], []).append(asignacion["EquipoId"])
                
                # Consultar ejecuciones activas para evitar desasignar equipos en uso
                query_ejecuciones_activas = """
                SELECT RobotId, EquipoId
                FROM dbo.Ejecuciones
                WHERE Estado IN ('PENDING_EXECUTION', 'DEPLOYED', 'RUNNING', 'UPDATE', 'RUN_PAUSED', 'QUEUED');
                """
                equipos_en_uso: Dict[int, List[int]] = {}  # RobotId -> [EquipoId]
                
                for ejecucion in (self.db_sam.ejecutar_consulta(query_ejecuciones_activas, es_select=True) or []):
                    equipos_en_uso.setdefault(ejecucion["RobotId"], []).append(ejecucion["EquipoId"])
                
                # Paso C: Desasignar equipos dinámicos excedentes
                logger.info("SAM Balanceador: Fase de Desasignación...")
                
                for robot_id_sam, config_robot in mapa_config_robots.items():
                    if hasattr(self.balanceador, '_is_shutting_down') and self.balanceador._is_shutting_down: break
                    
                    tickets_robot = carga_trabajo_por_robot.get(robot_id_sam, 0)
                    
                    # Verificar si existe el método para calcular equipos necesarios
                    if hasattr(self.balanceador, '_calcular_equipos_necesarios_para_robot'):
                        equipos_necesarios_robot = self.balanceador._calcular_equipos_necesarios_para_robot(tickets_robot, config_robot)
                    else:
                        # Implementación local como fallback
                        logger.warning("Usando implementación local de _calcular_equipos_necesarios_para_robot")
                        min_equipos = config_robot.get("MinEquipos", 1)
                        max_equipos_cfg = config_robot.get("MaxEquipos", -1)
                        tickets_por_equipo_adic_cfg = config_robot.get("TicketsPorEquipoAdicional")
                        
                        if tickets_robot <= 0:
                            equipos_necesarios_robot = 0
                        else:
                            ratio_aplicable = tickets_por_equipo_adic_cfg if tickets_por_equipo_adic_cfg and tickets_por_equipo_adic_cfg > 0 \
                                else self.cfg_balanceador_specifics.get("default_tickets_por_equipo", 10)
                            if ratio_aplicable <= 0:
                                ratio_aplicable = 1  # Evitar división por cero
                            
                            import math
                            equipos_por_tickets = math.ceil(tickets_robot / ratio_aplicable)
                            equipos_necesarios_robot = max(min_equipos, int(equipos_por_tickets))
                            
                            if max_equipos_cfg != -1:
                                equipos_necesarios_robot = min(equipos_necesarios_robot, max_equipos_cfg)
                    
                    asignaciones_dinamicas_actuales_ids = mapa_equipos_asignados_dinamicamente.get(robot_id_sam, [])
                    num_dinamicas_actuales = len(asignaciones_dinamicas_actuales_ids)
                    
                    # Verificar si se puede desasignar (período de enfriamiento)
                    if num_dinamicas_actuales > equipos_necesarios_robot:
                        can_scale_down, justificacion = self.cooling_manager.can_scale_down(
                            robot_id_sam, tickets_robot, num_dinamicas_actuales
                        )
                        
                        if can_scale_down:
                            equipos_a_liberar_count = num_dinamicas_actuales - equipos_necesarios_robot
                            logger.info(f"RobotId {robot_id_sam}: Necesita liberar {equipos_a_liberar_count} equipos dinámicos " +
                                       f"(asignados: {num_dinamicas_actuales}, necesita: {equipos_necesarios_robot}). " +
                                       f"Justificación: {justificacion}")
                            
                            # Obtener equipos que no están en uso actualmente
                            equipos_en_uso_robot = equipos_en_uso.get(robot_id_sam, [])
                            
                            # Ordenar los equipos a liberar: primero los que no están en uso
                            ids_dinamicos_actuales = list(asignaciones_dinamicas_actuales_ids)
                            ids_dinamicos_no_en_uso = [eq_id for eq_id in ids_dinamicos_actuales if eq_id not in equipos_en_uso_robot]
                            ids_dinamicos_en_uso = [eq_id for eq_id in ids_dinamicos_actuales if eq_id in equipos_en_uso_robot]
                            
                            # Priorizar liberar equipos no en uso
                            ids_a_liberar = ids_dinamicos_no_en_uso[:equipos_a_liberar_count]
                            
                            # Si aún necesitamos liberar más, incluir equipos en uso (esto debería ser excepcional)
                            if len(ids_a_liberar) < equipos_a_liberar_count and ids_dinamicos_en_uso:
                                logger.warning(f"RobotId {robot_id_sam}: Se liberarán {equipos_a_liberar_count - len(ids_a_liberar)} " +
                                              f"equipos que están en uso actualmente.")
                                ids_a_liberar.extend(ids_dinamicos_en_uso[:equipos_a_liberar_count - len(ids_a_liberar)])
                            
                            equipos_liberados = 0
                            for equipo_id_a_liberar in ids_a_liberar:
                                try:
                                    query_delete = """
                                    DELETE FROM dbo.Asignaciones 
                                    WHERE RobotId = ? AND EquipoId = ? AND Reservado = 0 AND EsProgramado = 0;
                                    """
                                    self.db_sam.ejecutar_consulta(query_delete, (robot_id_sam, equipo_id_a_liberar), es_select=False)
                                    logger.info(f"RobotId {robot_id_sam}: Desasignado dinámicamente de EquipoId {equipo_id_a_liberar}.")
                                    
                                    # Actualizar el mapa de asignaciones dinámicas
                                    if robot_id_sam in mapa_equipos_asignados_dinamicamente and equipo_id_a_liberar in mapa_equipos_asignados_dinamicamente[robot_id_sam]:
                                        mapa_equipos_asignados_dinamicamente[robot_id_sam].remove(equipo_id_a_liberar)
                                    
                                    equipos_liberados += 1
                                except Exception as e_deassign:
                                    logger.error(f"RobotId {robot_id_sam}: Error al desasignar EquipoId {equipo_id_a_liberar}: {e_deassign}", exc_info=True)
                            
                            # Registrar la operación de desasignación
                            if equipos_liberados > 0:
                                self.cooling_manager.register_scale_down(robot_id_sam, tickets_robot, equipos_liberados)
                                self.historico_client.registrar_decision_balanceo(
                                    robot_id_sam,
                                    tickets_robot,
                                    num_dinamicas_actuales,
                                    num_dinamicas_actuales - equipos_liberados,
                                    "DESASIGNAR",
                                    justificacion
                                )
                        else:
                            logger.info(f"RobotId {robot_id_sam}: No se desasignarán equipos. {justificacion}")
                
                if self.balanceador._is_shutting_down: return
                
                # Paso D: Calcular necesidad neta y priorizar asignación
                logger.info("SAM Balanceador: Fase de Cálculo de Necesidad y Asignación...")
                
                # Recalcular equipos disponibles después de desasignaciones
                equipos_disponibles_ids = [eq["EquipoId"] for eq in pool_dinamico_disponible]
                for robot_asignaciones in mapa_equipos_asignados_dinamicamente.values():
                    for equipo_id in robot_asignaciones:
                        if equipo_id in equipos_disponibles_ids:
                            equipos_disponibles_ids.remove(equipo_id)
                
                # Calcular necesidades de equipos adicionales por robot
                necesidades_adicionales: List[Tuple[int, int, int, Dict[str, Any]]] = []  # [(robot_id, necesidad, prioridad, config)]
                
                for robot_id_sam, config_robot in mapa_config_robots.items():
                    if hasattr(self.balanceador, '_is_shutting_down') and self.balanceador._is_shutting_down: break
                    
                    tickets_robot = carga_trabajo_por_robot.get(robot_id_sam, 0)
                    if tickets_robot <= 0:
                        continue  # No hay tickets, no necesita equipos
                    
                    equipos_necesarios_robot = self.balanceador._calcular_equipos_necesarios_para_robot(tickets_robot, config_robot)
                    asignaciones_actuales_ids = mapa_equipos_asignados_dinamicamente.get(robot_id_sam, [])
                    num_asignaciones_actuales = len(asignaciones_actuales_ids)
                    
                    if num_asignaciones_actuales < equipos_necesarios_robot:
                        # Verificar si se puede asignar (período de enfriamiento)
                        can_scale_up, justificacion = self.cooling_manager.can_scale_up(
                            robot_id_sam, tickets_robot, num_asignaciones_actuales
                        )
                        
                        if can_scale_up:
                            necesidad_adicional = equipos_necesarios_robot - num_asignaciones_actuales
                            prioridad_robot = config_robot.get("PrioridadBalanceo", 0)
                            
                            # Añadir a la lista de necesidades
                            necesidades_adicionales.append((
                                robot_id_sam,
                                necesidad_adicional,
                                prioridad_robot,
                                config_robot
                            ))
                            
                            logger.info(f"RobotId {robot_id_sam}: Necesita {necesidad_adicional} equipos adicionales " +
                                       f"(tiene: {num_asignaciones_actuales}, necesita: {equipos_necesarios_robot}). " +
                                       f"Justificación: {justificacion}")
                        else:
                            logger.info(f"RobotId {robot_id_sam}: No se asignarán equipos adicionales. {justificacion}")
                
                # Ordenar por prioridad y necesidad
                necesidades_adicionales.sort(key=lambda x: (x[2], x[1]), reverse=True)
                
                # Asignar equipos según disponibilidad y prioridad
                for robot_id, necesidad, _, config_robot in necesidades_adicionales:
                    if self.balanceador._is_shutting_down: break
                    if not equipos_disponibles_ids:
                        logger.warning("No hay más equipos disponibles para asignar.")
                        break
                    
                    tickets_robot = carga_trabajo_por_robot.get(robot_id, 0)
                    asignaciones_actuales_ids = mapa_equipos_asignados_dinamicamente.get(robot_id, [])
                    num_asignaciones_antes = len(asignaciones_actuales_ids)
                    
                    # Determinar cuántos equipos asignar (limitado por disponibilidad)
                    equipos_a_asignar_count = min(necesidad, len(equipos_disponibles_ids))
                    
                    if equipos_a_asignar_count > 0:
                        logger.info(f"RobotId {robot_id}: Asignando {equipos_a_asignar_count} equipos dinámicos " +
                                   f"(de {necesidad} necesarios).")
                        
                        equipos_asignados = 0
                        for _ in range(equipos_a_asignar_count):
                            if not equipos_disponibles_ids:
                                break
                            
                            equipo_id_a_asignar = equipos_disponibles_ids.pop(0)
                            
                            try:
                                query_insert = """
                                INSERT INTO dbo.Asignaciones 
                                (RobotId, EquipoId, EsProgramado, Reservado, AsignadoPor)
                                VALUES (?, ?, 0, 0, 'Balanceador');
                                """
                                self.db_sam.ejecutar_consulta(query_insert, (robot_id, equipo_id_a_asignar), es_select=False)
                                logger.info(f"RobotId {robot_id}: Asignado dinámicamente a EquipoId {equipo_id_a_asignar}.")
                                
                                # Actualizar el mapa de asignaciones dinámicas
                                mapa_equipos_asignados_dinamicamente.setdefault(robot_id, []).append(equipo_id_a_asignar)
                                
                                equipos_asignados += 1
                            except Exception as e_assign:
                                logger.error(f"RobotId {robot_id}: Error al asignar EquipoId {equipo_id_a_asignar}: {e_assign}", exc_info=True)
                                # Devolver el equipo al pool si falló la asignación
                                equipos_disponibles_ids.append(equipo_id_a_asignar)
                        
                        # Registrar la operación de asignación
                        if equipos_asignados > 0:
                            self.cooling_manager.register_scale_up(robot_id, tickets_robot, equipos_asignados)
                            self.historico_client.registrar_decision_balanceo(
                                robot_id,
                                tickets_robot,
                                num_asignaciones_antes,
                                num_asignaciones_antes + equipos_asignados,
                                "ASIGNAR",
                                f"Tickets pendientes: {tickets_robot}, Prioridad: {config_robot.get('PrioridadBalanceo', 0)}"
                            )
                
                logger.info("SAM Balanceador: Ciclo de balanceo completado exitosamente.")
            
            except Exception as e:
                logger.error(f"Error en ciclo de balanceo: {e}", exc_info=True)
                try:
                    # Usar el método correcto send_alert en lugar de enviar_alerta_error
                    if hasattr(self.balanceador.notificador, 'send_alert'):
                        self.balanceador.notificador.send_alert(
                            subject="Error crítico en ciclo de balanceo SAM",
                            message=f"Se ha producido un error crítico en el ciclo de balanceo: {e}",
                            is_critical=True
                        )
                    else:
                        logger.error("No se pudo enviar alerta: el método 'send_alert' no existe en el notificador")
                except Exception as email_ex:
                    logger.error(f"Fallo también al enviar email de notificación de error crítico del Balanceador: {email_ex}")
