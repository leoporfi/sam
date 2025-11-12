# **Documentación Técnica: Servicio Lanzador**

**Módulo:** sam.lanzador

## **1. Propósito**

El **Servicio Lanzador** es el componente orquestador central del ecosistema SAM. Su responsabilidad es gestionar el ciclo de vida completo de las ejecuciones de robots y mantener la sincronización de las entidades maestras (robots, usuarios, equipos) con Automation 360.

Es un servicio de fondo (demonio) asíncrono que opera en múltiples bucles paralelos para:

1. Lanzar nuevas ejecuciones programadas.  
2. Conciliar el estado de las ejecuciones en curso.  
3. Sincronizar los datos maestros de A360 con la base de datos de SAM.

## **2. Arquitectura y Componentes**

El servicio sigue un patrón de **Inyección de Dependencias** y opera de forma **asíncrona**. La clase principal (LanzadorService) gestiona tres bucles de tareas independientes que se ejecutan en paralelo, cada uno con su propio intervalo de tiempo.

### **Componentes Principales**

* **LanzadorService (service/main.py)**:  
  * **Rol:** Orquestador Asíncrono.  
  * **Descripción:** Gestiona el ciclo de vida del servicio. Sus tareas son:  
    1. Inicializar y recibir todas las dependencias (los "cerebros" y clientes).  
    2. Lanzar tres tareas (Tasks) de asyncio que se ejecutan concurrentemente: _run_launcher_cycle, _run_sync_cycle y _run_conciliador_cycle.  
    3. Cada tarea se ejecuta, espera un intervalo (configurable) y se repite, independientemente de las otras.  
    4. Gestionar el cierre ordenado (graceful shutdown) para detener todos los bucles.  
* **Desplegador (service/desplegador.py)**:  
  * **Rol:** Cerebro de Despliegue.  
  * **Descripción:** Encapsula la lógica para iniciar nuevos robots.  
    1. Consulta la base de datos (SP dbo.ObtenerRobotsEjecutables) para obtener los robots que deben ejecutarse.  
    2. Verifica si el servicio está en una "ventana de pausa" operacional (configurable).  
    3. Obtiene credenciales del API Gateway (ApiGatewayClient) para usarlas en la URL de callback.  
    4. Llama al método desplegar_bot_v4() del cliente de A360, inyectando la URL y cabeceras de callback.  
    5. Si el despliegue es exitoso, **inserta un nuevo registro** en dbo.Ejecuciones con el estado DEPLOYED y el deploymentId devuelto.  
    6. Maneja reintentos para fallos específicos (ej. dispositivo no activo).  
* **Sincronizador (service/sincronizador.py)**:  
  * **Rol:** Cerebro de Sincronización de Entidades.  
  * **Descripción:** Su única responsabilidad es delegar la lógica de sincronización de datos maestros a un componente común.  
    1. Invoca al SincronizadorComun, que es el encargado real de:  
    2. Consultar la API de A360 para obtener la lista actualizada de robots, usuarios y dispositivos.  
    3. Actualizar (hacer MERGE) estas entidades en las tablas maestras de la base de datos de SAM.  
  * **Nota:** Este componente *no* sincroniza estados de ejecución; esa es la tarea del Conciliador.  
* **Conciliador (service/conciliador.py)**:  
  * **Rol:** Cerebro de Conciliación de Estados.  
  * **Descripción:** Se encarga de verificar el estado de los robots que ya están en ejecución.  
    1. Busca en la BD todas las ejecuciones que no estén en un estado final (ej. DEPLOYED, RUNNING). (Nota: Esta búsqueda excluye ejecuciones en 'UNKNOWN' que hayan sido actualizadas recientemente, basándose en FechaUltimoUNKNOWN, para evitar consultas innecesarias).  
    2. Consulta la API de A360 (obtener_detalles_por_deployment_ids) para obtener el estado real de esos deploymentId.  
    3. **Manejo de Estados API:**
      * Si la API reporta un estado final (COMPLETED, RUN_FAILED, etc.), actualiza la BD, establece la `FechaFin` y resetea los intentos.
      * **Si la API reporta 'UNKNOWN'**: El servicio actualiza el `Estado` a 'UNKNOWN', registra la marca de tiempo en `FechaUltimoUNKNOWN` e incrementa `IntentosConciliadorFallidos`. **No se establece** `FechaFin`, tratando el estado como transitorio.
    4. Si un deploymentId no se encuentra en la API de A360 (un "deployment perdido"), incrementa un contador de intentos.  
    5. Si se supera un umbral de intentos (CONCILIADOR_MAX_INTENTOS_FALLIDOS) para un *deployment perdido*, marca la ejecución como `UNKNOWN` y registra `FechaUltimoUNKNOWN` para finalizar su ciclo de vida de conciliación.  
