
# Proyecto SAM: Sistema Automático de Robots

## 📜 Visión General

**SAM (Sistema Automático de Robots)** es un proyecto integral diseñado para la **implementación, distribución y orquestación automática de robots RPA (Robotic Process Automation) en máquinas virtuales (VMs)**. El sistema se compone de dos servicios principales que operan en conjunto: el **Lanzador** y el **Balanceador**, ambos pensados para ejecutarse como servicios continuos (por ejemplo, mediante NSSM en Windows).

SAM centraliza la gestión de robots, sincroniza información con **Automation Anywhere A360 (AA360)**, lanza ejecuciones de robots según la demanda y optimiza la asignación de recursos (VMs) basándose en la carga de trabajo pendiente.

---
## 🚀 Servicios Principales

El proyecto SAM se articula en torno a dos servicios fundamentales:

### 🤖 Servicio Lanzador

El servicio **Lanzador** actúa como el brazo ejecutor y el punto de sincronización con el Control Room de AA360. Sus responsabilidades clave son:

* **Sincronización con AA360**: Mantiene actualizada la base de datos de SAM (SAM DB) con la información más reciente sobre robots (`dbo.Robots`) y equipos/máquinas virtuales (`dbo.Equipos`, incluyendo sus usuarios A360 asociados y licencias) existentes en el Control Room de AA360. Esto se realiza mediante operaciones `MERGE` que comparan y actualizan los datos locales con los obtenidos de la API de AA360. `EquipoId` en SAM DB corresponde al `deviceId` de A360, y `RobotId` en SAM DB es el `fileId` de A360.
* **Ejecución de Robots**: Lanza los robots RPA asignados haciendo uso de la API de AA360. Selecciona los robots candidatos para ejecución basándose en la lógica definida en el Stored Procedure `dbo.ObtenerRobotsEjecutables` de la SAM DB.
* **Gestión de Ejecuciones**: Registra cada intento de lanzamiento y su `deploymentId` (si es exitoso) en la tabla `dbo.Ejecuciones` de la SAM DB.
* **Monitorización de Estado**:
    * **Servidor de Callbacks**: Un componente WSGI que recibe notificaciones (callbacks) en tiempo real desde AA360 cuando un robot finaliza su ejecución, actualizando inmediatamente el estado en `dbo.Ejecuciones`.
    * **Conciliador**: Un proceso periódico que verifica el estado de las ejecuciones que aún figuran como activas en la SAM DB consultando la API de AA360, sirviendo como respaldo o complemento a los callbacks.
* **Pausa Programada**: Permite definir una ventana de tiempo durante la cual el servicio no lanzará nuevos robots, útil para mantenimientos.

### ⚖️ Servicio Balanceador

El servicio **Balanceador** se encarga de la gestión inteligente de la carga de trabajo y la asignación de recursos (VMs) a los diferentes robots. Sus funciones principales son:

* **Adquisición de Carga de Trabajo**: Determina la cantidad de "tickets" o tareas pendientes para cada robot. Esta información se obtiene de **dos fuentes de datos distintas** de forma concurrente:
    * Una base de datos **SQL Server (rpa360)**, a través del Stored Procedure `dbo.usp_obtener_tickets_pendientes_por_robot`.
    * Una base de datos **MySQL (clouders)**, accediendo a través de un túnel SSH y consultando las tablas `task_task` y `task_robot`. Utiliza un mapeo (`MAPA_ROBOTS` en la configuración) para conciliar los nombres de los robots de Clouders con los nombres en SAM.
* **Asignación Dinámica de VMs**: Basándose en la carga de trabajo detectada y la configuración de cada robot **activo** (`Activo = 1` en `dbo.Robots`) (ej. `MinEquipos`, `MaxEquipos`, `TicketsPorEquipoAdicional`), asigna o desasigna dinámicamente equipos (VMs) a los robots.
* **Lógica de Balanceo Avanzada**:
    * Utiliza un **algoritmo de prioridades** (`PrioridadBalanceo` en `dbo.Robots`) para la asignación de VMs cuando los recursos son escasos.
    * Implementa un **mecanismo de enfriamiento (`CoolingManager`)** para prevenir el "thrashing" (asignaciones y desasignaciones demasiado frecuentes de VMs para un mismo robot).
