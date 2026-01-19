# 10. PREGUNTAS FRECUENTES (FAQ)

---
**Versión:** 1.0.0
**Última Actualización:** 2025-01-19
---

Este documento responde a las preguntas más comunes de los usuarios de SAM, recopiladas durante presentaciones y capacitaciones.

---

## 📋 ÍNDICE

1. [Conceptos Generales](#conceptos-generales)
2. [Servicio Balanceador](#servicio-balanceador)
3. [Configuración y Programaciones](#configuración-y-programaciones)
4. [Reportes y Monitoreo](#reportes-y-monitoreo)

---

## 🎯 CONCEPTOS GENERALES

### ¿Qué es SAM y cuál es su objetivo principal?

**SAM (Sistema Automático de Robots)** es un orquestador inteligente que gestiona la ejecución de robots de Automation Anywhere 360 (A360).

**Objetivo principal:**
- **Balanceo dinámico de carga:** Asigna equipos (Bot Runners) automáticamente según la demanda de trabajo.
- **Priorización inteligente:** Garantiza que robots críticos tengan recursos antes que los de baja prioridad.
- **Programaciones avanzadas:** Permite configurar ejecuciones cíclicas, por rangos de fechas y con tolerancias.
- **Monitoreo en tiempo real:** Detecta y recupera automáticamente ejecuciones en estado `UNKNOWN`.

> 💡 **Analogía:** Si A360 es la flota de taxis, SAM es el centro de despacho que decide estratégicamente a dónde enviar cada vehículo según la demanda.

---

## ⚖️ SERVICIO BALANCEADOR

### ¿Cómo sabe SAM cuántos tickets tiene cada robot?

SAM consulta **proveedores de carga externos** configurados en el sistema. Actualmente soporta:
- **Clouders:** Consulta la API del Orquestador (https://clouders.telefonica.com.ar/automatizacion/task/api) para obtener tickets pendientes por robot.
- **RPA360:** Consulta las colas de trabajo de la base de datos de RPA360.

El balanceador ejecuta esta consulta cada `BALANCEADOR_INTERVALO_CICLO_SEG` (configurable, default: 60 segundos) y ajusta las asignaciones dinámicamente.

**Ejemplo:**
```
Robot "Proceso_Pagos" tiene 100 tickets en Clouders
→ SAM calcula: 100 tickets / 10 tickets_por_equipo = 10 equipos necesarios
→ Asigna equipos del pool hasta alcanzar ese número
```

---

### ¿Qué pasa si no hay equipos disponibles en la bolsa general?

**Escenario:** Un pool tiene `Aislamiento=0` (flexible) y busca equipos en la bolsa general con `PermiteBalanceoDinamico=1`, pero no encuentra ninguno disponible.

**Comportamiento:**
1. **Sin Preemption:** Si no hay robots de menor prioridad usando equipos, el robot simplemente **no se ejecuta** hasta que haya recursos disponibles.
2. **Con Preemption:** Si hay robots de **menor prioridad** ejecutándose, SAM puede **quitar equipos** a esos robots para dárselos al de mayor prioridad (ver siguiente pregunta).

**Recomendación:** Configurar `MinEquipos` para robots críticos garantiza que siempre tengan al menos ese número de equipos reservados.

---

### ¿Cómo funciona la Preemption (quitar equipos a un robot en ejecución)?

**Preemption** es el mecanismo por el cual SAM **reasigna equipos** de un robot de baja prioridad a uno de alta prioridad.

**Importante:** SAM modifica las **asignaciones en la base de datos inmediatamente**, pero **NO detiene ejecuciones en curso** en A360.

**Flujo real:**
```
1. Robot A (Prioridad 1) necesita 5 equipos, pero el pool está lleno.
2. Robot B (Prioridad 10) tiene 8 equipos asignados.
3. SAM compara prioridades: 1 < 10 → Robot A tiene mayor prioridad.
4. SAM ejecuta DELETE en dbo.Asignaciones para quitar 5 equipos a Robot B.
5. Esos equipos quedan "libres" en la base de datos.
6. La fase de "Balanceo Interno" (que se ejecuta inmediatamente después) los asigna a Robot A.
7. Las ejecuciones actuales de Robot B en A360 continúan normalmente hasta completarse.
8. Cuando el Lanzador busca nuevos trabajos para Robot B, ya NO verá esos equipos asignados.
```

**Resultado:** El robot de alta prioridad "captura" los equipos para **futuras ejecuciones**, sin interrumpir el trabajo en curso. Si Robot B tiene una ejecución activa en un equipo desalojado, esa ejecución terminará normalmente, pero el siguiente ciclo del Lanzador ya no intentará usar ese equipo para Robot B.

> ⚙️ **Configuración:** La Preemption solo se activa si `BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO = FALSE` en `dbo.ConfiguracionSistema`.

---

### ¿Cómo se balancean robots que NO trabajan con tickets?

**Respuesta corta:** SAM está diseñado principalmente para robots **on-demand** (con carga externa). Para robots sin tickets, usa **programaciones fijas**.

**Opciones:**
1. **Programaciones con `EsCiclico=1`:** El robot se ejecuta repetidamente dentro de una ventana horaria sin necesidad de tickets.
2. **Asignaciones manuales permanentes:** Asigna equipos fijos al robot desde el panel web y desmarca `PermiteBalanceoDinamico` en esos equipos.
3. **Prioridad mínima garantizada:** Configura `MinEquipos` para que siempre tenga recursos, aunque no haya tickets.

**Ejemplo de uso:**
```
Robot "Monitoreo_Continuo" debe correr 24/7 en 2 equipos fijos:
→ Crear programación Diaria, EsCiclico=1, HoraInicio=00:00, HoraFin=23:59
→ Asignar 2 equipos manualmente y marcar EsProgramado=1
```

---

## ⚙️ CONFIGURACIÓN Y PROGRAMACIONES

### ¿Puedo priorizar un robot solo ciertos días de la semana?

**No automáticamente.** La prioridad (`PrioridadBalanceo`) es un valor fijo en la tabla `Robots` y **no cambia según el día de la semana**.

**Limitaciones técnicas:**
- `PrioridadBalanceo` es una columna estática en `dbo.Robots`.
- Un robot solo puede pertenecer a **un pool** a la vez (columna `PoolId`).
- No existe lógica de "prioridad temporal" o "prioridad por ventana horaria".

**Soluciones actuales (todas requieren intervención manual):**

**Opción 1: Cambio manual de prioridad**
```
Miércoles 07:00:
  - Editar el robot en el panel web
  - Cambiar PrioridadBalanceo de 50 a 1
  - Guardar

Jueves 07:00:
  - Volver a editar y cambiar a 50
```
**Desventaja:** Requiere intervención humana cada semana.

**Opción 2: Usar programaciones fijas con equipos dedicados**
```
- Crear una programación Semanal: DiasSemana="Mi", HoraInicio=08:00
- Asignar manualmente 8 equipos específicos al robot (EsProgramado=1)
- Esos equipos quedarán reservados solo para ese robot los miércoles
```
**Desventaja:** Los equipos no se pueden usar para otros robots ese día.

**Opción 3: Ajustar `MinEquipos` manualmente antes del día crítico**
```
Martes 23:00: Cambiar MinEquipos de 2 a 8
Miércoles 23:00: Volver a cambiar MinEquipos a 2
```
**Desventaja:** También requiere cambios manuales semanales.

> 📌 **Recomendación:** Si este escenario es frecuente, considera mantener una prioridad alta permanente para el robot y ajustar `MinEquipos` para garantizar recursos mínimos siempre.

> � **Futuro:** La funcionalidad de "Prioridad Dinámica por Ventana Temporal" podría agregarse en versiones futuras si hay demanda suficiente.

---

### ¿La variable `in_NumRepeticion` se puede variar por pool?

**No.** Los parámetros de entrada (`bot_input`) se configuran a nivel de **Robot**, no de Pool ni de Equipo.

**Configuración actual:**
```json
// En la tabla Robots, columna Parametros
{
  "in_NumRepeticion": {"type": "NUMBER", "number": "5"}
}
```

**Limitaciones técnicas:**
- La columna `Parametros` está en `dbo.Robots`, que tiene `RobotId` como PRIMARY KEY.
- Un `RobotId` (FileId de A360) solo puede tener **un registro** en la tabla.
- No existe lógica para "parámetros por pool" o "parámetros por equipo".

**¿Por qué no se puede hacer un workaround?**
No es posible crear múltiples registros con el mismo `RobotId` porque:
1. El Stored Procedure `dbo.CrearRobot` valida que el `RobotId` no exista antes de insertar.
2. La constraint PRIMARY KEY impide duplicados a nivel de base de datos.

**Alternativa (si realmente necesitas comportamiento diferente):**
Si un robot debe ejecutarse con parámetros diferentes según el contexto, debes:
1. **Modificar el Taskbot en A360** para que lea los parámetros de una fuente externa (ej. archivo de configuración, base de datos, variable de entorno del Bot Runner).
2. Configurar cada equipo con su propia configuración local.

**Ejemplo:**
```
Taskbot lee archivo: C:\Config\Proceso_A_Config.json
Equipo 1: {"in_NumRepeticion": 1}
Equipo 2: {"in_NumRepeticion": 10}
```

> 📌 **Recomendación:** Si necesitas comportamientos muy diferentes, considera crear **dos Taskbots separados en A360** (ej. "Proceso_A_Rapido" y "Proceso_A_Lento") y registrarlos como robots independientes en SAM.

---

---

### ¿Qué pasa si programo 2 robots para la misma hora en la misma VM?

**SAM SÍ valida conflictos de programación** y solo ejecuta **uno** de los robots. El sistema usa un mecanismo de priorización automática.

**Comportamiento real:**
1. SAM detecta que hay 2 programaciones para el mismo equipo a la misma hora.
2. Aplica el siguiente orden de prioridad para decidir cuál ejecutar:
   - **Primero:** Robots programados tienen prioridad sobre robots online.
   - **Segundo:** Si ambos son programados, gana el de **menor** `PrioridadBalanceo` (1 es más prioritario que 100).
   - **Tercero:** Si tienen la misma prioridad, gana el de **hora más temprana**.
3. Solo el robot ganador se envía a A360.
4. El robot perdedor **no se ejecuta** en ese ciclo.

**Ejemplo:**
```
Robot A: HoraInicio=08:00, PrioridadBalanceo=10
Robot B: HoraInicio=08:00, PrioridadBalanceo=50
Equipo: VM-001

Resultado: Solo se ejecuta Robot A (prioridad 10 < 50)
Robot B no se ejecuta en ese horario.
```

**¿Qué es la Tolerancia?**
La `Tolerancia` define una **ventana de tiempo** en la que el robot puede ejecutarse:
```
HoraInicio = 08:00
Tolerancia = 15 minutos
→ Ventana de ejecución: 08:00 a 08:15
```

Si SAM intenta lanzar el robot a las 08:10, aún está dentro de la ventana y se ejecutará.

**Recomendación:**
- **Evita programar múltiples robots a la misma hora en el mismo equipo** si quieres que ambos se ejecuten.
- Usa `Tolerancia` para dar margen de error, no para crear ventanas de ejecución amplias.
- Si necesitas que ambos robots se ejecuten, programa horarios diferentes o usa equipos diferentes.

**Ejemplo de buena práctica:**
```
Robot A: 08:00 (Tolerancia: 5 min) → Ventana: 08:00-08:05
Robot B: 08:10 (Tolerancia: 5 min) → Ventana: 08:10-08:15
```

---

---

## 📊 REPORTES Y MONITOREO

### ¿SAM genera reportes de ejecuciones, cantidad de VMs, etc.?

**Actualmente:** SAM tiene un **dashboard web en tiempo real** que muestra:
- Estado de ejecuciones recientes (últimas 24-48 horas)
- Equipos activos y su estado
- Robots configurados y sus asignaciones
- Programaciones activas

**Para reportes históricos:**
- **Opción 1:** Consultar directamente las tablas `dbo.Ejecuciones` y `dbo.Ejecuciones_Historico` (retención de 15 días).
- **Opción 2:** Usar el **Control Room de A360**, que tiene reportes nativos de auditoría y ejecución.
- **Opción 3 (Futuro):** Estamos evaluando agregar exportación a CSV/Excel desde el panel web.

**Consulta SQL de ejemplo:**
```sql
-- Ejecuciones por robot en los últimos 7 días
SELECT
    r.Robot,
    COUNT(*) AS TotalEjecuciones,
    SUM(CASE WHEN e.Estado LIKE '%COMPLETED' THEN 1 ELSE 0 END) AS Exitosas,
    SUM(CASE WHEN e.Estado LIKE '%FAILED' THEN 1 ELSE 0 END) AS Fallidas
FROM dbo.Ejecuciones e
INNER JOIN dbo.Robots r ON e.RobotId = r.RobotId
WHERE e.FechaInicio >= DATEADD(day, -7, GETDATE())
GROUP BY r.Robot
ORDER BY TotalEjecuciones DESC
```

---

## 📚 REFERENCIAS

| Pregunta relacionada con | Ver documento |
|--------------------------|---------------|
| Arquitectura del balanceador | `01_arquitectura.md` (sección Balanceador) |
| Crear programaciones | `05_ejemplos_tareas.md` (Tarea 3) |
| Configurar pools | `docs/servicios/servicio_balanceador.md` |
| Estados de ejecución | `09_glosario.md` |

---

*Última revisión: 2025-01-19 | ¿Tienes más preguntas? Contacta al equipo de SAM.*
