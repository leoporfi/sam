# **Documentación Técnica: Servicio Balanceador**

**Módulo:** sam.balanceador

## **1. Propósito**

El **Servicio Balanceador** es el componente estratégico del ecosistema SAM. A diferencia del Lanzador, que es puramente ejecutivo, el Balanceador actúa como el "cerebro táctico" del sistema. Su responsabilidad es analizar el estado actual de la demanda (robots en cola) y la oferta (recursos disponibles) para optimizar la asignación de licencias y la capacidad de ejecución de manera proactiva.

Opera como un servicio de fondo que, a intervalos regulares, evalúa el ecosistema y toma decisiones para maximizar la eficiencia y el rendimiento.

## **2. Arquitectura y Componentes**

Al igual que los otros servicios, sigue un estricto patrón de **Inyección de Dependencias** y **Separación de Responsabilidades**.

### **Componentes Principales**

* **BalanceadorService (service/main.py)**:  
  * **Rol:** Orquestador.  
  * **Descripción:** Gestiona el ciclo de vida del servicio.  
    1. Inicializa y recibe todas las dependencias necesarias (DatabaseConnector, clientes de APIs, etc.).  
    2. Ejecuta un bucle principal a un intervalo configurable (ej. cada 2 minutos, según BALANCEADOR_INTERVALO_CICLO_SEG).  
    3. En cada ciclo, invoca a los proveedores de carga (ej. Clouders, RPA360) para recolectar la demanda.  
    4. Pasa los datos recolectados al AlgoritmoBalanceo para su procesamiento.  
    5. Recibe las "decisiones" o "acciones" del algoritmo y las ejecuta (ej. actualizando la base de datos).  
* **Proveedores de Carga (service/proveedores.py)**:  
  * **Rol:** Proveedor de Datos de Demanda.  
  * **Descripción:** Su única función es actuar como una fachada para recolectar la información de "demanda" (tickets pendientes) de sistemas externos. Consulta a los clientes de API (Clouders) o bases de datos (RPA360) para obtener la carga de trabajo de cada robot.  
* **AlgoritmoBalanceo (service/algoritmo_balanceo.py)**:  
  * **Rol:** Cerebro de Decisión.  
  * **Descripción:** Es el corazón del servicio. Recibe un objeto de datos consolidado de los proveedores y aplica un conjunto de reglas de negocio para determinar qué acciones se deben tomar. Es un componente puro: no realiza operaciones de I/O (red, disco, BD), solo procesa datos y devuelve un resultado.  
* **CoolingManager (service/cooling_manager.py)**:  
  * **Rol:** Gestor de Enfriamiento.  
  * **Descripción:** Ayuda al algoritmo a evitar la oscilación (tomar y deshacer la misma decisión repetidamente). Mantiene un registro de las decisiones recientes para asegurar que, por ejemplo, si se asigna un recurso, no se intente desasignar inmediatamente en el siguiente ciclo.  
* **HistoricoBalanceoClient (service/historico_client.py)**:  
  * **Rol:** Registrador de Decisiones.  
  * **Descripción:** Componente dedicado a escribir un registro de auditoría en la tabla HistoricoBalanceo por cada decisión que toma el algoritmo.

## **3. Lógica del Algoritmo**

El AlgoritmoBalanceo toma decisiones basadas en la comparación entre la demanda de ejecución y la oferta de recursos.

1. **Cálculo de la Demanda:** Analiza la cantidad de robots en estado PENDIENTE y los agrupa por los pools de recursos que requieren.  
2. **Cálculo de la Oferta:** Obtiene la lista de todos los pools de máquinas (equipos) disponibles y su estado actual (ej. cuántas licencias están en uso).  
3. **Proceso de Decisión:**  
   * **Asignación de Recursos:** Si detecta que hay más demanda que oferta para un pool específico (ej. 5 robots esperando pero solo 3 máquinas asignadas), generará acciones para asignar máquinas adicionales a ese pool, si hay disponibles.  
   * **Desasignación de Recursos:** Si detecta que la oferta supera con creces la demanda (ej. 10 máquinas asignadas a un pool pero solo 1 robot en cola), generará acciones para liberar máquinas de ese pool y devolverlas al estado disponible, optimizando el uso de licencias.  
   * **Priorización:** La lógica puede incluir reglas para priorizar ciertos pools o tipos de robots sobre otros en caso de escasez de recursos.

