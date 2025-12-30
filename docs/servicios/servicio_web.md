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

* **api.py**: Router principal. Define endpoints como /api/robots, /api/equipos, /api/mappings, /api/schedules. Maneja parámetros de filtrado (programado, online, tipo, etc.) y validación de datos.
* **database.py**: Capa de acceso a datos. Ejecuta los procedimientos almacenados (ej. ActualizarRobotConfig, CrearProgramacion, ActualizarProgramacionSimple/Completa). Incluye manejo de STRING_AGG con NVARCHAR(MAX) para evitar límites de 8000 bytes.
* **schemas.py**: Modelos Pydantic para validación de requests/responses. Incluye ScheduleData, ScheduleEditData con soporte para campos de RangoMensual (DiaInicioMes, DiaFinMes, UltimosDiasMes, PrimerosDiasMes).

### **Frontend (ReactPy)**

Ubicado en src/sam/web/frontend. Construido con **ReactPy**, lo que permite definir la interfaz usando sintaxis Python. La UI se divide en módulos funcionales ("Features") y componentes compartidos ("Shared"):

#### **Componentes Compartidos (shared/)**

Componentes y utilidades reutilizables utilizados en toda la aplicación:

* **common_components.py**: Componentes UI genéricos:
  * `Pagination`: Control de paginación con resumen de resultados.
  * `LoadingSpinner`: Spinner de carga con diferentes tamaños.
  * `LoadingOverlay`: Overlay semi-transparente con spinner y mensaje, usado durante operaciones asíncronas para deshabilitar interacciones y proporcionar feedback visual.
  * `ConfirmationModal`: Modal genérico para confirmación de acciones críticas.
  * `ThemeSwitcher`: Interruptor para cambiar entre tema claro/oscuro.
  * `HeaderNav`: Navegación principal con sincronización global.

* **formatters.py**: Funciones de formateo compartidas:
  * `format_time()`: Formatea horas como HH:MM (sin segundos).
  * `format_equipos_list()`: Formatea listas de equipos con truncamiento inteligente (muestra hasta N elementos, luego "+X más" con tooltip completo).
  * `format_schedule_details()`: Formatea detalles de programaciones según su tipo (Semanal, Mensual, RangoMensual, Específica).

* **notifications.py**: Sistema de notificaciones tipo "Toast" para feedback de acciones (éxito, error, advertencia).

* **styles.py**: Constantes de estilos CSS reutilizables.

* **async_content.py**: Componente para manejar estados de carga, error y datos vacíos.

#### **Módulos Funcionales (features/)**

1. **Gestión de Robots (features/components/robot_list.py + features/modals/robots_modals.py)**:
   * Tabla interactiva para ver el estado de los robots con filtros (Online, Programados, búsqueda).
   * Modales para editar configuración crítica: **Prioridad** (1-10) y **Límites** (máx. equipos simultáneos).
   * Modal de **Asignación de Equipos**: Permite asignar/desasignar equipos a robots con búsqueda y selección múltiple. Incluye overlay de carga durante operaciones.
   * Modal de **Programación de Robots**: Gestión de programaciones específicas de cada robot, con soporte para todos los tipos de programación.

2. **Gestión de Equipos (features/components/equipo_list.py + features/modals/equipos_modals.py)**:
   * Visualización de dispositivos conectados.
   * Control para **Habilitar/Deshabilitar** equipos manualmente (modo mantenimiento).

3. **Gestión de Pools (features/components/pool_list.py + features/modals/pool_modals.py)**:
   * ABM de Pools (agrupaciones lógicas de máquinas).
   * Configuración de "Aislamiento" (si el pool acepta carga externa o no).

4. **Mapeos (features/components/mappings_page.py)**:
   * Interfaz para configurar la equivalencia entre nombres de robots externos e internos. Permite que el **Balanceador** reconozca un robot que no figura en la tabla principal con el mismo nombre que reportan los proveedores externos (como el Orquestador de Clouders, la base de datos RPA360 o futuras integraciones), asegurando la correcta asignación de carga.

