# Proyecto SAM: Sistema Automático de Robots

## 📜 Visión General

**SAM (Sistema Automático de Robots)** es un proyecto integral diseñado para la **implementación, distribución y orquestación automática de robots RPA (Robotic Process Automation) en máquinas virtuales (VMs)**. El sistema se compone de servicios independientes que operan en conjunto y se ejecutan de forma continua (por ejemplo, mediante NSSM en Windows).

SAM centraliza la gestión de robots, sincroniza información con **Automation Anywhere A360 (AA360)**, lanza ejecuciones de robots según la demanda, y optimiza la asignación de recursos (VMs) basándose en la carga de trabajo pendiente. Adicionalmente, cuenta con una **interfaz web de mantenimiento** para gestionar la configuración y las programaciones directamente desde un navegador.

---
## 🚀 Servicios Principales

El proyecto SAM se articula en torno a los siguientes servicios independientes:

### 🤖 Servicio Lanzador

Actúa como el brazo ejecutor y el punto de sincronización con el Control Room de AA360. Sus responsabilidades clave son la sincronización de tablas maestras (`Robots`, `Equipos`), la ejecución de robots basada en la lógica de `dbo.ObtenerRobotsEjecutables`, y la monitorización de los estados de ejecución a través del `Conciliador`.

### ⚖️ Servicio Balanceador

El servicio **Balanceador** se encarga de la gestión estratégica e inteligente de los recursos (VMs), asignándolos dinámicamente a los robots en función de la carga de trabajo real. Su objetivo es maximizar la eficiencia y el rendimiento del clúster de RPA.

#### Adquisición de Carga y Pool de Recursos
Para tomar decisiones, el Balanceador primero recopila toda la información necesaria sobre los recursos disponibles y la demanda existente:

* **Gestión del Pool de VMs**: Identifica las máquinas virtuales disponibles para asignación dinámica consultando la tabla `dbo.Equipos`. Un equipo se considera parte del pool dinámico solo si cumple con todos estos criterios:
    * Tiene una licencia de tipo `ATTENDEDRUNTIME`.
    * Está marcado como `Activo_SAM = 1`.
    * Tiene el flag `PermiteBalanceoDinamico = 1`.
    * No tiene asignaciones fijas (es decir, ni `Reservado = 1` ni `EsProgramado = 1` en `dbo.Asignaciones`).
* **Adquisición de Carga de Trabajo Concurrente**: Determina la cantidad de "tickets" o tareas pendientes para cada robot. Para ser eficiente, obtiene esta información de **dos fuentes de datos distintas de forma paralela** usando un `ThreadPoolExecutor`:
    * **SQL Server (rpa360)**: Ejecuta el Stored Procedure `dbo.usp_obtener_tickets_pendientes_por_robot` en una base de datos externa.
    * **MySQL (clouders)**: Utiliza un cliente SSH (`paramiko`) para crear un túnel seguro y ejecutar una consulta en una base de datos MySQL remota.
* **Mapeo de Nombres de Robots**: Utiliza un diccionario de mapeo definido en la variable de entorno `MAPA_ROBOTS` para conciliar los nombres de los robots que vienen de la base de datos "clouders" con los nombres estándar utilizados en SAM, asegurando la consistencia.

#### Lógica de Balanceo Avanzada y Multifásica
El núcleo del servicio es su algoritmo de balanceo, encapsulado en la clase `Balanceo`, que se ejecuta en varias fases secuenciales para garantizar un orden lógico en la toma de decisiones.

* **Pre-Fase: Validación de Asignaciones**: Antes de cualquier cálculo, el sistema verifica que todos los equipos asignados dinámicamente en ciclos anteriores sigan siendo válidos (es decir, que aún pertenezcan al pool dinámico). Si un equipo ya no es válido (p. ej., su licencia cambió), se intenta desasignar.
* **Fase 0: Limpieza de Robots No Candidatos**: Libera todos los equipos asignados dinámicamente a robots que han sido marcados como `Activo = 0` o `EsOnline = 0` en la tabla `dbo.Robots`. Esto asegura que los recursos no queden bloqueados por robots que no están operativos.
* **Fase 1: Satisfacción de Mínimos (con Reasignación)**:
    * Asegura que cada robot candidato con carga de trabajo alcance su `MinEquipos` funcional.
    * Primero intenta usar equipos del pool libre.
    * Si el pool se agota, el sistema puede **reasignar** un equipo de un robot "donante". Un donante es un robot de menor prioridad que tiene más equipos que su propio mínimo requerido. Esta reasignación solo ocurre si el `CoolingManager` lo permite para ambas partes.
