# **Proyecto SAM: Sistema Automático de Robots**

## **📜 Visión General**

**SAM (Sistema Automático de Robots)** es un proyecto integral diseñado para la **implementación, distribución y orquestación automática de robots RPA (Robotic Process Automation) en máquinas virtuales (VMs)**. El sistema se compone de cuatro servicios independientes que operan en conjunto y se ejecutan de forma continua, gestionados a través de una configuración centralizada y un conjunto de módulos comunes que garantizan la estabilidad y mantenibilidad del ecosistema.  
SAM centraliza la gestión de robots, sincroniza información de forma inteligente con **Automation Anywhere A360 (AA360)**, lanza ejecuciones según la demanda o programaciones, y optimiza la asignación de recursos (VMs) basándose en la carga de trabajo pendiente. Adicionalmente, cuenta con una **interfaz web de mantenimiento** para gestionar la configuración y las operaciones del sistema directamente desde un navegador.  

---
## **🚀 Servicios Principales**

El proyecto SAM se articula en torno a los siguientes servicios independientes:

### **🤖 Servicio Lanzador**

Actúa como el brazo ejecutor y el cerebro de sincronización con el Control Room de AA360. Es un servicio multifacético con tres responsabilidades clave que se ejecutan en ciclos independientes y configurables:

* **Sincronización Inteligente de Tablas Maestras**: Mantiene las tablas dbo.Robots y dbo.Equipos de SAM actualizadas con la realidad de AA360.  
  * **Sincronización de Equipos (VMs)**: Obtiene la lista de *devices* conectados desde A360, cruza la información con los datos de los usuarios asignados para determinar la licencia (`ATTENDEDRUNTIME`, etc.) y calcula un estado de actividad (`Activo_SAM`) antes de actualizar la tabla dbo.Equipos mediante una operación MERGE.  
  * **Sincronización de Robots**: Importa únicamente los *taskbots* que cumplen con criterios específicos de nombre y ubicación en el repositorio de A360, aplicando filtros por prefijo de nombre (`P\*`) y una expresión regular para asegurar la consistencia del catálogo de robots en SAM.  
* **Lanzamiento de Robots**: Es el núcleo ejecutor del servicio.  
  * **Lógica Centralizada en BD**: Su comportamiento se basa en los resultados del Stored Procedure dbo.ObtenerRobotsEjecutables, que determina qué robots deben ejecutarse en cada momento, ya sea por programación o por asignación dinámica del balanceador.  
  * **Ejecución Concurrente y con Reintentos**: Lanza múltiples robots en paralelo utilizando un ThreadPoolExecutor. Si un despliegue falla por una causa reintentable (ej. un problema de red o de dispositivo temporalmente ocupado), el sistema intentará lanzar el robot una segunda vez tras una breve pausa.  
  * **Pausa Operacional**: Se puede configurar una ventana de tiempo (ej. 23:00 a 05:00) durante la cual el servicio de lanzamiento se pausará para no iniciar nuevas ejecuciones, facilitando tareas de mantenimiento.  
* **Conciliación de Estados**: De forma periódica, el Conciliador revisa las ejecuciones que figuran como activas en la base de datos de SAM. Consulta su estado real en A360 y actualiza los registros locales. Si una ejecución ya no se encuentra en la API de A360 (posiblemente finalizada hace tiempo), se marca con el estado UNKNOWN para evitar que quede indefinidamente "activa".

### **⚖️ Servicio Balanceador**

El servicio **Balanceador** se encarga de la gestión estratégica e inteligente de los recursos (VMs), asignándolos dinámicamente a los robots en función de la carga de trabajo real. Su objetivo es maximizar la eficiencia y el rendimiento del clúster de RPA.

#### **Adquisición de Carga y Pool de Recursos**

Para tomar decisiones, el Balanceador primero recopila toda la información necesaria sobre los recursos disponibles y la demanda existente:

* **Gestión del Pool de VMs**: Identifica las máquinas virtuales disponibles para asignación dinámica consultando la tabla `dbo.Equipos`. Un equipo se considera parte del pool dinámico solo si cumple con todos estos criterios:  
  * Tiene una licencia de tipo `ATTENDEDRUNTIME`.  
  * Está marcado como `Activo_SAM = 1`.  
  * Tiene el flag `PermiteBalanceoDinamico = 1`.  
  * No tiene asignaciones fijas (es decir, ni `Reservado = 1` ni `EsProgramado = 1` en `dbo.Asignaciones`).  
