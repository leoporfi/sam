# SAM/src/balanceador/service/algoritmo_balanceo.py
# MODIFICADO: El constructor ahora sigue el patrón de Inyección de Dependencias.

import logging
import math
import threading
from typing import Any, Dict, List, Optional

from sam.common.database import DatabaseConnector
from sam.common.mail_client import EmailAlertClient

from .cooling_manager import CoolingManager
from .historico_client import HistoricoBalanceoClient

logger = logging.getLogger(__name__)


class Balanceo:
    """
    Contiene la lógica central y el algoritmo para el balanceo de cargas.
    """

    def __init__(
        self, db_connector: DatabaseConnector, notificador: EmailAlertClient, config_balanceador: Dict[str, Any]
    ):
        """
        Inicializa la clase de lógica de balanceo con sus dependencias inyectadas.
        """
        self.db_sam = db_connector
        self.notificador = notificador
        self.cfg_balanceador_specifics = config_balanceador

        self.historico_client = HistoricoBalanceoClient(self.db_sam)
        cooling_period = self.cfg_balanceador_specifics.get("cooling_period_seg", 300)
        self.cooling_manager = CoolingManager(cooling_period_seconds=cooling_period)
        self.aislamiento_estricto_pool = self.cfg_balanceador_specifics.get("aislamiento_estricto_pool", True)
        self._lock = threading.RLock()
        logger.debug(
            f"Modo de aislamiento estricto de pools: {'Activado' if self.aislamiento_estricto_pool else 'Desactivado'}"
        )

    def ejecutar_algoritmo_completo(self, carga_consolidada: Dict[int, int], pools_activos: List[Dict[str, Any]]):
        """
        Orquesta todas las fases del algoritmo de balanceo.
        """
        with self._lock:
            estado_global = self._obtener_estado_inicial_global(carga_consolidada)
            # 1. Limpieza estándar
            self.ejecutar_limpieza_global(estado_global)

            # 2. FASE NUEVA: Prioridad Estricta (Preemption)
            if self._leer_modo_prioridad_estricta():
                self.ejecutar_desalojo_por_prioridad_estricta(estado_global)

            # 3. Asignación Normal (Balanceo Interno)
            pool_ids = [p["PoolId"] for p in pools_activos]
            if None not in pool_ids:
                pool_ids.append(None)

            for pool_id in pool_ids:
                self.ejecutar_balanceo_interno_de_pool(pool_id, estado_global)

            # 4. Desborde
            self.ejecutar_fase_de_desborde_global(estado_global)

    def _leer_modo_prioridad_estricta(self) -> bool:
        """Consulta rápida a BD para ver si el modo agresivo está activo."""
        try:
            res = self.db_sam.ejecutar_consulta(
                "SELECT Valor FROM dbo.ConfiguracionSistema WHERE Clave = 'BALANCEO_PREEMPTION_MODE'", es_select=True
            )
            return res and res[0]["Valor"].upper() == "TRUE"
        except Exception as e:
            logger.error(f"Error leyendo configuración de Preemption: {e}")
            return False

    def ejecutar_desalojo_por_prioridad_estricta(self, estado_global: Dict[str, Any]):
        """
        Modo 'Prioridad Estricta': Desaloja equipos de robots de Baja Prioridad
        si existen robots de Alta Prioridad con demanda insatisfecha y sin equipos disponibles.
        """
        logger.info(">>> Ejecutando FASE DE PRIORIDAD ESTRICTA (Preemption) <<<")

        mapa_config = estado_global["mapa_config_robots"]
        carga = estado_global["carga_trabajo_por_robot"]
        asignaciones = estado_global["mapa_asignaciones_dinamicas"]

        # 1. Identificar robots con "Hambre" (Demanda insatisfecha)
        robots_hambrientos = []
        for rid, tickets in carga.items():
            config = mapa_config.get(rid, {})
            necesarios = self._calcular_equipos_necesarios_para_robot(rid, tickets, config)
            actuales = len(asignaciones.get(rid, []))

            if necesarios > actuales:
                # Guardamos tupla: (prioridad, robot_id, deficit)
                robots_hambrientos.append(
                    {
                        "id": rid,
                        "prio": config.get("PrioridadBalanceo", 100),
                        "deficit": necesarios - actuales,
                        "pool": config.get("PoolId"),
                    }
                )

        # Ordenar: Los más prioritarios (menor número) primero
        robots_hambrientos.sort(key=lambda x: x["prio"])

        if not robots_hambrientos:
            return

        # 2. Buscar víctimas para cada hambriento
        for robot_vip in robots_hambrientos:
            # Si ya satisfizo su déficit en este ciclo, continuar
            if robot_vip["deficit"] <= 0:
                continue

            # Buscar candidatos a ser desalojados:
            # - Deben ser de MENOR prioridad (numero mayor)
            # - Deben tener equipos asignados dinámicamente
            # - Deben estar en el mismo Pool (o compatibles si implementamos lógica cross-pool compleja,
            #   pero por seguridad empezamos por el mismo pool o global si es None)

            victimas_potenciales = []
            for rid_victima, equipos_victima in asignaciones.items():
                if not equipos_victima:
                    continue

                cfg_victima = mapa_config.get(rid_victima, {})
                prio_victima = cfg_victima.get("PrioridadBalanceo", 100)
                pool_victima = cfg_victima.get("PoolId")

                # Condición de desalojo:
                # 1. Victima tiene PEOR prioridad (Mayor número)
                # 2. Están en el mismo Pool (o ambos None)
                if prio_victima > robot_vip["prio"] and pool_victima == robot_vip["pool"]:
                    victimas_potenciales.append(
                        {
                            "id": rid_victima,
                            "prio": prio_victima,
                            "equipos": list(equipos_victima),  # Copia de la lista
                        }
                    )

            # Ordenar víctimas: Desalojar primero a los de PEOR prioridad (mayor número)
            victimas_potenciales.sort(key=lambda x: x["prio"], reverse=True)

            # 3. Ejecutar desalojo
            for victima in victimas_potenciales:
                while robot_vip["deficit"] > 0 and victima["equipos"]:
                    equipo_a_robar = victima["equipos"].pop()

                    logger.warning(
                        f"[PREEMPTION] Desalojando Equipo {equipo_a_robar} del Robot {victima['id']} (Prio {victima['prio']}) "
                        f"para favorecer al Robot {robot_vip['id']} (Prio {robot_vip['prio']})"
                    )

                    # Desasignamos forzosamente
                    exito = self._realizar_desasignacion_db(
                        victima["id"], equipo_a_robar, "DESALOJO_POR_PRIORIDAD_ESTRICTA", estado_global
                    )

                    if exito:
                        # Reducimos el déficit.
                        # NOTA: No asignamos inmediatamente aquí. Al liberar el equipo,
                        # la siguiente fase "Balanceo Interno" lo verá como "Libre"
                        # y se lo dará al robot_vip porque tiene mejor prioridad.
                        robot_vip["deficit"] -= 1
                    else:
                        # Si falló el desalojo (ej. cooling), paramos con esta víctima
                        break

    def _obtener_estado_inicial_global(self, carga_consolidada: Dict[int, int]) -> Dict[str, Any]:
        """
        Recopila toda la información necesaria de la base de datos para tomar decisiones.
        """
        logger.debug("Obteniendo estado inicial global del sistema...")

        robots_activos_query = "SELECT RobotId, Robot, EsOnline, MinEquipos, MaxEquipos, PrioridadBalanceo, TicketsPorEquipoAdicional, PoolId FROM dbo.Robots WHERE Activo = 1"
        mapa_config_robots = {
            r["RobotId"]: r for r in self.db_sam.ejecutar_consulta(robots_activos_query, es_select=True) or []
        }

        equipos_validos_query = (
            "SELECT EquipoId, PoolId FROM dbo.Equipos WHERE Activo_SAM = 1 AND PermiteBalanceoDinamico = 1"
        )
        equipos_validos = self.db_sam.ejecutar_consulta(equipos_validos_query, es_select=True) or []
        mapa_equipos_validos_por_pool = {}
        for eq in equipos_validos:
            pool_id = eq.get("PoolId")
            if pool_id not in mapa_equipos_validos_por_pool:
                mapa_equipos_validos_por_pool[pool_id] = set()
            mapa_equipos_validos_por_pool[pool_id].add(eq["EquipoId"])

        asignaciones_query = "SELECT RobotId, EquipoId, EsProgramado, Reservado FROM dbo.Asignaciones"
        asignaciones = self.db_sam.ejecutar_consulta(asignaciones_query, es_select=True) or []

        mapa_asignaciones_dinamicas = {}
        equipos_con_asignacion_fija = set()
        for a in asignaciones:
            robot_id = a.get("RobotId")
            equipo_id = a.get("EquipoId")
            if not robot_id or not equipo_id:
                continue

            if not a.get("EsProgramado") and not a.get("Reservado"):
                if robot_id not in mapa_asignaciones_dinamicas:
                    mapa_asignaciones_dinamicas[robot_id] = []
                mapa_asignaciones_dinamicas[robot_id].append(equipo_id)
            else:
                equipos_con_asignacion_fija.add(equipo_id)

        estado = {
            "mapa_config_robots": mapa_config_robots,
            "mapa_equipos_validos_por_pool": mapa_equipos_validos_por_pool,
            "mapa_asignaciones_dinamicas": mapa_asignaciones_dinamicas,
            "equipos_con_asignacion_fija": equipos_con_asignacion_fija,
            "carga_trabajo_por_robot": carga_consolidada,
        }
        logger.info("Estado inicial global obtenido.")
        return estado

    def ejecutar_limpieza_global(self, estado_global: Dict[str, Any]):
        """
        Libera recursos de robots que ya no son candidatos para el balanceo.
        """
        logger.info("Iniciando ETAPA DE LIMPIZA GLOBAL...")
        robots_a_limpiar = []
        mapa_config = estado_global["mapa_config_robots"]

        for robot_id, equipos_asignados in list(estado_global["mapa_asignaciones_dinamicas"].items()):
            config_robot = mapa_config.get(robot_id)
            tiene_carga = estado_global["carga_trabajo_por_robot"].get(robot_id, 0) > 0

            if not config_robot or not config_robot.get("EsOnline") or not tiene_carga:
                robots_a_limpiar.append(robot_id)

        for robot_id in robots_a_limpiar:
            self._liberar_equipos_de_robot(robot_id, "DESASIGNAR_ROBOT_NO_CANDIDATO", estado_global)

        logger.info("ETAPA DE LIMPIZA GLOBAL completada.")

    def ejecutar_balanceo_interno_de_pool(self, pool_id: Optional[int], estado_global: Dict[str, Any]):
        """
        Ejecuta el balanceo para un pool específico, usando solo sus propios recursos.
        """
        pool_nombre = f"PoolId {pool_id}" if pool_id is not None else "Pool General"
        logger.info(f"Iniciando ETAPA DE BALANCEO INTERNO para {pool_nombre}...")

        robots_del_pool = {
            rid: rcfg
            for rid, rcfg in estado_global["mapa_config_robots"].items()
            if rcfg.get("PoolId") == pool_id and rid in estado_global["carga_trabajo_por_robot"]
        }

        if not robots_del_pool:
            logger.info(f"No hay robots candidatos con carga en {pool_nombre}. Saltando.")
            return

        equipos_actualmente_asignados_en_pool = {
            eq for rid in robots_del_pool for eq in estado_global["mapa_asignaciones_dinamicas"].get(rid, [])
        }
        equipos_libres_del_pool = list(
            estado_global["mapa_equipos_validos_por_pool"].get(pool_id, set())
            - equipos_actualmente_asignados_en_pool
            - estado_global["equipos_con_asignacion_fija"]
        )

        necesidades = {}
        excedentes = {}
        for rid, rcfg in robots_del_pool.items():
            tickets = estado_global["carga_trabajo_por_robot"].get(rid, 0)
            equipos_necesarios = self._calcular_equipos_necesarios_para_robot(rid, tickets, rcfg)
            equipos_actuales = len(estado_global["mapa_asignaciones_dinamicas"].get(rid, []))

            diferencia = equipos_necesarios - equipos_actuales
            if diferencia > 0:
                necesidades[rid] = diferencia
            elif diferencia < 0:
                excedentes[rid] = -diferencia

        robots_por_prioridad = sorted(
            necesidades.keys(), key=lambda r: estado_global["mapa_config_robots"][r].get("PrioridadBalanceo", 100)
        )
        for rid in robots_por_prioridad:
            necesidad = necesidades[rid]
            while necesidad > 0 and equipos_libres_del_pool:
                equipo_a_asignar = equipos_libres_del_pool.pop(0)
                if self._realizar_asignacion_db(rid, equipo_a_asignar, "ASIGNAR_DEMANDA_POOL", estado_global):
                    necesidad -= 1

        for rid, cantidad_a_quitar in excedentes.items():
            equipos_del_robot = estado_global["mapa_asignaciones_dinamicas"].get(rid, [])
            for _ in range(min(cantidad_a_quitar, len(equipos_del_robot))):
                equipo_a_quitar = equipos_del_robot.pop()
                self._realizar_desasignacion_db(rid, equipo_a_quitar, "DESASIGNAR_EXCEDENTE_POOL", estado_global)

        logger.info(f"ETAPA DE BALANCEO INTERNO para {pool_nombre} completada.")

    def ejecutar_fase_de_desborde_global(self, estado_global: Dict[str, Any]):
        """
        Asigna equipos del Pool General a robots con necesidades no cubiertas.
        """
        logger.info("Iniciando ETAPA DE DESBORDE Y DEMANDA ADICIONAL GLOBAL...")
        # CAMBIO: Leer configuración dinámica en lugar de self.aislamiento_estricto_pool
        # if self.aislamiento_estricto_pool:
        if self._leer_config_aislamiento():
            logger.info("Aislamiento estricto activado (Configuración BD), no se realizará desborde entre pools.")
            return

        equipos_asignados_globalmente = {
            eq for subl in estado_global["mapa_asignaciones_dinamicas"].values() for eq in subl
        }
        equipos_libres_general = list(
            estado_global["mapa_equipos_validos_por_pool"].get(None, set())
            - equipos_asignados_globalmente
            - estado_global["equipos_con_asignacion_fija"]
        )

        if not equipos_libres_general:
            logger.info("No hay equipos libres en el Pool General para desborde.")
            return

        necesidades_globales = {}
        for rid, rcfg in estado_global["mapa_config_robots"].items():
            if rid in estado_global["carga_trabajo_por_robot"]:
                tickets = estado_global["carga_trabajo_por_robot"].get(rid, 0)
                equipos_necesarios = self._calcular_equipos_necesarios_para_robot(rid, tickets, rcfg)
                equipos_actuales = len(estado_global["mapa_asignaciones_dinamicas"].get(rid, []))
                diferencia = equipos_necesarios - equipos_actuales
                if diferencia > 0:
                    necesidades_globales[rid] = diferencia

        robots_por_prioridad = sorted(
            necesidades_globales.keys(),
            key=lambda r: estado_global["mapa_config_robots"][r].get("PrioridadBalanceo", 100),
        )
        for rid in robots_por_prioridad:
            necesidad = necesidades_globales[rid]
            while necesidad > 0 and equipos_libres_general:
                equipo_a_asignar = equipos_libres_general.pop(0)
                if self._realizar_asignacion_db(rid, equipo_a_asignar, "ASIGNAR_DESBORDE_GLOBAL", estado_global):
                    necesidad -= 1
        logger.info("ETAPA DE DESBORDE Y DEMANDA ADICIONAL GLOBAL completada.")

    def _calcular_equipos_necesarios_para_robot(self, robot_id: int, tickets: int, config: Dict) -> int:
        if tickets <= 0:
            return config.get("MinEquipos", 1) if config.get("EsOnline") else 0
        min_eq = config.get("MinEquipos", 1)
        max_eq = config.get("MaxEquipos", -1)
        ratio = config.get("TicketsPorEquipoAdicional", 10)
        ratio = ratio if ratio > 0 else 1
        needed = min_eq + math.floor(tickets / ratio)
        return min(needed, max_eq) if max_eq != -1 else needed

    def _liberar_equipos_de_robot(self, robot_id: int, motivo: str, estado_global: Dict[str, Any]):
        equipos_a_liberar = list(estado_global["mapa_asignaciones_dinamicas"].get(robot_id, []))
        if not equipos_a_liberar:
            return
        logger.warning(f"RobotId {robot_id} ya no es candidato. Liberando sus {len(equipos_a_liberar)} equipos.")
        for equipo_id in equipos_a_liberar:
            self._realizar_desasignacion_db(robot_id, equipo_id, motivo, estado_global)

    def _realizar_asignacion_db(
        self, robot_id: int, equipo_id: int, motivo: str, estado_global: Dict[str, Any]
    ) -> bool:
        puede_asignar, justificacion = self.cooling_manager.puede_ampliar(robot_id)
        if not puede_asignar:
            logger.debug(f"Asignación omitida por CoolingManager para RobotId {robot_id}. Just: {justificacion}")
            return False
        query = "INSERT INTO dbo.Asignaciones (RobotId, EquipoId, EsProgramado, Reservado, AsignadoPor) VALUES (?, ?, 0, 0, ?)"
        try:
            # 1. Capturar estado ANTES del cambio
            equipos_antes = len(estado_global["mapa_asignaciones_dinamicas"].get(robot_id, []))
            tickets = estado_global["carga_trabajo_por_robot"].get(robot_id, 0)
            pool_id = estado_global["mapa_config_robots"].get(robot_id, {}).get("PoolId")

            # 2. Ejecutar la operación
            self.db_sam.ejecutar_consulta(query, (robot_id, equipo_id, motivo), es_select=False)

            # 3. Actualizar el estado en memoria
            estado_global["mapa_asignaciones_dinamicas"].setdefault(robot_id, []).append(equipo_id)

            # 4. Registrar en histórico y Cooling Manager
            self.historico_client.registrar_decision_balanceo(
                robot_id=robot_id,
                pool_id=pool_id,
                tickets_pendientes=tickets,
                equipos_antes=equipos_antes,
                equipos_despues=equipos_antes + 1,
                accion=motivo,
                justificacion=justificacion,
            )
            self.cooling_manager.registrar_ampliacion(robot_id, tickets, 1)
            return True
        except Exception as e:
            logger.error(f"Error al asignar RobotId {robot_id} a EquipoId {equipo_id}: {e}")
            return False

    def _realizar_desasignacion_db(
        self, robot_id: int, equipo_id: int, motivo: str, estado_global: Dict[str, Any]
    ) -> bool:
        puede_desasignar, justificacion = self.cooling_manager.puede_reducir(
            robot_id, estado_global["carga_trabajo_por_robot"].get(robot_id, 0)
        )
        if not puede_desasignar:
            logger.debug(f"Desasignación omitida por CoolingManager para RobotId {robot_id}. Just: {justificacion}")
            return False
        query = "DELETE FROM dbo.Asignaciones WHERE RobotId = ? AND EquipoId = ? AND (EsProgramado = 0 OR EsProgramado IS NULL) AND (Reservado = 0 OR Reservado IS NULL)"
        try:
            # 1. Capturar estado ANTES del cambio
            equipos_antes = len(estado_global["mapa_asignaciones_dinamicas"].get(robot_id, []))
            tickets = estado_global["carga_trabajo_por_robot"].get(robot_id, 0)
            pool_id = estado_global["mapa_config_robots"].get(robot_id, {}).get("PoolId")

            # 2. Ejecutar la operación
            self.db_sam.ejecutar_consulta(query, (robot_id, equipo_id), es_select=False)

            # 3. Actualizar el estado en memoria
            if (
                robot_id in estado_global["mapa_asignaciones_dinamicas"]
                and equipo_id in estado_global["mapa_asignaciones_dinamicas"][robot_id]
            ):
                estado_global["mapa_asignaciones_dinamicas"][robot_id].remove(equipo_id)

            # 4. Registrar en histórico y Cooling Manager
            self.historico_client.registrar_decision_balanceo(
                robot_id=robot_id,
                pool_id=pool_id,
                tickets_pendientes=tickets,
                equipos_antes=equipos_antes,
                equipos_despues=equipos_antes - 1,
                accion=motivo,
                justificacion=justificacion,
            )
            self.cooling_manager.registrar_reduccion(robot_id, tickets, 1)
            return True
        except Exception as e:
            logger.error(f"Error al desasignar RobotId {robot_id} de EquipoId {equipo_id}: {e}")
            return False

    def _leer_config_aislamiento(self) -> bool:
        """Lee si el aislamiento estricto está activo en BD. Default: True (Conservador)"""
        try:
            res = self.db_sam.ejecutar_consulta(
                "SELECT Valor FROM dbo.ConfiguracionSistema WHERE Clave = 'BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO'",
                es_select=True,
            )
            if not res:
                return True
            return res[0]["Valor"].upper() == "TRUE"
        except Exception as e:
            logger.error(f"Error leyendo config aislamiento: {e}")
            return True
