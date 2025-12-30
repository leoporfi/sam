# Presentación Detallada: Interfaz Web
## Módulo sam.web - Control Central de Administración

---

## DIAPOSITIVA 1: Portada del Servicio
**Título:** Interfaz Web de SAM
**Subtítulo:** Consola Central de Gestión
**Elementos visuales:**
- Ícono de dashboard/panel de control
- Badge: "Módulo Gestión"
- Colores: Púrpura/Azul (interfaz)

---

## DIAPOSITIVA 2: Propósito - Más Que un Dashboard
**Título:** La Diferencia Entre Ver y Gestionar

**NO es solo visualización:**
❌ Dashboard de métricas pasivas
❌ Reportes estáticos
❌ Logs formateados

**ES una consola de gestión:**
✅ ABM completo (Alta, Baja, Modificación)
✅ Configuración en caliente
✅ Estrategia de asignación
✅ Programación de tareas

**Objetivo:**
Permitir al equipo de soporte y administradores configurar el comportamiento del orquestador **sin tocar la base de datos** directamente.

---

## DIAPOSITIVA 3: Arquitectura Tecnológica
**Título:** Stack Python Full-Stack

**Separación de responsabilidades:**
```
┌─────────────────────────────────┐
│        FRONTEND (ReactPy)       │
│  • Componentes en Python        │
│  • UI reactiva                  │
│  • Modales, tablas, formularios │
└─────────────┬───────────────────┘
              │ HTTP/JSON
┌─────────────┴───────────────────┐
│        BACKEND (FastAPI)        │
│  • API REST                     │
│  • Validación Pydantic          │
│  • Router modular               │
└─────────────┬───────────────────┘
              │ SQL
┌─────────────┴───────────────────┐
│      BASE DE DATOS (SQL)        │
│  • Stored Procedures            │
│  • Transacciones ACID           │
│  • Maestros + Configuración     │
└─────────────────────────────────┘
```

**Ventaja clave:** Todo en Python, mismo lenguaje que servicios SAM.

---

## DIAPOSITIVA 4: Funcionalidades ABM - Parte 1
**Título:** Gestión de Robots y Equipos

**1. GESTIÓN DE ROBOTS** 🤖
- **Visualización:** Tabla con todos los robots de A360
- **Configuración editable:**
  - **Prioridad:** 1 (crítico) a 10 (bajo)
  - **Límites:** Máximo de equipos simultáneos
  - **Estado:** Activo/Inactivo
- **Acciones:** Crear, Editar, Desactivar

**2. GESTIÓN DE EQUIPOS** 💻
- **Visualización:** Dispositivos conectados (Bot Runners)
- **Control manual:**
  - Habilitar/Deshabilitar (modo mantenimiento)
  - Asignar a Pool específico
  - Ver estado de conexión en tiempo real
- **Uso típico:** Sacar máquina para actualizaciones

---

## DIAPOSITIVA 5: Funcionalidades ABM - Parte 2
**Título:** Pools y Estrategias

**3. GESTIÓN DE POOLS** 🏊
- **Concepto:** Agrupaciones lógicas de equipos
- **Ejemplo práctico:**
  ```
  Pool_Finanzas:
    • 10 equipos dedicados
    • Robots: Pagos, Facturas, Conciliaciones
    • Aislamiento: Estricto

  Pool_RRHH:
    • 5 equipos dedicados
    • Robots: Liquidaciones, Legajos
    • Aislamiento: Flexible
  ```
- **Configuración:**
  - Nombre del pool
  - Modo de aislamiento (Estricto/Flexible)
  - Equipos asignados

**Impacto:** Define la estrategia de compartición de recursos entre áreas.

---

## DIAPOSITIVA 6: Funcionalidades ABM - Parte 3
**Título:** Mapeos y Programaciones

**4. MAPEOS** 🗺️
- **Problema que resuelve:** Nombres diferentes entre sistemas
- **Interfaz:**
  ```
  Nombre Externo (Clouders/A360) → Nombre Interno (SAM)

  [RBT_FAC_V3         ] → [Robot_Facturas  ]  [Guardar]
  [Queue_Pagos_Prod   ] → [Robot_Pagos     ]  [Guardar]
  [Proc_RRHH_Legacy   ] → [Robot_Legajos   ]  [Guardar]
  ```
- **Uso crítico:** Para que el Balanceador reconozca carga externa

**5. SCHEDULES** ⏰
- **Programación CRON:** Define cuándo ejecutar robots automáticamente
- **Interfaz:**
  - Robot a ejecutar
  - Expresión CRON (ej. `0 8 * * 1-5` = Lun-Vie 8AM)
  - Estado: Activo/Pausado