* **Adquisición de Carga de Trabajo Concurrente**: Determina la cantidad de "tickets" o tareas pendientes para cada robot. Para ser eficiente, obtiene esta información de **dos fuentes de datos distintas de forma paralela** usando un ThreadPoolExecutor:  
  * **SQL Server (rpa360)**: Ejecuta el Stored Procedure `dbo.usp_obtener_tickets_pendientes_por_robot` en una base de datos externa.  
  * **MySQL (clouders)**: Utiliza un cliente SSH (MySQLSSHClient) que gestiona un pool de conexiones, ejecuta comandos de forma remota y parsea los resultados para obtener la carga desde una base de datos MySQL remota.  
* **Mapeo de Nombres de Robots**: Utiliza un diccionario de mapeo definido en la variable de entorno `MAPA_ROBOTS` para conciliar los nombres de los robots que vienen de la base de datos "clouders" con los nombres estándar utilizados en SAM, asegurando la consistencia.

#### **Lógica de Balanceo Avanzada y Multifásica**

El núcleo del servicio es su algoritmo de balanceo, encapsulado en la clase Balanceo, que se ejecuta en varias fases secuenciales para garantizar un orden lógico en la toma de decisiones:

* **Pre-Fase: Validación de Asignaciones**: Antes de cualquier cálculo, el sistema verifica que todos los equipos asignados dinámicamente en ciclos anteriores sigan siendo válidos (es decir, que aún pertenezcan al pool dinámico). Si un equipo ya no es válido, se intenta desasignar.  
* **Fase 0: Limpieza de Robots No Candidatos**: Libera todos los equipos asignados dinámicamente a robots que han sido marcados como `Activo = 0` o `EsOnline = 0` en la tabla `dbo.Robots`. Esto asegura que los recursos no queden bloqueados por robots que no están operativos.  
* **Fase 1: Satisfacción de Mínimos**: Asegura que cada robot candidato con carga de trabajo alcance su MinEquipos funcional, asignándole máquinas del pool de recursos libres y priorizando según la PrioridadBalanceo.  
* **Fase 2: Desasignación de Excedentes Reales**: Evalúa los robots que, tras la Fase 1, tienen más equipos de los que necesitan para su carga de trabajo actual. Los equipos sobrantes se desasignan y devuelven al pool libre.  
* **Fase 3: Asignación de Demanda Adicional**: Los equipos que queden en el pool libre se distribuyen entre los robots que todavía tienen demanda de trabajo, ordenados por prioridad y necesidad, hasta alcanzar su necesidad calculada o su `MaxEquipos`.

#### **Mecanismos de Control y Auditoría**

Para garantizar un funcionamiento estable y transparente, el Balanceador implementa dos mecanismos clave:

* **Mecanismo de Enfriamiento (`CoolingManager`)**: Previene el "thrashing" (asignar y desasignar recursos a un mismo robot de forma repetida y frecuente). Impone un período de enfriamiento después de una operación de ampliación o reducción para un robot. Este enfriamiento puede ser ignorado si se detecta una variación drástica en la carga de tickets (por defecto, >30% de aumento o >40% de disminución), permitiendo una reacción rápida ante cambios significativos.  
* **Registro Histórico (`HistoricoBalanceoClient`)**: Cada decisión de asignación o desasignación, junto con su justificación (ej. `ASIGNAR_MIN_POOL`, `DESASIGNAR_EXC_REAL`, `DESASIGNAR_INACTIVO_OFFLINE`), se registra en la tabla `dbo.HistoricoBalanceo`. Esto proporciona una trazabilidad completa de todas las acciones del Balanceador para fines de auditoría y análisis de rendimiento.

### **📞 Servicio de Callbacks**

Un servidor web ligero y dedicado cuya única responsabilidad es escuchar notificaciones (callbacks) en tiempo real enviadas por AA360 cuando un robot finaliza su ejecución.

* **API Segura y Definida**: El endpoint está formalmente definido por una especificación **OpenAPI (swagger.yaml)**. Requiere un token de seguridad en el encabezado X-Authorization para validar que la llamada es legítima y prevenir peticiones no autorizadas.  
* **Procesamiento Inmediato**: Al recibir un callback válido, actualiza inmediatamente el estado de la ejecución en la tabla dbo.Ejecuciones y almacena el payload completo del callback en la columna CallbackInfo para una auditoría completa.  
* **Servidor de Producción**: Utiliza un servidor WSGI de producción (waitress) para manejar múltiples peticiones concurrentes de manera eficiente y estable.

### **🖥️ Interfaz Web de Mantenimiento**

