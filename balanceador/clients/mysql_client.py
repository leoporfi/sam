# SAM/Balanceador/clients/mysql_client.py

import csv
import io
import paramiko
import socket # Asegúrate de que esté importado si se usa explícitamente en manejo de excepciones
import logging
import time
from pathlib import Path
import sys
from typing import Dict, List, Any, Optional

# --- Configuración de Path ---
# Esto permite que el módulo common y otros del proyecto SAM sean importables
# asumiendo que el script que ejecuta esto (o el punto de entrada del servicio)
# ha añadido SAM_PROJECT_ROOT a sys.path.
CLIENTS_DIR = Path(__file__).resolve().parent
BALANCEADOR_MODULE_ROOT = CLIENTS_DIR.parent # SAM/Balanceador/
SAM_PROJECT_ROOT = BALANCEADOR_MODULE_ROOT.parent # SAM/

# Si SAM_PROJECT_ROOT no está en sys.path, añádelo.
# Esto es útil si el cliente se prueba o se usa de forma más aislada,
# aunque el run_balanceador.py ya debería manejarlo.
if str(SAM_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SAM_PROJECT_ROOT))
# --- Fin Configuración de Path ---

# Ya no se importa nada de balanceador.utils.config

# Configurar el nivel de log para Paramiko para reducir el ruido
logging.getLogger('paramiko').setLevel(logging.WARNING) 