* **EmailAlertClient (common/mail_client.py)**:  
  * **Rol:** Notificador.  
  * **Descripción:** Utilizado por LanzadorService para enviar alertas por correo electrónico si ocurre un error crítico e irrecuperable en cualquiera de los bucles principales.

## **3. Flujo de Datos**

El servicio opera en tres flujos paralelos y continuos:

1. **Bucle de Lanzamiento (Intervalo corto, ej. 15 seg):**  
   * LanzadorService invoca a Desplegador.desplegar_robots_pendientes().  
   * Desplegador obtiene robots programados de la BD.  
   * Desplegador obtiene token de API Gateway.  
   * Desplegador llama a desplegar_bot_v4() de A360 (con la URL de callback).  
   * Desplegador inserta una nueva fila en dbo.Ejecuciones con estado DEPLOYED.  
2. **Bucle de Conciliación (Intervalo medio, ej. 15 min):**  
   * LanzadorService invoca a Conciliador.conciliar_ejecuciones().  
   * Conciliador obtiene ejecuciones "en curso" de la BD de SAM.  
   * Conciliador consulta la API de A360 para verificar sus estados.  
   * Conciliador actualiza las filas en SAM a COMPLETED, RUN_FAILED, o UNKNOWN según corresponda.  
3. **Bucle de Sincronización (Intervalo largo, ej. 1 hora):**  
   * LanzadorService invoca a Sincronizador.sincronizar_entidades().  
   * Sincronizador delega a SincronizadorComun.  
   * SincronizadorComun consulta la API de A360 para obtener todos los robots, usuarios y devices.  
   * SincronizadorComun actualiza las tablas maestras (Robots, Equipos) en la BD de SAM.  
   * Este bucle se puede deshabilitar con LANZADOR_HABILITAR_SYNC.

## **4. Variables de Entorno Requeridas (.env)**

Este servicio depende de las siguientes variables. Dado que corre bajo NSSM, **cualquier cambio en estas variables requiere un reinicio del servicio** para que tenga efecto.

### **Configuración del Lanzador**

* LANZADOR_INTERVALO_LANZAMIENTO_SEG  
  * **Propósito:** Intervalo en segundos entre cada ciclo de *lanzamiento* de robots.  
  * **Efecto:** Requiere reinicio.  
* LANZADOR_INTERVALO_CONCILIACION_SEG  
  * **Propósito:** Intervalo en segundos entre cada ciclo de *conciliación* de estados.  
  * **Efecto:** Requiere reinicio.  
* LANZADOR_INTERVALO_SINCRONIZACION_SEG  
  * **Propósito:** Intervalo en segundos entre cada ciclo de *sincronización* de entidades (robots, devices).  
  * **Efecto:** Requiere reinicio.  
* LANZADOR_HABILITAR_SYNC  
  * **Propósito:** Define si el bucle de sincronización de entidades (robots, devices) debe ejecutarse. true para activar, false para desactivar.  
  * **Efecto:** Requiere reinicio.  
* LANZADOR_BOT_INPUT_VUELTAS  
  * **Propósito:** Valor numérico que se pasa como input (in_NumRepeticion) al desplegar un bot.  
  * **Efecto:** Requiere reinicio.  
* LANZADOR_MAX_WORKERS  
  * **Propósito:** Límite de tareas concurrentes para el despliegue de robots en un solo ciclo.  
  * **Efecto:** Requiere reinicio.  
* LANZADOR_MAX_REINTENTOS_DEPLOY  
  * **Propósito:** Número de reintentos (adicionales al primer intento) si el despliegue falla por un error de dispositivo no activo.  
  * **Efecto:** Requiere reinicio.  
* LANZADOR_DELAY_REINTENTO_DEPLOY_SEG  
  * **Propósito:** Segundos de espera antes de reintentar un despliegue fallido (por dispositivo no activo).  
  * **Efecto:** Requiere reinicio.  
* LANZADOR_PAUSA_INICIO_HHMM / LANZADOR_PAUSA_FIN_HHMM  
  * **Propósito:** Define una ventana de "pausa operacional" (en formato HH:MM) durante la cual el Desplegador no lanzará nuevos robots.  
  * **Efecto:** Requiere reinicio.  
