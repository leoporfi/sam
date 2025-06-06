# SAM/balanceador/service/balanceo.py

import logging
import threading
from typing import Dict, List, Any, Tuple, Set

from balanceador.database.historico_client import HistoricoBalanceoClient
from balanceador.service.cooling_manager import CoolingManager

logger = logging.getLogger(__name__)

class Balanceo:
    def __init__(self, balanceador_instance):
        self.balanceador = balanceador_instance
        for attr_name in ['db_sam', 'db_rpa360', 'mysql_clouders', 'cfg_balanceador_specifics', 'notificador']:
            if hasattr(balanceador_instance, attr_name):
                setattr(self, attr_name, getattr(balanceador_instance, attr_name))
            else:
                raise AttributeError(f"La instancia del Balanceador no tiene el atributo '{attr_name}'")
        
        self.historico_client = HistoricoBalanceoClient(self.db_sam)
        cooling_period = self.cfg_balanceador_specifics.get("cooling_period_seg", 300)
        self.cooling_manager = CoolingManager(cooling_period_seconds=cooling_period)
        self._lock = threading.RLock()

    def _realizar_asignacion_db(self, robot_id: int, equipo_id: int, motivo: str = "Balanceador") -> bool:
        try:
            query_insert = """
            INSERT INTO dbo.Asignaciones 
            (RobotId, EquipoId, EsProgramado, Reservado, AsignadoPor, FechaAsignacion)
            VALUES (?, ?, 0, 0, ?, GETDATE());
            """
            self.db_sam.ejecutar_consulta(query_insert, (robot_id, equipo_id, motivo[:50]), es_select=False)
            logger.info(f"RobotId {robot_id}: Asignado dinámicamente a EquipoId {equipo_id} (Motivo: {motivo}).")
            return True
        except Exception as e_assign:
            logger.error(f"RobotId {robot_id}: Error al asignar EquipoId {equipo_id}: {e_assign}", exc_info=True)
            return False

    def _realizar_desasignacion_db(self, robot_id: int, equipo_id: int) -> bool:
        logger.debug(f"_realizar_desasignacion_db: Intentando DELETE para RobotId {robot_id}, EquipoId {equipo_id}")
        try:
            query_delete = """
            DELETE FROM dbo.Asignaciones 
            WHERE RobotId = ? AND EquipoId = ? AND Reservado = 0 AND EsProgramado = 0;
            """
            rowcount = self.db_sam.ejecutar_consulta(query_delete, (robot_id, equipo_id), es_select=False) 
            
            if rowcount is not None and rowcount > 0:
                logger.info(f"_realizar_desasignacion_db: ÉXITO. RobotId {robot_id}, EquipoId {equipo_id} desasignado...")
                return True
            elif rowcount == 0: # No se borró nada
                logger.warning(f"_realizar_desasignacion_db: NINGUNA FILA BORRADA. RobotId {robot_id}, EquipoId {equipo_id}...")
                return False # Importante: si esperábamos borrar y no se borró, es un fallo de la operación.
            else: # Fallo o ambiguo
                logger.error(f"_realizar_desasignacion_db: FALLO O AMBIGUO. Rowcount: {rowcount}...")
                return False
        except Exception as e_deassign: 
            logger.error(f"_realizar_desasignacion_db: EXCEPCIÓN ...: {e_deassign}", exc_info=True)
            return False


    def _realizar_desasignacion_db_old(self, robot_id: int, equipo_id: int) -> bool:
        try:
            query_delete = """
            DELETE FROM dbo.Asignaciones 
            WHERE RobotId = ? AND EquipoId = ? AND Reservado = 0 AND EsProgramado = 0;
            """
            self.db_sam.ejecutar_consulta(query_delete, (robot_id, equipo_id), es_select=False)
            logger.info(f"RobotId {robot_id}: Desasignado dinámicamente de EquipoId {equipo_id}.")
            return True
        except Exception as e_deassign:
            logger.error(f"RobotId {robot_id}: Error al desasignar EquipoId {equipo_id}: {e_deassign}", exc_info=True)
            return False

    def _get_min_requerido_funcional(self, config_robot: Dict[str, Any], tickets_robot: int) -> int:
        min_equipos_db = config_robot.get("MinEquipos", 1)
        return max(1, min_equipos_db) if tickets_robot > 0 else min_equipos_db

    def _validar_y_limpiar_asignaciones_por_validez_maquina(self,
                                                          mapa_equipos_asignados_dinamicamente: Dict[int, List[int]], # IN-OUT
                                                          pool_dinamico_maquinas_validas_ids: Set[int],
                                                          carga_trabajo_por_robot: Dict[int, int],
                                                          equipos_en_uso_por_robot: Dict[int, Set[int]]):
        logger.info("Balanceo - Pre-Fase: Validando Asignaciones Dinámicas Existentes por Validez de Máquina...")
        robots_con_asignaciones_a_validar = list(mapa_equipos_asignados_dinamicamente.keys())

        for robot_id in robots_con_asignaciones_a_validar:
            if self.balanceador._is_shutting_down: break
            
            equipos_originalmente_asignados = list(mapa_equipos_asignados_dinamicamente.get(robot_id, []))
            if not equipos_originalmente_asignados:
                continue

            equipos_validados_a_mantener = []
            maquinas_invalidas_desasignadas_count = 0
            
            for equipo_id in equipos_originalmente_asignados:
                if equipo_id in pool_dinamico_maquinas_validas_ids:
                    equipos_validados_a_mantener.append(equipo_id)
                else:
                    # Máquina ya no es válida (ej. licencia cambió), intentar desasignar
                    logger.warning(f"Pre-Fase: EquipoId {equipo_id} (asignado a RobotId {robot_id}) ya no es válido para el pool dinámico. Intentando desasignar.")
                    
                    num_actual_din_robot = len(mapa_equipos_asignados_dinamicamente.get(robot_id, [])) # El número antes de esta posible desasignación
                    tickets_robot = carga_trabajo_por_robot.get(robot_id, 0)
                    can_sd, just_sd = self.cooling_manager.puede_reducirse(robot_id, tickets_robot, num_actual_din_robot)

                    if can_sd:
                        if self._realizar_desasignacion_db(robot_id, equipo_id):
                            # No modificar 'mapa_equipos_asignados_dinamicamente[robot_id]' directamente aquí
                            # porque estamos reconstruyendo la lista en 'equipos_validados_a_mantener'.
                            maquinas_invalidas_desasignadas_count += 1
                        else:
                            logger.error(f"Pre-Fase: Fallo al desasignar EquipoId {equipo_id} (máquina inválida) de RobotId {robot_id}. Se mantendrá asignado temporalmente.")
                            equipos_validados_a_mantener.append(equipo_id) # Mantener si falla desasignación
                    else:
                        logger.info(f"Pre-Fase: Desasignación de EquipoId {equipo_id} (máquina inválida) de R{robot_id} en espera por CoolingManager. Just: {just_sd}. Se mantendrá asignado.")
                        equipos_validados_a_mantener.append(equipo_id) # Mantener si cooling no permite
            
            # Actualizar el mapa principal con la lista filtrada/validada de equipos
            if len(equipos_validados_a_mantener) < len(equipos_originalmente_asignados): # Si hubo cambios
                if equipos_validados_a_mantener:
                    mapa_equipos_asignados_dinamicamente[robot_id] = equipos_validados_a_mantener
                elif robot_id in mapa_equipos_asignados_dinamicamente: # Si la lista quedó vacía
                    del mapa_equipos_asignados_dinamicamente[robot_id]
            
            if maquinas_invalidas_desasignadas_count > 0:
                self.cooling_manager.registrar_reduccion(robot_id, carga_trabajo_por_robot.get(robot_id,0), maquinas_invalidas_desasignadas_count)
                self.historico_client.registrar_decision_balanceo(
                    robot_id, carga_trabajo_por_robot.get(robot_id,0),
                    len(equipos_originalmente_asignados), # Antes de esta limpieza de máquinas inválidas
                    len(equipos_validados_a_mantener),    # Después de esta limpieza
                    "DESASIGNAR_MAQUINA_INVALIDA",
                    f"Liberados {maquinas_invalidas_desasignadas_count} por no cumplir criterios de pool."
                )
        logger.info("Balanceo - Pre-Fase: Validación de Asignaciones Existentes por Validez de Máquina completada.")


    def _limpiar_asignaciones_robots_no_candidatos(self,
                                                 mapa_equipos_asignados_dinamicamente: Dict[int, List[int]], # IN-OUT
                                                 carga_trabajo_por_robot: Dict[int, int],
                                                 equipos_en_uso_por_robot: Dict[int, Set[int]]):
        logger.info("Balanceo - Fase 0: Limpieza de Asignaciones a Robots Inactivos/Offline...")
        
        robot_ids_con_asignaciones_dinamicas = list(mapa_equipos_asignados_dinamicamente.keys())
        if not robot_ids_con_asignaciones_dinamicas:
            logger.info("Fase 0: No hay robots con asignaciones dinámicas preexistentes para limpiar.")
            return

        placeholders = ','.join(['?'] * len(robot_ids_con_asignaciones_dinamicas))
        query_estado_robots = f"SELECT RobotId, Activo, EsOnline FROM dbo.Robots WHERE RobotId IN ({placeholders});"
        try:
            estado_actual_robots_list = self.db_sam.ejecutar_consulta(query_estado_robots, tuple(robot_ids_con_asignaciones_dinamicas), es_select=True) or []
        except Exception as e:
            logger.error(f"Fase 0: Error al obtener estado actual de robots con asignaciones: {e}", exc_info=True)
            return

        mapa_estado_robots_db: Dict[int, Dict[str, Any]] = {r["RobotId"]: r for r in estado_actual_robots_list}
        
        ids_a_remover_del_mapa_principal = []

        for robot_id in robot_ids_con_asignaciones_dinamicas:
            if self.balanceador._is_shutting_down: break

            estado_robot = mapa_estado_robots_db.get(robot_id)
            es_candidato_actual_para_balanceo = False
            if estado_robot:
                es_candidato_actual_para_balanceo = bool(estado_robot.get("Activo")) and bool(estado_robot.get("EsOnline"))
            else:
                logger.warning(f"Fase 0: RobotId {robot_id} tiene asignaciones pero no se encontró en dbo.Robots. Se considera no candidato.")
            
            if not es_candidato_actual_para_balanceo:
                equipos_asignados_al_robot_no_candidato = list(mapa_equipos_asignados_dinamicamente.get(robot_id, []))
                if not equipos_asignados_al_robot_no_candidato:
                    continue

                logger.info(f"Fase 0: RobotId {robot_id} ya no es candidato (Activo/EsOnline={estado_robot}). Liberando sus {len(equipos_asignados_al_robot_no_candidato)} equipos dinámicos.")
                
                num_actual_din_no_candidato = len(equipos_asignados_al_robot_no_candidato)
                tickets_log_no_candidato = carga_trabajo_por_robot.get(robot_id, 0)
                can_sd, just_sd = self.cooling_manager.puede_reducirse(robot_id, tickets_log_no_candidato, num_actual_din_no_candidato)

                if can_sd:
                    equipos_en_uso_r = equipos_en_uso_por_robot.get(robot_id, set())
                    a_liberar_no_en_uso = [eq_id for eq_id in equipos_asignados_al_robot_no_candidato if eq_id not in equipos_en_uso_r]
                    a_liberar_en_uso = [eq_id for eq_id in equipos_asignados_al_robot_no_candidato if eq_id in equipos_en_uso_r]
                    equipos_a_intentar_liberar = a_liberar_no_en_uso + a_liberar_en_uso
                    
                    liberados_count = 0
                    for equipo_id_liberar in equipos_a_intentar_liberar:
                        if self._realizar_desasignacion_db(robot_id, equipo_id_liberar):
                            if robot_id in mapa_equipos_asignados_dinamicamente and equipo_id_liberar in mapa_equipos_asignados_dinamicamente[robot_id]:
                                mapa_equipos_asignados_dinamicamente[robot_id].remove(equipo_id_liberar)
                            liberados_count += 1
                    
                    if liberados_count > 0:
                        self.cooling_manager.registrar_reduccion(robot_id, tickets_log_no_candidato, liberados_count)
                        self.historico_client.registrar_decision_balanceo(
                            robot_id, tickets_log_no_candidato, 
                            num_actual_din_no_candidato, 
                            num_actual_din_no_candidato - liberados_count,
                            "DESASIGNAR_INACTIVO_OFFLINE", 
                            f"Robot no Act/On. Liberados:{liberados_count}. JustCool:{just_sd}"
                        )
                    if liberados_count < len(equipos_asignados_al_robot_no_candidato): # Si no se pudieron liberar todos
                        logger.warning(f"Fase 0: No se pudieron liberar todos los equipos de RobotId {robot_id} (no candidato). Quedan {len(mapa_equipos_asignados_dinamicamente.get(robot_id,[]))}")
                else:
                    logger.info(f"Fase 0: Desasignación de RobotId {robot_id} (no candidato) en espera por CoolingManager. Just: {just_sd}")
            
            if robot_id in mapa_equipos_asignados_dinamicamente and not mapa_equipos_asignados_dinamicamente[robot_id]:
                ids_a_remover_del_mapa_principal.append(robot_id)
        
        for robot_id_remove in ids_a_remover_del_mapa_principal:
            del mapa_equipos_asignados_dinamicamente[robot_id_remove]
        logger.info("Balanceo - Fase 0: Limpieza de Asignaciones por Robot Inactivo/Offline completada.")


    def ejecutar_balanceo(self):
        if hasattr(self.balanceador, '_is_shutting_down') and self.balanceador._is_shutting_down:
            logger.info("SAM Balanceador (Balanceo): Ciclo abortado (cierre general).")
            return
        
        logger.info("SAM Balanceador (Balanceo): Iniciando ciclo de balanceo...")
        
        with self._lock:
            if hasattr(self.balanceador, '_is_shutting_down') and self.balanceador._is_shutting_down: 
                return
            
            try:
                # --- PASO A: OBTENER ESTADO ACTUAL ---
                pool_dinamico_completo_obj_list = self.balanceador._obtener_pool_dinamico_disponible()
                # Set de IDs de máquinas que SÍ cumplen los criterios (licencia, activo SAM, permite balanceo) en ESTE ciclo
                pool_dinamico_completo_ids = {eq["EquipoId"] for eq in pool_dinamico_completo_obj_list}
                
                carga_trabajo_por_robot = self.balanceador._obtener_carga_de_trabajo_consolidada()
                
                query_asignaciones_actuales = "SELECT RobotId, EquipoId, Reservado, EsProgramado FROM dbo.Asignaciones;"
                asignaciones_actuales_list = self.db_sam.ejecutar_consulta(query_asignaciones_actuales, es_select=True) or []
                
                mapa_equipos_asignados_dinamicamente: Dict[int, List[int]] = {}
                all_fixed_assigned_equipo_ids = set() 

                for asignacion in asignaciones_actuales_list:
                    robot_id_asignacion = asignacion.get("RobotId")
                    if robot_id_asignacion is None and (not asignacion.get("Reservado") and not asignacion.get("EsProgramado")):
                        logger.warning(f"Balanceo: Encontrada asignación dinámica en dbo.Asignaciones con RobotId NULL para EquipoId {asignacion.get('EquipoId')}. Ignorando.")
                        continue
                    
                    if not asignacion.get("Reservado") and not asignacion.get("EsProgramado"):
                        # Asegurarse de que robot_id_asignacion no es None aquí antes de usarlo como clave
                        if robot_id_asignacion is not None:
                            mapa_equipos_asignados_dinamicamente.setdefault(robot_id_asignacion, []).append(asignacion["EquipoId"])
                    else:
                        # Las asignaciones fijas (reservadas o programadas) pueden o no tener RobotId,
                        # pero nos interesa el EquipoId para saber que no está en el pool dinámico.
                        if asignacion.get("EquipoId") is not None:
                            all_fixed_assigned_equipo_ids.add(asignacion["EquipoId"])

                query_ejecuciones_activas = "SELECT RobotId, EquipoId FROM dbo.Ejecuciones WHERE Estado IN ('PENDING_EXECUTION', 'DEPLOYED', 'RUNNING', 'UPDATE', 'RUN_PAUSED', 'QUEUED');"
                ejecuciones_activas_list = self.db_sam.ejecutar_consulta(query_ejecuciones_activas, es_select=True) or []
                equipos_en_uso_por_robot: Dict[int, Set[int]] = {}
                for ejecucion in ejecuciones_activas_list:
                    equipos_en_uso_por_robot.setdefault(ejecucion["RobotId"], set()).add(ejecucion["EquipoId"])

                # --- PRE-FASE: VALIDAR Y LIMPIAR ASIGNACIONES EXISTENTES POR VALIDEZ DE MÁQUINA ---
                self._validar_y_limpiar_asignaciones_por_validez_maquina(
                    mapa_equipos_asignados_dinamicamente,
                    pool_dinamico_completo_ids, # Pasamos el set de IDs de máquinas válidas
                    carga_trabajo_por_robot,
                    equipos_en_uso_por_robot
                )
                if self.balanceador._is_shutting_down: return

                # --- FASE 0: LIMPIEZA DE ASIGNACIONES A ROBOTS INACTIVOS/OFFLINE ---
                self._limpiar_asignaciones_robots_no_candidatos(
                    mapa_equipos_asignados_dinamicamente,
                    carga_trabajo_por_robot,
                    equipos_en_uso_por_robot
                )
                if self.balanceador._is_shutting_down: return

                # --- OBTENER ROBOTS CANDIDATOS (ACTIVOS Y ONLINE) PARA EL RESTO DEL BALANCEO ---
                # (mapa_config_robots ahora solo contendrá robots que pueden ser balanceados)
                query_robots_candidatos = """
                SELECT RobotId, Robot, MinEquipos, MaxEquipos, PrioridadBalanceo, TicketsPorEquipoAdicional 
                FROM dbo.Robots 
                WHERE Activo = 1 AND EsOnline = 1
                ORDER BY PrioridadBalanceo DESC, RobotId;
                """
                robots_candidatos_config_list = self.db_sam.ejecutar_consulta(query_robots_candidatos, es_select=True) or []
                mapa_config_robots: Dict[int, Dict[str, Any]] = {r["RobotId"]: r for r in robots_candidatos_config_list}


                # --- FASE 1: SATISFACCIÓN DE MÍNIMOS (CON REASIGNACIÓN SI ES NECESARIO) ---
                logger.info("Balanceo - Fase 1: Satisfacción de Mínimos con Reasignación...")
                min_needs_list: List[Tuple[int, int, int, Dict[str,Any], int, int]] = [] 
                for r_id, r_cfg in mapa_config_robots.items(): 
                    if self.balanceador._is_shutting_down: break
                    tickets = carga_trabajo_por_robot.get(r_id, 0)
                    if tickets <= 0: continue

                    min_req = self._get_min_requerido_funcional(r_cfg, tickets)
                    num_actual_din = len(mapa_equipos_asignados_dinamicamente.get(r_id, []))

                    if num_actual_din < min_req:
                        faltante_para_min = min_req - num_actual_din
                        can_add, just_add_min = self.cooling_manager.puede_ampliarse(r_id, tickets, num_actual_din)
                        if can_add:
                            min_needs_list.append((r_id, faltante_para_min, r_cfg.get("PrioridadBalanceo", 100), r_cfg, tickets, num_actual_din))
                            logger.info(f"Fase 1: RobotId {r_id} necesita {faltante_para_min} para min ({min_req}). Actuales Din: {num_actual_din}. JustCool: {just_add_min}")
                        else:
                            logger.info(f"Fase 1: RobotId {r_id} necesita {faltante_para_min} para min, pero CoolingManager impide asignarle. JustCool: {just_add_min}")
                
                min_needs_list.sort(key=lambda x: (x[2], x[1]), reverse=True)

                for r_id_req, faltante_req, prio_req, cfg_req, tks_req, num_asig_antes_req_fase1 in min_needs_list:
                    if self.balanceador._is_shutting_down: break
                    
                    equipos_asignados_a_req_en_fase1 = 0
                    while equipos_asignados_a_req_en_fase1 < faltante_req:
                        if self.balanceador._is_shutting_down: break

                        current_all_assigned_dyn_ids = set(eq_id for subl in mapa_equipos_asignados_dinamicamente.values() for eq_id in subl)
                        equipos_libres_en_pool_ahora = [
                            eq_id for eq_id in pool_dinamico_completo_ids 
                            if eq_id not in current_all_assigned_dyn_ids and eq_id not in all_fixed_assigned_equipo_ids
                        ]
                        
                        equipo_conseguido_para_req_subintento = False
                        if equipos_libres_en_pool_ahora:
                            equipo_a_asignar = equipos_libres_en_pool_ahora[0]
                            num_actual_din_req_antes_asign = len(mapa_equipos_asignados_dinamicamente.get(r_id_req, [])) # Para CoolingManager
                            can_add_req_sub, just_add_req_sub = self.cooling_manager.puede_ampliarse(r_id_req, tks_req, num_actual_din_req_antes_asign)
                            if can_add_req_sub:
                                if self._realizar_asignacion_db(r_id_req, equipo_a_asignar, "ASIGNAR_MIN_POOL"):
                                    mapa_equipos_asignados_dinamicamente.setdefault(r_id_req, []).append(equipo_a_asignar)
                                    self.cooling_manager.registrar_ampliacion(r_id_req, tks_req, 1)
                                    self.historico_client.registrar_decision_balanceo(
                                        r_id_req, tks_req, 
                                        num_asig_antes_req_fase1 + equipos_asignados_a_req_en_fase1, # antes de esta asignacion especifica
                                        num_asig_antes_req_fase1 + equipos_asignados_a_req_en_fase1 + 1, # despues
                                        "ASIGNAR_MIN_POOL", f"Prio:{prio_req}"
                                    )
                                    equipos_asignados_a_req_en_fase1 += 1
                                    equipo_conseguido_para_req_subintento = True
                            else:
                                logger.info(f"Fase 1: RobotId {r_id_req} no puede recibir más equipos del pool libre (enfriamiento). JustCool: {just_add_req_sub}")
                        
                        if not equipo_conseguido_para_req_subintento and (equipos_asignados_a_req_en_fase1 < faltante_req) : # Aún necesita y no se obtuvo del pool
                            potential_donors = []
                            for r_id_donor_loop, cfg_donor_loop in mapa_config_robots.items(): # Donantes deben ser Activos y Online
                                if r_id_donor_loop == r_id_req: continue

                                num_actual_din_donor = len(mapa_equipos_asignados_dinamicamente.get(r_id_donor_loop, []))
                                min_req_donor = self._get_min_requerido_funcional(cfg_donor_loop, carga_trabajo_por_robot.get(r_id_donor_loop, 0))

                                if num_actual_din_donor > min_req_donor:
                                    tks_donor_loop = carga_trabajo_por_robot.get(r_id_donor_loop, 0)
                                    can_remove_donor, just_rem_donor = self.cooling_manager.puede_reducirse(r_id_donor_loop, tks_donor_loop, num_actual_din_donor)
                                    if can_remove_donor:
                                        potential_donors.append({
                                            "id": r_id_donor_loop, "priority": cfg_donor_loop.get("PrioridadBalanceo", 100),
                                            "above_min": num_actual_din_donor - min_req_donor, 
                                            "num_assigned": num_actual_din_donor, "tickets": tks_donor_loop
                                        })
                                    else:
                                        logger.debug(f"Fase 1: Potencial donante {r_id_donor_loop} en enfriamiento para desasignar. JustCool: {just_rem_donor}")
                            
                            if potential_donors:
                                potential_donors.sort(key=lambda d: (d["priority"], -d["above_min"], -d["num_assigned"])) # Prio ASC, AboveMin DESC, NumAssigned DESC
                                
                                donor_sel = potential_donors[0]
                                r_id_d_sel = donor_sel["id"]
                                equipos_del_donante_sel = list(mapa_equipos_asignados_dinamicamente.get(r_id_d_sel, []))
                                equipos_en_uso_d_sel = equipos_en_uso_por_robot.get(r_id_d_sel, set())
                                eq_a_robar = next((eq_id for eq_id in equipos_del_donante_sel if eq_id not in equipos_en_uso_d_sel), None)
                                if not eq_a_robar and equipos_del_donante_sel: eq_a_robar = equipos_del_donante_sel[0]

                                if eq_a_robar:
                                    logger.info(f"Fase 1: Reasignando EquipoId {eq_a_robar} de RobotId {r_id_d_sel} (Prio:{donor_sel['priority']}) para RobotId {r_id_req} (Prio:{prio_req}).")
                                    if self._realizar_desasignacion_db(r_id_d_sel, eq_a_robar):
                                        mapa_equipos_asignados_dinamicamente[r_id_d_sel].remove(eq_a_robar)
                                        self.cooling_manager.registrar_reduccion(r_id_d_sel, donor_sel["tickets"], 1)
                                        self.historico_client.registrar_decision_balanceo(
                                            r_id_d_sel, donor_sel["tickets"], donor_sel["num_assigned"], donor_sel["num_assigned"] - 1,
                                            "DESASIGNAR_PARA_MIN_AJENO", f"Cedido a R{r_id_req}"
                                        )
                                        
                                        num_actual_din_req_antes_robado = len(mapa_equipos_asignados_dinamicamente.get(r_id_req, []))
                                        can_add_req_robado, just_add_req_robado = self.cooling_manager.puede_ampliarse(r_id_req, tks_req, num_actual_din_req_antes_robado)
                                        if can_add_req_robado:
                                            if self._realizar_asignacion_db(r_id_req, eq_a_robar, "ASIGNAR_MIN_REASIG"):
                                                mapa_equipos_asignados_dinamicamente.setdefault(r_id_req, []).append(eq_a_robar)
                                                self.cooling_manager.registrar_ampliacion(r_id_req, tks_req, 1)
                                                self.historico_client.registrar_decision_balanceo(
                                                    r_id_req, tks_req,
                                                    num_asig_antes_req_fase1 + equipos_asignados_a_req_en_fase1,
                                                    num_asig_antes_req_fase1 + equipos_asignados_a_req_en_fase1 + 1,
                                                    "ASIGNAR_MIN_REASIG", f"Prio:{prio_req}, Desde R{r_id_d_sel}"
                                                )
                                                equipos_asignados_a_req_en_fase1 += 1
                                                equipo_conseguido_para_req_subintento = True
                                            else: # Fallo al asignar al solicitante, el equipo "robado" queda libre
                                                logger.warning(f"Fase 1: Equipo {eq_a_robar} robado de {r_id_d_sel} NO pudo ser asignado a {r_id_req}.")
                                        else:
                                            logger.info(f"Fase 1: Equipo {eq_a_robar} liberado de {r_id_d_sel}, pero RobotId {r_id_req} no puede escalar (Cooling). JustCool:{just_add_req_robado}")
                                    else:
                                        logger.error(f"Fase 1: Fallo al desasignar equipo {eq_a_robar} de RobotId {r_id_d_sel} para reasignación.")
                        
                        if not equipo_conseguido_para_req_subintento:
                            logger.info(f"Fase 1: No se pudo obtener más equipos para el mínimo de RobotId {r_id_req} en este sub-intento del while.")
                            break # Salir del while para este r_id_req, no hay más que hacer por él ahora
                logger.info("Balanceo - Fase 1: Satisfacción de Mínimos completada.")
                if self.balanceador._is_shutting_down: return

                # --- FASE 2: DESASIGNACIÓN DE EXCEDENTES REALES (POST-MÍNIMOS) ---
                logger.info("Balanceo - Fase 2: Desasignación de Excedentes Reales...")
                for r_id, r_cfg in mapa_config_robots.items(): # Solo itera sobre robots Activos y Online
                    if self.balanceador._is_shutting_down: break
                    tickets = carga_trabajo_por_robot.get(r_id, 0)
                    
                    equipos_necesarios_total = self.balanceador._calcular_equipos_necesarios_para_robot(tickets, r_cfg)
                    min_req_funcional = self._get_min_requerido_funcional(r_cfg, tickets)
                    target_desasignacion = max(equipos_necesarios_total, min_req_funcional if tickets > 0 else 0)
                    num_actual_din = len(mapa_equipos_asignados_dinamicamente.get(r_id, []))

                    if num_actual_din > target_desasignacion:
                        can_sd, just_sd = self.cooling_manager.puede_reducirse(r_id, tickets, num_actual_din)
                        if can_sd:
                            a_liberar = num_actual_din - target_desasignacion
                            logger.info(f"Fase 2: RobotId {r_id} excede target. Actuales Din: {num_actual_din}, Target: {target_desasignacion}. Liberará: {a_liberar}. JustCool: {just_sd}")
                            
                            equipos_del_robot_f2 = list(mapa_equipos_asignados_dinamicamente.get(r_id, []))
                            equipos_en_uso_r_f2 = equipos_en_uso_por_robot.get(r_id, set())
                            candidatos_liberar_f2 = [eq_id for eq_id in equipos_del_robot_f2 if eq_id not in equipos_en_uso_r_f2]
                            if len(candidatos_liberar_f2) < a_liberar:
                                candidatos_liberar_f2.extend([eq_id for eq_id in equipos_del_robot_f2 if eq_id in equipos_en_uso_r_f2 and eq_id not in candidatos_liberar_f2])

                            liberados_f2_count = 0
                            for i in range(min(a_liberar, len(candidatos_liberar_f2))):
                                eq_id_lib_f2 = candidatos_liberar_f2[i]
                                if self._realizar_desasignacion_db(r_id, eq_id_lib_f2):
                                    mapa_equipos_asignados_dinamicamente.get(r_id, []).remove(eq_id_lib_f2)
                                    liberados_f2_count +=1
                            
                            if liberados_f2_count > 0:
                                self.cooling_manager.registrar_reduccion(r_id, tickets, liberados_f2_count)
                                self.historico_client.registrar_decision_balanceo(r_id, tickets, num_actual_din, num_actual_din - liberados_f2_count, "DESASIGNAR_EXC_REAL", just_sd)
                        else:
                             logger.info(f"Fase 2: Desasignación excedente RobotId {r_id} en espera por CoolingManager. JustCool: {just_sd}")
                logger.info("Balanceo - Fase 2: Desasignación de Excedentes Reales completada.")
                if self.balanceador._is_shutting_down: return

                # --- FASE 3: ASIGNACIÓN DE DEMANDA ADICIONAL (CON POOL LIBRE RESTANTE) ---
                logger.info("Balanceo - Fase 3: Asignación de Demanda Adicional...")
                current_all_assigned_dyn_ids_post_f2 = set(eq_id for subl in mapa_equipos_asignados_dinamicamente.values() for eq_id in subl)
                equipos_libres_final_pool = [
                    eq_id for eq_id in pool_dinamico_completo_ids 
                    if eq_id not in current_all_assigned_dyn_ids_post_f2 and eq_id not in all_fixed_assigned_equipo_ids
                ]
                logger.info(f"Fase 3: Equipos en pool para demanda adicional: {len(equipos_libres_final_pool)}")

                necesidades_adicionales_final = []
                for r_id, r_cfg in mapa_config_robots.items(): # Solo robots Activos y Online
                    if self.balanceador._is_shutting_down: break
                    tickets = carga_trabajo_por_robot.get(r_id, 0)
                    if tickets <= 0: continue

                    equipos_nec_total = self.balanceador._calcular_equipos_necesarios_para_robot(tickets, r_cfg)
                    num_actual_din_post_f2 = len(mapa_equipos_asignados_dinamicamente.get(r_id, []))
                    max_cfg = r_cfg.get("MaxEquipos", -1)
                    limite_sup = equipos_nec_total if max_cfg == -1 else min(equipos_nec_total, max_cfg)

                    if num_actual_din_post_f2 < limite_sup:
                        necesidad_final = limite_sup - num_actual_din_post_f2
                        can_add_f3, just_add_f3 = self.cooling_manager.puede_ampliarse(r_id, tickets, num_actual_din_post_f2)
                        if can_add_f3:
                            necesidades_adicionales_final.append((r_id, necesidad_final, r_cfg.get("PrioridadBalanceo",100), r_cfg, tickets, num_actual_din_post_f2))
                        else:
                            logger.info(f"Fase 3: RobotId {r_id} necesita {necesidad_final} adic, pero CoolingManager impide. JustCool: {just_add_f3}")
                
                necesidades_adicionales_final.sort(key=lambda x: (x[2], x[1]), reverse=True)

                for r_id, nec_adic, prio, cfg, tks, num_asig_antes_f3 in necesidades_adicionales_final:
                    if self.balanceador._is_shutting_down: break
                    if not equipos_libres_final_pool: break

                    a_asignar_final = min(nec_adic, len(equipos_libres_final_pool))
                    asignados_f3_count = 0
                    for _ in range(a_asignar_final):
                        if not equipos_libres_final_pool: break
                        eq_id_asig_final = equipos_libres_final_pool.pop(0)
                        if self._realizar_asignacion_db(r_id, eq_id_asig_final, "ASIGNAR_DEM_ADIC"):
                            mapa_equipos_asignados_dinamicamente.setdefault(r_id, []).append(eq_id_asig_final)
                            asignados_f3_count +=1
                        else:
                            equipos_libres_final_pool.insert(0, eq_id_asig_final) # Devolver si falla
                    
                    if asignados_f3_count > 0:
                        self.cooling_manager.registrar_ampliacion(r_id, tks, asignados_f3_count)
                        self.historico_client.registrar_decision_balanceo(
                            r_id, tks, num_asig_antes_f3, num_asig_antes_f3 + asignados_f3_count,
                            "ASIGNAR_DEM_ADIC", f"Prio:{prio}"
                        )
                logger.info("Balanceo - Fase 3: Asignación de Demanda Adicional completada.")
                logger.info("SAM Balanceador (Balanceo): Ciclo de balanceo TOTALMENTE completado.")

            except Exception as e:
                logger.error(f"Error crítico en ciclo de balanceo: {e}", exc_info=True)
                if hasattr(self, 'notificador') and hasattr(self.notificador, 'send_alert'):
                    import traceback
                    try:
                        self.notificador.send_alert(
                            subject="Error crítico en ciclo de balanceo SAM",
                            message=f"Se ha producido un error crítico en el ciclo de balanceo: {e}\n\n{traceback.format_exc()}",
                            is_critical=True
                        )
                    except Exception as email_ex:
                        logger.error(f"Fallo también al enviar email de notificación de error crítico del Balanceador: {email_ex}")