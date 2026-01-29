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

**Tipos:**
- **Aislamiento Estricto**: Equipos solo para robots del pool.
- **Aislamiento Flexible (Overflow)**: Si sobran equipos en el pool, pueden prestarse a otros pools.""",
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
                "description": """**Descripción:** Mecanismo del Balanceador (activado por `BALANCEO_PREEMPTION_MODE`) que desaloja robots de baja prioridad y cede sus equipos a robots de alta prioridad con demanda insatisfecha.

**Reglas:**
- Solo ocurre si el robot de alta prioridad tiene "hambre" (déficit de equipos).
- Solo desaloja si el robot víctima tiene menor prioridad (mayor número).
- Es diferente al Overflow: Preemption quita recursos ocupados, Overflow usa recursos libres.""",
            },
            {
                "slug": "cooling",
                "term": "Cooling (Enfriamiento)",
                "description": """**Descripción:** Periodo de tiempo durante el cual un Pool o Robot no puede sufrir cambios en sus asignaciones tras una modificación.

**Objetivo:** Evitar oscilaciones (flapping) y dar tiempo a que los cambios surtan efecto.

**Valor Default:** 300 segundos (5 minutos).""",
            },
            {
                "slug": "prioridad-balanceo",
                "term": "Prioridad de Balanceo",
                "description": """**Descripción:** Valor numérico (1-100) que determina la importancia de un robot. **Menor número = mayor prioridad**.

- `1-20`: Críticos (ej. procesos financieros)
- `21-80`: Normales
- `81-100`: Secundarios (ej. reportes)""",
            },
            {
                "slug": "max-equipos",
                "term": "MaxEquipos",
                "description": """**Descripción:** Límite máximo de equipos que el Balanceador puede asignar a un robot. Valor `-1` significa ilimitado.""",
            },
            {
                "slug": "min-equipos",
                "term": "MinEquipos",
                "description": """**Descripción:** Cantidad mínima garantizada de equipos para un robot, independiente de la carga.""",
            },
            {
                "slug": "es-online",
                "term": "EsOnline",
                "description": """**Descripción:** Campo booleano en `dbo.Robots` que indica si el robot responde a demanda (1) o solo a programaciones (0).

- `EsOnline = 1`: Robot **online** (balanceo dinámico)
- `EsOnline = 0`: Robot **programado** (solo ejecuta según agenda)""",
            },
            {
                "slug": "tickets-equipo-adicional",
                "term": "Tickets por Equipo Adicional",
                "description": """**Descripción:** Parámetro que define cuántos tickets pendientes justifican asignar un equipo adicional a un robot.

**Ejemplo:**
TicketsPorEquipoAdicional = 10, Carga actual = 100 tickets → Balanceador asigna 10 equipos.""",
            },
            {
                "slug": "tolerancia",
                "term": "Tolerancia",
                "description": """**Descripción:** Ventana de tiempo (en minutos) después de la hora programada en la que SAM reintentará ejecutar un robot si falló.

