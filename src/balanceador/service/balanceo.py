# SAM/src/balanceador/service/balanceo.py

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from balanceador.database.historico_client import HistoricoBalanceoClient
from balanceador.service.cooling_manager import CoolingManager

logger = logging.getLogger(__name__)


class Balanceo:
    def __init__(self, balanceador_instance):
        self.balanceador = balanceador_instance
        for attr_name in ["db_sam", "db_rpa360", "clouders_client", "cfg_balanceador_specifics", "notificador"]:
            if hasattr(balanceador_instance, attr_name):
                setattr(self, attr_name, getattr(balanceador_instance, attr_name))
            else:
                raise AttributeError(f"La instancia del Balanceador no tiene el atributo '{attr_name}'")

        self.historico_client = HistoricoBalanceoClient(self.db_sam)
        cooling_period = self.cfg_balanceador_specifics.get("cooling_period_seg", 300)
        self.cooling_manager = CoolingManager(cooling_period_seconds=cooling_period)
        self._lock = threading.RLock()
        self.aislamiento_estricto_pool = self.cfg_balanceador_specifics.get("aislamiento_estricto_pool", True)
        logger.info(f"Modo de aislamiento estricto de pools: {'Activado' if self.aislamiento_estricto_pool else 'Desactivado (permite desborde)'}")

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
            else:
                logger.warning(f"_realizar_desasignacion_db: NINGUNA FILA BORRADA. RobotId {robot_id}, EquipoId {equipo_id}...")
                return False
        except Exception as e_deassign:
            logger.error(f"_realizar_desasignacion_db: EXCEPCIÓN ...: {e_deassign}", exc_info=True)
            return False

    def _get_min_requerido_funcional(self, config_robot: Dict[str, Any], tickets_robot: int) -> int:
        min_equipos_db = config_robot.get("MinEquipos", 1)
        return max(1, min_equipos_db) if tickets_robot > 0 else min_equipos_db

    def _validar_y_limpiar_asignaciones_por_coherencia_pool(
        self,
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],
        mapa_config_robots: Dict[int, Dict[str, Any]],
        mapa_equipos_validos_por_pool: Dict[Optional[int], Set[int]],
        robot_state: Dict[str, Any],
    ):
        """
        Valida que cada asignación dinámica sea coherente (robot y equipo en el mismo pool).
        Si una asignación es incoherente (ej. Robot de Pool A en Equipo de Pool B), se desasigna.
        """
        logger.info("Pre-Fase: Validando coherencia de Pools en asignaciones dinámicas existentes...")
        carga_trabajo_por_robot = robot_state["carga_trabajo_por_robot"]
        robots_con_asignaciones = list(mapa_equipos_asignados_dinamicamente.keys())

        for robot_id in robots_con_asignaciones:
            config_robot = mapa_config_robots.get(robot_id)
            if not config_robot:
                continue  # El robot ya no es candidato, se limpiará en Fase 0

            robot_pool_id = config_robot.get("PoolId")  # Puede ser None para el Pool General
            equipos_validos_para_este_robot = mapa_equipos_validos_por_pool.get(robot_pool_id, set())

            equipos_originalmente_asignados = list(mapa_equipos_asignados_dinamicamente.get(robot_id, []))
            equipos_coherentes_a_mantener = []

            for equipo_id in equipos_originalmente_asignados:
                if equipo_id in equipos_validos_para_este_robot:
                    equipos_coherentes_a_mantener.append(equipo_id)
                else:
                    # INCOHERENCIA DETECTADA: El equipo no pertenece al pool del robot.
                    logger.warning(
                        f"Pre-Fase: INCOHERENCIA DETECTADA. RobotId {robot_id} (PoolId: {robot_pool_id}) "
                        f"está asignado a EquipoId {equipo_id}, que no pertenece a su pool. Intentando desasignar."
                    )
                    # Intentamos desasignar el equipo incoherente
                    num_actual_din = len(mapa_equipos_asignados_dinamicamente.get(robot_id, []))
                    tickets_robot = carga_trabajo_por_robot.get(robot_id, 0)
                    can_reduce, reason = self.cooling_manager.puede_reducirse(robot_id, tickets_robot, num_actual_din)

                    if can_reduce:
                        if self._realizar_desasignacion_db(robot_id, equipo_id):
                            self.historico_client.registrar_decision_balanceo(
                                robot_id,
                                robot_pool_id,
                                tickets_robot,
                                num_actual_din,
                                num_actual_din - 1,
                                "DESASIGNAR_INCOHERENCIA_POOL",
                                f"Equipo {equipo_id} no pertenece al pool del robot.",
                            )
                        else:
                            logger.error(f"Pre-Fase: Fallo al desasignar EquipoId {equipo_id} (incoherente) de RobotId {robot_id}.")
                            equipos_coherentes_a_mantener.append(equipo_id)  # Si falla la desasignación, lo mantenemos por ahora
                    else:
                        logger.info(f"Pre-Fase: Desasignación de EquipoId {equipo_id} (incoherente) en espera por CoolingManager: {reason}")
                        equipos_coherentes_a_mantener.append(equipo_id)

            # Actualizamos el mapa de asignaciones del robot con solo los equipos coherentes
            mapa_equipos_asignados_dinamicamente[robot_id] = equipos_coherentes_a_mantener

        logger.info("Pre-Fase: Validación de coherencia de Pools completada.")

    def _obtener_estado_robots(self, robot_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Obtiene el estado actual de los robots desde la base de datos."""
        query = """
        SELECT r.RobotId, r.Activo, r.EsOnline, r.PoolId
        FROM dbo.Robots r
        WHERE r.RobotId IN ({})
        """.format(",".join("?" * len(robot_ids)))
        try:
            if not robot_ids:
                return {}
            estado_actual_robots_list = self.db_sam.ejecutar_consulta(query, tuple(robot_ids), es_select=True) or []
            return {r["RobotId"]: r for r in estado_actual_robots_list}
        except Exception as e:
            logger.error(f"Fase 0: Error al obtener estado actual de robots con asignaciones: {e}", exc_info=True)
            return {}

    def _liberar_equipos_robot_no_candidato(
        self,
        robot_id: int,
        config_robot: Dict[str, Any],
        equipos_asignados: List[int],
        equipos_en_uso: Set[int],
        carga_trabajo: int,
        mapa_asignaciones: Dict[int, List[int]],
    ) -> int:
        """Libera los equipos asignados a un robot que ya no es candidato."""
        num_actual_din = len(equipos_asignados)
        can_sd, just_sd = self.cooling_manager.puede_reducirse(robot_id, carga_trabajo, num_actual_din)
        if not can_sd:
            logger.info(f"Fase 0: Desasignación de RobotId {robot_id} (no candidato) en espera por CoolingManager. Just: {just_sd}")
            return 0

        a_liberar_no_en_uso: List[int] = [eq_id for eq_id in equipos_asignados if eq_id not in equipos_en_uso]
        equipos_a_intentar_liberar: List[int] = a_liberar_no_en_uso + [eq_id for eq_id in equipos_asignados if eq_id in equipos_en_uso]

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
                config_robot.get("PoolId"),
                carga_trabajo,
                num_actual_din,
                num_actual_din - liberados_count,
                "DESASIGNAR_INACTIVO_OFFLINE",
                f"Robot no Act/On. Liberados:{liberados_count}. JustCool:{just_sd}",
            )
        return liberados_count

    def _limpiar_asignaciones_robots_no_candidatos(
        self,
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],
        carga_trabajo_por_robot: Dict[int, int],
        equipos_en_uso_por_robot: Dict[int, Set[int]],
        mapa_config_robots: Dict[int, Dict[str, Any]],
    ):
        logger.info("Fase 0: Limpieza de Asignaciones a Robots Inactivos/Offline...")
        robot_ids_con_asignaciones = list(mapa_equipos_asignados_dinamicamente.keys())
        if not robot_ids_con_asignaciones:
            logger.info("Fase 0: No hay robots con asignaciones dinámicas para limpiar.")
            return

        mapa_estado_robots_db = self._obtener_estado_robots(robot_ids_con_asignaciones)

        for robot_id in list(mapa_equipos_asignados_dinamicamente.keys()):
            config_robot = mapa_config_robots.get(robot_id)
            es_candidato = bool(config_robot and config_robot.get("Activo") and config_robot.get("EsOnline"))
            if not es_candidato:
                equipos_asignados = list(mapa_equipos_asignados_dinamicamente.get(robot_id, []))
                if not equipos_asignados:
                    continue

                logger.warning(f"Fase 0: RobotId {robot_id} ya no es candidato para balanceo. Liberando sus {len(equipos_asignados)} equipos.")

                self._liberar_equipos_robot_no_candidato(
                    robot_id,
                    config_robot or {},
                    equipos_asignados,
                    equipos_en_uso_por_robot.get(robot_id, set()),
                    carga_trabajo_por_robot.get(robot_id, 0),
                    mapa_equipos_asignados_dinamicamente,
                )

            if not mapa_equipos_asignados_dinamicamente.get(robot_id):
                del mapa_equipos_asignados_dinamicamente[robot_id]

        logger.info("Fase 0: Limpieza de Asignaciones por Robot Inactivo/Offline completada.")

    def _obtener_robots_candidatos(self) -> Dict[int, Dict[str, Any]]:
        query = """
        SELECT RobotId, Robot, MinEquipos, MaxEquipos, PrioridadBalanceo, TicketsPorEquipoAdicional, PoolId
        FROM dbo.Robots 
        WHERE Activo = 1 AND EsOnline = 1
        ORDER BY PrioridadBalanceo DESC, RobotId;
        """
        robots_candidatos_config_list = self.db_sam.ejecutar_consulta(query, es_select=True) or []
        return {r["RobotId"]: r for r in robots_candidatos_config_list}

    def _procesar_fase_satisfaccion_minimos(
        self,
        mapa_config_robots: Dict[int, Dict[str, Any]],
        carga_trabajo_por_robot: Dict[int, int],
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],
    ) -> List[Tuple[int, int, int, Dict[str, Any], int, int]]:
        logger.info("Fase 1: Satisfacción de Mínimos...")
        min_needs_list = []
        for r_id, r_cfg in mapa_config_robots.items():
            if self.balanceador._is_shutting_down:
                break
            tickets = carga_trabajo_por_robot.get(r_id, 0)
            if tickets <= 0:
                continue

            min_req = self._get_min_requerido_funcional(r_cfg, tickets)
            num_actual_din = len(mapa_equipos_asignados_dinamicamente.get(r_id, []))

            if num_actual_din < min_req:
                faltante = min_req - num_actual_din
                can_add, just_add = self.cooling_manager.puede_ampliarse(r_id, tickets, num_actual_din)
                if can_add:
                    min_needs_list.append((r_id, faltante, r_cfg.get("PrioridadBalanceo", 100), r_cfg.get("PoolId"), r_cfg, tickets, num_actual_din))
                else:
                    logger.info(f"Fase 1: RobotId {r_id} necesita {faltante} para min, pero CoolingManager impide. Just: {just_add}")

        return sorted(min_needs_list, key=lambda x: (x[2], x[1]), reverse=True)

    def _procesar_fase_desasignacion_excedentes(
        self,
        mapa_config_robots: Dict[int, Dict[str, Any]],
        carga_trabajo_por_robot: Dict[int, int],
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],
        equipos_en_uso_por_robot: Dict[int, Set[int]],
    ):
        logger.info("Fase 2: Desasignación de Excedentes...")
        for r_id, r_cfg in mapa_config_robots.items():
            if self.balanceador._is_shutting_down:
                break
            tickets = carga_trabajo_por_robot.get(r_id, 0)
            equipos_nec = self.balanceador._calcular_equipos_necesarios_para_robot(tickets, r_cfg)
            min_req = self._get_min_requerido_funcional(r_cfg, tickets)
            target = max(equipos_nec, min_req if tickets > 0 else 0)
            num_actual = len(mapa_equipos_asignados_dinamicamente.get(r_id, []))

            if num_actual > target:
                can_reduce, just_reduce = self.cooling_manager.puede_reducirse(r_id, tickets, num_actual)
                if can_reduce:
                    a_liberar = num_actual - target
                    equipos_del_robot = list(mapa_equipos_asignados_dinamicamente.get(r_id, []))
                    equipos_en_uso = equipos_en_uso_por_robot.get(r_id, set())
                    candidatos = [e for e in equipos_del_robot if e not in equipos_en_uso] + [e for e in equipos_del_robot if e in equipos_en_uso]

                    liberados_count = 0
                    for eq_id in candidatos[:a_liberar]:
                        if self._realizar_desasignacion_db(r_id, eq_id):
                            mapa_equipos_asignados_dinamicamente[r_id].remove(eq_id)
                            liberados_count += 1

                    if liberados_count > 0:
                        self.cooling_manager.registrar_reduccion(r_id, tickets, liberados_count)
                        self.historico_client.registrar_decision_balanceo(
                            r_id, r_cfg.get("PoolId"), tickets, num_actual, num_actual - liberados_count, "DESASIGNAR_EXCEDENTE", just_reduce
                        )
                else:
                    logger.info(f"Fase 2: Desasignación excedente RobotId {r_id} en espera por CoolingManager: {just_reduce}")

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

            equipos_nec = self.balanceador._calcular_equipos_necesarios_para_robot(tickets, r_cfg)
            num_actual = len(mapa_equipos_asignados_dinamicamente.get(r_id, []))
            max_cfg = r_cfg.get("MaxEquipos", -1)
            limite = equipos_nec if max_cfg == -1 else min(equipos_nec, max_cfg)

            if num_actual < limite:
                necesidad = limite - num_actual
                can_add, just_add = self.cooling_manager.puede_ampliarse(r_id, tickets, num_actual)
                if can_add:
                    if self.aislamiento_estricto_pool and r_cfg.get("PoolId") is not None:
                        logger.info(
                            f"Fase 3: RobotId {r_id} (PoolId: {r_cfg.get('PoolId')}) tiene necesidad adicional pero NO participará en desborde (aislamiento estricto activado)."
                        )
                    else:
                        necesidades_adicionales_final.append(
                            (r_id, necesidad, r_cfg.get("PrioridadBalanceo", 100), r_cfg.get("PoolId"), r_cfg, tickets, num_actual)
                        )
                else:
                    logger.info(f"Fase 3: RobotId {r_id} necesita {necesidad} adic, pero CoolingManager impide. Just: {just_add}")

        return sorted(necesidades_adicionales_final, key=lambda x: (x[2], x[1]), reverse=True)

    def _asignar_equipos_adicionales(
        self,
        necesidades_adicionales: List[Tuple[int, int, int, Dict[str, Any], int, int]],
        equipos_libres: List[int],
        mapa_equipos_asignados_dinamicamente: Dict[int, List[int]],
        motivo_asignacion: str,
    ):
        for r_id, nec, prio, pool_id, _, tks, num_antes in necesidades_adicionales:
            if self.balanceador._is_shutting_down or not equipos_libres:
                break
            a_asignar = min(nec, len(equipos_libres))
            asignados_count = 0
            for _ in range(a_asignar):
                if not equipos_libres:
                    break
                eq_id = equipos_libres.pop(0)
                if self._realizar_asignacion_db(r_id, eq_id, motivo_asignacion):
                    mapa_equipos_asignados_dinamicamente.setdefault(r_id, []).append(eq_id)
                    asignados_count += 1
                else:
                    equipos_libres.insert(0, eq_id)

            if asignados_count > 0:
                self.cooling_manager.registrar_ampliacion(r_id, tks, asignados_count)
                self.historico_client.registrar_decision_balanceo(
                    r_id, pool_id, tks, num_antes, num_antes + asignados_count, motivo_asignacion, f"Prio:{prio}"
                )

    def _obtener_recursos_para_pool(self, pool_id: Optional[int]) -> Dict[str, Any]:
        params = (pool_id,) if pool_id is not None else None
        query_robots = (
            "SELECT * FROM dbo.Robots WHERE Activo = 1 AND EsOnline = 1 AND "
            + ("PoolId = ?" if pool_id is not None else "PoolId IS NULL")
            + " ORDER BY PrioridadBalanceo DESC;"
        )
        query_equipos = (
            "SELECT EquipoId FROM dbo.Equipos WHERE PermiteBalanceoDinamico = 1 AND "
            + ("PoolId = ?" if pool_id is not None else "PoolId IS NULL")
            + ";"
        )

        robots_list = self.db_sam.ejecutar_consulta(query_robots, params, es_select=True) or []
        equipos_list = self.db_sam.ejecutar_consulta(query_equipos, params, es_select=True) or []

        return {"robots": {r["RobotId"]: r for r in robots_list}, "equipos": {eq["EquipoId"] for eq in equipos_list}}

    def _obtener_estado_inicial_global(self):
        logger.debug("Obteniendo estado inicial global del sistema...")
        query_equipos = "SELECT EquipoId, PoolId FROM dbo.Equipos WHERE PermiteBalanceoDinamico = 1 AND Activo_SAM = 1;"
        equipos_dinamicos_list = self.db_sam.ejecutar_consulta(query_equipos, es_select=True) or []

        mapa_equipos_validos_por_pool: Dict[Optional[int], Set[int]] = {None: set()}
        for eq in equipos_dinamicos_list:
            mapa_equipos_validos_por_pool.setdefault(eq["PoolId"], set()).add(eq["EquipoId"])

        query_asignaciones = "SELECT RobotId, EquipoId, Reservado, EsProgramado FROM dbo.Asignaciones;"
        asignaciones_list = self.db_sam.ejecutar_consulta(query_asignaciones, es_select=True) or []

        mapa_asignaciones_dinamicas: Dict[int, List[int]] = {}
        asignaciones_fijas_equipos: Set[int] = set()

        for a in asignaciones_list:
            if a.get("Reservado") or a.get("EsProgramado"):
                if a.get("EquipoId"):
                    asignaciones_fijas_equipos.add(a["EquipoId"])
            else:
                if a.get("RobotId") and a.get("EquipoId"):
                    mapa_asignaciones_dinamicas.setdefault(a["RobotId"], []).append(a["EquipoId"])

        query_ejecuciones = "SELECT RobotId, EquipoId FROM dbo.Ejecuciones WHERE Estado IN ('PENDING_EXECUTION', 'DEPLOYED', 'RUNNING', 'UPDATE', 'RUN_PAUSED', 'QUEUED');"
        ejecuciones_list = self.db_sam.ejecutar_consulta(query_ejecuciones, es_select=True) or []

        equipos_en_uso_por_robot: Dict[int, Set[int]] = {}
        for e in ejecuciones_list:
            if e.get("RobotId") and e.get("EquipoId"):
                equipos_en_uso_por_robot.setdefault(e["RobotId"], set()).add(e["EquipoId"])

        carga_trabajo_por_robot = self.balanceador._obtener_carga_de_trabajo_consolidada()

        return {
            "mapa_equipos_validos_por_pool": mapa_equipos_validos_por_pool,
            "carga_trabajo_por_robot": carga_trabajo_por_robot,
            "mapa_asignaciones_dinamicas": mapa_asignaciones_dinamicas,
            "asignaciones_fijas_equipos": asignaciones_fijas_equipos,
            "equipos_en_uso_por_robot": equipos_en_uso_por_robot,
        }

    def ejecutar_limpieza_global(self, estado_global: Dict[str, Any]):
        logger.info("Iniciando ETAPA DE LIMPIEZA GLOBAL...")
        mapa_config_robots = self._obtener_robots_candidatos()

        self._validar_y_limpiar_asignaciones_por_coherencia_pool(
            estado_global["mapa_asignaciones_dinamicas"], mapa_config_robots, estado_global["mapa_equipos_validos_por_pool"], estado_global
        )

        self._limpiar_asignaciones_robots_no_candidatos(
            estado_global["mapa_asignaciones_dinamicas"],
            estado_global["carga_trabajo_por_robot"],
            estado_global["equipos_en_uso_por_robot"],
            mapa_config_robots,
        )
        logger.info("ETAPA DE LIMPIEZA GLOBAL completada.")
        return mapa_config_robots

    def ejecutar_balanceo_interno_de_pool(self, pool_id: Optional[int], estado_global: Dict[str, Any]):
        pool_nombre = f"PoolId {pool_id}" if pool_id is not None else "Pool General"
        logger.info(f"Iniciando ETAPA DE BALANCEO INTERNO para {pool_nombre}...")

        recursos_pool = self._obtener_recursos_para_pool(pool_id)
        mapa_config_robots_pool = recursos_pool["robots"]

        if not mapa_config_robots_pool:
            logger.info(f"No hay robots candidatos en {pool_nombre}. Saltando.")
            return

        min_needs_list = self._procesar_fase_satisfaccion_minimos(
            mapa_config_robots_pool, estado_global["carga_trabajo_por_robot"], estado_global["mapa_asignaciones_dinamicas"]
        )

        current_assigned = {eq for subl in estado_global["mapa_asignaciones_dinamicas"].values() for eq in subl}
        equipos_libres_pool = [
            eq for eq in recursos_pool["equipos"] if eq not in current_assigned and eq not in estado_global["asignaciones_fijas_equipos"]
        ]

        self._asignar_equipos_adicionales(min_needs_list, equipos_libres_pool, estado_global["mapa_asignaciones_dinamicas"], "ASIGNAR_MIN_POOL")

        self._procesar_fase_desasignacion_excedentes(
            mapa_config_robots_pool,
            estado_global["carga_trabajo_por_robot"],
            estado_global["mapa_asignaciones_dinamicas"],
            estado_global["equipos_en_uso_por_robot"],
        )
        logger.info(f"ETAPA DE BALANCEO INTERNO para {pool_nombre} completada.")

    def ejecutar_fase_de_desborde_global(self, estado_global: Dict[str, Any], mapa_config_robots_global: Dict[str, Any]):
        logger.info("Iniciando ETAPA DE DESBORDE Y DEMANDA ADICIONAL GLOBAL...")

        recursos_pool_general = self._obtener_recursos_para_pool(None)
        current_assigned = {eq for subl in estado_global["mapa_asignaciones_dinamicas"].values() for eq in subl}

        equipos_libres_general = [
            eq for eq in recursos_pool_general["equipos"] if eq not in current_assigned and eq not in estado_global["asignaciones_fijas_equipos"]
        ]

        logger.info(f"Fase Desborde: {len(equipos_libres_general)} equipos disponibles en Pool General.")

        necesidades_globales = self._obtener_necesidades_adicionales(
            mapa_config_robots_global, estado_global["carga_trabajo_por_robot"], estado_global["mapa_asignaciones_dinamicas"]
        )

        self._asignar_equipos_adicionales(
            necesidades_globales, equipos_libres_general, estado_global["mapa_asignaciones_dinamicas"], "ASIGNAR_DESBORDE_O_ADICIONAL"
        )
        logger.info("ETAPA DE DESBORDE Y DEMANDA ADICIONAL GLOBAL completada.")
