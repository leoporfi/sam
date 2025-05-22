# Proyecto SAM - Módulo Lanzador de Robots RPA

## Descripción General

El Módulo Lanzador del Proyecto SAM es una aplicación Python diseñada para orquestar y gestionar la ejecución de robots (taskbots) en una instancia de **Automation Anywhere A360** (On-Premise o Cloud). Su funcionalidad principal incluye la selección de robots candidatos para ejecución, el despliegue en dispositivos/usuarios configurados, la monitorización del estado de las ejecuciones mediante un conciliador y un servidor de callbacks, y la sincronización de datos maestros (robots, equipos/usuarios) con el Control Room de A360.

El sistema está estructurado para operar como un servicio continuo (idealmente gestionado por NSSM en Windows o un gestor de servicios similar en otros sistemas), proporcionando una solución robusta para la automatización de procesos RPA.

## Características Principales

* **Interacción Robusta con A360 (`AutomationAnywhereClient`):**
    * Conexión con la API del Control Room de Automation Anywhere A360.
    * Gestión avanzada de tokens de autenticación, incluyendo refresco proactivo y manejo seguro en entornos multihilo.
    * Método centralizado para realizar peticiones API con manejo de errores y timeouts consistentes.
    * Capacidad para desplegar bots, especificando `fileId`, `runAsUserIds` y `botInput`.
    * Obtención de detalles de ejecuciones (`deploymentId`).
    * Obtención paginada y completa de listas de entidades de A360:
        * **Devices (Equipos/Runners):** Lista dispositivos y sus usuarios por defecto.
        * **Usuarios Detallados:** Obtiene información completa de usuarios (licencias, estado `disabled`, etc.).
        * **Robots (Files):** Lista los taskbots disponibles en el repositorio, con filtros por path y nombre.

* **Gestión de Base de Datos SQL Server (`DatabaseConnector`):**
    * Almacena información sobre robots, equipos (dispositivos/usuarios de ejecución de A360), asignaciones (si se implementa), programaciones (si se implementa), y el historial de ejecuciones en una base de datos SQL Server.
    * Utiliza `threading.local()` para conexiones de base de datos seguras por hilo.
    * Manejo de transacciones (commit/rollback) centralizado.
    * **Lógica de Reintentos:** Reintenta la ejecución de queries en caso de errores de BD específicos y reintentables (deadlocks, timeouts de query).
    * **Sincronización de Datos (MERGE):**
        * `merge_equipos`: Actualiza la tabla local `dbo.Equipos` con la información de devices y usuarios obtenida de A360. `EquipoId` en SAM es el `deviceId` de A360.
        * `merge_robots`: Actualiza la tabla local `dbo.Robots` con la información de bots obtenida de A360. `RobotId` en SAM es el `fileId` de A360. No modifica los campos `EsOnline` y `Activo` de robots existentes, permitiendo su gestión externa.

* **Orquestación de Robots (`LanzadorRobots` en `service/main.py`):**
    * **Lanzamiento Concurrente:** Despliega múltiples robots en paralelo usando `concurrent.futures.ThreadPoolExecutor` para mejorar el rendimiento.
    * **Lógica de Reintentos de Lanzamiento:** Intenta relanzar robots si el primer intento de despliegue falla con errores específicos considerados reintentables (ej. device ocupado temporalmente).
    * **Selección de Robots:** Obtiene los robots candidatos para ejecución a través de un Stored Procedure (`dbo.ObtenerRobotsEjecutables`) en la base de datos SAM.
    * **Pausa Programada:** Permite definir una ventana de tiempo configurable durante la cual el servicio no lanzará nuevos bots (útil para mantenimientos).
    * **Programación de Tareas con `schedule`:** Utiliza la biblioteca `schedule` para una gestión flexible y expresiva de la ejecución periódica de las tareas principales (lanzamiento de robots, conciliación de estados, sincronización de tablas maestras).

* **Servidor de Callbacks (`service/callback_server.py`):**
    * Un servidor WSGI independiente (usando Waitress para producción o `wsgiref.simple_server` para desarrollo) que escucha los callbacks HTTP POST enviados por el Control Room de A360 al finalizar una ejecución de bot.
    * Actualiza el estado final de la ejecución y la información del callback en la tabla `dbo.Ejecuciones` de SAM en tiempo real.
    * Responde a A360 con mensajes en español.
    * Configurable para tener su propio archivo de log.

* **Conciliación de Estados (`service/conciliador.py`):**
    * Verifica periódicamente el estado de las ejecuciones que la base de datos SAM considera "en curso" pero para las cuales no se ha recibido un callback (o como respaldo).
    * Actualiza el estado en la base de datos SAM basándose en la información de la API de A360.
    * Convierte las fechas `endDateTime` de la API (UTC) a la zona horaria local del servidor SAM.

* **Notificaciones por Email (`utils/mail_client.py`):**
    * Envía notificaciones por correo electrónico para eventos importantes, como:
        * Errores críticos en el servicio.
        * Fallos en el despliegue de robots.
    * Formato HTML y lógica para evitar el envío repetido de alertas críticas.