* CONCILIADOR_MAX_INTENTOS_FALLIDOS  
  * **Propósito:** Número de veces que el Conciliador debe fallar en encontrar un deploymentId en A360 antes de marcarlo como UNKNOWN.  
  * **Efecto:** Requiere reinicio.

### **Configuración de Automation Anywhere (A360)**

* AA_CR_URL  
  * **Propósito:** URL base de la Control Room (ej. https://control-room.com).  
  * **Efecto:** Requiere reinicio.  
* AA_CR_USER  
  * **Propósito:** Nombre de usuario del bot API de SAM para autenticarse contra A360.  
  * **Efecto:** Requiere reinicio.  
* AA_CR_API_KEY  
  * **Propósito:** Clave API (o contraseña) para el usuario AA_CR_USER. Se prioriza la API Key.  
  * **Efecto:** Requiere reinicio.  
* AA_API_TIMEOUT_SECONDS  
  * **Propósito:** Tiempo máximo (en segundos) de espera para las peticiones a la API de A360.  
  * **Efecto:** Requiere reinicio.  
* AA_URL_CALLBACK  
  * **Propósito:** URL completa del servicio de Callback a la que A360 debe notificar cuando un bot finaliza.  
  * **Efecto:** Requiere reinicio.

### **Configuración Base de Datos (SAM)**

* SQL_SAM_DRIVER  
  * **Propósito:** Driver ODBC para la conexión (ej. {ODBC Driver 17 for SQL Server}).  
  * **Efecto:** Requiere reinicio.  
* SQL_SAM_HOST  
  * **Propósito:** Dirección IP o Hostname del servidor SQL Server.  
  * **Efecto:** Requiere reinicio.  
* SQL_SAM_DB_NAME  
  * **Propósito:** Nombre de la base de datos de SAM.  
  * **Efecto:** Requiere reinicio.  
* SQL_SAM_UID / SQL_SAM_PWD  
  * **Propósito:** Credenciales (usuario y contraseña) para la base de datos SAM.  
  * **Efecto:** Requiere reinicio.  
* (Variables de reintento de SQL: SQL_SAM_MAX_REINTENTOS_QUERY, SQL_SAM_DELAY_REINTENTO_QUERY_BASE_SEG, SQL_SAM_CODIGOS_SQLSTATE_REINTENTABLES)

### **Configuración API Gateway (para Callback)**

* API_GATEWAY_URL  
  * **Propósito:** URL del endpoint de autenticación (token) del API Gateway.  
  * **Efecto:** Requiere reinicio.  
* API_GATEWAY_CLIENT_ID / API_GATEWAY_CLIENT_SECRET  
  * **Propósito:** Credenciales para obtener el token de autorización del API Gateway.  
  * **Efecto:** Requiere reinicio.  
* API_GATEWAY_SCOPE  
  * **Propósito:** El "scope" o permiso solicitado al API Gateway.  
  * **Efecto:** Requiere reinicio.  
* CALLBACK_TOKEN  
  * **Propósito:** Token estático (X-Authorization) que también se añade a las cabeceras del callback, además del token dinámico del API Gateway.  
  * **Efecto:** Requiere reinicio.

### **Configuración de Alertas (Email)**

* EMAIL_SMTP_SERVER / EMAIL_SMTP_PORT  
  * **Propósito:** Servidor SMTP y puerto para el envío de correos de alerta.  
  * **Efecto:** Requiere reinicio.  
* EMAIL_FROM  
  * **Propósito:** Dirección de correo remitente para las alertas.  
  * **Efecto:** Requiere reinicio.  
* EMAIL_RECIPIENTS  
  * **Propósito:** Lista de destinatarios (separados por comas) para las alertas de errores críticos.  
  * **Efecto:** Requiere reinicio.

### **Configuración de Logging**

* LOG_DIRECTORY  
  * **Propósito:** Carpeta donde se guardarán los archivos de log.  
  * **Efecto:** Requiere reinicio.  
* LOG_LEVEL  
  * **Propósito:** Nivel de detalle del log (ej. INFO, DEBUG).  
  * **Efecto:** Requiere reinicio.  
* APP_LOG_FILENAME_LANZADOR  
  * **Propósito:** Nombre específico del archivo de log para este servicio.  
  * **Efecto:** Requiere reinicio.

## **5. Ejecución**

Para ejecutar el servicio en un entorno de desarrollo:

Bash

uv run -m sam.lanzador

