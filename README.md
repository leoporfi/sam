# **Proyecto SAM: Sistema Automático de Robots**

## **📜 Visión General**

**SAM (Sistema Automático de Robots)** es un proyecto integral diseñado para la **implementación, distribución y orquestación automática de robots RPA (Robotic Process Automation) en máquinas virtuales (VMs)**. El sistema se compone de cuatro servicios independientes que operan en conjunto y se ejecutan de forma continua, gestionados a través de una configuración centralizada y un conjunto de módulos comunes que garantizan la estabilidad y mantenibilidad del ecosistema.

SAM centraliza la gestión de robots, sincroniza información de forma inteligente con **Automation Anywhere A360 (AA360)**, lanza ejecuciones según la demanda o programaciones, y optimiza la asignación de recursos (VMs) basándose en la carga de trabajo pendiente. El sistema segmenta los recursos en pools dedicados o generales para un control granular del rendimiento. Adicionalmente, cuenta con una **interfaz web de mantenimiento** para gestionar la configuración y las operaciones del sistema directamente desde un navegador.

---
## **🚀 Servicios Principales**

El proyecto SAM se articula en torno a los siguientes servicios independientes:

### **🤖 Servicio Lanzador**

Actúa como el brazo ejecutor y el cerebro de sincronización con el Control Room de AA360. Es un servicio multifacético con tres responsabilidades clave que se ejecutan en ciclos independientes y configurables:

* **Sincronización Inteligente de Tablas Maestras**: Mantiene las tablas dbo.Robots y dbo.Equipos de SAM actualizadas con la realidad de AA360. Utiliza Stored Procedures como dbo.MergeRobots y dbo.MergeEquipos para realizar esta operación de forma eficiente.  
* **Lanzamiento de Robots**: Es el núcleo ejecutor del servicio.  
  * **Lógica Centralizada en BD**: Su comportamiento se basa en los resultados del Stored Procedure dbo.ObtenerRobotsEjecutables.  
  * **Ejecución Concurrente y con Reintentos**: Lanza múltiples robots en paralelo utilizando un ThreadPoolExecutor.  
* **Conciliación de Estados**: De forma periódica, el Conciliador revisa las ejecuciones que figuran como activas en la base de datos de SAM. Consulta su estado real en A360 y actualiza los registros locales.

### **⚖️ Servicio Balanceador**

El servicio **Balanceador** se encarga de la gestión estratégica e inteligente de los recursos (VMs), asignándolos dinámicamente a los robots en función de la carga de trabajo real. Su objetivo es maximizar la eficiencia y el rendimiento del clúster de RPA.

#### **Gestión de Pools de Recursos y Carga de Trabajo**

El sistema de balanceo opera sobre una jerarquía de pools de recursos para ofrecer un control granular sobre la asignación de VMs.

* **Pools Dedicados**: Es posible crear grupos nombrados de recursos. Un Pool Dedicado consiste en un conjunto específico de **Equipos** (VMs) y **Robots** asignados a dicho pool.  
  * **Lógica de Prioridad:** Los robots de un pool dedicado **siempre intentarán satisfacer su demanda utilizando los equipos de su propio pool primero**.  
* **Pool General**:  
  * Cualquier robot o equipo que no esté asignado a un pool específico (PoolId IS NULL) pertenece automáticamente al Pool General.  
  * Funciona como un reservorio de recursos para **desborde (overflow)**. La demanda no cubierta por los pools dedicados compite por los recursos libres del Pool General.  
* **Adquisición de Carga de Trabajo Concurrente**: Para determinar la cantidad de "tickets" pendientes, el sistema obtiene información de **dos fuentes de datos distintas de forma paralela** utilizando un ThreadPoolExecutor:  
  * **SQL Server (rpa360)**: A través del Stored Procedure dbo.usp_obtener_tickets_pendientes_por_robot.  
  * **Clouders API**: A través de una llamada al endpoint REST /automatizacion/task/api/stats/pending_by_robot que devuelve los robots con tareas pendientes. Esta integración, gestionada por CloudersClient, reemplaza al antiguo método de conexión a MySQL vía SSH.

#### **Lógica de Balanceo Avanzada y Multifásica**

El núcleo del servicio es su algoritmo de balanceo, que opera con una lógica jerárquica para respetar los pools. El ciclo se ejecuta en tres etapas orquestadas:

* **Etapa 1: Limpieza Global (Pre-Fase y Fase 0)**: Antes de cualquier cálculo, el sistema valida **todas** las asignaciones dinámicas existentes en una única pasada. Libera recursos de robots que han sido marcados como inactivos u offline y de equipos que ya no son válidos para el balanceo.  
* **Etapa 2: Balanceo Interno de Pools (Fase 1 y 2)**: El algoritmo itera sobre cada pool (primero el general y luego cada pool dedicado). En cada iteración:  
  * **Satisface Mínimos**: Asegura que cada robot del pool alcance su MinEquipos funcional, asignándole máquinas **de su propio pool**.  
  * **Desasigna Excedentes**: Libera los equipos sobrantes de cada robot, devolviéndolos **a su pool de origen**.  