* **Manejo de Configuración (`utils/config.py`):**
    * Centraliza todas las configuraciones (rutas, credenciales, parámetros de API, BD, email, intervalos, etc.) leyendo variables de un archivo `.env` mediante `python-dotenv`.
    * Proporciona un `ConfigManager` para acceder a las diferentes secciones de configuración.

* **Logging Robusto:**
    * Genera logs detallados para el Lanzador principal y el Servidor de Callbacks en archivos separados.
    * Utiliza `TimedRotatingFileHandler` para la rotación de logs.
    * Formato de log configurable que incluye PID y nombre del logger.

* **Cierre Controlado (Graceful Shutdown):**
    * El servicio principal y el servidor de callbacks manejan señales de interrupción (`SIGINT`, `SIGTERM`) para finalizar tareas críticas en curso (como limpiar jobs de `schedule`, cerrar conexiones de BD) de forma segura antes de detenerse.

## Estructura del Proyecto (Módulo Lanzador SAM)

* **`run_lanzador.py`**: Script de punto de entrada para ejecutar el módulo Lanzador manualmente o como servicio (vía NSSM).
* **`service/main.py`**: Contiene la clase principal `LanzadorRobots` con la lógica de orquestación, programación con `schedule`, lanzamiento concurrente y pausa.
* **`service/conciliador.py`**: Clase `ConciliadorImplementaciones` para la conciliación de estados de ejecución por polling.
* **`service/callback_server.py`**: Servidor WSGI independiente para recibir callbacks de A360.
* **`clients/aa_client.py`**: Clase `AutomationAnywhereClient` que encapsula la interacción con la API de A360.
* **`database/sql_client.py`**: Clase `DatabaseConnector` para la gestión de la conexión y operaciones con la BD SQL Server SAM.
* **`utils/config.py`**: `ConfigManager` y definiciones de configuración cargadas desde `.env`.
* **`utils/mail_client.py`**: Clase `EmailAlertClient` para el envío de notificaciones.
* **`.env`**: Archivo (no versionado) para almacenar todas las variables de entorno (credenciales, URLs, etc.).
* **`requirements.txt`**: Lista de dependencias Python.
* **`SAM.sql`**: Script DDL con el esquema de la base de datos SAM.
* **`tests/`**: Directorio para scripts de prueba (unitarios, integración manual).

## Prerrequisitos

* Python 3.8 o superior.
* Acceso a una instancia de Automation Anywhere A360 Control Room (On-Premise o Cloud) con credenciales de API.
* Una base de datos SQL Server con el esquema `SAM.sql` aplicado y credenciales de acceso.
* Un servidor SMTP accesible para el envío de notificaciones por email.
* (Opcional, para producción) **NSSM (Non-Sucking Service Manager)** para ejecutar `run_lanzador.py` y `callback_server.py` como servicios Windows separados.
* (Opcional, para producción con `callback_server.py`) **Waitress** (`pip install waitress`) como servidor WSGI.

## Configuración

1.  **Clonar el Repositorio / Descomprimir Archivos.**
2.  **Crear y Activar un Entorno Virtual (Recomendado):**
    ```bash
    python -m venv venv
    # Windows: venv\Scripts\activate
    # Linux/macOS: source venv/bin/activate
    ```
3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
    Asegúrate de que `requirements.txt` incluya: `requests`, `pyodbc`, `python-dotenv`, `schedule`, `pytz`, `python-dateutil`, y `waitress` (si se usa para el callback server en producción).
4.  **Crear y Configurar el Archivo `.env`:**
    * Copia `.env.example` a `.env` (o crea `.env` en la raíz del módulo Lanzador o del proyecto SAM).
    * Completa **TODAS** las variables de entorno necesarias definidas en `utils/config.py` (URLs, credenciales de BD y A360, configuraciones de email, intervalos, puertos, etc.). Presta especial atención a:
        * `AA_URL_CALLBACK`: Debe ser la URL pública/accesible de tu `callback_server.py` (ej. `http://tu_ip_publica:PUERTO_CALLBACK/sam_callback`).
        * `CALLBACK_SERVER_PUBLIC_HOST`: El hostname o IP pública que A360 usará para alcanzar el callback server.
        * `CALLBACK_ENDPOINT_PATH`: El path específico del endpoint en el callback server (ej. `/sam_callback`).
5.  **Base de Datos:**
    * Asegúrate de que la base de datos SAM exista y que el esquema de `SAM.sql` se haya aplicado.
    * Verifica que SQL Server esté configurado para permitir conexiones remotas (TCP/IP habilitado) y que el firewall permita el acceso al puerto de SQL Server (usualmente 1433).
6.  **Firewall para Callback Server:**
    * Si ejecutas `callback_server.py`, el firewall de la máquina host (y cualquier firewall de red) debe permitir conexiones entrantes en el `CALLBACK_SERVER_PORT` desde las IPs de A360 Cloud.

## Uso

### Ejecución Manual (Para Desarrollo/Pruebas)

Puedes ejecutar cada componente principal por separado desde la línea de comandos (asegúrate de estar en la raíz del proyecto SAM, `C:\RPA\rpa_sam`, y que tu entorno virtual esté activado):