* **Fase 2: Desasignación de Excedentes Reales**: Evalúa los robots que, tras la Fase 1, tienen más equipos de los que necesitan para su carga de trabajo actual. Los equipos sobrantes se desasignan y devuelven al pool libre.
* **Fase 3: Asignación de Demanda Adicional**: Los equipos que queden en el pool libre se distribuyen entre los robots que todavía tienen demanda de trabajo, ordenados por prioridad y necesidad, hasta alcanzar su necesidad calculada o su `MaxEquipos`.

#### Mecanismos de Control y Auditoría
Para garantizar un funcionamiento estable y transparente, el Balanceador implementa dos mecanismos clave:

* **Mecanismo de Enfriamiento (`CoolingManager`)**: Previene el "thrashing" (asignar y desasignar recursos a un mismo robot de forma repetida y frecuente). Impone un período de enfriamiento después de una operación de ampliación o reducción para un robot. Este enfriamiento puede ser ignorado si se detecta una variación drástica en la carga de tickets (por defecto, >30% de aumento o >40% de disminución), permitiendo una reacción rápida ante cambios significativos.
* **Registro Histórico (`HistoricoBalanceoClient`)**: Cada decisión de asignación o desasignación, junto con su justificación (ej. `ASIGNAR_MIN_POOL`, `DESASIGNAR_EXC_REAL`, `DESASIGNAR_PARA_MIN_AJENO`), se registra en la tabla `dbo.HistoricoBalanceo`. Esto proporciona una trazabilidad completa de todas las acciones del Balanceador para fines de auditoría y análisis de rendimiento.

### 📞 Servicio de Callbacks

Un servidor web ligero y dedicado cuya única responsabilidad es escuchar notificaciones (callbacks) en tiempo real enviadas por AA360 cuando un robot finaliza su ejecución. Al recibir un callback, actualiza inmediatamente el estado de la ejecución en la base de datos SAM.

### 🖥️ Interfaz Web de Mantenimiento

Una aplicación web desarrollada con **ReactPy** y **FastAPI** que provee una interfaz de usuario para la administración del sistema. Permite a los operadores:
* Visualizar y modificar la configuración de los robots (ej. `Activo`, `EsOnline`, `PrioridadBalanceo`).
* Crear, ver y eliminar programaciones de ejecución para los robots.
* Asignar equipos (VMs) de forma exclusiva para ejecuciones programadas o reservadas.
* Gestionar el pool de equipos disponibles para el balanceo.

---
## 🛠️ Características Técnicas Clave
* **Integración con Automation Anywhere A360**: Cliente API (`AutomationAnywhereClient`) robusto con gestión de tokens, paginación y despliegue de bots.
* **Base de Datos SAM (SQL Server)**: Conexiones gestionadas por hilo con `pyodbc` y lógica de negocio encapsulada en Stored Procedures.
* **Algoritmo de Balanceo Dinámico**: Lógica multifásica que incluye limpieza, satisfacción de mínimos, desasignación de excedentes y asignación de demanda, gobernado por un `CoolingManager` para evitar thrashing.
* **Gestión Centralizada de Configuración**: A través de archivos `.env` y la clase `ConfigManager`.
* **Procesamiento Concurrente**: Uso de `ThreadPoolExecutor` en el Lanzador y Balanceador para tareas de I/O.
* **Interfaz Web Reactiva**: Panel de administración construido con **ReactPy** y **FastAPI**, permitiendo la gestión de la base de datos SAM sin necesidad de escribir código JavaScript.
* **Cierre Controlado (Graceful Shutdown)**: Manejo de señales del sistema para finalizar tareas y cerrar conexiones de forma segura.

---
## 📂 Estructura del Proyecto

```
SAM_PROJECT_ROOT/
├── balanceador/             # Código del Servicio Balanceador
│   ├── clients/
│   ├── database/
│   ├── service/
│   └── run_balanceador.py
├── callback/                # Código del Servicio de Callbacks
│   ├── service/
│   └── run_callback.py
├── interfaz_web/            # Código de la Interfaz Web de Mantenimiento
│   ├── service/
│   └── run_interfaz_web.py
├── lanzador/                # Código del Servicio Lanzador
│   ├── clients/
│   ├── service/
│   └── run_lanzador.py
├── common/                  # Módulos compartidos por todos los servicios
│   ├── database/
│   └── utils/
├── .env                     # Archivo principal de configuración
├── requirements.txt         # Dependencias Python
├── SAM.sql                  # Script DDL para la base de datos SAM
└── README.md                # Este archivo
```

---
## 📋 Prerrequisitos

* Python 3.8 o superior.
* Acceso a una instancia de Automation Anywhere A360 Control Room.
* Una base de datos SQL Server con el esquema de `SAM.sql` aplicado.
* Un servidor SMTP accesible.
* **NSSM (Non-Sucking Service Manager)** para ejecutar los servicios en producción.

---
## ⚙️ Configuración e Instalación

