# sam/web/backend/docs_data.py
"""
Datos estructurados de documentación (Glosario y FAQ).
Fuente de verdad extraída de los archivos generados por el Agente de Documentación.
"""

# Estructura de navegación global
NAVIGATION_STRUCTURE = {
    "site_title": "Documentación Técnica SAM",
    "description": "Fuente de verdad para el orquestador RPA SAM (Sistema Automático de Robots).",
    "sections": [
        {
            "slug": "glosario",
            "title": "Glosario del Proyecto",
            "type": "reference",
        },
        {
            "slug": "faq",
            "title": "Preguntas Frecuentes (FAQ)",
            "type": "q_and_a",
        },
    ],
}

# ============================================================================
# GLOSARIO DEL PROYECTO
# ============================================================================

GLOSSARY_DATA = {
    "dominio-negocio": {
        "title": "Dominio de Negocio",
        "terms": [
            {
                "slug": "robot",
                "term": "Robot",
                "description": """**Descripción:** Entidad lógica que representa un proceso automatizado (Taskbot) en Automation Anywhere 360.

**Objetivo:** Ejecutar tareas de negocio automatizadas.

**Reglas:**
- Debe existir en A360 y en la tabla `dbo.Robots`.
- Tiene una prioridad (1-100) que determina su importancia en el balanceo.
- Puede requerir un número mínimo y máximo de equipos.
- Puede ser "Online" (demanda dinámica) o "Programado" (horarios fijos).""",
            },
            {
                "slug": "equipo",
                "term": "Equipo (Device)",
                "description": """**Descripción:** Máquina virtual o física donde se ejecutan los robots (Bot Runner).

**Objetivo:** Proveer capacidad de cómputo para las ejecuciones.

**Reglas:**
- Debe tener el agente de A360 instalado y conectado.
- Puede pertenecer a un único Pool o al Pool General (si `PoolId` es NULL).
- Puede estar "Activo" o "Inactivo" en SAM.""",
            },
            {
                "slug": "pool",
                "term": "Pool",
                "description": """**Descripción:** Agrupación lógica de Equipos y Robots dedicada a un propósito o área de negocio específica.

**Objetivo:** Aislar recursos y garantizar capacidad para procesos críticos.

**Reglas:**
- Los equipos de un pool solo pueden ejecutar robots de ese pool (si `BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO` es TRUE).
- Permite segmentar la granja de robots.""",
            },
            {
                "slug": "ejecucion",
                "term": "Ejecución (Deployment)",
                "description": """**Descripción:** Instancia concreta de un Robot corriendo en un Equipo.

**Objetivo:** Realizar una tarea específica en un momento dado.

**Estados:** `DEPLOYED`, `RUNNING`, `COMPLETED`, `RUN_FAILED`, `DEPLOY_FAILED`, `RUN_ABORTED`, `UNKNOWN`, `COMPLETED_INFERRED`.""",
            },
            {
                "slug": "asignacion",
                "term": "Asignación",
                "description": """**Descripción:** Vínculo temporal o permanente entre un Robot y un Equipo.

**Objetivo:** Autorizar a un robot a ejecutarse en un equipo específico.

**Tipos:**
- **Dinámica:** Creada por el Balanceador según demanda.
- **Fija/Reservada:** Configurada manualmente para exclusividad.""",
            },
            {
                "slug": "preemption",
                "term": "Preemption (Prioridad Estricta)",
                "description": """**Descripción:** Mecanismo del Balanceador para desalojar robots de baja prioridad y ceder sus equipos a robots de alta prioridad con demanda insatisfecha.

**Reglas:**
- Solo ocurre si el robot de alta prioridad tiene "hambre" (déficit de equipos).
- Solo desaloja si el robot víctima tiene menor prioridad (mayor número).""",
            },
            {
                "slug": "cooling",
                "term": "Cooling (Enfriamiento)",
                "description": """**Descripción:** Periodo de tiempo durante el cual un Pool o Robot no puede sufrir cambios en sus asignaciones tras una modificación.

**Objetivo:** Evitar oscilaciones (flapping) y dar tiempo a que los cambios surtan efecto.

**Valor Default:** 300 segundos (5 minutos).""",
            },
        ],
    },
    "arquitectura-tecnologia": {
        "title": "Arquitectura y Tecnología",
        "terms": [
            {
                "slug": "reactpy",
                "term": "ReactPy",
                "description": """**Descripción:** Librería para construir interfaces de usuario en Python sin Javascript.

**Uso en SAM:** Base del Frontend. Permite mantener todo el stack en Python.

**Componentes:** Funciones decoradas con `@component` que retornan elementos HTML.""",
            },
            {
                "slug": "htmx",
                "term": "HTMX",
                "description": """**Descripción:** Librería que permite acceder a AJAX, CSS Transitions, WebSockets y Server Sent Events directamente en HTML.

**Uso en SAM:** Provee interactividad dinámica (SPA-like) sin escribir JavaScript complejo.""",
            },
            {
                "slug": "stored-procedure",
                "term": "Stored Procedure (SP)",
                "description": """**Descripción:** Código SQL precompilado y almacenado en la base de datos.

**Regla de Oro:** Único mecanismo permitido para que Python interactúe con los datos.

**Beneficios:** Seguridad (evita SQL Injection), Performance (planes de ejecución cacheados) y Centralización de lógica.""",
            },
            {
                "slug": "migracion",
                "term": "Migración",
                "description": """**Descripción:** Script SQL versionado (ej. `008_update_logic.sql`) que aplica cambios controlados al esquema o datos de la BD.

**Regla:** Todo cambio en BD debe tener su migración asociada.""",
            },
            {
                "slug": "table-valued-parameter",
                "term": "Table-Valued Parameter (TVP)",
                "description": """**Descripción:** Tipo de dato en SQL Server que permite enviar múltiples filas (como una tabla) en un solo parámetro a un SP.

**Uso en SAM:** Operaciones masivas, como asignar 50 equipos a un pool en una sola llamada.""",
            },
        ],
    },
    "arquitectura": {
        "title": "Arquitectura General",
        "terms": [
            {
                "slug": "vision-general",
                "term": "Visión General",
                "description": """SAM es un orquestador RPA que extiende las capacidades de Automation Anywhere 360, añadiendo balanceo de carga dinámico, priorización y recuperación ante fallos. Funciona como un sistema de 4 microservicios acoplados por una base de datos central.""",
            },
            {
                "slug": "capas",
                "term": "Capas",
                "description": """1. **Frontend (Web):** Interfaz de usuario ReactPy para gestión y monitoreo.
2. **Backend (API):** FastAPI para servir datos al frontend y recibir webhooks.
3. **Core Services:**
   - **Lanzador:** Motor de ejecución y monitoreo.
   - **Balanceador:** Cerebro de optimización de recursos.
   - **Callback:** Receptor de eventos tiempo real de A360.
4. **Datos:** SQL Server como Single Source of Truth.""",
            },
            {
                "slug": "comunicacion",
                "term": "Comunicación",
                "description": """- **Interna:** A través de la Base de Datos (Polling/Updates).
- **Externa (Salida):** API REST de Automation Anywhere 360 (httpx).
- **Externa (Entrada):** Webhooks (Callback) desde A360.""",
            },
        ],
    },
    "componentes-frontend": {
        "title": "Componentes Frontend",
        "terms": [
            {
                "slug": "robot-list-py",
                "term": "robot_list.py",
                "description": """**Tipo:** Page / Feature Component

**Responsabilidad:** Dashboard principal de robots. Muestra estado, carga, asignaciones y permite acciones de control (activar/desactivar).

**Hooks:** `use_robots_hook`""",
            },
            {
                "slug": "equipo-list-py",
                "term": "equipo_list.py",
                "description": """**Tipo:** Page / Feature Component

**Responsabilidad:** Gestión de equipos. Muestra estado de conexión, pool asignado y permite editar propiedades.

**Hooks:** `use_equipos_hook`""",
            },
            {
                "slug": "schedule-list-py",
                "term": "schedule_list.py",
                "description": """**Tipo:** Page / Feature Component

**Responsabilidad:** Gestión de programaciones (Cron jobs).

**Hooks:** `use_schedules_hook`""",
            },
            {
                "slug": "bot-input-editor-py",
                "term": "bot_input_editor.py",
                "description": """**Tipo:** Shared Component

**Responsabilidad:** Editor JSON visual para configurar los parámetros de entrada (bot_input) de los robots.""",
            },
            {
                "slug": "data-table-py",
                "term": "data_table.py",
                "description": """**Tipo:** Shared Component

**Responsabilidad:** Tabla genérica con soporte para ordenamiento, paginación y filtrado. Usada en todas las listas.""",
            },
        ],
    },
    "servicios-apis": {
        "title": "Servicios y APIs",
        "terms": [
            {
                "slug": "servicio-lanzador",
                "term": "Servicio Lanzador",
                "description": """**Tipo:** Servicio de Windows (Background Loop)

**Responsabilidad:**
- Detectar robots para ejecutar (`dbo.ObtenerRobotsEjecutables`).
- Desplegar robots en A360 (`POST /v1/deployments`).
- Monitorear integridad (Errores 412/400).
- Conciliar estados (detectar zombies/huérfanos).""",
            },
            {
                "slug": "servicio-balanceador",
                "term": "Servicio Balanceador",
                "description": """**Tipo:** Servicio de Windows (Background Loop)

**Responsabilidad:**
- Leer carga de trabajo (Tickets pendientes).
- Calcular equipos necesarios por robot.
- Asignar/Desasignar equipos dinámicamente (`dbo.Asignaciones`).
- Ejecutar Preemption.""",
            },
            {
                "slug": "servicio-callback",
                "term": "Servicio Callback",
                "description": """**Tipo:** API REST (FastAPI)

**Endpoint:** `POST /api/callback`

**Inputs:** JSON con `deploymentId`, status, `botOutput`.

**Responsabilidad:** Recibir notificación inmediata de fin de robot y actualizar `dbo.Ejecuciones`.""",
            },
            {
                "slug": "api-web",
                "term": "API Web",
                "description": """**Tipo:** API REST (FastAPI)

**Endpoints Clave:**
- `GET /api/robots`: Listado de robots.
- `GET /api/analytics/executions`: Dashboard de ejecuciones recientes.
- `POST /api/executions/{id}/unlock`: Destrabe manual de ejecuciones.
- `POST /api/sync/robots`: Forzar sincronización con A360.""",
            },
            {
                "slug": "sistema-de-alertas",
                "term": "Sistema de Alertas",
                "description": """**Componentes:** `EmailAlertClient`, `AlertContext`.

**Niveles:** `CRITICAL`, `HIGH`, `MEDIUM`.

**Throttling:** Mecanismo que agrupa alertas idénticas para evitar spam (ej. 1 correo cada 30 mins para el mismo error).""",
            },
        ],
    },
    "seguridad-operaciones": {
        "title": "Seguridad y Operaciones",
        "terms": [
            {
                "slug": "enmascaramiento",
                "term": "Enmascaramiento (Masking)",
                "description": """**Descripción:** Práctica de ocultar caracteres sensibles en logs y UI (ej. `token[:4]***`).

**Regla:** Obligatorio para API Keys, Passwords y Tokens.""",
            },
            {
                "slug": "principio-minimo-privilegio",
                "term": "Principio de Mínimo Privilegio",
                "description": """**Descripción:** Estrategia de seguridad donde cada usuario/servicio tiene solo los permisos estrictamente necesarios.

**Implementación:** El usuario de BD de SAM solo tiene `EXECUTE` sobre el esquema `dbo`, sin permisos directos de `DELETE` o `DROP` en tablas.""",
            },
            {
                "slug": "auditoria-manual",
                "term": "Auditoría Manual",
                "description": """**Descripción:** Tabla `dbo.AuditoriaManual` y procedimiento asociado.

**Uso:** Obligatorio registrar aquí cualquier cambio manual de datos (UPDATE/DELETE) realizado por un operador humano para corregir incidentes.""",
            },
        ],
    },
    "flujos-clave": {
        "title": "Flujos Clave",
        "terms": [
            {
                "slug": "despliegue-online",
                "term": "Despliegue de Robot (Online)",
                "description": """1. **Balanceador:** Detecta carga → Asigna Equipo en `dbo.Asignaciones`.
2. **Lanzador:** Consulta `dbo.ObtenerRobotsEjecutables` → Encuentra Robot+Equipo libre.
3. **Lanzador:** Llama API A360 (`deploy`).
4. **Lanzador:** Inserta registro en `dbo.Ejecuciones` (Estado `DEPLOYED`).""",
            },
            {
                "slug": "fin-de-ejecucion",
                "term": "Fin de Ejecución (Happy Path)",
                "description": """1. **Robot A360:** Termina su tarea.
2. **A360:** Envía POST a `sam.callback`.
3. **Callback:** Valida tokens → Actualiza `dbo.Ejecuciones` a `COMPLETED`.
4. **BD:** Libera el equipo para la siguiente tarea.""",
            },
            {
                "slug": "manejo-error-412",
                "term": "Manejo de Error 412 (Integridad)",
                "description": """1. **Lanzador:** Intenta deploy → Recibe 412 de A360.
2. **Lanzador:** Analiza mensaje. Si es "No compatible targets":
   - Marca error permanente.
   - **Elimina la asignación** en `dbo.Asignaciones` para detener el ciclo de error.
   - Envía Alerta Crítica.
   - Inserta `DEPLOY_FAILED` en `dbo.Ejecuciones`.""",
            },
            {
                "slug": "preemption-prioridad",
                "term": "Preemption (Prioridad)",
                "description": """1. **Balanceador:** Detecta Robot A (Prio 1) con carga y sin equipos.
2. **Balanceador:** Busca en el mismo Pool robots de menor prioridad (ej. Robot B, Prio 10) con equipos.
3. **Balanceador:** Quita equipo a Robot B (`DELETE Asignacion`).
4. **Balanceador:** (En siguiente ciclo) Encuentra equipo libre y lo asigna a Robot A.""",
            },
        ],
    },
}