5. **Programaciones (features/components/schedule_list.py + features/modals/schedule_modal.py + features/modals/schedule_create_modal.py)**:
   * Gestión completa de tareas programadas con soporte para múltiples tipos:
     * **Diaria**: Ejecución diaria a una hora específica.
     * **Semanal**: Ejecución en días específicos de la semana.
     * **Mensual**: Ejecución en un día específico del mes.
     * **RangoMensual**: Ejecución en rangos de días del mes (del X al Y, primeros N días, últimos N días).
     * **Específica**: Ejecución en una fecha concreta.
   * Creación de programaciones desde la página principal con selección de robot (búsqueda incluida).
   * Edición de programaciones existentes.
   * Asignación de equipos a programaciones.
   * Visualización clara de detalles de programación con formateo inteligente.
   * Filtros por tipo, robot y búsqueda por nombre.
   * Todos los modales incluyen overlay de carga y feedback visual durante operaciones asíncronas.

## **3. Flujo de Datos**

### **Ejemplo 1: Edición de un Robot**

1. **Usuario**: En la pantalla "Robots", hace clic en "Editar" sobre un proceso y cambia la prioridad a '1'.
2. **Frontend (robots_modals.py)**: Captura el evento y llama a api_client.update_robot().
3. **Cliente API**: Envía un PUT /api/robots/{id} con el payload JSON.
4. **Backend (api.py)**: Recibe la petición, valida los datos con Pydantic (schemas.py).
5. **Base de Datos (database.py)**: Ejecuta el SP dbo.ActualizarRobotConfig con los nuevos parámetros.
6. **Confirmación**: La BD confirma el cambio, el Backend responde 200 OK, y el Frontend muestra una notificación "Toast" (notifications.py) de éxito.

### **Ejemplo 2: Creación de una Programación con Feedback Visual**

1. **Usuario**: En la pantalla "Programaciones", hace clic en "Programación" → "Crear Nueva Programación".
2. **Frontend (schedule_create_modal.py)**:
   * Muestra el modal con formulario completo.
   * Usuario selecciona robot (con búsqueda), tipo de programación, hora, y configuración específica según el tipo.
3. **Usuario**: Hace clic en "Crear Programación".
4. **Frontend**:
   * Muestra `LoadingOverlay` con mensaje "Creando programación, esto puede tardar unos segundos...".
   * Deshabilita botón de cierre y todos los controles del modal.
   * Cambia texto del botón a "Procesando...".
5. **Cliente API**: Envía POST /api/schedules con el payload JSON.
6. **Backend (api.py)**: Valida datos y llama a database.create_schedule().
7. **Base de Datos (database.py)**: Ejecuta SP dbo.CrearProgramacion (que automáticamente establece EsOnline=0 si el robot estaba online).
8. **Confirmación**:
   * Backend responde 200 OK.
   * Frontend oculta el overlay, muestra notificación de éxito y cierra el modal.
   * La lista de programaciones se actualiza automáticamente.

### **Mejoras de UX Implementadas**

* **LoadingOverlay**: Overlay semi-transparente con blur que aparece durante operaciones asíncronas, deshabilitando interacciones y mostrando spinner + mensaje contextual.
* **Feedback Visual**: Botones cambian su texto a "Procesando..." durante operaciones.
* **Prevención de Acciones**: Botones de cierre y navegación se deshabilitan durante operaciones para evitar pérdida de datos.
* **Formatters Compartidos**: Formateo consistente de horas (HH:MM), listas de equipos (truncamiento inteligente) y detalles de programaciones en toda la aplicación.

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

* **Ejecución Manual (Dev):** `uv run -m sam.web`
* **Servicio Windows:** SAM_Web (Gestionado por NSSM).
* **Logs:** Revisar web.log para errores de conexión con la BD o validación de datos.

## **6. Reglas de Negocio y Procedimientos Operativos**

Esta sección detalla **qué se puede hacer**, **cómo hacerlo** y **qué restricciones aplican** en el servicio web.

