# **Documentación del Modelo de Datos y Reglas de Negocio \- SAM**

## **1\. Visión General del Modelo**

El modelo de datos de SAM está diseñado para soportar una orquestación híbrida de RPA (Robotic Process Automation). Combina elementos estáticos (Inventario, Programaciones) con elementos dinámicos y transaccionales (Ejecuciones, Balanceo de Carga).

El núcleo del modelo gira en torno a tres entidades principales: **Robots** (la tarea), **Equipos** (el recurso) y **Pools** (la agrupación lógica).

## **2\. Diagrama Relacional (Conceptual)**

Las relaciones principales se definen de la siguiente manera:

* Un **Pool** agrupa múltiples **Robots** y múltiples **Equipos**.
* Un **Robot** puede tener múltiples **Programaciones** (Diaria, Semanal, etc.).
* La tabla **Asignaciones** rompe la relación M:N entre Robots y Equipos, definiendo quién ejecuta qué.
* La tabla **Ejecuciones** registra el historial transaccional de cada lanzamiento.

## **3\. Diccionario de Datos Clave**

A continuación, se describen las tablas críticas y sus campos con lógica de negocio asociada.

### **3.1. Entidades Principales**

#### **dbo.Robots**

Define los procesos automatizados (Taskbots de A360).

* **PrioridadBalanceo (int):** Define la importancia del robot. **Menor valor \= Mayor prioridad** (1 es más importante que 10). Usado por el servicio *Balanceador* para preemption.
* **MinEquipos / MaxEquipos:** Límites duros para el escalado dinámico.
* **EsOnline (bit):** Si es 1, el robot está disponible para ejecución bajo demanda (Tickets). Si es 0, suele ser un robot agendado (Cron).
* **TicketsPorEquipoAdicional:** Umbral para el escalado (ej. cada 10 tickets pendientes, asignar 1 equipo más).

#### **dbo.Equipos**

Define los Bot Runners (Máquinas).

* **Activo\_SAM (bit):** Interruptor maestro. Si es 0, SAM ignora este equipo para cualquier operación (Mantenimiento).
* **PermiteBalanceoDinamico (bit):** Interruptor para el algoritmo. Regla Estricta: El equipo debe tener este valor en 1 para que el servicio Balanceador pueda asignarle tareas dinámicamente (Carga). Si está en 0, el equipo puede pertenecer al Pool pero funciona en modo "Manual/Estático" (solo acepta Programaciones o Reservas manuales).
* **Licencia:** Debe ser ATTENDEDRUNTIME o RUNTIME para ser elegible.

#### **dbo.Pools**

Agrupación lógica para aislar recursos.

* **Aislamiento:** Los equipos de un Pool idealmente solo atienden robots de ese Pool (configurable vía ConfiguracionSistema).

### **3.2. Operativas y Transaccionales**

#### **dbo.Asignaciones**

Tabla pivote que determina la "Oferta" actual.

* **EsProgramado (bit):**
  * 1: Asignación fija por calendario. El Balanceador **NO** puede tocarla.
  * 0: Asignación dinámica. El Balanceador puede crearla o borrarla según la demanda.
* **Reservado (bit):** Asignación manual forzosa. Inmune al balanceo automático.

#### **dbo.Programaciones**

Define cuándo debe correr un robot.

* **TipoProgramacion:** Enum ('Diaria', 'Semanal', 'Mensual', 'Especifica').
* **Tolerancia (int):** Ventana de tiempo (minutos) después de la HoraInicio en la que aún es válido lanzar el robot.

#### **dbo.Ejecuciones**

Historial de despliegues.

* **Estado:** Controla el ciclo de vida (PENDING\_EXECUTION \-\> DEPLOYED \-\> RUNNING \-\> COMPLETED/FAILED).
* **IntentosConciliadorFallidos:** Contador para detectar Zombies.

## **4\. Reglas de Negocio (Explícitas e Implicitas)**

Estas reglas se derivan del análisis de los Stored Procedures (SAM.sql) y la lógica de los servicios (\*.md).

### **4.1. Reglas de Base de Datos (Integridad y Lógica SP)**

1. **Prioridad de Asignación (SP ListarEquipos):**
   * Un equipo puede tener múltiples entradas en Asignaciones, pero visualmente y operativamente se prioriza:
     1. EsProgramado \= 1 (Máxima prioridad).
     2. Reservado \= 1 (Prioridad manual).
     3. Dinámico (Balanceo automático).
2. **Unicidad de Pool (SP AsignarRecursosAPool):**
   * Un Robot o un Equipo solo puede pertenecer a un Pool a la vez. Al asignar a un nuevo Pool, se desvincula automáticamente del anterior.
3. **Restricción de Programación (SP CrearProgramacion):**
   * No se pueden crear programaciones (agenda) para robots marcados como EsOnline \= 1\. Los robots Online son exclusivamente para consumo bajo demanda (colas/tickets).
4. **Bloqueo de Balanceo al Programar:**
   * Al crear una programación (Diaria, Semanal, etc.), los equipos involucrados se marcan automáticamente con PermiteBalanceoDinamico \= 0\. Esto evita que el Balanceador les quite la tarea agendada para poner una de tickets.
