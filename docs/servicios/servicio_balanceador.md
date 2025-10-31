# **Documentación Técnica: Servicio Balanceador**

**Módulo:** sam.balanceador

## **1. Propósito**

El **Servicio Balanceador** es un componente estratégico del ecosistema SAM. Su responsabilidad principal es monitorear la carga de trabajo pendiente (demanda) y la capacidad de procesamiento de los equipos (oferta) para reasignar dinámicamente los robots a diferentes "Pools" de ejecución.

El objetivo es optimizar el uso de licencias y la capacidad de los equipos, asegurando que los robots de alta prioridad tengan los recursos necesarios.

## **2. Arquitectura y Componentes**

El servicio opera en un bucle continuo y utiliza un diseño modular para la toma de decisiones, separando la obtención de datos de la lógica de balanceo.

### **Componentes Principales**

* **BalanceadorService (service/main.py)**:  
  * **Rol:** Orquestador.  
  * **Descripción:** Gestiona el bucle principal del servicio. En cada ciclo, invoca a los "Proveedores de Carga" para recolectar el estado actual del sistema y luego pasa esta información al AlgoritmoBalanceo para que tome decisiones.  
* **Proveedores de Carga (service/proveedores.py)**:  
  * **Rol:** Recolección de Datos.  
  * **Descripción:** Son clases responsables de consultar las diferentes fuentes de datos (APIs, bases de datos) para determinar la "carga" o demanda de trabajo.  
  * **Implementaciones:**  
    * CloudersProveedor: Consulta la API de Clouders (usando CloudersClient) para obtener el número de "tickets" pendientes para los robots mapeados.  
    * RPA360Proveedor: Consulta la base de datos histórica de RPA360 (usando HistoricoClient) para obtener la profundidad de la cola (ítems en "work queue") de los robots mapeados.  
* **AlgoritmoBalanceo (service/algoritmo_balanceo.py)**:  
  * **Rol:** Cerebro de Decisión.  
  * **Descripción:** Recibe el "estado global" (la información de carga de todos los proveedores) y ejecuta la lógica de balanceo.  
* **EstrategiaBalanceo (service/algoritmo_balanceo.py)**:  
  * **Rol:** Lógica de Cálculo.  
  * **Descripción:** Componente utilizado por el AlgoritmoBalanceo para calcular las *decisiones* específicas (ej. "mover Robot X al Pool Y") basándose en la carga y la configuración de aislamiento (BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO).  
* **CoolingManager (service/cooling_manager.py)**:  
  * **Rol:** Gestor de Enfriamiento.  
  * **Descripción:** Evita que el balanceador tome acciones sobre el mismo pool repetidamente. Cuando el algoritmo decide mover un robot, este manager pone al pool afectado en un período de "enfriamiento" (BALANCEADOR_COOLING_PERIOD_SEG), durante el cual no se pueden realizar otras acciones sobre él.

## **3. Flujo de Datos**

El flujo es un ciclo que se repite según el intervalo configurado:

1. BalanceadorService inicia su bucle.  
2. Consulta a todos los proveedores de carga configurados en BALANCEADOR_PROVEEDORES_CARGA (ej. 'clouders', 'rpa360').  
3. Toda la información de carga se consolida en un estado_global.  
4. El estado_global se pasa a AlgoritmoBalanceo.ejecutar_balanceo().  
5. El algoritmo usa EstrategiaBalanceo para generar una lista de *decisiones* (qué robot mover a qué pool).  
6. Para cada decisión, el algoritmo consulta al CoolingManager para saber si el pool afectado está en período de enfriamiento.  
7. Si el pool *no* está en enfriamiento, el algoritmo invoca al conector de base de datos para aplicar el cambio (específicamente, llama al método _db_connector.actualizar_pool_robot()).  
8. Si la actualización es exitosa, se informa al CoolingManager para que inicie el período de enfriamiento para ese pool.  
9. El BalanceadorService espera el tiempo definido en BALANCEADOR_INTERVALO_CICLO_SEG y el ciclo se repite.