### **6.1. Gestión de Robots**

#### **¿Qué se puede hacer?**
* Crear nuevos robots (alta).
* Editar configuración de robots existentes (modificación).
* Ver estado de robots (Online/Offline, Programados, etc.).
* Asignar/desasignar equipos a robots.
* Crear y gestionar programaciones para robots.

#### **Reglas de Negocio:**
1. **Prioridad de Balanceo:**
   * Rango válido: 1-100 (enteros).
   * **Menor valor = Mayor prioridad** (1 es más importante que 10).
   * El servicio Balanceador usa este valor para decidir qué robots ejecutar primero cuando hay recursos limitados.

2. **Límites de Equipos:**
   * **MinEquipos**: Mínimo de equipos que debe tener asignado el robot (rango: 1-99).
   * **MaxEquipos**: Máximo de equipos que puede tener asignado el robot (rango: -1 a 100).
     * Si `MaxEquipos = -1`, significa "sin límite máximo".
   * El sistema nunca asignará menos de `MinEquipos` ni más de `MaxEquipos` (si es diferente de -1).

3. **Estado EsOnline:**
   * **EsOnline = 1**: Robot disponible para ejecución bajo demanda (Tickets/Colas).
   * **EsOnline = 0**: Robot agendado (solo ejecuta según Programaciones).
   * **Regla Automática**: Al crear una programación para un robot con `EsOnline=1`, el sistema automáticamente cambia `EsOnline=0`. Esto es **irreversible desde la interfaz web** (debe hacerse manualmente en BD si se requiere).

4. **Tickets por Equipo Adicional:**
   * Define cuántos tickets pendientes se necesitan para asignar un equipo adicional.
   * Rango válido: 1-100.
   * Usado por el servicio Balanceador para escalado automático.

#### **Procedimiento: Crear un Robot**
1. Ir a la página "Robots".
2. Hacer clic en el botón "Nuevo Robot" (si está disponible) o usar el modal de creación.
3. Completar campos obligatorios:
   * **Robot ID**: ID numérico del robot en A360 (único, no se puede cambiar después).
   * **Nombre**: Nombre descriptivo del robot.
4. Configurar opcionales:
   * **Prioridad Balanceo**: Valor entre 1-100 (default: 100).
   * **Min Equipos**: Mínimo de equipos (default: 1).
   * **Max Equipos**: Máximo de equipos o -1 para sin límite (default: -1).
   * **Tickets por Equipo Adicional**: Umbral para escalado (default: 10).
5. Hacer clic en "Guardar".
6. **Resultado**: El robot se crea con `EsOnline=1` por defecto (disponible para tickets).

#### **Procedimiento: Editar Configuración de Robot**
1. Ir a la página "Robots".
2. Localizar el robot en la tabla (usar filtros si es necesario).
3. Hacer clic en el botón "Editar" (ícono de lápiz).
4. Modificar los campos deseados:
   * **Nota**: El Robot ID no se puede cambiar (campo deshabilitado).
5. Hacer clic en "Guardar".
6. **Resultado**: Los cambios se aplican inmediatamente. El Balanceador los usará en el próximo ciclo.

#### **Procedimiento: Asignar Equipos a un Robot**
1. Ir a la página "Robots".
2. Localizar el robot en la tabla.
3. Hacer clic en el botón "Asignación de Equipos" (ícono de computadora).
4. En el modal:
   * **Columna Izquierda**: Equipos disponibles (no asignados a este robot).
   * **Columna Derecha**: Equipos asignados actualmente.
5. Para asignar:
   * Seleccionar uno o más equipos de la columna izquierda (usar checkboxes o "Seleccionar todos").
   * Hacer clic en la flecha "→" (Asignar).
6. Para desasignar:
   * Seleccionar uno o más equipos de la columna derecha.
   * Hacer clic en la flecha "←" (Desasignar).
