# 📖 GLOSARIO DE TÉRMINOS - PROYECTO SAM

---
**Versión:** 1.0.0
**Última Actualización:** 2025-01-19
---

## 🎯 PROPÓSITO

Este glosario define términos técnicos y conceptos específicos utilizados en SAM. Úsalo como referencia rápida cuando encuentres terminología desconocida.

---

## A

### A360
**Automation Anywhere 360** - Plataforma RPA cloud nativa que ejecuta los bots. SAM orquesta las ejecuciones sobre A360.

### Asignación
Relación entre un **Robot** y un **Equipo** que indica qué máquina puede ejecutar qué bot. Puede ser:
- **Dinámica**: Gestionada por el Balanceador
- **Programada**: Fija para programaciones específicas

---

## B

### Balanceador
Servicio (`sam.balanceador`) que asigna/desasigna equipos dinámicamente según la demanda externa (tickets pendientes).

**Ver:** [docs/servicios/servicio_balanceador.md](../servicios/servicio_balanceador.md)

### Bot Runner
Agente de Automation Anywhere instalado en una máquina Windows que ejecuta los bots. En SAM se llama **Equipo**.

---

## C

### Callback
Servicio (`sam.callback`) que recibe notificaciones HTTP desde A360 cuando un bot termina su ejecución.

**Ver:** [docs/servicios/servicio_callback.md](../servicios/servicio_callback.md)

### Conciliador
Componente del Lanzador que audita el estado de ejecuciones activas consultando la API de A360. Detecta discrepancias y actualiza estados.

**Frecuencia:** 5-15 minutos (configurable)

### Cooling (Pool Cooling)
Período de espera (default: 5 minutos) después de modificar asignaciones de un pool. Evita fluctuaciones rápidas en el balanceo.

**Configuración:** `BALANCEADOR_PERIODO_ENFRIAMIENTO_SEG`

### Control Room
Interfaz web de Automation Anywhere donde se gestionan bots, dispositivos y ejecuciones.

---

## D

### Deployment
Acción de enviar un bot a ejecutarse en un Bot Runner específico. Genera un `deploymentId` único.

### DeploymentId
Identificador único de una ejecución en A360. SAM lo almacena en `dbo.Ejecuciones.DeploymentId`.

### Desplegador
Componente del Lanzador que ejecuta robots consultando `dbo.ObtenerRobotsEjecutables()` y desplegándolos vía API A360.

**Frecuencia:** 15 segundos (configurable)

---

## E

### Equipo
Máquina física/virtual con Bot Runner instalado. Equivalente a "Device" en A360.

**Tabla:** `dbo.Equipos`

### EsOnline
Campo booleano en `dbo.Robots` que indica si el robot responde a demanda (1) o solo a programaciones (0).

- `EsOnline = 1`: Robot **online** (balanceo dinámico)
- `EsOnline = 0`: Robot **programado** (solo ejecuta según agenda)

### Estado
Valor que indica el ciclo de vida de una ejecución:
- `DEPLOYED`: Enviado a A360, esperando confirmación
- `RUNNING`: En ejecución
- `QUEUED`: Ejecución en cola
- `COMPLETED` o `RUN_COMPLETED`: Finalizado exitosamente
- `RUN_FAILED`: Falló durante ejecución
- `DEPLOY_FAILED`: Falló al desplegar
- `UNKNOWN`: Pérdida de comunicación con A360
- `COMPLETED_INFERRED`: Inferido tras múltiples intentos fallidos

---

## I

### Inferencia de Completitud
Mecanismo del Conciliador que marca una ejecución como `COMPLETED_INFERRED` cuando:
1. No aparece en la lista de ejecuciones activas de A360
2. Supera el umbral de intentos fallidos (`LANZADOR_CONCILIADOR_MAX_INTENTOS_INFERENCIA`)

**Ver:** [Estrategia "By Status"](../servicios/servicio_lanzador.md)

---

## L

### Lanzador
Servicio principal (`sam.lanzador`) que ejecuta robots, audita estados y sincroniza catálogos.

**Componentes:**
- Desplegador
- Conciliador
- Sincronizador

**Ver:** [docs/servicios/servicio_lanzador.md](../servicios/servicio_lanzador.md)

---

## M

### Mapeo
Relación entre el nombre de un robot en sistemas externos (Clouders, RPA360) y el nombre interno en SAM.

**Tabla:** `dbo.Mapeos`

**Ejemplo:**
```
Nombre Externo: "ROBOT_PAGOS_V2"
Nombre Interno: "Proceso_Pagos"
```

### MaxEquipos
Límite máximo de equipos que el Balanceador puede asignar a un robot. Valor `-1` significa ilimitado.

### MinEquipos
Cantidad mínima garantizada de equipos para un robot, independiente de la carga.

---

## P

### Pool
Grupo lógico de equipos que pueden compartirse entre robots. Permite aislar recursos por área de negocio.

**Tabla:** `dbo.Pools`

**Tipos:**
- **Aislamiento Estricto**: Equipos solo para robots del pool
- **Aislamiento Flexible**: Equipos pueden compartirse

### Preemption
Mecanismo del Balanceador que quita equipos a robots de baja prioridad para asignarlos a robots de alta prioridad cuando hay escasez de recursos.