**Ejemplo:** Hora Inicio: 09:00, Tolerancia: 30 min → Si falla a las 9:00, reintenta hasta las 9:30.""",
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
            {
                "slug": "a360",
                "term": "A360 (Automation Anywhere 360)",
                "description": """**Descripción:** Plataforma RPA cloud nativa que ejecuta los bots. SAM orquesta las ejecuciones sobre A360.""",
            },
            {
                "slug": "bot-runner",
                "term": "Bot Runner",
                "description": """**Descripción:** Agente de Automation Anywhere instalado en una máquina Windows que ejecuta los bots. En SAM se llama **Equipo**.""",
            },
            {
                "slug": "control-room",
                "term": "Control Room",
                "description": """**Descripción:** Interfaz web de Automation Anywhere donde se gestionan bots, dispositivos y ejecuciones.""",
            },
            {
                "slug": "deployment-id",
                "term": "DeploymentId",
                "description": """**Descripción:** Identificador único de una ejecución en A360. SAM lo almacena en `dbo.Ejecuciones.DeploymentId`.""",
            },
            {
                "slug": "nssm",
                "term": "NSSM",
                "description": """**Descripción:** Non-Sucking Service Manager. Herramienta utilizada para ejecutar los scripts de Python como servicios de Windows.""",
            },
            {
                "slug": "jwt",
                "term": "JWT (JSON Web Token)",
                "description": """**Descripción:** Estándar para la creación de tokens de acceso. Utilizado para la autenticación con la API de A360.""",
            },
        ],
    },
    "componentes-servicios": {
        "title": "Componentes y Servicios",
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

**Responsabilidad:** Recibir notificación inmediata de fin de robot y actualizar `dbo.Ejecuciones`.""",
            },
            {
                "slug": "api-web",
                "term": "API Web",
                "description": """**Tipo:** API REST (FastAPI)

**Responsabilidad:** Interfaz de gestión ABM de SAM. Permite configurar robots, equipos, pools, programaciones y mapeos.""",
            },
            {
                "slug": "desplegador",
                "term": "Desplegador",
                "description": """**Descripción:** Componente del Lanzador que ejecuta robots consultando `dbo.ObtenerRobotsEjecutables()` y desplegándolos vía API A360.

**Frecuencia:** 15 segundos (configurable).""",
            },
            {
                "slug": "conciliador",
                "term": "Conciliador",
                "description": """**Descripción:** Componente del Lanzador que audita el estado de ejecuciones activas consultando la API de A360. Detecta discrepancias y actualiza estados.

**Frecuencia:** 5-15 minutos (configurable).""",
            },
            {
                "slug": "sincronizador",
                "term": "Sincronizador",
                "description": """**Descripción:** Componente del Lanzador que actualiza los catálogos de robots y equipos consultando la API de A360.

**Frecuencia:** 1 hora (configurable).""",
            },
            {
                "slug": "proveedor-carga",
                "term": "Proveedor de Carga",
                "description": """**Descripción:** Componente del Balanceador que consulta sistemas externos (Clouders, RPA360 Work Queues) para obtener la demanda (tickets pendientes).""",
            },
        ],
    },
    "conceptos-a360": {
        "title": "Conceptos A360",
        "terms": [
            {
                "slug": "target",
                "term": "Target (Compatible Target)",
                "description": """**Descripción:** Configuración en A360 que define qué Bot Runners pueden ejecutar un bot específico.

**Errores comunes:**
- "No compatible targets found" → El bot no tiene targets configurados.
- "Bad Request" → Problemas de integridad en el bot.""",
            },
            {
                "slug": "taskbot",
                "term": "Taskbot",
                "description": """**Descripción:** El archivo de código del bot en A360.

**Errores de Integridad:** Paquetes faltantes, variables eliminadas, dependencias rotas.""",
            },
        ],
    },
    "estados": {
        "title": "Estados de Ejecución",
        "terms": [
            {
                "slug": "estado",
                "term": "Estado",
                "description": """**Descripción:** Valor que indica el ciclo de vida de una ejecución:
- `DEPLOYED`: Enviado a A360.
- `RUNNING`: En ejecución.
- `QUEUED`: En cola.
- `COMPLETED`: Finalizado exitosamente.
- `RUN_FAILED`: Falló durante ejecución.
- `DEPLOY_FAILED`: Falló al desplegar.
- `UNKNOWN`: Pérdida de comunicación.
- `COMPLETED_INFERRED`: Inferido tras intentos fallidos.""",
            },
            {
                "slug": "unknown",
                "term": "UNKNOWN",
                "description": """**Descripción:** Estado de una ejecución cuando SAM pierde comunicación con A360.

**Causas:** Timeout API, ejecución purgada, red.
**Resolución:** El Conciliador intenta recuperar o inferir el estado.""",
            },
            {
                "slug": "inferencia-completitud",
                "term": "Inferencia de Completitud",
                "description": """**Descripción:** Mecanismo del Conciliador que marca una ejecución como `COMPLETED_INFERRED` cuando no aparece en A360 tras múltiples intentos.""",
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
                "description": """**Descripción:** Estrategia de seguridad donde cada usuario/servicio tiene solo los permisos estrictamente necesarios.""",
            },
            {
                "slug": "auditoria-manual",
                "term": "Auditoría Manual",
                "description": """**Descripción:** Tabla `dbo.AuditoriaManual` y procedimiento asociado.

**Uso:** Obligatorio registrar aquí cualquier cambio manual de datos (UPDATE/DELETE) realizado por un operador humano.""",
            },
            {
                "slug": "sistema-de-alertas",
                "term": "Sistema de Alertas",
                "description": """**Componentes:** `EmailAlertClient`, `AlertContext`.

**Niveles:** `CRITICAL`, `HIGH`, `MEDIUM`.

**Throttling:** Mecanismo que agrupa alertas idénticas para evitar spam.""",
            },
        ],
    },
    "general": {
        "title": "General",
        "terms": [
            {
                "slug": "sam",
                "term": "SAM",
                "description": """**Sistema Automático de Robots** - Orquestador RPA que gestiona ejecuciones sobre Automation Anywhere 360.""",
            },
            {
                "slug": "mapeo",
                "term": "Mapeo",
                "description": """**Descripción:** Relación entre el nombre de un robot en sistemas externos (Clouders, RPA360) y el nombre interno en SAM.""",
            },
            {
                "slug": "abm",
                "term": "ABM",
                "description": """Alta, Baja, Modificación (CRUD).""",
            },
        ],
    },
}

# ============================================================================
# FAQ DEL PROYECTO
# ============================================================================