5. **Validación de Ejecución Duplicada (SP ObtenerRobotsEjecutables):**
   * Un robot programado no se lanzará si ya existe una ejecución exitosa para ese mismo RobotId, EquipoId y Hora en el día actual (evita ejecuciones dobles si el ciclo del Lanzador es rápido).

### **4.2. Reglas del Servicio Lanzador (Core)**

1. **Lógica del Estado UNKNOWN:**
   * **Transitorio (\< 2 horas):** Si A360 reporta "Unknown" o pierde conexión, SAM asume que el robot *podría* estar corriendo. El equipo se considera **Ocupado** y no se le asignan nuevas tareas.
   * **Definitivo (\> 2 horas):** Se asume que la ejecución murió. El sistema libera el equipo para nuevas tareas (Limpieza de Zombies).
2. **Ventana de Mantenimiento (Pausa Operacional):**
   * Existe un rango horario (LANZADOR\_PAUSA\_INICIO a LANZADOR\_PAUSA\_FIN) donde el Lanzador **NO** disparará nuevas tareas, aunque estén programadas o haya tickets pendientes.
3. **Criterio de Elegibilidad de Equipo:**
   * Un equipo es elegible para lanzar un robot si:
     * Está activo en SAM (Activo\_SAM \= 1).
     * Tiene licencia de ejecución (Runtime).
     * No tiene ninguna ejecución activa en curso (DEPLOYED, RUNNING, etc.).

### **4.3. Reglas del Servicio Balanceador (Inteligencia)**

1. **Regla de Preemption (Robo de Recursos):**
   * Si el Pool está lleno, un robot de **Alta Prioridad** (ej. valor 1\) forzará la desasignación de equipos de un robot de **Baja Prioridad** (ej. valor 10), incluso si este último tiene trabajo pendiente.
2. **Regla de Cooling (Enfriamiento):**
   * Tras modificar la asignación de un Pool (agregar/quitar equipos), ese Pool entra en estado de "Cooling" (ej. 5 minutos). Durante este tiempo, se ignoran cambios en la demanda para evitar oscilaciones (flapping).
3. **Escalado por Demanda:**
   * Se añaden equipos si: (Tickets Pendientes / TicketsPorEquipoAdicional) \> Equipos Actuales.
   * Nunca se excederá MaxEquipos.
   * Nunca se reducirá por debajo de MinEquipos si hay al menos 1 ticket.
4. **Aislamiento de Pools:**
   * **Estricto:** Los equipos de un Pool solo atienden robots de ese Pool.
   * **Flexible:** Si un Pool tiene capacidad ociosa (sin tickets), sus equipos pueden ser "prestados" temporalmente a otro Pool con alta demanda (controlado por BALANCEADOR\_POOL\_AISLAMIENTO\_ESTRICTO).

### **4.4. Reglas del Servicio Callback y Conciliador**

1. **Finalización Inmediata vs. Auditada:**
   * Si llega un **Callback** (desde A360): La ejecución se cierra inmediatamente, liberando el equipo en milisegundos.
   * Si falla el Callback: El **Conciliador** (ciclo de 5-15 min) detectará eventualmente que el robot terminó en A360 y actualizará la BD.
2. **Seguridad de Callbacks:**
   * Si CALLBACK\_AUTH\_MODE es 'required', se rechazarán notificaciones que no traigan tanto el Token Estático (SAM) como el JWT (Gateway).

### **4.5. Reglas del Servicio Web (Gestión)**

1. **Inmutabilidad Externa:**
   * La interfaz Web es la única fuente de verdad para la configuración de prioridades y límites. Los cambios hechos directamente en A360 (ej. cambiar nombre de robot) no impactan la lógica de negocio de SAM a menos que se actualicen los **Mapeos** en la Web.
2. **Mapeo de Nombres:**
   * Permite desacoplar el nombre interno del robot en SAM del nombre técnico en A360 o Clouders, facilitando el mantenimiento si los nombres externos cambian.

## **5\. Resumen de Estados de Ejecución**

El ciclo de vida de una ejecución en dbo.Ejecuciones sigue este flujo:

| Estado | Descripción | Regla de Negocio |
| :---- | :---- | :---- |
| **PENDING\_EXECUTION** | Tarea identificada, en cola interna de SAM. | Equipo reservado lógicamente. |
| **DEPLOYED** | Orden enviada a la API de A360. | Esperando confirmación de inicio. |
| **RUNNING** | Confirmado por A360 que está corriendo. | Equipo bloqueado físicamente. |
| **RUN\_PAUSED** | Robot pausado humanamente en A360. | Equipo sigue bloqueado. |
| **COMPLETED / RUN\_COMPLETED** | Finalización exitosa. | Equipo liberado. |
| **RUN\_FAILED / RUN\_ABORTED** | Finalización con error o parada manual. | Equipo liberado. |
| **UNKNOWN** | Pérdida de trazabilidad con A360. | Equipo bloqueado por 2 horas (Security hold). |
