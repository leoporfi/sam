Resumen y decisiones pendientes:

## Resumen del análisis

### Situación actual
1. Robots Online (`EsOnline = 1`): ejecución cíclica continua, sin restricciones temporales
2. Robots Programados: ejecución única según cronograma, con restricciones temporales
3. Necesidad: robots cíclicos con ventanas temporales (ejecutar cíclicamente solo dentro de rangos horarios/fechas)

### Solución propuesta
Agregar campos a `Programaciones` (sin replanteo mayor):
- `EsCiclico` [bit]: indica ejecución cíclica
- `HoraFin` [time]: fin del rango horario
- `FechaInicioVentana` [date]: inicio de la ventana
- `FechaFinVentana` [date]: fin de la ventana
- `IntervaloEntreEjecuciones` [int]: minutos entre ejecuciones (opcional)

### Decisiones tomadas
1. Reutilizar `PrioridadBalanceo` del robot (no crear `PrioridadEjecucion`)

## Decisiones pendientes

### 1. Gestión de asignaciones
- Opción A: Asignaciones fijas (`EsProgramado = 1`) que persisten siempre
  - Ventaja: simple, consistente con programaciones actuales
  - Desventaja: equipos bloqueados fuera de ventana
- Opción B: Asignaciones dinámicas que se crean/eliminan según ventana
  - Ventaja: equipos liberados fuera de ventana
  - Desventaja: más complejo, requiere lógica adicional
- Opción C: Asignaciones fijas + validación en ejecución (recomendada)
  - Las asignaciones persisten, pero `ObtenerRobotsEjecutables` valida la ventana
  - Equipos bloqueados fuera de ventana (trade-off aceptable)

¿Cuál prefieres? Recomiendo Opción C.

### 2. Validación de solapamientos
- Opción A: Bloqueo total (no permite crear si hay solapamiento)
- Opción B: Solo advertencias (permite crear pero alerta)
- Opción C: Híbrida (bloquea solapamientos totales, advierte parciales) (recomendada)

¿Cuál prefieres? Recomiendo Opción C.

### 3. Comportamiento de robots cíclicos
- ¿Se ejecutan inmediatamente al entrar en ventana?
- ¿Respetan `IntervaloEntreEjecuciones`?
- ¿Qué pasa si una ejecución se extiende más allá de `HoraFin`?

Propuesta:
- Respetar `IntervaloEntreEjecuciones` si está definido
- Si no está definido, ejecutar tan pronto como el equipo esté libre
- Si una ejecución se extiende más allá de `HoraFin`, permitir que termine (no cancelar)

¿De acuerdo?

### 4. Múltiples ventanas del mismo robot
- ¿Un robot puede tener múltiples programaciones con diferentes ventanas?
- Ejemplo: Programación 1 (9:00-12:00) y Programación 2 (14:00-18:00)

Propuesta: Sí, permitir múltiples programaciones. Cada una crea sus asignaciones y `ObtenerRobotsEjecutables` valida si alguna ventana está activa.

¿De acuerdo?

### 5. Interacción con Balanceador
- ¿El Balanceador puede tocar asignaciones de robots cíclicos con ventana?

Propuesta: No. Tratar como `EsProgramado = 1` (fijas, el Balanceador no las toca).

¿De acuerdo?

### 6. Campos opcionales vs requeridos
- ¿`HoraFin` es obligatorio para robots cíclicos?
- ¿`FechaInicioVentana` y `FechaFinVentana` son obligatorios?

Propuesta:
- `EsCiclico = 1` sin `HoraFin`: cíclico todo el día
- `EsCiclico = 1` con `HoraFin`: cíclico solo en ese rango horario
- Sin fechas de ventana: válido indefinidamente
- Con fechas: válido solo en ese rango

¿De acuerdo?

## Checklist de decisiones

- [ ] Decisión 1: Gestión de asignaciones → Opción C (fijas + validación)
- [ ] Decisión 2: Validación de solapamientos → Opción C (híbrida)
- [ ] Decisión 3: Comportamiento cíclico → Propuesta aceptada
- [ ] Decisión 4: Múltiples ventanas → Permitir
- [ ] Decisión 5: Interacción Balanceador → No tocar asignaciones
- [ ] Decisión 6: Campos opcionales → Propuesta aceptada

## Próximos pasos (después de aprobación)

1. Crear rama: `feature/robots-ciclicos-con-ventanas`
2. Script SQL: agregar campos a `Programaciones`
3. Modificar SPs: `CrearProgramacion`, `ActualizarProgramacionCompleta`, `ObtenerRobotsEjecutables`
4. Nuevo SP: `ValidarSolapamientoVentanas`
5. Actualizar documentación

Confirma las decisiones y procedo a crear la rama y los scripts.