**Ejemplo:**
```
Robot_A (Prioridad 1) necesita equipos
Robot_B (Prioridad 50) tiene 10 equipos
→ Balanceador quita 3 equipos a Robot_B y los asigna a Robot_A
```

### Prioridad de Balanceo
Valor numérico (1-100) que determina la importancia de un robot. **Menor número = mayor prioridad**.

- `1-20`: Críticos (ej. procesos financieros)
- `21-80`: Normales
- `81-100`: Secundarios (ej. reportes)

### Programación
Configuración que define cuándo ejecutar un robot automáticamente (ej. diariamente a las 9am).

**Tipos:**
- Diaria
- Semanal
- Mensual
- Única

**Tabla:** `dbo.Programaciones`

### Proveedor de Carga
Componente del Balanceador que consulta sistemas externos (Clouders, RPA360 Work Queues) para obtener la demanda (tickets pendientes).

**Interfaz:** `ProveedorCarga`

---

## R

### Robot
Bot de Automation Anywhere gestionado por SAM. Tiene configuración de prioridad, límites de equipos y parámetros de entrada.

**Tabla:** `dbo.Robots`

---

## S

### SAM
**Sistema Automático de Robots** - Orquestador RPA que gestiona ejecuciones sobre Automation Anywhere 360.

### Sincronizador
Componente del Lanzador que actualiza los catálogos de robots y equipos consultando la API de A360.

**Frecuencia:** 1 hora (configurable)

### Stored Procedure (SP)
Procedimiento almacenado en SQL Server. En SAM, **TODA** la lógica de negocio reside en SPs.

**Convención:** `dbo.NombreVerbo` (ej. `dbo.ObtenerRobotsEjecutables`)

---

## T

### Target (Compatible Target)
Configuración en A360 que define qué Bot Runners pueden ejecutar un bot específico. Puede ser:
- Device Pool
- Dispositivos específicos

**Errores comunes:**
- "No compatible targets found" → El bot no tiene targets configurados.
- "Bad Request" o "Internal Server Error" → Puede indicar problemas de integridad en el código del bot (ver **Taskbot**).

### Taskbot
El archivo de código del bot en A360.
**Errores de Integridad:** Ocurren cuando el bot tiene errores internos que impiden su despliegue, como:
- Paquetes (Packages) no instalados o versiones inexistentes en el Control Room.
- Referencias a variables que han sido eliminadas o mal renombradas.
- Dependencias de archivos (scripts, configs) que no están en la ruta esperada.

### Tickets por Equipo Adicional
Parámetro que define cuántos tickets pendientes justifican asignar un equipo adicional a un robot.

**Ejemplo:**
```
TicketsPorEquipoAdicional = 10
Carga actual = 100 tickets
→ Balanceador asigna 10 equipos (100 / 10)
```

### Tolerancia
Ventana de tiempo (en minutos) después de la hora programada en la que SAM reintentará ejecutar un robot si falló.

**Ejemplo:**
```
Hora Inicio: 09:00
Tolerancia: 30 minutos
→ Si falla a las 9:00, reintenta hasta las 9:30
```

---

## U

### UNKNOWN
Estado de una ejecución cuando SAM pierde comunicación con A360 y no puede determinar el estado real.

**Causas:**
- Timeout API A360
- Ejecución purgada del historial (>30 días)
- Problemas de red

**Resolución:** El Conciliador intenta recuperar el estado. Si falla múltiples veces, marca como `COMPLETED_INFERRED`.

---

## W

### Web (Servicio Web)
Interfaz de gestión ABM de SAM. Permite configurar robots, equipos, pools, programaciones y mapeos.

**Tecnología:** FastAPI + ReactPy

**Puerto:** 8000 (default)

**Ver:** [docs/servicios/servicio_web.md](../servicios/servicio_web.md)

---

## Símbolos y Abreviaturas

| Símbolo/Abreviatura | Significado |
|---------------------|-------------|
| **ABM** | Alta, Baja, Modificación (CRUD) |
| **API** | Application Programming Interface |
| **BD** | Base de Datos |
| **BDD** | Behavior-Driven Development |
| **CR** | Control Room (A360) |
| **CRUD** | Create, Read, Update, Delete |
| **JWT** | JSON Web Token |
| **NSSM** | Non-Sucking Service Manager |
| **RPA** | Robotic Process Automation |
| **SP** | Stored Procedure |
| **SQL** | Structured Query Language |
| **TLS** | Transport Layer Security |

---

## 📚 REFERENCIAS

Para más detalles sobre conceptos específicos, consulta:

- **Arquitectura general:** [01_arquitectura.md](01_arquitectura.md)
- **Servicios:**
  - [servicio_lanzador.md](../servicios/servicio_lanzador.md)
  - [servicio_balanceador.md](../servicios/servicio_balanceador.md)
  - [servicio_callback.md](../servicios/servicio_callback.md)
  - [servicio_web.md](../servicios/servicio_web.md)
- **Reglas SQL:** [03_reglas_sql.md](03_reglas_sql.md)
- **Ejemplos prácticos:** [05_ejemplos_tareas.md](05_ejemplos_tareas.md)

---

*Última revisión: 2025-01-19*