7. Hacer clic en "Guardar".
8. **Confirmación**: El sistema mostrará un modal de confirmación antes de aplicar los cambios.
9. **Resultado**:
   * Los equipos asignados se marcan con `EsProgramado=1` en la tabla `Asignaciones`.
   * Si el robot tiene programaciones activas, los equipos se vinculan a esas programaciones.
   * Los equipos asignados se marcan con `PermiteBalanceoDinamico=0` para proteger las asignaciones programadas.

### **6.2. Gestión de Programaciones**

#### **¿Qué se puede hacer?**
* Crear programaciones para cualquier robot activo.
* Editar programaciones existentes (tipo, hora, días, equipos).
* Activar/desactivar programaciones sin eliminarlas.
* Asignar/desasignar equipos a programaciones.
* Eliminar programaciones (con confirmación).

#### **Reglas de Negocio:**

1. **Tipos de Programación y Validaciones:**
   * **Diaria**: Ejecuta todos los días a la hora especificada.
     * Campos requeridos: `HoraInicio`, `Tolerancia`.
   * **Semanal**: Ejecuta en días específicos de la semana.
     * Campos requeridos: `HoraInicio`, `Tolerancia`, `DiasSemana` (formato: "Lu,Ma,Mi,Ju,Vi,Sa,Do").
   * **Mensual**: Ejecuta en un día específico del mes.
     * Campos requeridos: `HoraInicio`, `Tolerancia`, `DiaDelMes` (1-31).
   * **RangoMensual**: Ejecuta en un rango de días del mes.
     * Campos requeridos: `HoraInicio`, `Tolerancia`.
     * **Opciones mutuamente excluyentes**:
       * **Opción 1 - Rango específico**: `DiaInicioMes` (1-31) Y `DiaFinMes` (1-31), donde `DiaInicioMes ≤ DiaFinMes`.
       * **Opción 2 - Primeros N días**: Se mapea internamente a `DiaInicioMes=1` y `DiaFinMes=N` (donde N es el valor ingresado).
       * **Opción 3 - Últimos N días**: `UltimosDiasMes` (1-31).
     * **Validaciones**:
       * No se puede especificar simultáneamente un rango Y `UltimosDiasMes`.
       * Si se especifica `DiaInicioMes`, también debe especificarse `DiaFinMes` (y viceversa).
       * `DiaInicioMes` no puede ser mayor que `DiaFinMes`.
   * **Específica**: Ejecuta una sola vez en una fecha concreta.
     * Campos requeridos: `HoraInicio`, `Tolerancia`, `FechaEspecifica` (formato: YYYY-MM-DD).

2. **Tolerancia:**
   * Ventana de tiempo (en minutos) después de `HoraInicio` en la que aún es válido lanzar el robot.
   * Rango válido: 0-1440 minutos (0-24 horas).
   * Si la hora programada pasa y no se ejecutó, el sistema intentará ejecutarlo dentro de la ventana de tolerancia.

3. **Efectos Automáticos al Crear una Programación:**
   * El robot se marca automáticamente como `EsOnline=0` (si estaba en 1).
   * Los equipos asignados se marcan con `PermiteBalanceoDinamico=0` (protección contra balanceo automático).
   * Se crean registros en `Asignaciones` con `EsProgramado=1` para cada equipo asignado.

4. **Restricciones:**
   * No se pueden crear programaciones para robots inactivos (`ActivoSAM=0`).
   * Solo se pueden asignar equipos activos (`Activo_SAM=1`) a programaciones.
   * Una programación debe tener al menos un equipo asignado para ser funcional.

#### **Procedimiento: Crear una Programación (Desde Página Programaciones)**
1. Ir a la página "Programaciones".
2. Hacer clic en el botón "Programación" → "Crear Nueva Programación".
3. En el modal de creación:
   * **Seleccionar Robot**:
     * Usar el buscador para filtrar robots por nombre.
     * Seleccionar el robot del dropdown (muestra todos los robots activos).
   * **Tipo de Programación**: Seleccionar uno de los 5 tipos disponibles.
   * **Hora de Inicio**: Formato HH:MM (ej: "09:00").
   * **Tolerancia**: Minutos de ventana (ej: 60).
   * **Campos Específicos según Tipo**:
     * Si es **Semanal**: Seleccionar días de la semana usando los checkboxes.
     * Si es **Mensual**: Ingresar día del mes (1-31).
     * Si es **RangoMensual**: Elegir una de las 3 opciones y completar los campos correspondientes.
     * Si es **Específica**: Seleccionar fecha del calendario.
