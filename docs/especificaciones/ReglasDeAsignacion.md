# Reglas de Negocio: Asignación y Desasignación de Recursos

Este documento consolida las reglas de negocio para la gestión de recursos (Robots y Equipos) en el sistema SAM.

## 1. Definiciones de Estado

El estado de un Equipo se determina por su relación con Robots y Pools.

*   **Disponible (Libre)**: Equipo activo que no tiene ninguna asignación.
    *   *Visualización*: Etiqueta <span style="color:white; background-color:#10b981; padding:2px 6px; border-radius:4px;">Disponible</span> (Verde).
*   **Programado**: Equipo asignado a un Robot mediante una configuración de horario (Programación).
    *   *Regla*: Puede ser compartido entre múltiples robots si los horarios no se superponen.
    *   *Visualización*: Etiqueta <span style="color:white; background-color:#0ea5e9; padding:2px 6px; border-radius:4px;">Programado</span> (Azul).
*   **Reservado**: Equipo asignado manualmente de forma exclusiva a un Robot.
    *   *Regla*: No puede ser tomado por el balanceador ni por otros robots, a menos que se libere explícitamente.
    *   *Visualización*: Etiqueta <span style="color:white; background-color:#f59e0b; padding:2px 6px; border-radius:4px;">Reservado</span> (Naranja).
*   **Dinámico**: Equipo asignado temporalmente por el Balanceador de Carga.
    *   *Regla*: Puede ser reasignado manual o programáticamente (Override).
    *   *Visualización*: Etiqueta <span style="color:white; background-color:#8b5cf6; padding:2px 6px; border-radius:4px;">Dinámico</span> (Violeta).
*   **En Pool**: Estado específico dentro de la gestión de Pools. Indica pertenencia al grupo lógico.
    *   *Regla*: Un equipo puede estar "En Pool" y a la vez tener cualquiera de los estados anteriores (Programado, etc.).
    *   *Visualización*: Etiqueta <span style="color:white; background-color:#651fff; padding:2px 6px; border-radius:4px;">En Pool</span> (Violeta Oscuro) dentro del modal de Pool.

---

## 2. Reglas de Asignación por Modalidad

### A. Gestión de Pools (Modal de Pools)

El Pool es una agrupación lógica. Asignar un recurso a un Pool **NO destruye** sus otras relaciones.

*   **Acción: Asignar al Pool (Flecha Derecha)**
    *   *Lógica*: Establece el `PoolId` del recurso (Robot o Equipo).
    *   *Impacto*: El recurso pasa a formar parte del Pool.
    *   *Restricción*: Ninguna.
*   **Acción: Quitar del Pool (Flecha Izquierda)**
    *   *Lógica*: Establece el `PoolId` en `NULL`.
    *   *Impacto*: El recurso deja de pertenecer al Pool.
    *   *Seguridad*: No afecta las asignaciones de robots/tareas que el equipo ya tenga.

### B. Gestión de Programaciones (Modal de Programación)

Asigna equipos para ejecutar tareas en un horario específico.

*   **Acción: Asignar Equipo a Programación**
    *   *Lógica*: Crea un vínculo en `ProgramacionDispositivos`.
    *   *Restricción Coherencia*: Un equipo solo debería trabajar en una tarea a la vez, pero SAM permite multi-asignación programada (solapamientos son riesgo del usuario).
*   **Información al Usuario**:
    > "ℹ️ Info: Los equipos asignados aquí se vincularán exclusivamente a esta programación cuando esté activa."

### C. Gestión Manual de Robots (Modal de Robot)

Permite asignar equipos directamente a un robot, actuando como un **Override** sobre el balanceador.

*   **Acción: Asignar Equipo a Robot**
    *   *Lógica*: Inserta registro en tabla `Asignaciones` con `EsProgramado=0` y `Reservado=0` (comportamiento estándar) o `Reservado=1` (si es reserva explícita).
    *   *Impacto*: El equipo comienza a trabajar para ese robot inmediatamente.
    *   *Sobre-escritura*: Si el equipo estaba siendo usado dinámicamente por otro robot, esta acción manual toma precedencia.
*   **Información al Usuario**:
    > "ℹ️ Info: Los equipos seleccionados aquí trabajarán para esta programación específica, ignorando asignaciones dinámicas."