* **Gestión del Pool de VMs**: Identifica las VMs disponibles para asignación dinámica desde la tabla `dbo.Equipos` de la SAM DB, considerando su licencia (`ATTENDEDRUNTIME`), estado de actividad SAM y si permiten balanceo dinámico, además de no estar ya asignadas de forma fija (reservada o programada).
* **Registro Histórico**: Todas las decisiones de asignación y desasignación tomadas por el Balanceador se registran en la tabla `dbo.HistoricoBalanceo` para auditoría y análisis.

---
## ⚙️ Arquitectura y Flujo de Trabajo del Sistema

1.  **Inicio de Servicios**: Tanto el Lanzador como el Balanceador (y el Servidor de Callbacks del Lanzador) se inician como servicios independientes.
2.  **Sincronización (Lanzador)**: Periódicamente, el Lanzador consulta la API de AA360 para obtener la lista de robots y equipos (devices/usuarios). Actualiza las tablas `dbo.Robots` y `dbo.Equipos` en la SAM DB.
3.  **Detección de Carga (Balanceador)**: El Balanceador consulta sus fuentes de datos (SQL Server rpa360 y MySQL clouders) para determinar la cantidad de tickets pendientes por cada robot.
4.  **Balanceo de Carga (Balanceador)**:
    * El Balanceador analiza la carga de trabajo y la disponibilidad de VMs.
    * Decide si necesita asignar más VMs a ciertos robots activos o desasignar VMs de robots con poca o ninguna carga, respetando las reglas de enfriamiento y prioridad.
    * Actualiza la tabla `dbo.Asignaciones` en la SAM DB para reflejar los cambios (marcando las asignaciones como `AsignadoPor = 'Balanceador'`).
5.  **Lanzamiento de Robots (Lanzador)**:
    * Periódicamente, el Lanzador consulta `dbo.ObtenerRobotsEjecutables` (que considera las asignaciones hechas por el Balanceador y otras programaciones) para obtener la lista de robots a ejecutar.
    * Si no está en período de pausa, lanza los robots de forma concurrente utilizando la API de AA360.
    * Registra el inicio de la ejecución en `dbo.Ejecuciones`.
6.  **Procesamiento y Callback (Lanzador/AA360)**:
    * El robot se ejecuta en la VM asignada a través de AA360.
    * Al finalizar, AA360 envía un callback HTTP POST al Servidor de Callbacks del Lanzador.
    * El Servidor de Callbacks actualiza el estado final y `FechaFin` en `dbo.Ejecuciones`.
7.  **Conciliación (Lanzador)**: Periódicamente, el Conciliador del Lanzador revisa las ejecuciones que aún figuran "en curso" en la SAM DB pero no han recibido callback, consulta su estado real en AA360 y actualiza la SAM DB.
8.  **Notificaciones**: Ambos servicios envían alertas por email en caso de errores críticos o fallos significativos.

---
## 🛠️ Características Técnicas Clave

* **Integración con Automation Anywhere A360**:
    * Cliente API (`AutomationAnywhereClient`) robusto para interactuar con AA360, incluyendo gestión avanzada de tokens, paginación automática de resultados, y despliegue de bots con parámetros de entrada.
* **Base de Datos SAM (SQL Server)**:
    * Utiliza `pyodbc` para la conexión a SQL Server.
    * Conexiones gestionadas por hilo (`threading.local`) para seguridad en entornos concurrentes.
    * Manejo de transacciones (commit/rollback) y lógica de reintentos para queries.
    * Stored Procedures para encapsular lógica de negocio (ej. `dbo.ObtenerRobotsEjecutables`).
* **Adquisición de Carga de Trabajo Multi-fuente (Balanceador)**:
    * Capacidad de conectarse a SQL Server y MySQL (vía túnel SSH con `paramiko`) para obtener datos de tickets.