Una aplicación web que provee una interfaz de usuario para la administración y monitorización del sistema SAM. Permite a los operadores realizar tareas de mantenimiento críticas sin necesidad de acceder directamente a la base de datos.

* **Gestión de Robots**: Permite visualizar la lista completa de robots con filtros y paginación, modificar sus propiedades (ej. `Activo`, `EsOnline`, `PrioridadBalanceo`, `MinEquipos`), y crear nuevos robots.  
* **Gestión de Asignaciones**: Ofrece un modal interactivo para asignar o desasignar equipos (VMs) a un robot de forma manual, marcándolos como Reservado para excluirlos del balanceo dinámico.  
* **Gestión de Programaciones**: Proporciona una interfaz completa para crear, visualizar, editar y eliminar programaciones de ejecución (diarias, semanales, mensuales o específicas) para cualquier robot, asignando los equipos correspondientes para cada tarea programada.

---

## **🛠️ Características Técnicas Clave**

* **Módulos Comunes Centralizados**: El proyecto se apoya en un directorio common que contiene utilidades de alta calidad compartidas por todos los servicios.  
  * **Gestión de Configuración Jerárquica**: El sistema utiliza un ConfigLoader que carga la configuración desde archivos .env a nivel de proyecto y de servicio, permitiendo sobreescrituras específicas para cada entorno.  
  * **Data Access Layer (DatabaseConnector)**: La interacción con la base de datos se realiza a través de un cliente SQL que ofrece conexiones seguras por hilo (thread-safe), reconexión automática y un mecanismo inteligente de **reintentos con backoff exponencial** para errores transitorios de base de datos (ej. deadlocks), lo que aumenta enormemente la resiliencia del sistema.  
  * **Logging de Producción**: El logging está estandarizado y utiliza un manejador de rotación de archivos (TimedRotatingFileHandler) que previene caídas del servicio por problemas de bloqueo de archivos en entornos Windows.  
* **Integración con Automation Anywhere A360**: Cliente API (`AutomationAnywhereClient`) con gestión de token de autenticación automática y thread-safe, paginación completa para obtener todos los registros, y manejo detallado de errores.  
* **Algoritmo de Balanceo Dinámico**: Lógica multifásica que incluye limpieza, satisfacción de mínimos, desasignación de excedentes y asignación de demanda, gobernado por un `CoolingManager` para evitar *thrashing*.  
* **Procesamiento Concurrente**: Uso extensivo de `ThreadPoolExecutor` en el Lanzador y Balanceador para realizar tareas de I/O (llamadas a API, consultas a bases de datos) en paralelo, mejorando el rendimiento.  
* **API Segura para Callbacks**: El servicio de callbacks expone una API segura con autenticación por token, siguiendo la especificación OpenAPI.  
* **Cierre Controlado (Graceful Shutdown)**: Todos los servicios manejan señales del sistema (SIGTERM, SIGINT) para finalizar tareas en curso y cerrar conexiones de forma segura.

---

## **📂 Estructura del Proyecto**

```
SAM_PROJECT_ROOT/  
├── src/  
│   ├── balanceador/             # Código del Servicio Balanceador  
│   │   ├── clients/  
│   │   ├── database/  
│   │   └── service/  
│   ├── callback/                # Código del Servicio de Callbacks
│   │   └── service/  
│   ├── interfaz_web/           # Código de la Interfaz Web de Mantenimiento  
│   │   ├── components/  
│   │   ├── hooks/  
│   │   └── services/  
│   ├── lanzador/                # Código del Servicio Lanzador  
│   │   ├── clients/  
│   │   └── service/  
│   └── common/                  # Módulos compartidos por todos los servicios  
│       ├── database/  
│       └── utils/  
├── .env                         # Archivo principal de configuración
├── requirements.txt             # Dependencias Python
├── SAM.sql                      # Script DDL para la base de datos SAM  
└── README.md                    # Este archivo
```

## **📋 Prerrequisitos**

* Python 3.8 o superior.  
* Acceso a una instancia de Automation Anywhere A360 Control Room.  
* Una base de datos SQL Server con el esquema de `SAM.sql` aplicado.  
* Un servidor SMTP accesible para el envío de alertas por correo.  
* **NSSM (Non-Sucking Service Manager)** o una herramienta similar para ejecutar los servicios en producción en Windows.

---

## **⚙️ Configuración e Instalación**