* **Etapa 3: Asignación Global por Desborde y Prioridad (Fase 3)**: Esta es la fase final.  
  * **Cálculo de Demanda Restante**: Se identifican las necesidades de equipos no cubiertas de todos los robots (demanda de **desborde** de pools dedicados y demanda adicional del pool general).  
  * **Competencia por Recursos**: Toda esta demanda restante se consolida en una única lista ordenada por PrioridadBalanceo.  
  * **Asignación desde el Pool General**: El algoritmo asigna los equipos **libres y restantes del Pool General** a los robots de la lista consolidada.

#### **Mecanismos de Control y Auditoría**

* **Mecanismo de Enfriamiento (CoolingManager)**: Previene el "thrashing" (asignar y desasignar recursos de forma repetida). Impone un período de enfriamiento (cooling_period_seconds) después de una operación. Este enfriamiento puede ser ignorado si se detecta una variación drástica en la carga de tickets, permitiendo una reacción rápida.  
* **Registro Histórico (HistoricoBalanceoClient)**: Cada decisión de asignación o desasignación se registra en la tabla dbo.HistoricoBalanceo. El registro ahora incluye el PoolId afectado, lo que permite una auditoría más detallada.

### **📞 Servicio de Callbacks**

Un servidor web ligero y dedicado cuya única responsabilidad es escuchar notificaciones (callbacks) en tiempo real enviadas por AA360 cuando un robot finaliza su ejecución.

* **API Segura y Definida**: Requiere un token de seguridad en el encabezado X-Authorization para validar la llamada.  
* **Procesamiento Inmediato**: Al recibir un callback válido, actualiza inmediatamente el estado de la ejecución en la tabla dbo.Ejecuciones.  
* **Servidor de Producción**: Utiliza un servidor WSGI de producción (waitress) para manejar múltiples peticiones concurrentes.

### **🖥️ Interfaz Web de Mantenimiento**

Una aplicación web que provee una interfaz de usuario para la administración y monitorización del sistema SAM. Permite la gestión de robots, asignaciones manuales (Reservado=1) y programaciones.

## **🛠️ Características Técnicas Clave**

* **Módulos Comunes Centralizados**: El proyecto se apoya en un directorio common que contiene utilidades compartidas por todos los servicios.  
* **Data Access Layer (DatabaseConnector)**: La interacción con SQL Server se realiza a través de un cliente robusto que ofrece:  
  * **Conexiones seguras por hilo** (thread-safe) utilizando threading.local.  
  * **Reconexión automática** para asegurar que cada operación tenga una conexión válida.  
  * Un mecanismo inteligente de **reintentos con backoff exponencial** para errores transitorios de base de datos (ej. deadlocks o timeouts), basado en SQLSTATE.  
* **Logging de Producción Robusto**: La configuración de logging, centralizada en setup_logging, utiliza una clase RobustTimedRotatingFileHandler. Esta clase previene caídas del servicio por problemas de bloqueo de archivos en entornos Windows al reintentar la rotación de logs.  
* **Integración Asíncrona con A360 (AutomationAnywhereClient)**: Un cliente httpx asíncrono para interactuar con la API de Automation Anywhere, con gestión de token y paginación automática para obtener todos los registros.  
* **Alertas por Email (EmailAlertClient)**: Un cliente de correo centralizado que puede enviar notificaciones críticas o informativas. Incluye una lógica para evitar el envío repetido de alertas críticas idénticas en un corto período de tiempo.  
* **Adquisición de Carga de Trabajo Concurrente**: Uso de ThreadPoolExecutor en el Balanceador para consultar las cargas de trabajo de SQL Server y la API de Clouders en paralelo, mejorando el rendimiento.  
* **Cierre Controlado (Graceful Shutdown)**: Todos los servicios manejan señales del sistema (SIGTERM, SIGINT) para finalizar tareas en curso y cerrar conexiones de forma segura.

## **📂 Estructura del Proyecto**