class MySQLSSHClient:
    def __init__(self,
                 config_ssh_mysql: Dict[str, Any],
                 mapa_robots: Dict[str, str],
                 logger_instance: Optional[logging.Logger] = None):
        
        if logger_instance:
            self.logger = logger_instance
        else:
            # Obtener un logger estándar. Su configuración (handlers, level, format)
            # provendrá de la configuración global de logging de la aplicación
            # (hecha en service/main.py del Balanceador usando setup_logging común).
            self.logger = logging.getLogger(f"SAM.{BALANCEADOR_MODULE_ROOT.name}.clients.{Path(__file__).stem}")
            # Opcional: Si se quiere evitar que loguee si no hay configuración global:
            # self.logger.addHandler(logging.NullHandler())

        self.logger.debug(f"MySQLSSHClient inicializado para host SSH: {config_ssh_mysql.get('host_ssh')}")
        # Configuración SSH
        self.host_ssh = config_ssh_mysql.get("host_ssh")
        self.puerto_ssh = int(config_ssh_mysql.get("puerto_ssh", 22))
        self.usuario_ssh = config_ssh_mysql.get("usuario_ssh")
        self.password_ssh = config_ssh_mysql.get("pass_ssh")

        # Configuración MySQL (a través del túnel SSH)
        self.db_host_mysql = config_ssh_mysql.get("db_host_mysql", "127.0.0.1") # Suele ser localhost desde la perspectiva del server SSH
        self.db_port_mysql = int(config_ssh_mysql.get("db_port_mysql", 3306))
        self.usuario_mysql = config_ssh_mysql.get("usuario_mysql") # Para el comando mysql
        self.password_mysql = config_ssh_mysql.get("pass_mysql") # Para el comando mysql, si no se usa .my.cnf

        # Parámetros de reintento (obtenidos de config_ssh_mysql)
        self.max_reintentos_ssh = int(config_ssh_mysql.get("max_reintentos_ssh_connect", 3))
        self.delay_reintento_ssh_seg = int(config_ssh_mysql.get("delay_reintento_ssh_seg", 5))
        self.max_reintentos_mysql = int(config_ssh_mysql.get("max_reintentos_mysql_query", 2))
        self.delay_reintento_mysql_seg = int(config_ssh_mysql.get("delay_reintento_mysql_query_seg", 3))

        self.cliente_ssh: Optional[paramiko.SSHClient] = None
        self.mapa_robots = mapa_robots

        # Validación de configuración esencial
        required_ssh = ["host_ssh", "usuario_ssh", "pass_ssh"]
        required_mysql = ["usuario_mysql", "pass_mysql"] # Asumiendo que no siempre se usa .my.cnf
        missing_ssh = [k for k in required_ssh if not self.host_ssh or not self.usuario_ssh or not self.password_ssh] # Simplificado
        missing_mysql = [k for k in required_mysql if not self.usuario_mysql or not self.password_mysql]

        if missing_ssh:
            self.logger.critical(f"Configuración SSH incompleta para MySQLSSHClient. Faltan: {missing_ssh}")
            raise ValueError(f"Configuración SSH incompleta. Faltan: {missing_ssh}")
        # La validación de mysql_user/pass puede ser opcional si se confía en .my.cnf en el servidor remoto.

    def conectar_ssh(self):
        if self.cliente_ssh:
            try:
                # Verificar si la conexión SSH sigue activa
                transport = self.cliente_ssh.get_transport()
                if transport and transport.is_active():
                    # Opcional: enviar un comando no-op para verificar realmente
                    self.cliente_ssh.exec_command('echo -n', timeout=10)
                    self.logger.info(f"Conexión SSH a {self.host_ssh} ya estaba activa y verificada.")
                    return
                else:
                    self.logger.warning(f"Transporte SSH a {self.host_ssh} no activo. Intentando reconectar.")
                    self.cerrar_ssh() # Cierra y limpia self.cliente_ssh
            except Exception as e_check:
                self.logger.warning(f"Conexión SSH existente a {self.host_ssh} falló la verificación ({type(e_check).__name__}: {e_check}). Intentando reconectar.")
                self.cerrar_ssh()

        for intento in range(1, self.max_reintentos_ssh + 1):
            try:
                self.logger.info(f"Intento SSH {intento}/{self.max_reintentos_ssh} para conectar a {self.host_ssh}:{self.puerto_ssh} con usuario {self.usuario_ssh}")
                self.cliente_ssh = paramiko.SSHClient()
                self.cliente_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.cliente_ssh.connect(
                    hostname=self.host_ssh,
                    port=self.puerto_ssh,
                    username=self.usuario_ssh,
                    password=self.password_ssh,
                    timeout=20,  # Timeout para la conexión TCP
                    banner_timeout=30,  # Timeout para el banner SSH
                    auth_timeout=30 # Timeout para la autenticación
                )
                self.logger.info(f"Conexión SSH establecida con éxito a {self.host_ssh}")
                return
            except paramiko.AuthenticationException as e_auth:
                self.logger.error(f"Error de autenticación SSH en intento {intento} a {self.host_ssh}: {e_auth}")
                self.cliente_ssh = None # Asegurar que esté limpio
                raise  # No reintentar en fallo de autenticación, es un error de configuración
            except (paramiko.SSHException, socket.timeout, socket.error, EOFError) as e_ssh:
                self.logger.warning(f"Error de conexión/socket SSH en intento {intento} a {self.host_ssh} ({type(e_ssh).__name__}): {e_ssh}")
                self.cliente_ssh = None # Asegurar que esté limpio
                if intento < self.max_reintentos_ssh:
                    time.sleep(self.delay_reintento_ssh_seg * intento)  # Backoff incremental
                else:
                    self.logger.error(f"Máximos reintentos SSH ({self.max_reintentos_ssh}) alcanzados para {self.host_ssh}.")
                    raise  # Relanzar la última excepción de conexión
        
        # Si el bucle termina y no se conectó (no debería pasar si raise se ejecuta)
        if not self.cliente_ssh:
             raise ConnectionError(f"No se pudo establecer conexión SSH a {self.host_ssh} después de {self.max_reintentos_ssh} intentos.")

    def ejecutar_consulta_mysql(self, base_datos: str, consulta: str) -> List[Dict[str, Any]]:
        # El comando que usa --defaults-file=~/.my.cnf es preferible si está configurado
        # en el servidor remoto para el usuario SSH, ya que evita exponer credenciales MySQL.
        comando = f"mysql --defaults-file=~/.my.cnf -h {self.db_host_mysql} -P {self.db_port_mysql} -D {base_datos} -B -e \"{consulta}\""
        # Alternativa si .my.cnf no es viable (menos segura, expone pass en el comando):
        # comando = f"mysql -h {self.db_host_mysql} -P {self.db_port_mysql} -u {self.usuario_mysql} -p'{self.password_mysql}' -D {base_datos} -B -e \"{consulta}\""

        for intento_mysql in range(1, self.max_reintentos_mysql + 1):
            try:
                # Asegurar que la conexión SSH esté activa antes de cada intento de query MySQL
                self.conectar_ssh() # conectar_ssh() ya tiene su propia lógica de reintentos y verificación
                if not self.cliente_ssh: # Si conectar_ssh falló críticamente
                    raise ConnectionError("Cliente SSH no disponible después de intentar conectar.")

                self.logger.debug(f"Ejecutando MySQL (intento {intento_mysql}/{self.max_reintentos_mysql}) en BD '{base_datos}': {consulta[:100]}...")
                stdin, stdout, stderr = self.cliente_ssh.exec_command(comando, timeout=30) # Timeout para la ejecución del comando
                
                salida_bytes = stdout.read()
                error_bytes = stderr.read()
                exit_status = stdout.channel.recv_exit_status()

                salida_str = salida_bytes.decode("utf-8", errors="replace")
                error_str = error_bytes.decode("utf-8", errors="replace")

                if exit_status != 0:
                    self.logger.error(f"Error en comando MySQL (status {exit_status}, intento {intento_mysql}). Stderr: {error_str.strip()}. Stdout: {salida_str.strip()[:200]}")
                    # Lógica de reintento para errores específicos de MySQL "gone away"
                    if "2006" in error_str or "2013" in error_str or "gone away" in error_str.lower() or "lost connection" in error_str.lower():
                        if intento_mysql < self.max_reintentos_mysql:
                            self.logger.warning(f"Error MySQL reintentable detectado (intento {intento_mysql}). Esperando {self.delay_reintento_mysql_seg}s y forzando reconexión SSH...")
                            time.sleep(self.delay_reintento_mysql_seg)
                            self.cerrar_ssh() # Forzar reconexión SSH completa en el próximo intento
                            continue # Reintentar el ciclo MySQL
                        else:
                            self.logger.error("Máximos reintentos MySQL alcanzados para error reintentable.")
                            raise Exception(f"Máximos reintentos MySQL. Último error: {error_str.strip()}")
                    else: # Error MySQL no considerado reintentable por esta lógica
                        raise Exception(f"Error no reintentable en comando MySQL (status {exit_status}): {error_str.strip()}")
                
                self.logger.info(f"Comando MySQL ejecutado con éxito (intento {intento_mysql}).")
                return self._parsear_salida_tsv(salida_str)

            except (paramiko.SSHException, socket.timeout, socket.error, EOFError) as e_ssh_exec:
                self.logger.warning(f"Error de transporte SSH durante ejecución de query MySQL (intento {intento_mysql}, {type(e_ssh_exec).__name__}): {e_ssh_exec}")
                self.cerrar_ssh() # Forzar cierre y reconexión en el siguiente intento de conectar_ssh()
                if intento_mysql < self.max_reintentos_mysql:
                    time.sleep(self.delay_reintento_mysql_seg)
                    # No es necesario 'continue' aquí si conectar_ssh() se llama al inicio del bucle 'try'
                else:
                    self.logger.error("Máximos reintentos tras error SSH durante ejecución de query MySQL.")
                    raise # Relanzar la excepción SSH
            except ConnectionError as e_conn: # Capturar ConnectionError de conectar_ssh si falla críticamente
                 self.logger.error(f"Fallo crítico de conexión SSH impidió ejecutar query MySQL: {e_conn}")
                 raise # Relanzar, no hay más que hacer aquí.
            except Exception as e_general:
                self.logger.error(f"Error general inesperado ejecutando query MySQL (intento {intento_mysql}): {e_general}", exc_info=True)
                raise # Relanzar para que no se considere un éxito silencioso

        # Si el bucle termina sin un return exitoso o un raise (no debería ocurrir con la lógica actual)
        self.logger.critical(f"Se salió del bucle de reintentos de MySQL sin éxito ni excepción clara para la consulta: {consulta[:100]}")
        raise Exception(f"No se pudo ejecutar la consulta MySQL en '{base_datos}' después de {self.max_reintentos_mysql} intentos.")

    def _parsear_salida_tsv(self, salida_tsv: str) -> List[Dict[str, Any]]:
        if not salida_tsv.strip():
            self.logger.debug("Parsear TSV: Salida TSV vacía, devolviendo lista vacía.")
            return []

        resultados_parseados: List[Dict[str, Any]] = []
        try:
            # Usar io.StringIO para tratar el string como un archivo
            f = io.StringIO(salida_tsv)
            lector_csv = csv.DictReader(f, delimiter='\t')
            for fila_dict in lector_csv:
                # Opcional: Limpiar espacios extra en claves y valores si es necesario
                fila_limpia = {k.strip() if k else k: v.strip() if isinstance(v, str) else v for k, v in fila_dict.items()}
                
                # Mapeo de nombre de robot si 'robot_name' está presente y hay un mapa
                nombre_robot_clouders = fila_limpia.get("robot_name")
                if nombre_robot_clouders and self.mapa_robots:
                    nombre_robot_sam = self.mapa_robots.get(nombre_robot_clouders)
                    if nombre_robot_sam:
                        fila_limpia["robot_name_sam"] = nombre_robot_sam # Añadir el nombre mapeado
                        self.logger.debug(f"Parsear TSV: Robot '{nombre_robot_clouders}' mapeado a SAM como '{nombre_robot_sam}'.")
                    else:
                        self.logger.debug(f"Parsear TSV: Robot '{nombre_robot_clouders}' de Clouders no encontrado en mapa_robots (variable de entorno).")

                # Conversión de tipos, ejemplo para 'CantidadTickets'
                if "CantidadTickets" in fila_limpia:
                    try:
                        fila_limpia["CantidadTickets"] = int(fila_limpia["CantidadTickets"])
                    except (ValueError, TypeError):
                        self.logger.warning(f"Parsear TSV: Valor no válido para 'CantidadTickets': '{fila_limpia.get('CantidadTickets')}' en fila. Se usará 0.")
                        fila_limpia["CantidadTickets"] = 0
                
                resultados_parseados.append(fila_limpia)
            self.logger.debug(f"Parsear TSV: {len(resultados_parseados)} filas procesadas del TSV.")
        except csv.Error as e_csv:
            self.logger.error(f"Error de formato CSV/TSV al parsear salida de MySQL: {e_csv}. Salida (primeros 500 chars):\n{salida_tsv[:500]}", exc_info=True)
            # Devolver lista vacía o relanzar, dependiendo de cómo se quiera manejar el error.
            # Por ahora, devolvemos vacío para no detener el flujo completamente por un parseo fallido.
            return []
        except Exception as e_parse:
            self.logger.error(f"Error inesperado durante _parsear_salida_tsv: {e_parse}. Salida (primeros 500 chars):\n{salida_tsv[:500]}", exc_info=True)
            return []
            
        return resultados_parseados

    def cerrar_ssh(self):
        if self.cliente_ssh:
            try:
                self.cliente_ssh.close()
                self.logger.info(f"Conexión SSH a {self.host_ssh} cerrada.")
            except Exception as e:
                # Loguear el error pero no relanzar si es durante un cierre
                self.logger.error(f"Error al cerrar conexión SSH a {self.host_ssh}: {e}", exc_info=True)
            finally:
                self.cliente_ssh = None # Importante para que la próxima conexión sea fresca

    def __del__(self):
        # Asegurar que la conexión SSH se cierre cuando el objeto es destruido
        self.logger.debug(f"MySQLSSHClient para {self.host_ssh} está siendo destruido. Intentando cerrar SSH si está activa.")
        self.cerrar_ssh()