4. Hacer clic en "Crear Programación".
5. **Confirmación**: El sistema mostrará un modal de confirmación.
6. **Resultado**:
   * La programación se crea con estado `Activo=1`.
   * El robot pasa a `EsOnline=0` automáticamente.
   * **Nota**: Los equipos se asignan después de crear la programación (ver procedimiento siguiente).

#### **Procedimiento: Asignar Equipos a una Programación**
1. Desde la página "Programaciones":
   * Localizar la programación en la tabla.
   * Hacer clic en el botón "Asignar Equipos" (ícono de computadora).
2. O desde la página "Robots":
   * Abrir el modal "Programación de Robots" del robot.
   * Localizar la programación en la lista.
   * Hacer clic en "Editar" y luego asignar equipos en el formulario.
3. En el modal de asignación:
   * Seleccionar los equipos deseados de la lista disponible.
   * Hacer clic en "Guardar".
4. **Resultado**:
   * Los equipos se vinculan a la programación en `Asignaciones` con `EsProgramado=1`.
   * Los equipos se marcan con `PermiteBalanceoDinamico=0`.

#### **Procedimiento: Editar una Programación**
1. Desde la página "Programaciones":
   * Localizar la programación en la tabla.
   * Hacer clic en el botón "Editar" (ícono de lápiz).
2. En el modal de edición:
   * **Nota**: El robot NO se puede cambiar (es inmutable).
   * Modificar los campos deseados:
     * Tipo de Programación (esto limpiará campos específicos del tipo anterior).
     * Hora de Inicio.
     * Tolerancia.
     * Campos específicos según el nuevo tipo.
     * Estado Activo (checkbox).
3. Hacer clic en "Guardar Cambios".
4. **Confirmación**: El sistema mostrará un modal de confirmación.
5. **Resultado**: Los cambios se aplican. Si se cambió el tipo, los campos no aplicables se limpian automáticamente.

#### **Procedimiento: Activar/Desactivar una Programación**
1. Desde la página "Programaciones":
   * Localizar la programación en la tabla o tarjeta.
   * Hacer clic en el switch "Activo" (toggle).
2. **Resultado Inmediato**:
   * Si se desactiva (`Activo=0`): El servicio Lanzador ignorará esta programación.
   * Si se activa (`Activo=1`): El servicio Lanzador la considerará en el próximo ciclo.

#### **Procedimiento: Eliminar una Programación**
1. Desde la página "Programaciones":
   * Localizar la programación en la tabla o tarjeta.
   * Hacer clic en el botón "Eliminar" (ícono de basura).
2. **Confirmación**: El sistema mostrará un modal pidiendo confirmación.
3. Hacer clic en "Confirmar" en el modal.
4. **Resultado**:
   * La programación se elimina de `Programaciones`.
   * Las asignaciones relacionadas (`EsProgramado=1`) se eliminan de `Asignaciones`.
   * **Nota**: Los equipos NO recuperan automáticamente `PermiteBalanceoDinamico=1` (debe hacerse manualmente si se requiere).

### **6.3. Gestión de Equipos**

#### **¿Qué se puede hacer?**
* Ver lista de equipos conectados.
* Habilitar/deshabilitar equipos (modo mantenimiento).

#### **Reglas de Negocio:**
1. **Activo_SAM:**
   * **Activo_SAM=1**: El equipo está disponible para SAM (puede recibir asignaciones).
   * **Activo_SAM=0**: El equipo está en mantenimiento. SAM lo ignora completamente.
   * **Efecto**: Si un equipo se desactiva, todas sus asignaciones activas se mantienen, pero no recibirá nuevas tareas.