- **Ejemplo:** Reporte diario de ventas cada día a las 7AM

---

## DIAPOSITIVA 7: Flujo de Datos - Ejemplo Edición
**Título:** Ciclo Completo de una Modificación

**Caso: Cambiar prioridad de Robot_Facturas de 5 a 1**

```
PASO 1: USUARIO
Panel Robots → Clic "Editar" → Cambiar prioridad a 1 → Guardar
      ↓
PASO 2: FRONTEND (robots_modals.py)
Captura evento → api_client.update_robot(id=15, prioridad=1)
      ↓
PASO 3: HTTP REQUEST
PUT /api/robots/15
Body: {"prioridad": 1, "limite_equipos": 10, ...}
      ↓
PASO 4: BACKEND (api.py)
Recibe request → Valida con Pydantic (schemas.py)
      ↓
PASO 5: BASE DE DATOS (database.py)
EXEC dbo.ActualizarRobotConfig
  @RobotId=15,
  @Prioridad=1
      ↓
PASO 6: CONFIRMACIÓN
BD confirma → Backend 200 OK → Frontend notificación ✓
      ↓
PASO 7: IMPACTO INMEDIATO
Balanceador lee nueva prioridad en próximo ciclo (60 seg)
```

---

## DIAPOSITIVA 8: Configuración y Variables
**Título:** Parámetros de Operación

**Variables de entorno (.env):**

**Servidor Web:**
```bash
INTERFAZ_WEB_HOST=0.0.0.0
INTERFAZ_WEB_PORT=8000
INTERFAZ_WEB_DEBUG=false  # true solo en desarrollo
```

**Base de datos:**
```bash
SQL_SAM_DRIVER={ODBC Driver 17 for SQL Server}
SQL_SAM_HOST=sql-server.empresa.com
SQL_SAM_DB_NAME=SAM_Production
SQL_SAM_UID=svc_sam_web
SQL_SAM_PWD=*****************
```

**Logging:**
```bash
LOG_DIRECTORY=C:\RPA\Logs\SAM
APP_LOG_FILENAME_INTERFAZ_WEB=web.log
```

**Acceso:**
```
URL: http://servidor-sam:8000
Autenticación: [Si aplica, definir método]
```

---

## DIAPOSITIVA 9: Estructura de Componentes
**Título:** Organización del Frontend (ReactPy)

**Arquitectura modular:**
```
src/sam/web/frontend/
├── features/
│   └── components/
│       ├── robots_components.py      # Tabla + Modales robots
│       ├── equipos_components.py     # Gestión de equipos
│       ├── pools_components.py       # ABM de pools
│       ├── mappings_page.py          # Mapeos externos
│       └── schedules_components.py   # Programaciones CRON
│
├── shared/
│   ├── api_client.py                 # Cliente HTTP reutilizable
│   ├── notifications.py              # Toast messages
│   └── styles.py                     # CSS global
│
└── app.py                            # Punto de entrada
```

**Beneficio:** Cada feature es independiente, fácil mantenimiento.

---

## DIAPOSITIVA 10: Troubleshooting y Casos de Uso
**Título:** Soporte y Operación Diaria

**Casos de uso comunes:**

**Caso 1: Agregar nuevo robot**
```
Web → Robots → "Nuevo Robot"
  ├─ Nombre: Robot_NuevoProceso
  ├─ Prioridad: 5
  ├─ Límite equipos: 3
  └─ Pool: Pool_Finanzas
```

**Caso 2: Mantenimiento de equipo**
```
Web → Equipos → Seleccionar "EQ-WIN-01"
  └─ Deshabilitar temporalmente
  └─ Balanceador NO lo asignará hasta re-habilitar
```

**Caso 3: Configurar mapeo para nuevo proveedor**
```
Web → Mapeos → "Nuevo Mapeo"
  ├─ Sistema origen: Clouders
  ├─ Nombre externo: PROC_VENTAS_2024
  └─ Robot SAM: Robot_Ventas
```

**Troubleshooting:**

| Problema | Log | Solución |
|----------|-----|----------|
| Error 500 al guardar | web.log | Verificar conexión BD |
| Cambio no se refleja | (servicio afectado).log | Esperar próximo ciclo |
| Interfaz no carga | web.log | Verificar puerto 8000 libre |

**Servicio Windows:** `SAM_Web` (NSSM)

**URL de acceso:** `http://[servidor]:8000`
