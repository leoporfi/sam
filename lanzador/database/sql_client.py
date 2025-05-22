# SAM/Lanzador/database/sql_client.py
import time
import pyodbc
import logging
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Any, Optional

from lanzador.clients.aa_client import AutomationAnywhereClient
from lanzador.utils.config import setup_logging, ConfigManager # Importar ConfigManager

logger = setup_logging()

class DatabaseConnector:
    def __init__(self, servidor: str, base_datos: str, usuario: str, contrasena: str, 
                 timeout_conexion: Optional[int] = None): # timeout_conexion es ahora opcional aquí
        
        sql_cfg = ConfigManager.get_sql_server_config() # Cargar toda la config SQL

        self.servidor = servidor
        self.base_datos = base_datos
        self.usuario = usuario
        self.contrasena = contrasena
        
        self.timeout_conexion_inicial = timeout_conexion if timeout_conexion is not None else sql_cfg.get("timeout_conexion_inicial", 30)
        
        # Parámetros de reintento para queries
        self.max_reintentos_query = sql_cfg.get("max_reintentos_query", 3)
        self.delay_reintento_query_base_seg = sql_cfg.get("delay_reintento_query_base_seg", 2)
        self.codigos_sqlstate_reintentables = sql_cfg.get("codigos_sqlstate_reintentables", ["40001", "HYT00", "HYT01", "08S01"])
        
        self._thread_local_conn = threading.local()
        # La conexión se establece en obtener_cursor si no existe para el hilo

    def _get_current_thread_connection(self) -> Optional[pyodbc.Connection]:
        return getattr(self._thread_local_conn, 'connection', None)

    def _set_current_thread_connection(self, conn: Optional[pyodbc.Connection]):
        """Establece la conexión para el hilo actual."""
        self._thread_local_conn.connection = conn

    def conectar_base_datos(self) -> pyodbc.Connection: # Ahora devuelve la conexión
        """Establece una nueva conexión a la base de datos para el hilo actual."""
        # Cerrar conexión existente del hilo si la hay
        existing_conn = self._get_current_thread_connection()
        if existing_conn:
            try:
                existing_conn.close()
                logger.debug(f"Hilo {threading.get_ident()}: Conexión previa cerrada antes de reconectar.")
            except pyodbc.Error as e_close:
                logger.warning(f"Hilo {threading.get_ident()}: Error menor al cerrar conexión previa: {e_close}")
        
        sql_cfg_local = ConfigManager.get_sql_server_config() # Para el driver
        driver = sql_cfg_local.get("driver", "{ODBC Driver 17 for SQL Server}")
        
        connection_string = (
            f"Driver={driver};"
            f"Server={self.servidor};"
            f"Database={self.base_datos};"
            f"UID={self.usuario};"
            f"PWD={self.contrasena};"
            f"Connection Timeout={self.timeout_conexion_inicial};"
        )
        try:
            conn = pyodbc.connect(connection_string, autocommit=False)
            self._set_current_thread_connection(conn)
            logger.info(f"Hilo {threading.get_ident()}: Nueva conexión a BD SAM ({self.base_datos}) establecida.")
            return conn
        except pyodbc.Error as e:
            logger.error(f"Hilo {threading.get_ident()}: Error al conectar a BD SAM ({self.base_datos}): {e}", exc_info=True)
            self._set_current_thread_connection(None)
            raise

    def verificar_conexion(self) -> bool:
        """Verifica la conexión del hilo actual."""
        conn = self._get_current_thread_connection()
        if conn is None:
            logger.debug(f"Hilo {threading.get_ident()}: verificar_conexion - No hay objeto de conexión.")
            return False
        try:
            if getattr(conn, 'closed', False): # Chequeo preliminar si el atributo existe
                 logger.warning(f"Hilo {threading.get_ident()}: verificar_conexion - Conexión marcada como cerrada por el driver.")
                 return False
            with conn.cursor() as cursor: # cursor se cierra automáticamente aquí
                cursor.execute("SELECT 1")
            logger.debug(f"Hilo {threading.get_ident()}: verificar_conexion - Conexión activa.")
            return True
        except pyodbc.Error as e:
            logger.warning(f"Hilo {threading.get_ident()}: verificar_conexion - Conexión inactiva o error ({type(e).__name__}): {e}")
            return False
        except Exception as ex_general:
            logger.error(f"Hilo {threading.get_ident()}: verificar_conexion - Excepción inesperada: {ex_general}", exc_info=True)
            return False

    @contextmanager
    def obtener_cursor(self):
        conn = self._get_current_thread_connection()
        if conn is None or not self.verificar_conexion(): # verificar_conexion ya loguea
            logger.warning(f"Hilo {threading.get_ident()}: Conexión no activa/existente en obtener_cursor. Intentando (re)conectar...")
            try:
                conn = self.conectar_base_datos()
            except Exception as e_reconnect:
                logger.error(f"Fallo crítico al intentar reconectar en obtener_cursor: {e_reconnect}", exc_info=True)
                raise # No podemos continuar sin conexión

        if conn is None: # Si la reconexión falló silenciosamente (no debería si se levanta excepción)
             raise pyodbc.Error(f"Hilo {threading.get_ident()}: No se pudo establecer la conexión a la base de datos.")

        cursor = None
        try:
            cursor = conn.cursor()
            yield cursor
            if not conn.autocommit: # Si no está en autocommit (que es nuestro default)
                conn.commit()
                logger.debug(f"Hilo {threading.get_ident()}: Operación de BD commiteada.")
        except pyodbc.Error as db_err:
            logger.error(f"Hilo {threading.get_ident()}: Error de BD (pyodbc.Error) en bloque 'with obtener_cursor': {db_err}", exc_info=True)
            if conn and not getattr(conn, 'closed', True) and not conn.autocommit:
                try:
                    conn.rollback()
                    logger.info(f"Hilo {threading.get_ident()}: Rollback de BD realizado.")
                except pyodbc.Error as rb_err:
                    logger.error(f"Hilo {threading.get_ident()}: Error durante el rollback de BD: {rb_err}", exc_info=True)
            raise # Relanzar la excepción original para que la lógica de reintento en ejecutar_consulta la vea
        except Exception as e_cursor:
            logger.error(f"Hilo {threading.get_ident()}: Error inesperado con el cursor: {e_cursor}", exc_info=True)
            if conn and not getattr(conn, 'closed', True) and not conn.autocommit:
                try:
                    conn.rollback()
                except Exception as rb_gen_err:
                     logger.error(f"Hilo {threading.get_ident()}: Error durante el rollback (genérico): {rb_gen_err}", exc_info=True)
            raise
        finally:
            if cursor:
                try:
                    cursor.close()
                except pyodbc.Error as cur_close_err: # Puede fallar si la conexión ya está mal
                    logger.debug(f"Hilo {threading.get_ident()}: Error menor al cerrar cursor: {cur_close_err}")

    def ejecutar_consulta(self, query: str, parametros: Optional[tuple] = None, es_select: Optional[bool] = None):
        """
        Ejecuta una consulta con lógica de reintentos para errores específicos de BD.
        """
        if es_select is None:
            query_lower = query.strip().lower()
            es_select = query_lower.startswith("select") or \
                        (query_lower.startswith("exec") and ("obtener" in query_lower or "consultar" in query_lower))
        
        for intento in range(1, self.max_reintentos_query + 1):
            try:
                with self.obtener_cursor() as cursor: # obtener_cursor maneja la conexión y el commit/rollback básico
                    logger.debug(f"Intento {intento}/{self.max_reintentos_query} - Ejecutando query: {query[:150]}... con params: {str(parametros)[:150]}...")
                    if parametros:
                        cursor.execute(query, parametros)
                    else:
                        cursor.execute(query)
                    
                    if es_select:
                        if cursor.description:
                            columnas = [col[0] for col in cursor.description]
                            filas_raw = cursor.fetchall()
                            filas = [dict(zip(columnas, fila)) for fila in filas_raw]
                        else:
                            filas = []
                        logger.debug(f"Consulta SELECT devolvió {len(filas)} filas.")
                        return filas # Éxito, salir del bucle de reintentos
                    else: # DML
                        rowcount = cursor.rowcount
                        logger.debug(f"Consulta DML/EXEC afectó {rowcount} filas.")
                        return rowcount # Éxito, salir del bucle de reintentos
            
            except pyodbc.Error as db_err:
                sql_state = db_err.args[0] if db_err.args else ''
                error_msg_lower = str(db_err).lower()
                
                # Verificar si es un error reintentable por SQLSTATE o mensaje (ej. deadlock)
                es_error_reintentable = sql_state in self.codigos_sqlstate_reintentables or \
                                      "deadlock" in error_msg_lower
                
                if es_error_reintentable:
                    logger.warning(f"Intento {intento}/{self.max_reintentos_query} falló con error de BD REINTENTABLE (SQLSTATE: {sql_state}): {db_err}")
                    if intento < self.max_reintentos_query:
                        # Backoff exponencial
                        sleep_time = self.delay_reintento_query_base_seg * (2 ** (intento - 1))
                        logger.info(f"Esperando {sleep_time}s antes del próximo reintento...")
                        time.sleep(sleep_time)
                        # La conexión podría haberse cerrado; obtener_cursor intentará reconectar en el próximo intento.
                    else:
                        logger.error(f"Máximo de reintentos ({self.max_reintentos_query}) alcanzado para error de BD reintentable. Query: {query[:150]}")
                        raise # Relanzar la última excepción después de agotar reintentos
                else:
                    # Error de BD no reintentable por esta lógica (ej. violación de constraint, sintaxis SQL)
                    # Ya fue logueado por obtener_cursor, pero relanzamos para que el llamador lo sepa.
                    logger.error(f"Error de BD NO REINTENTABLE (SQLSTATE: {sql_state}) durante la ejecución. Query: {query[:150]}. Error: {db_err}")
                    raise # Relanzar la excepción
            except Exception as e_general:
                # Otras excepciones no pyodbc.Error (inesperado)
                logger.error(f"Excepción general inesperada durante la ejecución de query (intento {intento}): {e_general}", exc_info=True)
                # Considerar si estos errores generales deben ser reintentados o no. Por ahora, no.
                raise # Relanzar la excepción
        
        # Si el bucle termina sin return (no debería si la excepción se relanza correctamente),
        # es un estado anómalo.
        logger.critical(f"Lógica de reintentos en ejecutar_consulta finalizó inesperadamente para query: {query[:150]}")
        raise Exception(f"Fallo inesperado en la lógica de reintentos de ejecutar_consulta para query: {query[:150]}")

    def merge_equipos(self, lista_equipos_procesados: List[Dict[str, Any]]):
        if not lista_equipos_procesados:
            logger.info("merge_equipos: Lista de equipos procesados vacía, no se realiza MERGE.")
            return 0

        # Query asumiendo que dbo.Equipos tiene EquipoId (PK, A360 DeviceId), Equipo, UserId (A360 UserId, NOT NULL), UserName, Licencia
        # Y una columna Activo BIT (recomendada)
        query = """
        MERGE dbo.Equipos AS T
        USING (SELECT 
                   CAST(? AS INT) AS EquipoId_S,         -- 1. EquipoId (PK, A360 Device ID)
                   CAST(? AS NVARCHAR(100)) AS Equipo_S,  -- 2. Equipo (Nombre del Device/Host)
                   CAST(? AS INT) AS UserId_S,            -- 3. UserId (A360 User ID) - DEBE SER NOT NULL
                   CAST(? AS NVARCHAR(50)) AS UserName_S, -- 4. UserName (A360 User Name)
                   CAST(? AS NVARCHAR(50)) AS Licencia_S -- 5. Licencia
                   -- CAST(? AS BIT) AS Activo_S          -- 6. Activo_SAM (si la columna existe)
              ) AS S ON T.EquipoId = S.EquipoId_S
        WHEN MATCHED AND (
                T.Equipo <> S.Equipo_S OR
                T.UserId <> S.UserId_S OR -- UserId es NOT NULL, no necesita ISNULL para comparación directa si S.UserId_S tampoco es NULL
                ISNULL(T.UserName, N'') <> ISNULL(S.UserName_S, N'') OR
                ISNULL(T.Licencia, N'') <> ISNULL(S.Licencia_S, N'')
                -- OR ISNULL(T.Activo, 0) <> S.Activo_S -- Si existe T.Activo
               ) THEN
            UPDATE SET 
                T.Equipo = S.Equipo_S,
                T.UserId = S.UserId_S,
                T.UserName = S.UserName_S,
                T.Licencia = S.Licencia_S
                -- , T.Activo = S.Activo_S -- Si existe T.Activo
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (EquipoId, Equipo, UserId, UserName, Licencia) -- Añadir Activo si existe
            VALUES (S.EquipoId_S, S.Equipo_S, S.UserId_S, S.UserName_S, S.Licencia_S); -- Añadir S.Activo_S
        """
        
        datos_para_merge = []
        for eq_data in lista_equipos_procesados:
            if eq_data.get("EquipoId") is None:
                logger.warning(f"MERGE EQUIPOS: Registro omitido por falta de EquipoId (A360 DeviceId): {eq_data}")
                continue
            # Dado que Equipos.UserId es NOT NULL en tu BD SAM:
            if eq_data.get("UserId") is None:
                logger.warning(f"MERGE EQUIPOS: Registro omitido para EquipoId {eq_data.get('EquipoId')} por falta de UserId (A360 UserID): {eq_data}")
                continue
            
            params_tupla = (
                eq_data.get("EquipoId"),
                eq_data.get("Equipo"),
                eq_data.get("UserId"), # Debe ser un INT no nulo
                eq_data.get("UserName"),
                eq_data.get("Licencia", "NO_ASIGNADA"),
                # eq_data.get("Activo_SAM", 1) # Descomentar y ajustar si añades la columna Activo
            )
            datos_para_merge.append(params_tupla)

        if not datos_para_merge:
            logger.info("merge_equipos: No hay datos válidos para MERGE después de la preparación y validación de UserId.")
            return 0
        
        total_filas_afectadas = 0
        try:
            logger.info(f"Iniciando MERGE para {len(datos_para_merge)} registros en dbo.Equipos...")
            for params_eq in datos_para_merge:
                filas_iter = self.ejecutar_consulta(query, params_eq, es_select=False)
                total_filas_afectadas += filas_iter if isinstance(filas_iter, int) and filas_iter != -1 else 1
            logger.info(f"merge_equipos completado. Filas afectadas/procesadas aprox: {total_filas_afectadas}")
            return total_filas_afectadas
        except Exception as e:
            logger.error(f"Error durante merge_equipos: {e}", exc_info=True)
            raise

    def merge_robots(self, lista_robots_api: List[Dict[str, Any]]): # Nombre sin _sam
        """
        Actualiza (MERGE) la tabla dbo.Robots en SAM con datos de la API.
        - RobotId (FileID de A360) es la clave de unión.
        - Robot (nombre) y Descripcion se actualizan si cambian en la API.
        - EsOnline y Activo NO se actualizan si el robot ya existe; se mantienen los valores de la BD.
        - Para robots NUEVOS, EsOnline y Activo se insertan con valores por defecto.
        - Parametros se inserta con NULL para nuevos robots y no se actualiza para existentes.
        
        Campos esperados en cada dict de lista_robots_api:
        "RobotId", "Robot" (nombre), "Descripcion".
        """
        if not lista_robots_api:
            logger.info("merge_robots: Lista de robots de API vacía, no se realiza MERGE.")
            return 0

        DEFAULT_ESONLINE_NUEVO_ROBOT = 0 # False
        DEFAULT_ACTIVO_NUEVO_ROBOT = 1   # True

        query = """
        MERGE dbo.Robots AS T
        USING (SELECT 
                CAST(? AS INT) AS RobotId_S,          -- 1. RobotId (PK, A360 FileID)
                CAST(? AS NVARCHAR(100)) AS Robot_S,   -- 2. Robot (Nombre desde API)
                CAST(? AS NVARCHAR(4000)) AS Descripcion_S, -- 3. Descripcion desde API
                CAST(? AS BIT) AS EsOnline_Default_S,  -- 4. Default para EsOnline (SOLO para INSERT)
                CAST(? AS BIT) AS Activo_Default_S     -- 5. Default para Activo (SOLO para INSERT)
            ) AS S ON T.RobotId = S.RobotId_S      -- Clave de unión: RobotId (A360 FileID)
        WHEN MATCHED AND (
                -- Solo actualizar si el nombre o la descripción han cambiado.
                -- NO se compara T.EsOnline ni T.Activo aquí.
                T.Robot <> S.Robot_S OR
                ISNULL(T.Descripcion, N'') <> ISNULL(S.Descripcion_S, N'') 
            ) THEN
            UPDATE SET 
                T.Robot = S.Robot_S,         -- Actualizar nombre del robot
                T.Descripcion = S.Descripcion_S -- Actualizar descripción
                -- NO SE ACTUALIZAN T.EsOnline NI T.Activo. Se mantienen los valores existentes en la BD.
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (RobotId, Robot, Descripcion, EsOnline, Activo, Parametros) 
            VALUES (S.RobotId_S, S.Robot_S, S.Descripcion_S, 
                    S.EsOnline_Default_S, -- Usar el default para EsOnline para nuevos robots
                    S.Activo_Default_S,   -- Usar el default para Activo para nuevos robots
                    NULL);                -- Parametros se inserta con NULL para nuevos robots
        """
        
        datos_para_merge = []
        for bot_data_api in lista_robots_api:
            if bot_data_api.get("RobotId") is None:
                logger.warning(f"MERGE ROBOTS: Registro omitido por falta de RobotId (A360 FileID): {bot_data_api}")
                continue
            
            params_tupla = (
                bot_data_api.get("RobotId"),
                bot_data_api.get("Robot"),
                bot_data_api.get("Descripcion"),
                # Estos dos siguientes valores solo se usan en la cláusula INSERT del MERGE
                # Si quieres que los defaults vengan de la llamada, tendrías que pasarlos en bot_data_api
                # con claves como "EsOnline_SAM_default", "Activo_SAM_default"
                DEFAULT_ESONLINE_NUEVO_ROBOT, 
                DEFAULT_ACTIVO_NUEVO_ROBOT
            )
            datos_para_merge.append(params_tupla)
        
        if not datos_para_merge:
            logger.info("merge_robots: No hay datos válidos para MERGE después de la preparación.")
            return 0

        total_filas_afectadas = 0
        try:
            logger.info(f"Iniciando MERGE para {len(datos_para_merge)} registros en dbo.Robots...")
            for params_bot in datos_para_merge:
                filas_iter = self.ejecutar_consulta(query, params_bot, es_select=False)
                total_filas_afectadas += filas_iter if isinstance(filas_iter, int) and filas_iter != -1 else 1
            logger.info(f"merge_robots completado. Filas afectadas/procesadas aprox: {total_filas_afectadas}")
            return total_filas_afectadas
        except Exception as e:
            logger.error(f"Error durante merge_robots: {e}", exc_info=True)
        raise

    def obtener_robots_ejecutables(self) -> List[Dict[str, Any]]: # Especificar tipo de retorno
        try:
            query = "EXEC dbo.ObtenerRobotsEjecutables"
            return self.ejecutar_consulta(query, es_select=True) or [] # Asegurar que devuelva lista
        except Exception as e:
            logger.error(f"Error al obtener robots ejecutables: {e}", exc_info=True)
            return []

    def obtener_ejecuciones_en_curso(self) -> List[Dict[str, Any]]:
        try:
            query = (
                "SELECT DeploymentId, RobotId, EquipoId, UserId FROM dbo.Ejecuciones "
                "WHERE Estado NOT IN ('COMPLETED', 'RUN_COMPLETED', 'RUN_FAILED', 'RUN_ABORTED', 'DEPLOY_FAILED', 'UNKNOWN') "
                "AND DATEDIFF(SECOND, FechaInicio, GETDATE()) > 30;" 
            )
            return self.ejecutar_consulta(query, es_select=True) or [] # Asegurar que devuelva lista
        except Exception as e:
            logger.error(f"Error al obtener ejecuciones en curso: {e}", exc_info=True)
            return []

    def insertar_registro_ejecucion(self, id_despliegue: str, db_robot_id: int, db_equipo_id: int, a360_user_id: int, marca_tiempo_programada: Optional[Any], estado: str):
        if id_despliegue is None:
            logger.error(f"Intento de insertar ejecución con DeploymentId NULO para RobotID(SAM): {db_robot_id}, EquipoID(SAM): {db_equipo_id}. Operación abortada.")
            return

        hora_db: Optional[datetime.time] = None
        if marca_tiempo_programada:
            if isinstance(marca_tiempo_programada, str):
                try:
                    hora_db = datetime.strptime(marca_tiempo_programada, "%H:%M:%S").time()
                except ValueError:
                    try: 
                        hora_db = datetime.strptime(marca_tiempo_programada, "%H:%M:%S.%f").time()
                    except ValueError:
                        logger.warning(f"Formato de marca_tiempo_programada '{marca_tiempo_programada}' no reconocido. Se guardará Hora como NULL.")
            elif isinstance(marca_tiempo_programada, datetime.time):
                hora_db = marca_tiempo_programada
            elif isinstance(marca_tiempo_programada, datetime): 
                hora_db = marca_tiempo_programada.time()
            else:
                 logger.warning(f"Tipo de marca_tiempo_programada '{type(marca_tiempo_programada)}' no esperado. Se guardará Hora como NULL.")
        try:
            query = """
                INSERT INTO dbo.Ejecuciones 
                (DeploymentId, RobotId, EquipoId, UserId, Hora, Estado, FechaInicio) 
                VALUES (?, ?, ?, ?, ?, ?, GETDATE())
            """
            # UserId en tu tabla Ejecuciones es nchar(10) NULL, pero a360_user_id es int.
            # Convertir a string para la inserción si la columna es nchar.
            # Viendo SAM.sql, Ejecuciones.UserId es nchar(10), así que castear.
            params = (id_despliegue, db_robot_id, db_equipo_id, str(a360_user_id) if a360_user_id is not None else None, hora_db, estado)
            self.ejecutar_consulta(query, params, es_select=False)
            logger.info(f"Registro de ejecución insertado para DeploymentId: {id_despliegue}")
        except Exception as e:
            logger.error(f"Error al insertar ejecución para DeploymentId {id_despliegue}: {e}", exc_info=True)
            # Considera si relanzar la excepción

    def lanzar_robots(self, robots_a_ejecutar: List[Dict[str, Any]], aa_client: AutomationAnywhereClient, botInput_plantilla: Optional[dict] = None) -> List[Dict[str, Any]]:
        robots_fallidos_detalle = []
        for robot_info in robots_a_ejecutar:
            db_robot_id = robot_info.get("RobotId")
            db_equipo_id = robot_info.get("EquipoId")
            a360_user_id = robot_info.get("UserId") 
            hora_programada_obj = robot_info.get("Hora") # Esto debería ser un objeto time o None

            if not all([db_robot_id is not None, db_equipo_id is not None, a360_user_id is not None]):
                logger.error(f"Datos insuficientes para lanzar robot (RobotId, EquipoId o UserId faltantes), se omite: {robot_info}")
                robots_fallidos_detalle.append({
                    "robot_id": db_robot_id, "equipo_id": db_equipo_id, "user_id": a360_user_id,
                    "error": "Datos de Robot/Equipo/Usuario incompletos desde la BD."})
                continue

            a360_deployment_id = None
            error_lanzamiento = None
            try:
                a360_deployment_id = aa_client.desplegar_bot(
                    file_id=db_robot_id, run_as_user_ids=[a360_user_id], bot_input=botInput_plantilla)
                if a360_deployment_id:
                    self.insertar_registro_ejecucion(
                        a360_deployment_id, db_robot_id, db_equipo_id, a360_user_id, 
                        hora_programada_obj, "RUNNING") # "PENDING_EXECUTION")
                else:
                    error_lanzamiento = "Fallo en API de despliegue (no se obtuvo DeploymentId)."
                    logger.warning(f"{error_lanzamiento} para RobotID(SAM):{db_robot_id}, UserID(A360):{a360_user_id}.")
            except Exception as e:
                error_lanzamiento = str(e)
                logger.error(f"Excepción al procesar/lanzar RobotID(SAM):{db_robot_id}, UserID(A360):{a360_user_id}: {e}", exc_info=True)
            if error_lanzamiento:
                 robots_fallidos_detalle.append({
                    "robot_id": db_robot_id, "equipo_id": db_equipo_id, "user_id": a360_user_id,
                    "error": error_lanzamiento })
        return robots_fallidos_detalle
    
    def generar_mensaje_notificacion(self, robots_fallidos_con_detalle: list):
        if not robots_fallidos_con_detalle:
            return "No se reportaron robots con fallos en el último ciclo de despliegue."

        mensaje_final = "Resumen de robots con fallos en el despliegue y/o registro:\n\n"
        for i, fallo_info in enumerate(robots_fallidos_con_detalle):
            db_robot_id_lanzador = fallo_info.get("robot_id")
            db_equipo_id_lanzador = fallo_info.get("equipo_id")
            a360_user_id_lanzador = fallo_info.get("user_id")
            error_reportado = fallo_info.get("error", "Error no especificado.")

            nombre_robot_str = f"Robot SAM ID: {db_robot_id_lanzador if db_robot_id_lanzador is not None else 'Desconocido'}"
            nombre_equipo_str = f"Equipo SAM ID: {db_equipo_id_lanzador if db_equipo_id_lanzador is not None else 'Desconocido'}"
            a360_username_str = f"Usuario A360 ID: {a360_user_id_lanzador if a360_user_id_lanzador is not None else 'Desconocido'}"
            try:
                if db_robot_id_lanzador is not None:
                    query_robot = "SELECT Robot FROM dbo.Robots WHERE RobotId = ?"
                    resultado_robot = self.ejecutar_consulta(query_robot, (db_robot_id_lanzador,), es_select=True)
                    if resultado_robot and resultado_robot[0] and resultado_robot[0].get("Robot"):
                        nombre_robot_str = resultado_robot[0]["Robot"]
                
                if db_equipo_id_lanzador is not None: # Usar el EquipoId (PK de dbo.Equipos) para buscar
                    query_equipo = "SELECT Equipo, UserName, UserId FROM dbo.Equipos WHERE EquipoId = ?"
                    resultado_equipo = self.ejecutar_consulta(query_equipo, (db_equipo_id_lanzador,), es_select=True)
                    if resultado_equipo and resultado_equipo[0]:
                        nombre_equipo_desc = resultado_equipo[0].get("Equipo")
                        username_a360_db = resultado_equipo[0].get("UserName")
                        userid_a360_db_check = resultado_equipo[0].get("UserId") # Para verificar
                        
                        nombre_equipo_str = f"{nombre_equipo_desc} (ID: {db_equipo_id_lanzador})"
                        if username_a360_db: a360_username_str = username_a360_db
                        
                        # Si el UserID de A360 que teníamos del lanzamiento no coincide con el de la tabla Equipos para ese EquipoId
                        if userid_a360_db_check != a360_user_id_lanzador and a360_user_id_lanzador is not None:
                             logger.warning(f"Discrepancia de UserId para EquipoId {db_equipo_id_lanzador}: Lanzado con {a360_user_id_lanzador}, BD tiene {userid_a360_db_check}")
                        # Actualizar a360_user_id_lanzador si no lo teníamos y la BD sí
                        elif a360_user_id_lanzador is None and userid_a360_db_check is not None:
                            a360_user_id_lanzador = userid_a360_db_check
                            a360_username_str = f"Usuario A360 ID: {a360_user_id_lanzador}" # Actualizar también el string
                            if username_a360_db: a360_username_str = username_a360_db


                elif a360_user_id_lanzador is not None: # Fallback si no tenemos db_equipo_id_lanzador pero sí el UserId de A360
                    query_equipo_usr = "SELECT Equipo, UserName, EquipoId FROM dbo.Equipos WHERE UserId = ?"
                    resultado_equipo_usr = self.ejecutar_consulta(query_equipo_usr, (a360_user_id_lanzador,), es_select=True)
                    if resultado_equipo_usr and resultado_equipo_usr[0]:
                        nombre_equipo_desc = resultado_equipo_usr[0].get("Equipo")
                        username_a360_db = resultado_equipo_usr[0].get("UserName")
                        # db_equipo_id_obtenido = resultado_equipo_usr[0].get("EquipoId") # Podríamos obtener el EquipoId de SAM aquí
                        if username_a360_db: a360_username_str = username_a360_db
                        nombre_equipo_str = f"{nombre_equipo_desc} (Usuario A360 ID: {a360_user_id_lanzador})"
                
                mensaje_final += (f"{i+1}. Robot: '{nombre_robot_str}'\n"
                                  f"   Equipo SAM: '{nombre_equipo_str}'\n"
                                  f"   Usuario Ejecución A360: '{a360_username_str}' (A360 UserID: {a360_user_id_lanzador})\n"
                                  f"   Error Reportado: {error_reportado}\n\n")
            except Exception as e_detalle:
                logger.error(f"Error al construir detalles de notificación para RobotID(SAM): {db_robot_id_lanzador}, EquipoID(SAM): {db_equipo_id_lanzador}, UserID(A360): {a360_user_id_lanzador}: {e_detalle}", exc_info=True)
                mensaje_final += (f"{i+1}. Robot SAM ID: {db_robot_id_lanzador}\n"
                                  f"   Equipo SAM ID: {db_equipo_id_lanzador}\n"
                                  f"   Usuario Ejecución A360 ID: {a360_user_id_lanzador}\n"
                                  f"   Error Reportado: {error_reportado} (Error adicional al obtener nombres: {e_detalle})\n\n")
        mensaje_final += "\nPor favor, revise los logs del Lanzador SAM para más detalles y el estado de los usuarios/dispositivos en A360."
        return mensaje_final
  
    def ejecutar_consulta_multiple(self, query: str, lista_de_parametros: List[tuple]) -> int:
        """
        Ejecuta una consulta DML (INSERT, UPDATE, DELETE) con múltiples conjuntos de parámetros
        utilizando cursor.executemany().
        Devuelve el número total de filas afectadas si es posible, o un conteo de operaciones.
        """
        if not lista_de_parametros:
            logger.info("ejecutar_consulta_multiple: La lista de parámetros está vacía. No se ejecuta nada.")
            return 0

        with self.obtener_cursor() as cursor:
            logger.debug(f"Ejecutando consulta múltiple (executemany): {query[:150]}... con {len(lista_de_parametros)} conjuntos de parámetros.")
            try:
                # Habilitar fast_executemany si el driver lo soporta y es beneficioso
                # (principalmente para SQL Server con ODBC Driver 17+)
                if self.servidor and "SQL Server" in pyodbc.drivers() and "{ODBC Driver 17 for SQL Server}" in pyodbc.drivers(): # Heurística
                    # O si sabes que tu driver es el correcto:
                    # driver_name = self.conexion.getinfo(pyodbc.SQL_DRIVER_NAME)
                    # if 'msodbcsql17.dll' in driver_name.lower(): # Ejemplo
                    try:
                        cursor.fast_executemany = True
                        logger.debug("fast_executemany habilitado para la consulta múltiple.")
                    except AttributeError: # No todos los cursores/drivers lo soportan
                        logger.debug("fast_executemany no es soportado por el cursor/driver actual.")
                
                cursor.executemany(query, lista_de_parametros)
                rowcount = cursor.rowcount 
                # El rowcount para executemany puede ser -1 (indica éxito pero no conteo)
                # o el número total de filas afectadas, dependiendo del driver y la operación.
                if rowcount == -1:
                    logger.debug(f"Consulta múltiple (executemany) ejecutada. Driver no reportó rowcount detallado (devolvió -1). Asumiendo {len(lista_de_parametros)} operaciones.")
                    return len(lista_de_parametros) # Devuelve el número de operaciones enviadas
                else:
                    logger.debug(f"Consulta múltiple (executemany) afectó {rowcount} filas.")
                    return rowcount
            except pyodbc.Error as e:
                # Loguear el error específico de executemany
                logger.error(f"Error durante executemany con query: {query[:150]}. Error: {e}", exc_info=True)
                # La excepción ya será capturada y relanzada por el context manager de obtener_cursor
                raise 
            except Exception as ex: # Otras excepciones
                logger.error(f"Error inesperado durante executemany con query: {query[:150]}. Error: {ex}", exc_info=True)
                raise

    def actualizar_ejecucion_desde_callback(self, deployment_id: str, estado_callback: str, callback_payload_str: str) -> bool:
        """
        Actualiza un registro en la tabla Ejecuciones basado en un callback de A360.
        Intenta parsear la fecha de fin si el estado es terminal.
        """
        if not deployment_id or not estado_callback:
            logger.error("actualizar_ejecucion_desde_callback: Falta deployment_id o estado_callback.")
            return False

        # Estados terminales donde se debería registrar FechaFin
        ESTADOS_TERMINALES_CALLBACK = ["RUN_COMPLETED", "RUN_FAILED", "RUN_ABORTED", "RUN_TIMED_OUT"]
        
        fecha_fin_para_db = None
        if estado_callback.upper() in ESTADOS_TERMINALES_CALLBACK:
            fecha_fin_para_db = datetime.now() # Usar la hora actual del servidor de callback como FechaFin

        try:
            # Tu tabla Ejecuciones tiene: DeploymentId, Estado, FechaFin, CallbackInfo
            # FechaInicio ya debería estar.
            query = """
            UPDATE dbo.Ejecuciones
            SET 
                Estado = ?,
                FechaFin = CASE WHEN ? IS NOT NULL THEN ? ELSE FechaFin END, -- Solo actualiza FechaFin si se provee
                CallbackInfo = ?,
                FechaActualizacion = GETDATE() -- Nueva columna recomendada para tracking
            WHERE DeploymentId = ?;
            """
            
            params = (estado_callback, fecha_fin_para_db, fecha_fin_para_db, callback_payload_str, deployment_id)
            
            rowcount = self.ejecutar_consulta(query, params, es_select=False)
            
            if rowcount is not None and rowcount > 0:
                logger.info(f"Callback recibido y procesado para DeploymentId: {deployment_id}. Nuevo Estado: {estado_callback}. Filas afectadas: {rowcount}")
                return True
            elif rowcount == 0:
                logger.warning(f"Callback recibido para DeploymentId: {deployment_id} (Estado: {estado_callback}), pero no se encontró o actualizó ningún registro. ¿Ya estaba en estado terminal o el ID es incorrecto?")
                return False
            else: # rowcount es None o -1 (éxito pero sin conteo claro)
                logger.info(f"Callback recibido y procesado para DeploymentId: {deployment_id}. Nuevo Estado: {estado_callback}. (Rowcount no definitivo)")
                return True
                
        except Exception as e:
            logger.error(f"Error al actualizar ejecución desde callback para DeploymentId {deployment_id}: {e}", exc_info=True)
            return False

    def cerrar_conexion_hilo_actual(self):
        conn = self._get_current_thread_connection()
        if conn:
            try:
                conn.close()
                logger.info(f"Hilo {threading.get_ident()}: Conexión a BD SAM ({self.base_datos}) cerrada.")
            except pyodbc.Error as e:
                logger.error(f"Hilo {threading.get_ident()}: Error al cerrar conexión a BD SAM ({self.base_datos}): {e}", exc_info=True)
            finally:
                self._set_current_thread_connection(None)

    def cerrar_conexion(self): 
        self.cerrar_conexion_hilo_actual()