2. **PermiteBalanceoDinamico:**
   * **PermiteBalanceoDinamico=1**: El equipo puede recibir asignaciones dinámicas del servicio Balanceador.
   * **PermiteBalanceoDinamico=0**: El equipo solo acepta asignaciones programadas o reservadas manualmente.
   * **Nota**: Este campo se modifica automáticamente al crear programaciones (se establece en 0). No se puede cambiar desde la interfaz web directamente.

#### **Procedimiento: Deshabilitar un Equipo (Mantenimiento)**
1. Ir a la página "Equipos".
2. Localizar el equipo en la tabla.
3. Hacer clic en el switch "Activo" para desactivarlo.
4. **Resultado**:
   * El equipo se marca como `Activo_SAM=0`.
   * El servicio Lanzador y Balanceador ignorarán este equipo.
   * Las ejecuciones en curso continuarán, pero no se asignarán nuevas tareas.

### **6.4. Gestión de Pools**

#### **¿Qué se puede hacer?**
* Crear nuevos pools.
* Editar configuración de pools (nombre, aislamiento).
* Asignar robots y equipos a pools.
* Eliminar pools.

#### **Reglas de Negocio:**
1. **Unicidad de Pool:**
   * Un robot solo puede pertenecer a UN pool a la vez.
   * Un equipo solo puede pertenecer a UN pool a la vez.
   * **Efecto Automático**: Al asignar un robot/equipo a un nuevo pool, se desvincula automáticamente del pool anterior.

2. **Aislamiento:**
   * **Aislamiento=1 (Estricto)**: Los equipos del pool solo atienden robots de ese pool.
   * **Aislamiento=0 (Flexible)**: Los equipos pueden ser "prestados" a otros pools si hay capacidad ociosa.
   * **Nota**: El comportamiento real depende de la configuración del servicio Balanceador (`BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO`).

### **6.5. Filtros y Búsquedas**

#### **Página de Robots:**
* **Filtro "Online"**:
  * **"Online: Todos"**: Muestra todos los robots (sin filtro).
  * **"Solo Online"**: Muestra solo robots con `EsOnline=1`.
  * **"Solo Programados"**: Muestra solo robots con `EsOnline=0` Y que tienen al menos una programación activa.
* **Búsqueda**: Filtra robots por nombre (búsqueda parcial, case-insensitive).

#### **Página de Programaciones:**
* **Filtro "Tipo"**:
  * **"Tipo: Todos"**: Muestra todas las programaciones (default).
  * Filtros específicos: Diaria, Semanal, Mensual, RangoMensual, Específica.
* **Filtro "Robot"**: Filtra por robot específico.
* **Búsqueda**: Filtra por nombre de robot (búsqueda parcial, case-insensitive).

### **6.6. Notas Técnicas Adicionales**

#### **Formateo y Visualización**
* Las horas se muestran consistentemente como HH:MM (sin segundos) en toda la aplicación.
* Las listas de equipos se truncan inteligentemente: se muestran hasta N elementos visibles, luego un indicador "(+X más)" con tooltip que muestra la lista completa al pasar el mouse.
* Los detalles de programación se formatean de manera legible según el tipo (ej: "Del 5 al 15 de cada mes", "Últimos 3 día(s) del mes").

#### **Experiencia de Usuario**
* Todos los modales que realizan operaciones asíncronas (crear, editar, asignar) incluyen:
  * Overlay de carga con spinner y mensaje contextual.
  * Deshabilitación de controles durante la operación.
  * Feedback visual en botones ("Procesando...").
  * Prevención de cierre accidental durante operaciones.

#### **Optimizaciones de Base de Datos**
* El uso de `STRING_AGG` con `CAST(... AS NVARCHAR(MAX))` evita el límite de 8000 bytes cuando se concatenan muchos nombres de equipos.
* Los stored procedures han sido actualizados para soportar los nuevos campos de `RangoMensual` en las operaciones de creación y actualización.
