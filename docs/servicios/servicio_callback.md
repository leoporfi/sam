# **Documentación Técnica: Servicio de Callback**

**Módulo:** sam.callback

## **1. Propósito**

El **Servicio de Callback** es un microservicio web (API) cuya única responsabilidad es recibir notificaciones *push* (webhooks) desde Automation 360 cuando una ejecución de robot finaliza.

Esto permite al ecosistema SAM registrar el estado final de un robot (ej. COMPLETED, RUN_FAILED) de forma inmediata, sin tener que esperar al próximo ciclo del Conciliador del Servicio Lanzador.

## **2. Arquitectura y Componentes**

El servicio es una API ligera construida con **FastAPI** que expone un único endpoint.

### **Componentes Principales**

* **FastAPI App (service/main.py)**:  
  * **Rol:** Servidor Web.  
  * **Descripción:** Configura y ejecuta un servidor uvicorn. Define el endpoint que recibirá las notificaciones.  
* **Endpoint de Callback (service/main.py)**:  
  * **Rol:** Receptor de Notificaciones.  
  * **Descripción:** Es un endpoint POST (la ruta es configurable, por defecto /api/callback) que espera un JSON con la estructura de CallbackPayload enviada por A360.  
* **AuthDependency (service/main.py)**:  
  * **Rol:** Gestor de Seguridad.  
  * **Descripción:** Una dependencia de FastAPI que se ejecuta en cada petición para validar la autenticidad de la llamada. Implementa una lógica de autenticación dual (ver sección 4).  
* **CallbackPayload (Modelo Pydantic)**:  
  * **Rol:** Modelo de Datos.  
  * **Descripción:** Valida que el JSON entrante contenga los campos esperados por A360 (como deploymentId, status, type).  
* **DatabaseConnector (common/database.py)**:  
  * **Rol:** Persistencia de Datos.  
  * **Descripción:** Se utiliza para invocar el método actualizar_ejecucion_desde_callback en la base de datos de SAM.

## **3. Flujo de Datos**

1. El **Servicio Lanzador** despliega un bot en A360 e inyecta la URL de este servicio (AA_URL_CALLBACK) en la petición.  
2. Cuando el bot finaliza en A360, A360 envía una petición POST al endpoint de callback (ej. /api/callback).  
3. AuthDependency intercepta la petición y valida las credenciales (Token estático y/o JWT) según el modo configurado.  
4. Si la autenticación es exitosa, FastAPI valida el cuerpo (JSON) de la petición contra el modelo CallbackPayload.  
5. El servicio invoca db_connector.actualizar_ejecucion_desde_callback(), pasando el deploymentId, el estado final y el JSON completo.  
6. La base de datos (mediante actualizar_ejecucion_desde_callback) actualiza la fila correspondiente en dbo.Ejecuciones, marcando el estado (ej. COMPLETED) y almacenando el JSON crudo en la columna CallbackInfo.  
7. El servicio devuelve un HTTP 200 OK a A360 para confirmar la recepción.

## **4. Seguridad (Autenticación)**

El endpoint de callback valida las peticiones entrantes usando una combinación de dos tokens. El comportamiento se controla mediante la variable CALLBACK_AUTH_MODE:

1. **Token Estático (X-Authorization):** Un token secreto compartido (definido en CALLBACK_TOKEN) que se envía en la cabecera X-Authorization.  
2. **Token Dinámico JWT (Authorization):** Un token Bearer (JWT) que es generado por el API Gateway (ApiGatewayClient) y validado por este servicio usando una clave pública (JWT_PUBLIC_KEY).

Los modos de autenticación (CALLBACK_AUTH_MODE) son:

* optional (Default): La petición es válida si **al menos uno** de los dos tokens (estático o JWT) está presente y es correcto.  
* required: La petición es válida solo si **ambos** tokens (estático y JWT) están presentes y son correctos.  
* none: No se realiza ninguna validación. **(No recomendado para producción)**.

## **5. Variables de Entorno Requeridas (.env)**

Este servicio depende de las siguientes variables. Dado que corre bajo NSSM, **cualquier cambio en estas variables requiere un reinicio del servicio** para que tenga efecto.

### **Configuración del Servidor**

* CALLBACK_SERVER_HOST  
  * **Propósito:** Dirección IP en la que el servidor FastAPI escuchará (ej. 0.0.0.0 para todas las interfaces).  
  * **Efecto:** Requiere reinicio.  
* CALLBACK_SERVER_PORT  
  * **Propósito:** Puerto en el que el servidor FastAPI escuchará (ej. 8008).  
  * **Efecto:** Requiere reinicio.  
* CALLBACK_SERVER_THREADS  
  * **Propósito:** Número de "workers" (hilos) que uvicorn utilizará para manejar peticiones concurrentes.  
  * **Efecto:** Requiere reinicio.  
* CALLBACK_ENDPOINT_PATH  
  * **Propósito:** La ruta de la URL para el endpoint de callback (ej. /api/callback).  
  * **Efecto:** Requiere reinicio.

### **Configuración de Seguridad y Autenticación**

* CALLBACK_AUTH_MODE  
  * **Propósito:** Define la lógica de validación de tokens (optional, required, none).  
  * **Efecto:** Requiere reinicio.  
* CALLBACK_TOKEN  
  * **Propósito:** El token secreto estático (API Key) esperado en la cabecera X-Authorization.  
  * **Efecto:** Requiere reinicio.  
* API_GATEWAY_CLIENT_ID  
  * **Propósito:** El Client ID del API Gateway, esperado en la cabecera x-ibm-client-id (usado para validación cruzada del JWT).  
  * **Efecto:** Requiere reinicio.  
* JWT_PUBLIC_KEY  
  * **Propósito:** La clave pública (en formato PEM) usada para verificar la firma de los tokens JWT provenientes del API Gateway.  
  * **Efecto:** Requiere reinicio.  
* JWT_AUDIENCE  
  * **Propósito:** El valor "audience" esperado dentro del token JWT.  
  * **Efecto:** Requiere reinicio.  
* JWT_ISSUER  
  * **Propósito:** El valor "issuer" (emisor) esperado dentro del token JWT.  
  * **Efecto:** Requiere reinicio.

### **Configuración Base de Datos (SAM)**

* SQL_SAM_DRIVER, SQL_SAM_HOST, SQL_SAM_DB_NAME, SQL_SAM_UID, SQL_SAM_PWD  
  * **Propósito:** Credenciales completas para conectarse a la base de datos de SAM y actualizar el estado de las ejecuciones.  
  * **Efecto:** Requiere reinicio.

### **Configuración de Logging**

* LOG_DIRECTORY  
  * **Propósito:** Carpeta donde se guardarán los archivos de log.  
  * **Efecto:** Requiere reinicio.  
* LOG_LEVEL  
  * **Propósito:** Nivel de detalle del log (ej. INFO, DEBUG).  
  * **Efecto:** Requiere reinicio.  
* APP_LOG_FILENAME_CALLBACK  
  * **Propósito:** Nombre específico del archivo de log para este servicio.  
  * **Efecto:** Requiere reinicio.

## **6. Ejecución**

Para ejecutar el servicio en un entorno de desarrollo:

Bash

uv run -m sam.callback