1.  **Servidor de Callbacks:**
    ```bash
    python lanzador\service\callback_server.py
    ```
2.  **Lanzador Principal (en otra terminal):**
    ```bash
    python lanzador\run_lanzador.py
    ```
Los logs se generarán en los directorios y archivos especificados en `LOG_CONFIG` dentro de `utils/config.py`. Usa `Ctrl+C` para intentar un cierre controlado.

### Ejecución como Servicio Windows (usando NSSM)

Recomendado para producción. Deberás configurar **dos servicios separados** con NSSM:

1.  **Servicio SAM-Lanzador:**
    * **Aplicación:** `python.exe` (ruta completa a tu python.exe del venv).
    * **Argumentos:** `C:\ruta\completa\a\rpa_sam\lanzador\run_lanzador.py`.
    * **Directorio de Inicio:** `C:\ruta\completa\a\rpa_sam\`.
2.  **Servicio SAM-Callback-Server:**
    * **Aplicación:** `python.exe` (ruta completa a tu python.exe del venv).
    * **Argumentos:** `C:\ruta\completa\a\rpa_sam\lanzador\service\callback_server.py`.
    * **Directorio de Inicio:** `C:\ruta\completa\a\rpa_sam\`.

Configura NSSM para que los servicios se reinicien en caso de fallo y para un cierre adecuado.

## Flujo de Trabajo Principal

1.  **Inicio:**
    * `run_lanzador.py` (a través de `service/main.py`) inicializa `LanzadorRobots`.
    * `LanzadorRobots` configura sus tareas periódicas (lanzamiento, conciliación, sincronización de tablas) usando `schedule`.
    * Se realiza una ejecución inicial de cada tarea.
    * El bucle principal de `schedule` comienza a correr, ejecutando tareas según su programación.
    * Paralelamente, `callback_server.py` inicia su servidor WSGI y escucha por callbacks de A360.
2.  **Sincronización de Tablas:** Periódicamente, se obtienen datos de robots y equipos/usuarios de A360 y se actualizan las tablas `dbo.Robots` y `dbo.Equipos` en la BD SAM mediante operaciones `MERGE`.
3.  **Ciclo de Lanzamiento:**
    * Periódicamente, se consulta la BD SAM (vía `dbo.ObtenerRobotsEjecutables`) para obtener la lista de robots que deben ejecutarse.
    * Se verifica si el servicio está en una ventana de "pausa programada".
    * Los robots elegibles se lanzan de forma concurrente usando `AutomationAnywhereClient`. Se registra la ejecución en `dbo.Ejecuciones`.
    * Se manejan reintentos para fallos de despliegue específicos.
4.  **Recepción de Callbacks:** Cuando un bot finaliza en A360, este envía un POST al `callback_server.py`. El servidor parsea el payload y actualiza el estado, `FechaFin`, y `CallbackInfo` en la tabla `dbo.Ejecuciones`.
5.  **Conciliación de Estados:** Periódicamente, el `ConciliadorImplementaciones` consulta las ejecuciones que siguen "en curso" en la BD SAM y no han recibido callback, verifica su estado real en A360 y actualiza la BD SAM.
6.  **Notificaciones:** Se envían emails para errores críticos o fallos en el despliegue.
7.  **Cierre Controlado:** Al recibir una señal de terminación, los servicios intentan finalizar limpiamente sus tareas, limpiar los jobs de `schedule` y cerrar conexiones.

## Troubleshooting

* **Verificar Logs:** Revisa los archivos `sam_lanzador_app.log` y `sam_callback_server.log` (o los nombres configurados). Aumenta el `LOG_LEVEL` a `DEBUG` en `.env` para más detalle.
* **Errores de `INVALID_ARGUMENT` (Usuario Deshabilitado/Eliminado):** La causa más probable es que el SP `dbo.ObtenerRobotsEjecutables` está seleccionando `UserId`s que no son válidos en A360. Asegúrate que la sincronización de `dbo.Equipos` funcione y que el SP use una columna `Activo` en `dbo.Equipos` para filtrar. Verifica manualmente el estado de los usuarios en A360.
* **Callbacks No Llegan (A360 Cloud):**
    * Verifica que `AA_URL_CALLBACK` sea una IP/hostname público accesible desde internet.
    * Asegura que el Port Forwarding esté configurado en tu router si el servidor de callback está en una red privada.
    * Confirma que los firewalls (de la máquina y de la red) permitan tráfico entrante al puerto del callback server desde las IPs de A360 Cloud.
    * Considera si A360 Cloud requiere HTTPS para callbacks.
    * Usa un servicio como Webhook.site para probar si A360 está enviando callbacks.
* **Errores de Conexión a BD desde Callback Server:** Similar al Lanzador, asegúrate de que la configuración de BD sea correcta y la red/firewall permitan la conexión desde la máquina del callback server a SQL Server.
* **Permisos de Servicio (NSSM):** La cuenta bajo la cual corren los servicios NSSM (usualmente Local System) debe tener permisos para escribir en los directorios de logs y acceso a la red.

---