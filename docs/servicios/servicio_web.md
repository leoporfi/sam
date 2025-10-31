# **Documentación Técnica: Interfaz Web**

**Módulo:** sam.web

## **1. Propósito**

La **Interfaz Web** de SAM es un dashboard de monitoreo y gestión. Permite a los usuarios visualizar el estado de las ejecuciones de robots, el estado de los equipos (devices) y gestionar la configuración de los robots y su asignación a "Pools" de ejecución.

## **2. Arquitectura y Componentes**

El servicio es una **única aplicación FastAPI** que se ejecuta en un servidor uvicorn. Esta aplicación sirve dos componentes principales montados en rutas diferentes:

1. **Backend (API):** Un conjunto de endpoints API RESTful montados bajo el prefijo /api.  
2. **Frontend (UI):** Una interfaz de usuario interactiva (un dashboard) montada en la ruta raíz (/).

### **Componentes Principales**

* **Servidor (sam.web.run_web.py)**:  
  * **Rol:** Lanzador del Servidor.  
  * **Descripción:** Utiliza uvicorn para iniciar el servidor web, cargando la aplicación principal (app) desde sam.web.main.py.  
* **App Principal (sam.web.main.py)**:  
  * **Rol:** Orquestador Web.  
  * **Descripción:** Es el corazón de la aplicación. Crea la instancia principal de FastAPI y:  
    1. Monta el router del **Backend** (desde backend.api.router) bajo la ruta /api.  
    2. Monta la aplicación **Frontend** de ReactPy (desde frontend.app.layout) en la ruta raíz (/).  
    3. Configura el servicio de archivos estáticos (CSS, JS) en la ruta /static.  
* **Backend (sam.web.backend/api.py)**:  
  * **Rol:** API de Datos.  
  * **Descripción:** Expone todos los endpoints RESTful que el frontend necesita (ej. /api/robots/, /api/pools/, /api/equipos/, /api/dashboard/stats). No contiene lógica de negocio; su función es recibir peticiones, llamar a la base de datos y devolver los datos como JSON.  
* **Gestor de Base de Datos (sam.web.backend/database.py)**:  
  * **Rol:** Capa de Acceso a Datos del Backend.  
  * **Descripción:** Contiene los métodos que ejecutan las consultas y Stored Procedures (SPs) específicos contra la base de datos de SAM (ej. ObtenerRobotsDetalle, ObtenerEquiposDetalle, ActualizarRobotConfig).  
* **Frontend (sam.web.frontend/app.py)**:  
  * **Rol:** Interfaz de Usuario (UI).  
  * **Descripción:** Es el dashboard interactivo construido con **ReactPy**. Define la estructura de las páginas (Robots, Equipos, Pools, Dashboard), los componentes visuales (tablas, modales) y la lógica de estado.  
* **Cliente API (sam.web.frontend/api/api_client.py)**:  
  * **Rol:** Conector Frontend ->> Backend.  
  * **Descripción:** Un componente del *Frontend* que utiliza httpx para realizar las llamadas a los endpoints del *Backend* (ej. llama a /api/robots/ para obtener la lista de robots) y devolver los datos a la interfaz.

## **3. Flujo de Datos**

1. Un usuario accede a la URL del servicio (ej. http://localhost:8000/) en su navegador.  
2. El servidor uvicorn recibe la petición y la dirige a la **App Principal (FastAPI)**.  
3. Como la ruta es /, FastAPI la dirige al **Frontend (ReactPy)**.  
4. ReactPy renderiza la página principal y la envía al navegador.  
5. Los componentes de ReactPy (ej. la tabla de robots) se cargan e invocan al **Cliente API** del frontend.  
6. El **Cliente API** realiza una petición GET a la ruta del backend (ej. GET /api/robots/).  
7. FastAPI recibe esta petición /api/ y la dirige al **Backend (API)**.  
8. El endpoint del Backend llama al **Gestor de Base de Datos** para ejecutar el Stored Procedure (ej. ObtenerRobotsDetalle).  
9. La base de datos devuelve los datos al Backend, que los formatea como JSON y los devuelve en la respuesta.  
10. El **Cliente API** recibe el JSON y se lo entrega a los componentes del **Frontend**.  
11. El Frontend (ReactPy) actualiza la interfaz para mostrar los datos (ej. rellena la tabla de robots).

## **4. Variables de Entorno Requeridas (.env)**

Este servicio depende de las siguientes variables. Dado que corre bajo NSSM, **cualquier cambio en estas variables requiere un reinicio del servicio** para que tenga efecto.

### **Configuración de la Interfaz Web**

* INTERFAZ_WEB_HOST  
  * **Propósito:** La dirección IP en la que escuchará el servidor uvicorn (ej. 127.0.0.1 o 0.0.0.0).  
  * **Efecto:** Requiere reinicio.  
* INTERFAZ_WEB_PORT  
  * **Propósito:** El puerto TCP en el que escuchará el servidor (ej. 8000).  
  * **Efecto:** Requiere reinicio.  
* INTERFAZ_WEB_DEBUG  
  * **Propósito:** true o false. Activa el modo "debug" de FastAPI, que proporciona más detalles de errores y recarga automáticamente el servidor en cambios (no recomendado en producción).  
  * **Efecto:** Requiere reinicio.

### **Configuración Base de Datos (SAM)**

* SQL_SAM_DRIVER  
  * **Propósito:** Driver ODBC para la conexión (ej. {ODBC Driver 17 for SQL Server}).  
  * **Efecto:** Requiere reinicio.  
* SQL_SAM_HOST  
  * **Propósito:** Dirección IP o Hostname del servidor SQL Server donde reside la BD de SAM.  
  * **Efecto:** Requiere reinicio.  
* SQL_SAM_DB_NAME  
  * **Propósito:** Nombre de la base de datos de SAM.  
  * **Efecto:** Requiere reinicio.  
* SQL_SAM_UID / SQL_SAM_PWD  
  * **Propósito:** Credenciales (usuario y contraseña) para la base de datos SAM.  
  * **Efecto:** Requiere reinicio.  
* (Variables de reintento de SQL: SQL_SAM_MAX_REINTENTOS_QUERY, etc.)

### **Configuración de Logging**

* LOG_DIRECTORY  
  * **Propósito:** Carpeta donde se guardarán los archivos de log.  
  * **Efecto:** Requiere reinicio.  
* LOG_LEVEL  
  * **Propósito:** Nivel de detalle del log (ej. INFO, DEBUG).  
  * **Efecto:** Requiere reinicio.  
* APP_LOG_FILENAME_INTERFAZ_WEB  
  * **Propósito:** Nombre específico del archivo de log para este servicio.  
  * **Efecto:** Requiere reinicio.

## **5. Ejecución**

Para ejecutar el servicio en un entorno de desarrollo:

Bash

uv run -m sam.web