1. **Clonar/Descomprimir** el repositorio.  
2. **Crear y activar un entorno virtual** de Python.  
3. **Instalar Dependencias:**  
    ```Bash  
    pip install -r requirements.txt
    ```
   Asegúrate de que `requirements.txt` incluya: `requests`, `pyodbc`, `python-dotenv`, `schedule`, `paramiko`, `pytz`, `python-dateutil`, `waitress`, `fastapi`, `reactpy`, y `uvicorn`.  
4. **Configurar `.env`**: Crea un archivo `.env` en la raíz del proyecto y completa todas las variables de entorno necesarias definidas en `src/common/utils/config_manager.py`. Presta especial atención a las credenciales de bases de datos, API de A360, y el `CALLBACK_TOKEN`.  
5. **Base de Datos**: Aplica el script `SAM.sql` a tu instancia de SQL Server para crear todas las tablas, vistas y Stored Procedures necesarios.  
6. **Firewall**: Asegura que el puerto del Servicio de Callbacks (ej. 8008\ y el de la Interfaz Web (ej. 8080) estén abiertos para las conexiones necesarias.

---

## **▶️ Despliegue y Ejecución (NSSM)**

Para un entorno de producción, se recomienda ejecutar los **cuatro servicios** como servicios de Windows utilizando NSSM.

1. **Servicio SAM-Lanzador:**  
   * **Aplicación:** `python.exe` (ruta completa).  
   * **Argumentos:** `C:\ruta\a\SAM_PROJECT_ROOT\src\lanzador\run_lanzador.py`.  
   * **Directorio de Inicio:** `C:\ruta\a\SAM_PROJECT_ROOT\`.  
2. **Servicio SAM-Balanceador:**  
   * **Aplicación:** python.exe.  
   * **Argumentos:** `C:\ruta\a\SAM_PROJECT_ROOT\src\balanceador\run_balanceador.py`.  
   * **Directorio de Inicio:** `C:\ruta\a\SAM_PROJECT_ROOT\`.  
3. **Servicio SAM-Callback:**  
   * **Aplicación:** python.exe.  
   * **Argumentos:** `C:\ruta\a\SAM_PROJECT_ROOT\src\callback\run_callback.py`.  
   * **Directorio de Inicio:** `C:\ruta\a\SAM_PROJECT_ROOT\`.  
4. **Servicio SAM-InterfazWeb:**  
   * **Aplicación:** python.exe.  
   * **Argumentos:** `C:\ruta\a\SAM_PROJECT_ROOT\src\interfaz_web\run_interfaz_web.py`.  
   * **Directorio de Inicio:** `C:\ruta\a\SAM_PROJECT_ROOT\`.

---

## **🐛 Troubleshooting Básico**

* **Verificar Logs**: Revisa los archivos de log generados por cada servicio (ej. `sam_lanzador_app.log`, `sam_callback_server.log`, etc.) en el directorio configurado en `LOG_DIRECTORY`. Aumenta el `LOG_LEVEL` a `DEBUG` en `.env` para obtener más detalles.  
* **Conectividad de Base de Datos**: Asegúrate de que las credenciales y los nombres de host/instancia para todas las bases de datos (SAM DB, RPA360 DB, Clouders MySQL) sean correctos y que haya conectividad de red.  
* **Callbacks No Llegan**:  
  * La URL de callback configurada en A360 debe ser públicamente accesible y apuntar al host y puerto del Servicio de Callbacks.  
  * El `CALLBACK_TOKEN` definido en tu archivo .env debe coincidir exactamente con el token configurado en el header X-Authorization de la llamada de callback en A360.  
* **Lanzador no inicia robots**:  
  * Verifica que no te encuentres dentro de la ventana de Pausa de Lanzamiento configurada en el .env (`LANZADOR_PAUSA_INICIO_HHMM` y L`ANZADOR_PAUSA_FIN_HHMM`).  
  * Asegúrate de que la sincronización de tablas esté funcionando y que los robots y equipos tengan el estado Activo correcto en sus respectivas tablas.  
* **Balanceador no asigna/desasigna VMs**: Revisa los logs del Balanceador para entender las decisiones del algoritmo y el CoolingManager. Verifica la carga de trabajo detectada y la configuración de MinEquipos/MaxEquipos/PrioridadBalanceo para los robots. Asegúrate que los robots candidatos para balanceo sean Activo \= 1 y EsOnline \= 1 en dbo.Robots.  
* **Interfaz Web no carga o no responde**: Asegúrate de que el servicio SAM-InterfazWeb esté corriendo. Verifica en los logs si el servidor Uvicorn se inició correctamente y si hay errores de conexión a la base de datos.