FAQ_DATA = {
    "faq-general": {
        "title": "Conceptos Generales",
        "questions": [
            {
                "slug": "que-es-sam",
                "question": "¿Qué es SAM y cuál es su objetivo principal?",
                "answer": """**SAM (Sistema Automático de Robots)** es un orquestador inteligente que gestiona la ejecución de robots de Automation Anywhere 360 (A360).

**Objetivo principal:**
- **Balanceo dinámico de carga:** Asigna equipos automáticamente según la demanda.
- **Priorización inteligente:** Garantiza recursos a robots críticos.
- **Programaciones avanzadas:** Ejecuciones cíclicas y tolerancias.
- **Monitoreo en tiempo real:** Recuperación automática de fallos.""",
            },
        ],
    },
    "faq-balanceador": {
        "title": "Servicio Balanceador",
        "questions": [
            {
                "slug": "como-sabe-sam-tickets",
                "question": "¿Cómo sabe SAM cuántos tickets tiene cada robot?",
                "answer": """SAM consulta **proveedores de carga externos** (Clouders, RPA360) cada `BALANCEADOR_INTERVALO_CICLO_SEG` (default: 120s).

**Ejemplo:** 100 tickets / 10 tickets_por_equipo = 10 equipos necesarios.""",
            },
            {
                "slug": "sin-equipos-disponibles",
                "question": "¿Qué pasa si no hay equipos disponibles en la bolsa general?",
                "answer": """Si un pool busca equipos y no encuentra:
1. **Aislamiento Estricto:** El robot debe esperar a que se liberen equipos en su propio Pool.
2. **Aislamiento Flexible (Overflow):** Si `BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO = FALSE`, el robot puede tomar prestados equipos **libres** del Pool General.
3. **Preemption:** Si `BALANCEO_PREEMPTION_MODE = TRUE`, el robot puede **quitar equipos** a robots de menor prioridad.""",
            },
            {
                "slug": "como-funciona-preemption",
                "question": "¿Cómo funciona la Preemption?",
                "answer": """SAM reasigna equipos de un robot de baja prioridad a uno de alta.
**Importante:** Modifica la BD inmediatamente pero **NO detiene ejecuciones en curso** en A360. El robot prioritario "captura" el equipo para la siguiente ejecución.
**Configuración:** Solo se activa si `BALANCEO_PREEMPTION_MODE = TRUE` en `dbo.ConfiguracionSistema`. (Nota: `BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO` controla el préstamo de equipos libres, no el desalojo).""",
            },
            {
                "slug": "balanceo-sin-tickets",
                "question": "¿Cómo se balancean robots que NO trabajan con tickets?",
                "answer": """Para robots sin tickets (no on-demand), usa:
1. **Programaciones Cíclicas:** `EsCiclico=1`.
2. **Asignaciones Fijas:** Manualmente desde el panel.
3. **Prioridad Mínima Garantizada:** Configurar `MinEquipos`.""",
            },
        ],
    },
    "faq-configuracion": {
        "title": "Configuración y Programaciones",
        "questions": [
            {
                "slug": "priorizar-dias-semana",
                "question": "¿Puedo priorizar un robot solo ciertos días de la semana?",
                "answer": """**No automáticamente.** La prioridad es fija.
**Soluciones:**
1. Cambio manual de prioridad.
2. Usar programaciones fijas con equipos dedicados esos días.
3. Ajustar `MinEquipos` manualmente.""",
            },
            {
                "slug": "parametros-por-pool",
                "question": "¿La variable `in_NumRepeticion` se puede variar por pool?",
                "answer": """**No.** Los parámetros son a nivel de **Robot**.
**Alternativa:** Modificar el Taskbot para leer configuración externa local en cada equipo, o crear dos robots lógicos distintos en SAM.""",
            },
            {
                "slug": "conflicto-programacion",
                "question": "¿Qué pasa si programo 2 robots para la misma hora en la misma VM?",
                "answer": """SAM valida conflictos y ejecuta solo uno basado en prioridad:
1. Programados > Online.
2. Menor `PrioridadBalanceo` gana.
3. Hora más temprana gana.""",
            },
        ],
    },
    "faq-reportes": {
        "title": "Reportes y Monitoreo",
        "questions": [
            {
                "slug": "reportes-ejecuciones",
                "question": "¿SAM genera reportes de ejecuciones?",
                "answer": """**Actualmente:** Dashboard web en tiempo real.
**Histórico:** Consultar tablas `dbo.Ejecuciones` y `dbo.Ejecuciones_Historico` o usar Control Room de A360.""",
            },
        ],
    },
    "faq-tecnica": {
        "title": "Técnica",
        "questions": [
            {
                "slug": "decision-arquitectura",
                "question": "¿Por qué se eligió esta arquitectura de microservicios en Windows?",
                "answer": """Para desacoplar responsabilidades. Lanzador (rápido), Balanceador (cálculos pesados), Callback (API HTTP). Servicios Windows permiten integración nativa y reinicio automático.""",
            },
            {
                "slug": "por-que-reactpy",
                "question": "¿Por qué se eligió ReactPy?",
                "answer": """Para mantener el stack 100% en Python, permitiendo que el equipo de backend mantenga el frontend sin aprender JS/Node.js.""",
            },
            {
                "slug": "por-que-stored-procedures",
                "question": "¿Por qué es OBLIGATORIO usar Stored Procedures?",
                "answer": """Seguridad (SQL Injection), Rendimiento (caché de planes), Integridad (ACID) y Centralización de lógica.""",
            },
        ],
    },
}