## **4. Flujo de Datos**

1. BalanceadorService inicia su bucle (schedule).  
2. Invoca a los Proveedores de Carga (Clouders, RPA360) en hilos separados para obtener la demanda.  
3. Consolida los resultados de todos los proveedores en un único diccionario de carga.  
4. Obtiene los Pools activos desde la base de datos SAM.  
5. BalanceadorService pasa la carga consolidada y los pools al AlgoritmoBalanceo.ejecutar_algoritmo_completo().  
6. El AlgoritmoBalanceo consulta el estado actual de equipos y asignaciones en la BD.  
7. El Algoritmo aplica su lógica (limpieza, balanceo interno, desborde) y llama a sus métodos internos (_realizar_asignacion_db, _realizar_desasignacion_db) para ejecutar los cambios.  
8. Cada cambio en la BD se registra usando el HistoricoBalanceoClient.  
9. El bucle espera el intervalo configurado (BALANCEADOR_INTERVALO_CICLO_SEG) y vuelve a empezar.

## **5. Variables de Entorno Requeridas**

El servicio Balanceador depende de varias variables de entorno definidas en el archivo .env para su correcta configuración.

### **5.1. Variables Principales**

| Variable(s) | Propósito en el Servicio Balanceador |
| :---- | :---- |
| **BALANCEADOR_INTERVALO_CICLO_SEG** | (Crítica) Define la frecuencia (en segundos) con la que se ejecuta el ciclo completo de balanceo. |
| **BALANCEADOR_COOLING_PERIOD_SEG** | (Crítica) Segundos que el algoritmo espera antes de volver a mover equipos de un robot para evitar cambios erráticos ("thrashing"). |
| **BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO** | (Crítica) Si es true, un pool solo puede usar sus propios equipos. Si es false, puede "tomar prestados" equipos del pool general. |
| **BALANCEADOR_PROVEEDORES_CARGA** | (Crítica) Lista separada por comas (ej. clouders,rpa360) que define qué sistemas consultará el balanceador para obtener la "demanda" (tickets pendientes). |
| **MAPA_ROBOTS** | Mapeo JSON para "traducir" nombres de robots de sistemas externos (como Clouders) a los nombres de robots en la BD de SAM. |
| **SQL_SAM_...** (HOST, DB_NAME, UID, PWD) | Credenciales de la base de datos principal de SAM, donde se leen los robots, equipos, pools y se escriben las asignaciones. |
| **SQL_RPA360_...** (HOST, DB_NAME, UID, PWD) | Credenciales de la base de datos de RPA360. Usada solo si rpa360 está en BALANCEADOR_PROVEEDORES_CARGA. |
| **CLOUDERS_API_...** (URL, AUTH, TIMEOUT) | Credenciales de la API de Clouders. Usada solo si clouders está en BALANCEADOR_PROVEEDORES_CARGA. |
| **LOG_...** (LEVEL, DIRECTORY, etc.) | Configuración general del sistema de logging (nivel de detalle, ubicación de archivos, etc.). |
| **EMAIL_...** (SMTP_SERVER, RECIPIENTS, etc.) | Configuración del servidor de correo para enviar alertas de error críticas. |

### **5.2. Actualización de Variables (Importante)**

Debido a la arquitectura del servicio (que sigue el patrón "Fábrica" e "Inyección de Dependencias"), toda la configuración se lee **una única vez al arrancar el servicio**.

**Todos los cambios** realizados en estas variables de entorno en el archivo .env **requieren un reinicio del Servicio Balanceador** para que tomen efecto. El servicio no detectará cambios en caliente.

## **6. Lógica de Selección de Equipos**

Para que el Balanceador considere a un equipo como "disponible" para asignarlo dinámicamente, el equipo debe cumplir las siguientes **tres condiciones** en la base de datos:

1. Equipos.Activo_SAM = 1  
2. Equipos.PermiteBalanceoDinamico = 1  
3. No debe tener una asignación "fija" (es decir, ningún registro en Asignaciones donde EsProgramado = 1 o Reservado = 1).

El servicio consulta esta lógica al inicio de cada ciclo para construir su pool de recursos disponibles.

## **7. Ejecución**

Para ejecutar el servicio en un entorno de desarrollo:

uv run -m sam.balanceador