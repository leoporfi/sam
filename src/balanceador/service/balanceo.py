# SAM/balanceador/service/balanceo.py

import logging
import threading
from typing import Any, Dict, List, Set, Tuple

from balanceador.database.historico_client import HistoricoBalanceoClient
from balanceador.service.cooling_manager import CoolingManager

logger = logging.getLogger(__name__)


class Balanceo:
    def __init__(self, balanceador_instance):
        self.balanceador = balanceador_instance
        for attr_name in ["db_sam", "db_rpa360", "mysql_clouders", "cfg_balanceador_specifics", "notificador"]:
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
            elif rowcount == 0:  # No se borró nada
                logger.warning(f"_realizar_desasignacion_db: NINGUNA FILA BORRADA. RobotId {robot_id}, EquipoId {equipo_id}...")
                return False  # Importante: si esperábamos borrar y no se borró, es un fallo de la operación.
            else:  # Fallo o ambiguo
                logger.error(f"_realizar_desasignacion_db: FALLO O AMBIGUO. Rowcount: {rowcount}...")
                return False
        except Exception as e_deassign:
            logger.error(f"_realizar_desasignacion_db: EXCEPCIÓN ...: {e_deassign}", exc_info=True)
            return False

    def _get_min_requerido_funcional(self, config_robot: Dict[str, Any], tickets_robot: int) -> int:
        min_equipos_db = config_robot.get("MinEquipos", 1)
        return max(1, min_equipos_db) if tickets_robot > 0 else min_equipos_db

    def _procesar_equipo_invalido(
        self,
        robot_id: int,
        equipo_id: int,
        carga_trabajo_por_robot: Dict[int, int],
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],
    ) -> bool:
        """Procesa un equipo inválido, intentando desasignarlo si es posible."""
        num_actual_din_robot: int = len(mapa_equipos_asignados_dinamicamente.get(robot_id, []))
        tickets_robot: int = carga_trabajo_por_robot.get(robot_id, 0)
        can_sd, just_sd = self.cooling_manager.puede_reducirse(robot_id, tickets_robot, num_actual_din_robot)

        if can_sd:
            if self._realizar_desasignacion_db(robot_id, equipo_id):
                return True
            else:
                logger.error(
                    f"Pre-Fase: Fallo al desasignar EquipoId {equipo_id} (máquina inválida) de RobotId {robot_id}. Se mantendrá asignado temporalmente.",
                )
        else:
            logger.info(
                f"Pre-Fase: Desasignación de EquipoId {equipo_id} (máquina inválida) de R{robot_id} en espera por CoolingManager. Just: {just_sd}.",
            )
        return False

    def _actualizar_mapa_asignaciones(self, robot_id: int, equipos_validados: List[int], mapa_equipos_asignados_dinamicamente: Dict[int, List[int]]):
        """Actualiza el mapa de asignaciones con la lista filtrada de equipos."""
        if equipos_validados:
            mapa_equipos_asignados_dinamicamente[robot_id] = equipos_validados
        elif robot_id in mapa_equipos_asignados_dinamicamente:
            del mapa_equipos_asignados_dinamicamente[robot_id]

    def _validar_y_limpiar_asignaciones_por_validez_maquina(
        self,
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],  # IN-OUT
        pool_dinamico_maquinas_validas_ids: Set[int],
        robot_state: Dict[str, Any],  # contiene carga_trabajo_por_robot y equipos_en_uso_por_robot
    ):
        logger.info("Balanceo - Pre-Fase: Validando Asignaciones Dinámicas Existentes por Validez de Máquina...")
        robots_con_asignaciones_a_validar = list(mapa_equipos_asignados_dinamicamente.keys())
        carga_trabajo_por_robot = robot_state["carga_trabajo_por_robot"]

        for robot_id in robots_con_asignaciones_a_validar:
            if self.balanceador._is_shutting_down:
                break

            equipos_originalmente_asignados = list(mapa_equipos_asignados_dinamicamente.get(robot_id, []))
            if not equipos_originalmente_asignados:
                continue

            equipos_validados_a_mantener = []
            maquinas_invalidas_desasignadas_count = 0

            for equipo_id in equipos_originalmente_asignados:
                if equipo_id in pool_dinamico_maquinas_validas_ids:
                    equipos_validados_a_mantener.append(equipo_id)
                else:
                    logger.warning(
                        f"Pre-Fase: EquipoId {equipo_id} (asignado a RobotId {robot_id}) ya no es válido para el pool dinámico. Intentando desasignar.",
                    )
                    if self._procesar_equipo_invalido(robot_id, equipo_id, carga_trabajo_por_robot, mapa_equipos_asignados_dinamicamente):
                        maquinas_invalidas_desasignadas_count += 1
                    else:
                        equipos_validados_a_mantener.append(equipo_id)

            if len(equipos_validados_a_mantener) < len(equipos_originalmente_asignados):
                self._actualizar_mapa_asignaciones(robot_id, equipos_validados_a_mantener, mapa_equipos_asignados_dinamicamente)

            if maquinas_invalidas_desasignadas_count > 0:
                self.cooling_manager.registrar_reduccion(robot_id, carga_trabajo_por_robot.get(robot_id, 0), maquinas_invalidas_desasignadas_count)
                self.historico_client.registrar_decision_balanceo(
                    robot_id,
                    carga_trabajo_por_robot.get(robot_id, 0),
                    len(equipos_originalmente_asignados),
                    len(equipos_validados_a_mantener),
                    "DESASIGNAR_MAQUINA_INVALIDA",
                    f"Liberados {maquinas_invalidas_desasignadas_count} por no cumplir criterios de pool.",
                )

        logger.info("Balanceo - Pre-Fase: Validación de Asignaciones Existentes por Validez de Máquina completada.")

    def _obtener_estado_robots(self, robot_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Obtiene el estado actual de los robots desde la base de datos."""
        query = """
        SELECT r.RobotId, r.Activo, r.EsOnline
        FROM dbo.Robots r
        INNER JOIN (SELECT value FROM STRING_SPLIT(?, ',')) AS ids ON r.RobotId = CAST(ids.value AS INT);
        """
        try:
            robot_ids_str: str = ",".join(map(str, robot_ids))
            estado_actual_robots_list = self.db_sam.ejecutar_consulta(query, (robot_ids_str,), es_select=True) or []
            return {r["RobotId"]: r for r in estado_actual_robots_list}
        except Exception as e:
            logger.error(f"Fase 0: Error al obtener estado actual de robots con asignaciones: {e}", exc_info=True)
            return {}

    def _liberar_equipos_robot_no_candidato(
        self,
        robot_id: int,
        equipos_asignados: List[int],
        equipos_en_uso: Set[int],
        carga_trabajo: int,
        num_actual_din: int,
        mapa_asignaciones: Dict[int, List[int]],
    ) -> int:
        """Libera los equipos asignados a un robot que ya no es candidato."""
        can_sd, just_sd = self.cooling_manager.puede_reducirse(robot_id, carga_trabajo, num_actual_din)
        if not can_sd:
            logger.info(f"Fase 0: Desasignación de RobotId {robot_id} (no candidato) en espera por CoolingManager. Just: {just_sd}")
            return 0

        a_liberar_no_en_uso: List[int] = [eq_id for eq_id in equipos_asignados if eq_id not in equipos_en_uso]
        a_liberar_en_uso: List[int] = [eq_id for eq_id in equipos_asignados if eq_id in equipos_en_uso]
        equipos_a_intentar_liberar: List[int] = a_liberar_no_en_uso + a_liberar_en_uso

        liberados_count = 0
        for equipo_id in equipos_a_intentar_liberar:
            if self._realizar_desasignacion_db(robot_id, equipo_id):
                if robot_id in mapa_asignaciones and equipo_id in mapa_asignaciones[robot_id]:
                    mapa_asignaciones[robot_id].remove(equipo_id)
                liberados_count += 1

        if liberados_count > 0:
            self.cooling_manager.registrar_reduccion(robot_id, carga_trabajo, liberados_count)
            self.historico_client.registrar_decision_balanceo(
                robot_id,
                carga_trabajo,
                num_actual_din,
                num_actual_din - liberados_count,
                "DESASIGNAR_INACTIVO_OFFLINE",
                f"Robot no Act/On. Liberados:{liberados_count}. JustCool:{just_sd}",
            )

        return liberados_count

    def _limpiar_asignaciones_robots_no_candidatos(
        self,
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],  # IN-OUT
        carga_trabajo_por_robot: Dict[int, int],
        equipos_en_uso_por_robot: Dict[int, Set[int]],
    ):
        logger.info("Balanceo - Fase 0: Limpieza de Asignaciones a Robots Inactivos/Offline...")

        robot_ids_con_asignaciones_dinamicas = list(mapa_equipos_asignados_dinamicamente.keys())
        if not robot_ids_con_asignaciones_dinamicas:
            logger.info("Fase 0: No hay robots con asignaciones dinámicas preexistentes para limpiar.")
            return

        mapa_estado_robots_db = self._obtener_estado_robots(robot_ids_con_asignaciones_dinamicas)
        ids_a_remover_del_mapa_principal = []

        for robot_id in robot_ids_con_asignaciones_dinamicas:
            if self.balanceador._is_shutting_down:
                break

            estado_robot = mapa_estado_robots_db.get(robot_id)
            es_candidato_actual_para_balanceo = bool(estado_robot.get("Activo")) and bool(estado_robot.get("EsOnline")) if estado_robot else False

            if not es_candidato_actual_para_balanceo:
                equipos_asignados = list(mapa_equipos_asignados_dinamicamente.get(robot_id, []))
                if not equipos_asignados:
                    continue

                logger.info(
                    f"Fase 0: RobotId {robot_id} ya no es candidato (Activo/EsOnline={estado_robot}). Liberando sus {len(equipos_asignados)} equipos dinámicos.",
                )

                tickets_robot: int = carga_trabajo_por_robot.get(robot_id, 0)
                equipos_en_uso: Set[int] = equipos_en_uso_por_robot.get(robot_id, set())
                num_actual_din: int = len(equipos_asignados)

                liberados = self._liberar_equipos_robot_no_candidato(
                    robot_id,
                    equipos_asignados,
                    equipos_en_uso,
                    tickets_robot,
                    num_actual_din,
                    mapa_equipos_asignados_dinamicamente,
                )

                if liberados < len(equipos_asignados):
                    logger.warning(
                        f"Fase 0: No se pudieron liberar todos los equipos de RobotId {robot_id} (no candidato). Quedan {len(mapa_equipos_asignados_dinamicamente.get(robot_id, []))}",
                    )

            if robot_id in mapa_equipos_asignados_dinamicamente and not mapa_equipos_asignados_dinamicamente[robot_id]:
                ids_a_remover_del_mapa_principal.append(robot_id)

        for robot_id_remove in ids_a_remover_del_mapa_principal:
            del mapa_equipos_asignados_dinamicamente[robot_id_remove]
        logger.info("Balanceo - Fase 0: Limpieza de Asignaciones por Robot Inactivo/Offline completada.")

    def _obtener_estado_inicial(self) -> Tuple[Set[int], Dict[int, int], List[Dict[str, Any]], Dict[int, List[int]], Set[int], Dict[int, Set[int]]]:
        """Obtiene el estado inicial necesario para el balanceo."""
        pool_dinamico_completo_obj_list = self.balanceador._obtener_pool_dinamico_disponible()
        pool_dinamico_completo_ids = {eq["EquipoId"] for eq in pool_dinamico_completo_obj_list}
        carga_trabajo_por_robot = self.balanceador._obtener_carga_de_trabajo_consolidada()

        query_asignaciones = "SELECT RobotId, EquipoId, Reservado, EsProgramado FROM dbo.Asignaciones;"
        asignaciones_actuales_list = self.db_sam.ejecutar_consulta(query_asignaciones, es_select=True) or []

        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]] = {}
        all_fixed_assigned_equipo_ids = set()

        for asignacion in asignaciones_actuales_list:
            robot_id = asignacion.get("RobotId")
            if robot_id is None and (not asignacion.get("Reservado") and not asignacion.get("EsProgramado")):
                logger.warning(
                    f"Balanceo: Encontrada asignación dinámica en dbo.Asignaciones con RobotId NULL para EquipoId {asignacion.get('EquipoId')}. Ignorando.",
                )
                continue

            if not asignacion.get("Reservado") and not asignacion.get("EsProgramado"):
                if robot_id is not None:
                    mapa_equipos_asignados_dinamicamente.setdefault(robot_id, []).append(asignacion["EquipoId"])
            elif asignacion.get("EquipoId") is not None:
                all_fixed_assigned_equipo_ids.add(asignacion["EquipoId"])

        query_ejecuciones = """
        SELECT RobotId, EquipoId FROM dbo.Ejecuciones
        WHERE Estado IN ('PENDING_EXECUTION', 'DEPLOYED', 'RUNNING', 'UPDATE', 'RUN_PAUSED', 'QUEUED');
        """
        ejecuciones_activas_list = self.db_sam.ejecutar_consulta(query_ejecuciones, es_select=True) or []
        equipos_en_uso_por_robot: Dict[int, Set[int]] = {}
        for ejecucion in ejecuciones_activas_list:
            equipos_en_uso_por_robot.setdefault(ejecucion["RobotId"], set()).add(ejecucion["EquipoId"])

        return (
            pool_dinamico_completo_ids,
            carga_trabajo_por_robot,
            asignaciones_actuales_list,
            mapa_equipos_asignados_dinamicamente,
            all_fixed_assigned_equipo_ids,
            equipos_en_uso_por_robot,
        )

    def _obtener_robots_candidatos(self) -> Dict[int, Dict[str, Any]]:
        """Obtiene la configuración de robots candidatos para balanceo."""
        query = """SELECT RobotId, Robot, MinEquipos, MaxEquipos, PrioridadBalanceo, TicketsPorEquipoAdicional 
        FROM dbo.Robots 
        WHERE Activo = 1 AND EsOnline = 1
        ORDER BY PrioridadBalanceo DESC, RobotId;"""  # noqa: W291
        robots_candidatos_config_list = self.db_sam.ejecutar_consulta(query, es_select=True) or []
        return {r["RobotId"]: r for r in robots_candidatos_config_list}

    def _procesar_fase_satisfaccion_minimos(
        self,
        mapa_config_robots: Dict[int, Dict[str, Any]],
        carga_trabajo_por_robot: Dict[int, int],
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],
    ) -> List[Tuple[int, int, int, Dict[str, Any], int, int]]:
        """Procesa la fase de satisfacción de mínimos y retorna la lista de necesidades."""
        logger.info("Balanceo - Fase 1: Satisfacción de Mínimos con Reasignación...")
        min_needs_list: List[Tuple[int, int, int, Dict[str, Any], int, int]] = []

        for r_id, r_cfg in mapa_config_robots.items():
            if self.balanceador._is_shutting_down:
                break
            tickets = carga_trabajo_por_robot.get(r_id, 0)
            if tickets <= 0:
                continue

            min_req: int = self._get_min_requerido_funcional(r_cfg, tickets)
            num_actual_din = len(mapa_equipos_asignados_dinamicamente.get(r_id, []))

            if num_actual_din < min_req:
                faltante_para_min = min_req - num_actual_din
                can_add, just_add_min = self.cooling_manager.puede_ampliarse(r_id, tickets, num_actual_din)
                if can_add:
                    min_needs_list.append((r_id, faltante_para_min, r_cfg.get("PrioridadBalanceo", 100), r_cfg, tickets, num_actual_din))
                    logger.info(
                        f"Fase 1: RobotId {r_id} necesita {faltante_para_min} para min ({min_req}). Actuales Din: {num_actual_din}. JustCool: {just_add_min}",
                    )
                else:
                    logger.info(
                        f"Fase 1: RobotId {r_id} necesita {faltante_para_min} para min, pero CoolingManager impide asignarle. JustCool: {just_add_min}",
                    )

        return sorted(min_needs_list, key=lambda x: (x[2], x[1]), reverse=True)

    def _procesar_fase_desasignacion_excedentes(
        self,
        mapa_config_robots: Dict[int, Dict[str, Any]],
        carga_trabajo_por_robot: Dict[int, int],
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],
        equipos_en_uso_por_robot: Dict[int, Set[int]],
    ):
        """Procesa la fase de desasignación de excedentes."""
        logger.info("Balanceo - Fase 2: Desasignación de Excedentes Reales...")
        for r_id, r_cfg in mapa_config_robots.items():
            if self.balanceador._is_shutting_down:
                break
            tickets = carga_trabajo_por_robot.get(r_id, 0)

            equipos_necesarios_total = self.balanceador._calcular_equipos_necesarios_para_robot(tickets, r_cfg)
            min_req_funcional: int = self._get_min_requerido_funcional(r_cfg, tickets)
            target_desasignacion: int = max(equipos_necesarios_total, min_req_funcional if tickets > 0 else 0)
            num_actual_din: int = len(mapa_equipos_asignados_dinamicamente.get(r_id, []))

            if num_actual_din > target_desasignacion:
                can_sd, just_sd = self.cooling_manager.puede_reducirse(r_id, tickets, num_actual_din)
                if can_sd:
                    a_liberar: int = num_actual_din - target_desasignacion
                    logger.info(
                        f"Fase 2: RobotId {r_id} excede target. Actuales Din: {num_actual_din}, Target: {target_desasignacion}. Liberará: {a_liberar}. JustCool: {just_sd}",
                    )

                    equipos_del_robot_f2 = list(mapa_equipos_asignados_dinamicamente.get(r_id, []))
                    equipos_en_uso_r_f2: Set[int] = equipos_en_uso_por_robot.get(r_id, set())
                    candidatos_liberar_f2: List[int] = [eq_id for eq_id in equipos_del_robot_f2 if eq_id not in equipos_en_uso_r_f2]
                    if len(candidatos_liberar_f2) < a_liberar:
                        candidatos_liberar_f2.extend(
                            [eq_id for eq_id in equipos_del_robot_f2 if eq_id in equipos_en_uso_r_f2 and eq_id not in candidatos_liberar_f2],
                        )

                    liberados_f2_count = 0
                    for i in range(min(a_liberar, len(candidatos_liberar_f2))):
                        eq_id_lib_f2 = candidatos_liberar_f2[i]
                        if self._realizar_desasignacion_db(r_id, eq_id_lib_f2):
                            mapa_equipos_asignados_dinamicamente.get(r_id, []).remove(eq_id_lib_f2)
                            liberados_f2_count += 1

                    if liberados_f2_count > 0:
                        self.cooling_manager.registrar_reduccion(r_id, tickets, liberados_f2_count)
                        self.historico_client.registrar_decision_balanceo(
                            r_id,
                            tickets,
                            num_actual_din,
                            num_actual_din - liberados_f2_count,
                            "DESASIGNAR_EXC_REAL",
                            just_sd,
                        )
                else:
                    logger.info(f"Fase 2: Desasignación excedente RobotId {r_id} en espera por CoolingManager. JustCool: {just_sd}")

    def _obtener_necesidades_adicionales(
        self,
        mapa_config_robots: Dict[int, Dict[str, Any]],
        carga_trabajo_por_robot: Dict[int, int],
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],
    ) -> List[Tuple[int, int, int, Dict[str, Any], int, int]]:
        necesidades_adicionales_final = []
        for r_id, r_cfg in mapa_config_robots.items():
            if self.balanceador._is_shutting_down:
                break
            tickets = carga_trabajo_por_robot.get(r_id, 0)
            if tickets <= 0:
                continue

            equipos_nec_total = self.balanceador._calcular_equipos_necesarios_para_robot(tickets, r_cfg)
            num_actual_din_post_f2 = len(mapa_equipos_asignados_dinamicamente.get(r_id, []))
            max_cfg = r_cfg.get("MaxEquipos", -1)
            limite_sup = equipos_nec_total if max_cfg == -1 else min(equipos_nec_total, max_cfg)

            if num_actual_din_post_f2 < limite_sup:
                necesidad_final = limite_sup - num_actual_din_post_f2
                can_add_f3, just_add_f3 = self.cooling_manager.puede_ampliarse(r_id, tickets, num_actual_din_post_f2)
                if can_add_f3:
                    necesidades_adicionales_final.append(
                        (r_id, necesidad_final, r_cfg.get("PrioridadBalanceo", 100), r_cfg, tickets, num_actual_din_post_f2),
                    )
                else:
                    logger.info(f"Fase 3: RobotId {r_id} necesita {necesidad_final} adic, pero CoolingManager impide. JustCool: {just_add_f3}")

        return sorted(necesidades_adicionales_final, key=lambda x: (x[2], x[1]), reverse=True)

    def _asignar_equipos_adicionales(
        self,
        necesidades_adicionales: List[Tuple[int, int, int, Dict[str, Any], int, int]],
        equipos_libres: List[int],
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],
    ):
        for r_id, nec_adic, prio, _, tks, num_asig_antes_f3 in necesidades_adicionales:
            if self.balanceador._is_shutting_down:
                break
            if not equipos_libres:
                break

            a_asignar_final: int = min(nec_adic, len(equipos_libres))
            asignados_f3_count = 0
            for _ in range(a_asignar_final):
                if not equipos_libres:
                    break
                eq_id_asig_final = equipos_libres.pop(0)
                if self._realizar_asignacion_db(r_id, eq_id_asig_final, "ASIGNAR_DEM_ADIC"):
                    mapa_equipos_asignados_dinamicamente.setdefault(r_id, []).append(eq_id_asig_final)
                    asignados_f3_count += 1
                else:
                    equipos_libres.insert(0, eq_id_asig_final)

            if asignados_f3_count > 0:
                self.cooling_manager.registrar_ampliacion(r_id, tks, asignados_f3_count)
                self.historico_client.registrar_decision_balanceo(
                    r_id,
                    tks,
                    num_asig_antes_f3,
                    num_asig_antes_f3 + asignados_f3_count,
                    "ASIGNAR_DEM_ADIC",
                    f"Prio:{prio}",
                )

    def _procesar_fase_demanda_adicional(
        self,
        mapa_config_robots: Dict[int, Dict[str, Any]],
        carga_trabajo_por_robot: Dict[int, int],
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],
        pool_dinamico_completo_ids: Set[int],
        all_fixed_assigned_equipo_ids: Set[int],
    ):
        """Procesa la fase de asignación de demanda adicional."""
        logger.info("Balanceo - Fase 3: Asignación de Demanda Adicional...")
        current_all_assigned_dyn_ids = set(eq_id for subl in mapa_equipos_asignados_dinamicamente.values() for eq_id in subl)  # noqa: C401
        equipos_libres_final_pool = [
            eq_id for eq_id in pool_dinamico_completo_ids if eq_id not in current_all_assigned_dyn_ids and eq_id not in all_fixed_assigned_equipo_ids
        ]
        logger.info(f"Fase 3: Equipos en pool para demanda adicional: {len(equipos_libres_final_pool)}")

        necesidades_adicionales = self._obtener_necesidades_adicionales(
            mapa_config_robots,
            carga_trabajo_por_robot,
            mapa_equipos_asignados_dinamicamente,
        )
        self._asignar_equipos_adicionales(necesidades_adicionales, equipos_libres_final_pool, mapa_equipos_asignados_dinamicamente)

    def ejecutar_balanceo(self):
        if hasattr(self.balanceador, "_is_shutting_down") and self.balanceador._is_shutting_down:
            logger.info("SAM Balanceador (Balanceo): Ciclo abortado (cierre general).")
            return

        logger.info("SAM Balanceador (Balanceo): Iniciando ciclo de balanceo...")

        with self._lock:
            if hasattr(self.balanceador, "_is_shutting_down") and self.balanceador._is_shutting_down:
                return

            try:
                # --- PASO A: OBTENER ESTADO ACTUAL ---
                (
                    pool_dinamico_completo_ids,
                    carga_trabajo_por_robot,
                    asignaciones_actuales_list,
                    mapa_equipos_asignados_dinamicamente,
                    all_fixed_assigned_equipo_ids,
                    equipos_en_uso_por_robot,
                ) = self._obtener_estado_inicial()

                # --- PRE-FASE: VALIDAR Y LIMPIAR ASIGNACIONES EXISTENTES POR VALIDEZ DE MÁQUINA ---
                self._validar_y_limpiar_asignaciones_por_validez_maquina(
                    mapa_equipos_asignados_dinamicamente,
                    pool_dinamico_completo_ids,
                    {"carga_trabajo_por_robot": carga_trabajo_por_robot, "equipos_en_uso_por_robot": equipos_en_uso_por_robot},
                )
                if self.balanceador._is_shutting_down:
                    return

                # --- FASE 0: LIMPIEZA DE ASIGNACIONES A ROBOTS INACTIVOS/OFFLINE ---
                self._limpiar_asignaciones_robots_no_candidatos(
                    mapa_equipos_asignados_dinamicamente,
                    carga_trabajo_por_robot,
                    equipos_en_uso_por_robot,
                )
                if self.balanceador._is_shutting_down:
                    return

                # --- OBTENER ROBOTS CANDIDATOS ---
                mapa_config_robots = self._obtener_robots_candidatos()

                # --- FASE 1: SATISFACCIÓN DE MÍNIMOS ---
                min_needs_list = self._procesar_fase_satisfaccion_minimos(
                    mapa_config_robots,
                    carga_trabajo_por_robot,
                    mapa_equipos_asignados_dinamicamente,
                )
                if self.balanceador._is_shutting_down:
                    return

                # Process minimum needs
                current_all_assigned_dyn_ids = set(eq_id for subl in mapa_equipos_asignados_dinamicamente.values() for eq_id in subl)  # noqa: C401
                equipos_libres_min = [
                    eq_id
                    for eq_id in pool_dinamico_completo_ids
                    if eq_id not in current_all_assigned_dyn_ids and eq_id not in all_fixed_assigned_equipo_ids
                ]
                self._asignar_equipos_adicionales(min_needs_list, equipos_libres_min, mapa_equipos_asignados_dinamicamente)

                # --- FASE 2: DESASIGNACIÓN DE EXCEDENTES ---
                self._procesar_fase_desasignacion_excedentes(
                    mapa_config_robots,
                    carga_trabajo_por_robot,
                    mapa_equipos_asignados_dinamicamente,
                    equipos_en_uso_por_robot,
                )
                if self.balanceador._is_shutting_down:
                    return

                # --- FASE 3: ASIGNACIÓN DE DEMANDA ADICIONAL ---
                self._procesar_fase_demanda_adicional(
                    mapa_config_robots,
                    carga_trabajo_por_robot,
                    mapa_equipos_asignados_dinamicamente,
                    pool_dinamico_completo_ids,
                    all_fixed_assigned_equipo_ids,
                )

                logger.info("SAM Balanceador (Balanceo): Ciclo de balanceo TOTALMENTE completado.")

            except Exception as e:
                logger.error(f"Error crítico en ciclo de balanceo: {e}", exc_info=True)
                if hasattr(self, "notificador") and hasattr(self.notificador, "send_alert"):
                    import traceback

                    try:
                        self.notificador.send_alert(
                            subject="Error crítico en ciclo de balanceo SAM",
                            message=f"Se ha producido un error crítico en el ciclo de balanceo: {e}\n\n{traceback.format_exc()}",
                            is_critical=True,
                        )
                    except Exception as email_ex:
                        logger.error(f"Fallo también al enviar email de notificación de error crítico del Balanceador: {email_ex}")