* **Algoritmo de Balanceo Dinámico (Balanceador)**:
    * Toma decisiones basadas en la carga actual, configuración de robots (`MinEquipos`, `MaxEquipos`, `TicketsPorEquipoAdicional`, `PrioridadBalanceo`), y disponibilidad de VMs.
    * Protección contra thrashing mediante `CoolingManager`.
* **Gestión Centralizada de Configuración**:
    * Todas las configuraciones (credenciales, URLs, parámetros de API, intervalos, etc.) se gestionan a través de archivos `.env` y la clase `ConfigManager`.
* **Logging y Notificaciones**:
    * Logging detallado en archivos con rotación (`TimedRotatingFileHandler`) para cada servicio y componente principal (como el Callback Server).
    * Alertas por email (`EmailAlertClient`) para eventos críticos y fallos.
* **Procesamiento Concurrente**:
    * El Lanzador utiliza `concurrent.futures.ThreadPoolExecutor` para el despliegue paralelo de múltiples robots.
    * El Balanceador también usa `concurrent.futures.ThreadPoolExecutor` para la obtención concurrente de la carga de trabajo de sus diferentes fuentes.
* **Manejo de Callbacks y Conciliación de Estados (Lanzador)**:
    * El Servidor de Callbacks (`waitress` o `wsgiref.simple_server`) procesa actualizaciones de estado de AA360 en tiempo real.
    * El Conciliador asegura la consistencia de los estados de ejecución mediante polling periódico a la API de AA360, convirtiendo fechas UTC a la zona horaria local del servidor SAM con `pytz` y `dateutil`.
* **Programación de Tareas con `schedule`**:
    * Ambos servicios utilizan la biblioteca `schedule` para la gestión flexible de la ejecución periódica de sus ciclos principales (lanzamiento, conciliación, sincronización para el Lanzador; ciclo de balanceo para el Balanceador).
* **Cierre Controlado (Graceful Shutdown)**:
    * Ambos servicios manejan señales del sistema (`SIGINT`, `SIGTERM`) para finalizar tareas pendientes, limpiar jobs de `schedule` y cerrar conexiones de forma segura antes de detenerse.

---
## 📂 Estructura del Proyecto

```
SAM_PROJECT_ROOT/
├── balanceador/             # Código específico del Servicio Balanceador
│   ├── clients/             # Clientes para fuentes de datos externas (ej. mysql_client.py)
│   ├── database/            # Lógica de BD específica del Balanceador (ej. historico_client.py)
│   ├── service/             # Lógica principal del Balanceador (main.py, balanceo.py, cooling_manager.py)
│   ├── run_balanceador.py   # Punto de entrada del Balanceador
│   └── .env                 # (Opcional) Configuración específica del Balanceador
├── lanzador/                # Código específico del Servicio Lanzador
│   ├── clients/             # Cliente para AA360 (aa_client.py)
│   ├── service/             # Lógica principal del Lanzador (main.py, conciliador.py, callback_server.py)
│   ├── run_lanzador.py      # Punto de entrada del Lanzador
│   └── .env                 # (Opcional) Configuración específica del Lanzador
├── common/                  # Módulos compartidos por ambos servicios
│   ├── database/            # Cliente SQL Server genérico (sql_client.py)
│   └── utils/               # Utilidades comunes (config_manager.py, logging_setup.py, mail_client.py)
├── .env                     # Archivo principal de configuración para variables de entorno
├── requirements.txt         # Dependencias Python del proyecto
├── SAM.sql                  # Script DDL para la base de datos SAM
└── README.md                # Este archivo
```

---
## 🗃️ Esquema de la Base de Datos SAM

El script `SAM.sql` define la estructura de la base de datos utilizada por el sistema, incluyendo tablas clave como:

* `dbo.Robots`: Información sobre los robots RPA sincronizados desde AA360 (ID, nombre, descripción, configuración de balanceo como `MinEquipos`, `MaxEquipos`, `PrioridadBalanceo`, `TicketsPorEquipoAdicional`).
* `dbo.Equipos`: Información sobre las máquinas virtuales/dispositivos y sus usuarios A360 asociados (ID, nombre, `UserId` de A360, licencia, estado de actividad para SAM, si permite balanceo dinámico).
* `dbo.Asignaciones`: Registra qué robots están asignados a qué equipos (ya sea por programación, manualmente o dinámicamente por el Balanceador).
* `dbo.Ejecuciones`: Historial y estado actual de cada ejecución de robot lanzada por SAM (incluye `DeploymentId` de AA360, `RobotId`, `EquipoId`, `Estado`, `FechaInicio`, `FechaFin`, `CallbackInfo`).
* `dbo.Programaciones`: Define horarios programados para la ejecución de robots. El SP `ObtenerRobotsEjecutables` ya considera esta tabla.
* `dbo.HistoricoBalanceo`: Log de las decisiones tomadas por el servicio Balanceador.
* `dbo.ErrorLog`: Tabla para registrar errores dentro de Stored Procedures.

Consulte `SAM.sql` para la definición detallada de todas las tablas, vistas, funciones y Stored Procedures.

---
## 📋 Prerrequisitos

* Python 3.8 o superior.
* Acceso a una instancia de Automation Anywhere A360 Control Room (On-Premise o Cloud) con credenciales de API.
* Una base de datos SQL Server con el esquema de `SAM.sql` aplicado y credenciales de acceso.
* (Para el Balanceador) Acceso a las bases de datos de origen de tickets (SQL Server rpa360 y MySQL clouders, esta última vía SSH).
* Un servidor SMTP accesible para el envío de notificaciones por email.
* **NSSM (Non-Sucking Service Manager)** o un gestor de servicios similar para ejecutar los servicios en producción.
* (Para el `callback_server.py` en producción) **Waitress** (`pip install waitress`).

---
## ⚙️ Configuración (`.env`)

1.  **Clonar el Repositorio / Descomprimir Archivos.**
2.  **Crear y Activar un Entorno Virtual Python (Recomendado).**
3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
    Asegúrate de que `requirements.txt` incluya: `requests`, `pyodbc`, `python-dotenv`, `schedule`, `paramiko` (para Balanceador), `pytz`, `python-dateutil`, y `waitress` (para Lanzador).
4.  **Crear y Configurar el Archivo `.env`:**
    * Crea un archivo llamado `.env` en la raíz del proyecto SAM (`SAM_PROJECT_ROOT`).
    * Completa **TODAS** las variables de entorno necesarias según lo definido en `common/utils/config_manager.py`. Esto incluye:
        * **Configuración de Logging Común** (`LOG_DIRECTORY`, `LOG_LEVEL`, etc.).
        * **Configuración de SQL Server para SAM DB** (`SQL_SAM_HOST`, `SQL_SAM_DB_NAME`, etc.).
        * **Configuración de la API de AA360** (`AA_URL`, `AA_USER`, `AA_PWD`, `AA_API_KEY` (opcional)).
        * **Configuración del Servidor de Callbacks del Lanzador** (`CALLBACK_SERVER_HOST`, `CALLBACK_SERVER_PORT`, `AA_URL_CALLBACK` - esta última debe ser la URL pública/accesible de tu `callback_server.py`).
        * **Configuración de Email** (`EMAIL_SMTP_SERVER`, `EMAIL_FROM`, `EMAIL_RECIPIENTS`, etc.).
        * **Configuración Específica del Lanzador** (`LANZADOR_INTERVALO_LANZADOR_SEG`, `LANZADOR_PAUSA_INICIO_HHMM`, etc.).
        * **Configuración de SQL Server para RPA360 DB (Balanceador)** (`SQL_RPA360_HOST`, etc.).
        * **Configuración SSH y MySQL para Clouders (Balanceador)** (`CLOUDERS_SSH_HOST`, `CLOUDERS_MYSQL_DB_NAME`, `MAPA_ROBOTS` en formato JSON string, etc.).
        * **Configuración Específica del Balanceador** (`BALANCEADOR_INTERVALO_CICLO_SEG`, `BALANCEADOR_DEFAULT_TICKETS_POR_EQUIPO`, etc.).