SAM_PROJECT_ROOT/  
├── src/  
│   ├── balanceador/             # Código del Servicio Balanceador  
│   │   ├── clients/  
│   │   │   └── clouders_client.py # Cliente para la API de Clouders  
│   │   ├── database/  
│   │   │   └── historico_client.py  
│   │   └── service/  
│   │       ├── balanceo.py  
│   │       ├── cooling_manager.py  
│   │       └── main.py  
│   ├── callback/                # Código del Servicio de Callbacks  
│   ├── lanzador/                # Código del Servicio Lanzador  
│   └── common/                  # Módulos compartidos  
│       ├── clients/  
│       │   └── aa_client.py  
│       ├── database/  
│       │   └── sql_client.py  
│       └── utils/  
│           ├── config_loader.py  
│           ├── config_manager.py  
│           ├── logging_setup.py  
│           └── mail_client.py  
├──.env                         # Archivo principal de configuración  
├── requirements.txt             # Dependencias Python  
├── SAM.sql                      # Script DDL para la base de datos SAM  
└── README.md                    # Este archivo

## **📋 Prerrequisitos**

* Python 3.8 o superior.  
* Acceso a una instancia de Automation Anywhere A360 Control Room.  
* Una base de datos SQL Server con el esquema de SAM.sql aplicado.  
* Credenciales de acceso a la API de Clouders.  
* Un servidor SMTP accesible para el envío de alertas por correo.  
* **NSSM (Non-Sucking Service Manager)** o una herramienta similar para ejecutar los servicios en producción en Windows.

## **⚙️ Configuración e Instalación**

1. **Clonar/Descomprimir** el repositorio.  
2. **Crear y activar un entorno virtual** de Python.  
3. **Instalar Dependencias:**  
   ```Bash 
    pip install -r requirements.txt

   ```  

   Asegúrate de que requirements.txt incluya: requests, pyodbc, python-dotenv, schedule, httpx, waitress, fastapi, reactpy, y uvicorn.
4. **Configurar.env**: Crea un archivo.env en la raíz del proyecto y completa todas las variables de entorno necesarias definidas en src/common/utils/config_manager.py. Presta especial atención a:  
   * Credenciales de bases de datos (SQL_SAM_*, SQL_RPA360_*).  
   * Credenciales de la API de A360 (AA_URL, AA_USER, AA_PWD).  
   * **Credenciales de la API de Clouders (CLOUDERS_API_URL, CLOUDERS_AUTH)**.  
   * El token para el servicio de callbacks (CALLBACK_TOKEN).  
5. **Base de Datos**: Aplica el script SAM.sql a tu instancia de SQL Server.  
6. **Firewall**: Asegura que los puertos de los servicios web (Callbacks, Interfaz Web) estén abiertos.

## **▶️ Despliegue y Ejecución (NSSM)**

Para un entorno de producción, se recomienda ejecutar los servicios utilizando NSSM. La configuración para cada servicio es similar:

1. **Servicio SAM-Balanceador:**  
   * **Aplicación:** python.exe (ruta completa al ejecutable dentro del entorno virtual).  
   * **Argumentos:** C:\ruta\a\SAM_PROJECT_ROOT\src\balanceador\run_balanceador.py.  
   * **Directorio de Inicio:** C:\ruta\a\SAM_PROJECT_ROOT.

*(Repetir configuración para los otros servicios: Lanzador, Callback, InterfazWeb)*

## **🐛 Troubleshooting Básico**

* **Verificar Logs**: Revisa los archivos de log (sam_balanceador_app.log, etc.) en el directorio configurado en LOG_DIRECTORY. Aumenta el LOG_LEVEL a DEBUG para obtener más detalles.  
* **Conectividad de Base de Datos**: Asegúrate de que las credenciales y los hosts de SQL Server sean correctos.  
* **Balanceador no asigna/desasigna VMs**:  
  * Revisa los logs del Balanceador para entender las decisiones del algoritmo de pools, el desborde y el CoolingManager.  
  * Verifica la carga de trabajo detectada desde SQL y la API de Clouders.  
  * Asegúrate de que las variables CLOUDERS_API_URL y CLOUDERS_AUTH en el.env son correctas y que hay conectividad con la API.

  * **Lanzador no inicia robots**:  
  * Verifica que no te encuentres dentro de la ventana de Pausa de Lanzamiento configurada en el .env (`LANZADOR_PAUSA_INICIO_HHMM` y L`ANZADOR_PAUSA_FIN_HHMM`).  
  * Asegúrate de que la sincronización de tablas esté funcionando y que los robots y equipos tengan el estado Activo correcto en sus respectivas tablas.

* **Callbacks No Llegan**:  
  * La URL de callback configurada en A360 debe ser accesible y apuntar al host/puerto del Servicio de Callbacks.  
  * El CALLBACK_TOKEN en tu.env debe coincidir con el token en el header X-Authorization de la llamada en A360.
  
  * **Interfaz Web no carga o no responde**: Asegúrate de que el servicio SAM-InterfazWeb esté corriendo. Verifica en los logs si el servidor Uvicorn se inició correctamente y si hay errores de conexión a la base de datos.
  