# ============================================================================
# FAQ DEL PROYECTO
# ============================================================================

FAQ_DATA = {
    "faq-negocio": {
        "title": "Negocio",
        "questions": [
            {
                "slug": "que-problema-resuelve",
                "question": "¿Qué problema resuelve el sistema SAM?",
                "answer": """SAM resuelve la ineficiencia en la asignación de robots a equipos en Automation Anywhere. El agendador nativo no permite balanceo dinámico ni priorización inteligente. SAM actúa como un "Dispatcher" que asigna recursos en tiempo real basándose en la demanda (tickets pendientes) y la prioridad del negocio, maximizando el uso de licencias y equipos.""",
            },
            {
                "slug": "comportamiento-alta-demanda",
                "question": "¿Cómo se comporta ante escenarios de alta demanda?",
                "answer": """El sistema utiliza el **Servicio Balanceador** para detectar cuellos de botella. Si un robot de alta prioridad tiene mucha carga, SAM puede quitar equipos a robots de menor prioridad (ver **Preemption** en Glosario) para asignárselos al proceso crítico, siempre respetando los límites de `MaxEquipos` configurados.""",
            },
            {
                "slug": "reglas-criticas",
                "question": "¿Qué reglas son críticas para el negocio?",
                "answer": """1. **Prioridad Estricta:** Un proceso de prioridad 1 siempre debe ejecutarse antes que uno de prioridad 10.
2. **Aislamiento de Pools:** Si `BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO` está activo, los equipos de Finanzas nunca deben ejecutar robots de RRHH.
3. **Integridad de Datos:** La base de datos SQL Server es la única fuente de verdad. Lo que dice A360 es secundario ante lo que dice SAM.""",
            },
            {
                "slug": "que-no-hace-sam",
                "question": "¿Qué NO hace el sistema?",
                "answer": """- No ejecuta la lógica del negocio del robot (eso lo hace el Taskbot .bot).
- No gestiona credenciales de aplicaciones finales (SAP, Salesforce); solo gestiona las credenciales de ejecución del robot.
- No reemplaza al Control Room de A360, sino que lo orquesta vía API.""",
            },
        ],
    },
    "faq-funcional": {
        "title": "Funcional",
        "questions": [
            {
                "slug": "flujo-despliegue",
                "question": "¿Cómo funciona el flujo de despliegue?",
                "answer": """El **Lanzador** consulta cada 15 segundos la BD. Si encuentra un robot con asignación válida y sin ejecución activa, llama a la API de A360. Si A360 responde con un `deploymentId`, se registra en `dbo.Ejecuciones` como `DEPLOYED`.""",
            },
            {
                "slug": "manejo-fallos-despliegue",
                "question": "¿Qué sucede si un despliegue falla?",
                "answer": """Depende del error:
- **Error 412 (Integridad):** Se asume que el robot está roto. Se elimina la asignación y se alerta.
- **Error 400 (Bad Request):** Se asume error de configuración. Se elimina la asignación y se alerta.
- **Error 500 (Server):** Se reintenta si es caída general, o se elimina asignación si es específico del robot.
- **Timeout/Red:** Se reintenta hasta `max_reintentos_deploy`.""",
            },
            {
                "slug": "ejecuciones-huerfanas",
                "question": '¿Cómo se manejan estados especiales como "Huérfanas"?',
                "answer": """Una ejecución es "Huérfana" si está en `QUEUED` por más de 5 minutos sin pasar a `RUNNING`. El **Conciliador** las detecta y, dependiendo de la configuración, puede marcarlas como `RUN_FAILED` o intentar recuperarlas.""",
            },
        ],
    },
    "faq-tecnica": {
        "title": "Técnica",
        "questions": [
            {
                "slug": "decision-arquitectura",
                "question": "¿Por qué se eligió esta arquitectura de microservicios en Windows?",
                "answer": """Se eligió para desacoplar responsabilidades. El **Lanzador** debe ser rápido y reactivo. El **Balanceador** requiere cálculos pesados que no deben bloquear al Lanzador. El **Callback** debe ser una API HTTP siempre disponible. Correr como servicios Windows (NSSM) permite integración nativa con la infraestructura del cliente y reinicio automático.""",
            },
            {
                "slug": "por-que-reactpy",
                "question": "¿Por qué se eligió ReactPy en lugar de React/Angular?",
                "answer": """Para mantener el stack tecnológico 100% en Python. Esto permite que el equipo de backend pueda mantener el frontend sin necesidad de aprender un ecosistema completamente diferente (Node.js, npm, Webpack). ReactPy genera la UI en el servidor y la envía al cliente, simplificando el despliegue.""",
            },
            {
                "slug": "por-que-stored-procedures",
                "question": "¿Por qué es OBLIGATORIO usar Stored Procedures?",
                "answer": """1. **Seguridad:** Previene Inyección SQL al separar datos de comandos.
2. **Rendimiento:** SQL Server cachea los planes de ejecución.
3. **Integridad:** Garantiza que las transacciones ACID se manejen en el motor de base de datos.
4. **Centralización:** Si la lógica de negocio cambia, solo se actualiza el SP, no múltiples servicios Python.""",
            },
            {
                "slug": "manejo-errores",
                "question": "¿Cómo se manejan errores y edge cases?",
                "answer": """- **Base de Datos:** Uso de transacciones y bloques `TRY...CATCH` en Stored Procedures.
- **API:** Middleware de manejo de excepciones global en FastAPI.
- **Lanzador:** Circuit Breaker local (`_cooldown_despliegues`) para evitar bucles de error con A360.""",
            },
        ],
    },
    "faq-operaciones": {
        "title": "Operaciones",
        "questions": [
            {
                "slug": "correccion-manual-datos",
                "question": "¿Qué hago si necesito corregir datos manualmente en Producción?",
                "answer": """Si es una emergencia (ej. destrabar una ejecución):
1. **No hagas UPDATE directo.**
2. Usa el procedimiento de auditoría: `INSERT INTO dbo.AuditoriaManual ...` explicando la razón.
3. Luego ejecuta el cambio dentro de una transacción.

Esto garantiza que quede rastro de quién y por qué se modificó la data.""",
            },
            {
                "slug": "disparo-alertas",
                "question": "¿Cuándo se dispara una Alerta?",
                "answer": """El sistema envía correos (vía `EmailAlertClient`) en casos como:
- **Críticos:** Excepciones no controladas en los bucles principales de los servicios.
- **Funcionales:** Errores 412 persistentes (el equipo no se conecta).
- **Seguridad:** Fallos de autenticación con A360.

Las alertas se agrupan (throttling) para no saturar el correo.""",
            },
        ],
    },
}
