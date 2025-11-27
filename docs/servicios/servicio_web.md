# **Documentación Técnica: Interfaz de Gestión (Web)**

**Módulo:** sam.web

## **1. Propósito**

La **Interfaz Web** de SAM actúa como la consola central de administración y operación del sistema. Más que un dashboard de métricas, es una herramienta de **Gestión (ABM)** que permite al equipo de soporte y a los administradores configurar el comportamiento del orquestador sin interactuar directamente con la base de datos.

Sus funciones principales son:

1. **Inventario:** Alta, baja y modificación de Robots y Equipos.  
2. **Configuración:** Definición de prioridades, límites de concurrencia y ventanas de mantenimiento.  
3. **Estrategia:** Creación de "Pools" de equipos y asignación (Mapeo) de robots a estos pools.  
4. **Programación:** Gestión de los cronogramas de ejecución (Schedules).

## **2. Arquitectura y Componentes**

El servicio opera como una aplicación monolítica ligera que sirve tanto la API como la UI.

### **Backend (FastAPI)**

Ubicado en src/sam/web/backend. Expone una API RESTful que actúa como pasarela hacia los Stored Procedures de la base de datos.

* **api.py**: Router principal. Define endpoints como /api/robots, /api/equipos, /api/mappings, /api/schedules.  
* **database.py**: Capa de acceso a datos. Ejecuta los procedimientos almacenados (ej. ActualizarRobotConfig, GuardarSchedule).

### **Frontend (ReactPy)**

Ubicado en src/sam/web/frontend. Construido con **ReactPy**, lo que permite definir la interfaz usando sintaxis Python. La UI se divide en módulos funcionales ("Features"):

1. **Gestión de Robots (features/components/robots_components.py)**:  
   * Tabla interactiva para ver el estado de los robots.  
   * Modales para editar configuración crítica: **Prioridad** (1-10) y **Límites** (máx. equipos simultáneos).  
2. **Gestión de Equipos (features/components/equipos_components.py)**:  
   * Visualización de dispositivos conectados.  
   * Control para **Habilitar/Deshabilitar** equipos manualmente (modo mantenimiento).  
3. **Gestión de Pools (features/components/pools_components.py)**:  
   * ABM de Pools (agrupaciones lógicas de máquinas).  
   * Configuración de "Aislamiento" (si el pool acepta carga externa o no).  
4. **Mapeos (features/components/mappings_page.py)**:  
   * Interfaz para configurar la equivalencia entre nombres de robots externos e internos. Permite que el **Balanceador** reconozca un robot que no figura en la tabla principal con el mismo nombre que reportan los proveedores externos (como el Orquestador de Clouders, la base de datos RPA360 o futuras integraciones), asegurando la correcta asignación de carga.  
5. **Programaciones (features/components/schedules_components.py)**:  
   * Gestión de tareas programadas (CRON).  
   * Permite definir cuándo debe SAM lanzar un proceso automáticamente.

## **3. Flujo de Datos (Ejemplo: Edición de un Robot)**

1. **Usuario**: En la pantalla "Robots", hace clic en "Editar" sobre un proceso y cambia la prioridad a '1'.  
2. **Frontend (robots_modals.py)**: Captura el evento y llama a api_client.update_robot().  
3. **Cliente API**: Envía un PUT /api/robots/{id} con el payload JSON.  
4. **Backend (api.py)**: Recibe la petición, valida los datos con Pydantic (schemas.py).  
5. **Base de Datos (database.py)**: Ejecuta el SP dbo.ActualizarRobotConfig con los nuevos parámetros.  
6. **Confirmación**: La BD confirma el cambio, el Backend responde 200 OK, y el Frontend muestra una notificación "Toas" (notifications.py) de éxito.

## **4. Variables de Entorno Requeridas (.env)**

Cualquier cambio en estas variables requiere reiniciar el servicio SAM_Web.

### **Servidor Web**

* INTERFAZ_WEB_HOST: IP de escucha (default 0.0.0.0).  
* INTERFAZ_WEB_PORT: Puerto TCP (default 8000).  
* INTERFAZ_WEB_DEBUG: true/false. Modo desarrollo (recarga automática). **Desactivar en Producción**.

### **Base de Datos**

* SQL_SAM_DRIVER: Driver ODBC (ej. {ODBC Driver 17 for SQL Server}).  
* SQL_SAM_HOST, SQL_SAM_DB_NAME: Ubicación de la BD.  
* SQL_SAM_UID, SQL_SAM_PWD: Credenciales de acceso.

### **Logging**

* LOG_DIRECTORY: Ruta física de logs (ej. C:\RPA\Logs\SAM).  
* APP_LOG_FILENAME_INTERFAZ_WEB: Nombre del archivo (ej. web.log).

## **5. Ejecución y Soporte**

* **Ejecución Manual (Dev):** uv run -m sam.web  
* **Servicio Windows:** SAM_Web (Gestionado por NSSM).  
* **Logs:** Revisar web.log para errores de conexión con la BD o validación de datos.