1.  **Clonar/Descomprimir** el repositorio.
2.  **Crear y activar un entorno virtual** de Python.
3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
    Asegúrate de que `requirements.txt` incluya: `requests`, `pyodbc`, `python-dotenv`, `schedule`, `paramiko`, `pytz`, `python-dateutil`, `waitress`, **`reactpy`**, **`fastapi`**, y **`"uvicorn[standard]"`**.
4.  **Configurar `.env`**: Crea un archivo `.env` en la raíz del proyecto y completa todas las variables de entorno necesarias definidas en `common/utils/config_manager.py`.
5.  **Base de Datos**: Aplica el script `SAM.sql` a tu instancia de SQL Server.
6.  **Firewall**: Asegura que el puerto del `Servicio de Callbacks` (ej. 8008) y el de la `Interfaz Web` (ej. 8000) estén abiertos para las conexiones necesarias.

---
## ▶️ Despliegue y Ejecución (NSSM)

Para un entorno de producción, se recomienda ejecutar los **cuatro servicios** como servicios de Windows utilizando NSSM.

1.  **Servicio SAM-Lanzador:**
    * **Aplicación:** `python.exe` (ruta completa).
    * **Argumentos:** `C:\ruta\a\SAM_PROJECT_ROOT\lanzador\run_lanzador.py`.
    * **Directorio de Inicio:** `C:\ruta\a\SAM_PROJECT_ROOT\`.

2.  **Servicio SAM-Balanceador:**
    * **Aplicación:** `python.exe`.
    * **Argumentos:** `C:\ruta\a\SAM_PROJECT_ROOT\balanceador\run_balanceador.py`.
    * **Directorio de Inicio:** `C:\ruta\a\SAM_PROJECT_ROOT\`.

3.  **Servicio SAM-Callback:**
    * **Aplicación:** `python.exe`.
    * **Argumentos:** `C:\ruta\a\SAM_PROJECT_ROOT\callback\run_callback.py`.
    * **Directorio de Inicio:** `C:\ruta\a\SAM_PROJECT_ROOT\`.

4.  **Servicio SAM-InterfazWeb:**
    * **Aplicación:** `python.exe`.
    * **Argumentos:** `C:\ruta\a\SAM_PROJECT_ROOT\interfaz_web\run_interfaz_web.py`.
    * **Directorio de Inicio:** `C:\ruta\a\SAM_PROJECT_ROOT\`.

---
### Resumen de los Cambios Clave en el README:
* **Se añadió la Interfaz Web** como un componente principal del sistema.
* **Se actualizó la Estructura del Proyecto** para reflejar la modularización del `callback` y la adición de `interfaz_web`.
* **Se actualizaron las Instrucciones de Despliegue con NSSM** para incluir los cuatro servicios independientes.
* **Se añadieron las nuevas dependencias** (`reactpy`, `fastapi`, `uvicorn`) a la lista de prerrequisitos.

---
## 🐛 Troubleshooting Básico

* **Verificar Logs**: Revisa los archivos de log generados por cada servicio (ej. `sam_lanzador_app.log`, `sam_callback_server.log`, `sam_balanceador_app.log` definidos en `ConfigManager.get_log_config()`). Aumenta el `LOG_LEVEL` a `DEBUG` en `.env` para obtener más detalles.
* **Conectividad de Base de Datos**: Asegúrate de que las credenciales y los nombres de host/instancia para todas las bases de datos (SAM DB, RPA360 DB, Clouders MySQL) sean correctos y que haya conectividad de red.
* **API de AA360**: Verifica que la URL del Control Room y las credenciales de API sean válidas y que el usuario API tenga los permisos necesarios en A360.
* **Callbacks No Llegan (Lanzador)**:
    * La URL `AA_URL_CALLBACK` (o la construida desde `CALLBACK_SERVER_PUBLIC_HOST`, `CALLBACK_SERVER_PORT`, `CALLBACK_ENDPOINT_PATH`) debe ser públicamente accesible desde A360.
    * Confirma la configuración del firewall y el port forwarding si es necesario.
* **Permisos de Servicio (NSSM)**: La cuenta bajo la cual corren los servicios NSSM (usualmente "Local System") debe tener permisos para escribir en los directorios de logs y acceso a la red según sea necesario.
* **Errores `INVALID_ARGUMENT` de AA360 (Lanzador)**: Suele indicar que un `UserId` usado para lanzar un bot está deshabilitado o no existe en A360. Verifica la sincronización de `dbo.Equipos` y la lógica de `dbo.ObtenerRobotsEjecutables`.
* **Balanceador no asigna/desasigna VMs**: Revisa los logs del Balanceador para entender las decisiones del algoritmo de balanceo y el `CoolingManager`. Verifica la carga de trabajo detectada y la configuración de `MinEquipos`/`MaxEquipos`/`TicketsPorEquipoAdicional` para los robots. Asegúrate que los robots candidatos para balanceo sean `Activo = 1` y `EsOnline = 1` en `dbo.Robots`.