## **4. Variables de Entorno Requeridas (.env)**

Este servicio depende de las siguientes variables. Dado que corre bajo NSSM, **cualquier cambio en estas variables requiere un reinicio del servicio** para que tenga efecto.

### **Configuración del Balanceador**

* BALANCEADOR_INTERVALO_CICLO_SEG  
  * **Propósito:** Intervalo en segundos entre cada ciclo de balanceo.  
  * **Efecto:** Requiere reinicio.  
* BALANCEADOR_COOLING_PERIOD_SEG  
  * **Propósito:** Segundos que un pool debe esperar en "enfriamiento" después de una acción de balanceo antes de poder recibir otra.  
  * **Efecto:** Requiere reinicio.  
* BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO  
  * **Propósito:** true o false. Define si los pools de aislamiento pueden tomar carga de otros pools si están ociosos.  
  * **Efecto:** Requiere reinicio.  
* BALANCEADOR_PROVEEDORES_CARGA  
  * **Propósito:** Lista separada por comas de los proveedores de carga a utilizar (ej. clouders,rpa360).  
  * **Efecto:** Requiere reinicio.  
* BALANCEADOR_DEFAULT_TICKETS_POR_EQUIPO  
  * **Propósito:** Valor numérico que define la capacidad de procesamiento (tickets) de un equipo si no se puede calcular de otra forma.  
  * **Efecto:** Requiere reinicio.  
* MAPA_ROBOTS  
  * **Propósito:** Un string JSON que mapea nombres de robots (clave) a identificadores de "work queue" (valor). Usado por RPA360Proveedor.  
  * **Efecto:** Requiere reinicio.

### **Configuración API Clouders**

* CLOUDERS_API_URL  
  * **Propósito:** URL base de la API de Clouders.  
  * **Efecto:** Requiere reinicio.  
* CLOUDERS_AUTH  
  * **Propósito:** Credencial de autenticación (ej. Basic ...) para la API de Clouders.  
  * **Efecto:** Requiere reinicio.  
* CLOUDERS_VERIFY_SSL  
  * **Propósito:** true o false. Define si se debe verificar el certificado SSL de la API de Clouders.  
  * **Efecto:** Requiere reinicio.  
* CLOUDERS_API_TIMEOUT  
  * **Propósito:** Segundos de espera para las peticiones a la API de Clouders.  
  * **Efecto:** Requiere reinicio.

### **Configuración Bases de Datos**

* SQL_SAM_DRIVER, SQL_SAM_HOST, SQL_SAM_DB_NAME, SQL_SAM_UID, SQL_SAM_PWD  
  * **Propósito:** Credenciales para conectarse a la base de datos de **SAM** (para actualizar los pools de robots).  
  * **Efecto:** Requiere reinicio.  
* SQL_RPA360_DRIVER, SQL_RPA360_HOST, SQL_RPA360_DB_NAME, SQL_RPA360_UID, SQL_RPA360_PWD  
  * **Propósito:** Credenciales para conectarse a la base de datos de **RPA360** (usado por HistoricoClient para leer las colas).  
  * **Efecto:** Requiere reinicio.

### **Configuración de Logging**

* LOG_DIRECTORY  
  * **Propósito:** Carpeta donde se guardarán los archivos de log.  
  * **Efecto:** Requiere reinicio.  
* LOG_LEVEL  
  * **Propósito:** Nivel de detalle del log (ej. INFO, DEBUG).  
  * **Efecto:** Requiere reinicio.  
* APP_LOG_FILENAME_BALANCEADOR  
  * **Propósito:** Nombre específico del archivo de log para este servicio.  
  * **Efecto:** Requiere reinicio.

## **5. Ejecución**

Para ejecutar el servicio en un entorno de desarrollo:

uv run -m sam.balanceador