5.  **Base de Datos SAM:**
    * Asegúrate de que la base de datos SAM exista en SQL Server y que el esquema de `SAM.sql` se haya aplicado correctamente.
    * Verifica la conectividad de red y los permisos de usuario para SQL Server.
6.  **Bases de Datos de Origen de Tickets (para Balanceador):**
    * Asegura la conectividad a la base de datos SQL Server rpa360.
    * Configura el acceso SSH y MySQL para la base de datos "clouders". El usuario SSH debe tener permisos para ejecutar el comando `mysql` en el servidor remoto.
7.  **Firewall para Callback Server (Lanzador):**
    * El firewall de la máquina host y cualquier firewall de red deben permitir conexiones entrantes en el `CALLBACK_SERVER_PORT` desde las IPs del Control Room de A360.

---
## ▶️ Despliegue y Ejecución (NSSM)

Para un entorno de producción, se recomienda ejecutar los servicios Lanzador, Callback Server (del Lanzador) y Balanceador como servicios Windows utilizando **NSSM**.

Deberás configurar **tres servicios separados**:

1.  **Servicio SAM-Lanzador-Principal:**
    * **Aplicación:** `python.exe` (ruta completa al `python.exe` de tu entorno virtual).
    * **Argumentos:** `C:\ruta\completa\a\SAM_PROJECT_ROOT\lanzador\run_lanzador.py`.
    * **Directorio de Inicio:** `C:\ruta\completa\a\SAM_PROJECT_ROOT\`.
2.  **Servicio SAM-Lanzador-Callback-Server:**
    * **Aplicación:** `python.exe` (ruta completa al `python.exe` de tu entorno virtual).
    * **Argumentos:** `C:\ruta\completa\a\SAM_PROJECT_ROOT\lanzador\service\callback_server.py`.
    * **Directorio de Inicio:** `C:\ruta\completa\a\SAM_PROJECT_ROOT\`.
3.  **Servicio SAM-Balanceador:**
    * **Aplicación:** `python.exe` (ruta completa al `python.exe` de tu entorno virtual).
    * **Argumentos:** `C:\ruta\completa\a\SAM_PROJECT_ROOT\balanceador\run_balanceador.py`.
    * **Directorio de Inicio:** `C:\ruta\completa\a\SAM_PROJECT_ROOT\`.

Configura NSSM para que los servicios se reinicien en caso de fallo y para un cierre adecuado.

---
## 🐛 Troubleshooting Básico

* **Verificar Logs**: Revisa los archivos de log generados por cada servicio (ej. `sam_lanzador_app.log`, `sam_callback_server.log`, `sam_balanceador_app.log`). Aumenta el `LOG_LEVEL` a `DEBUG` en `.env` para obtener más detalles.
* **Conectividad de Base de Datos**: Asegúrate de que las credenciales y los nombres de host/instancia para todas las bases de datos (SAM DB, RPA360 DB, Clouders MySQL) sean correctos y que haya conectividad de red.
* **API de AA360**: Verifica que la URL del Control Room y las credenciales de API sean válidas y que el usuario API tenga los permisos necesarios en A360.
* **Callbacks No Llegan (Lanzador)**:
    * La URL `AA_URL_CALLBACK` debe ser públicamente accesible desde A360.
    * Confirma la configuración del firewall y el port forwarding si es necesario.
* **Permisos de Servicio (NSSM)**: La cuenta bajo la cual corren los servicios NSSM (usualmente "Local System") debe tener permisos para escribir en los directorios de logs y acceso a la red según sea necesario.
* **Errores `INVALID_ARGUMENT` de AA360 (Lanzador)**: Suele indicar que un `UserId` usado para lanzar un bot está deshabilitado o no existe en A360. Verifica la sincronización de `dbo.Equipos` y la lógica de `dbo.ObtenerRobotsEjecutables`.
* **Balanceador no asigna/desasigna VMs**: Revisa los logs del Balanceador para entender las decisiones del algoritmo de balanceo y el `CoolingManager`. Verifica la carga de trabajo detectada y la configuración de `MinEquipos`/`MaxEquipos`/`TicketsPorEquipoAdicional` para los robots.
