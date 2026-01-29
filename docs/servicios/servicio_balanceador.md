# **Documentación Técnica: Servicio Balanceador (Inteligencia)**

**Módulo:** sam.balanceador

## **1\. Propósito**

El **Servicio Balanceador** es el estratega del ecosistema SAM. Mientras el Lanzador se ocupa de ejecutar tareas, el Balanceador se encarga de **optimizar los recursos** antes de que esas tareas se lancen.

Su función principal es monitorear la "Demanda" (cuánto trabajo pendiente tiene cada robot) y ajustar la "Oferta" (cuántos equipos tiene asignados ese robot en su Pool) en tiempo real.

**Analogía Funcional:** Mientras que el Servicio Lanzador actúa como el agente operativo encargado de la ejecución individual de tareas (similar a un conductor asignado a un servicio), el Servicio Balanceador opera como un centro de control logístico. Su función es determinar estratégicamente la asignación óptima de recursos(equipos) a cada sector, basándose en el análisis en tiempo real del volumen de demanda y la capacidad disponible.

## **2\. Arquitectura y Componentes**

El servicio opera en un bucle continuo de análisis y decisión.

### **Componentes Principales**

1. **Proveedores de Carga (service/proveedores.py) \- Los Ojos:**
   * Se conectan a fuentes externas para saber "cuánto trabajo hay".
   * **Clouders (API):** Consulta tickets pendientes en el orquestador externo.
   * **RPA360 (BD):** Consulta elementos en las "Work Queues" de Automation Anywhere.
   * **Extensibilidad:** Es posible agregar nuevos proveedores de carga (ej. ServiceNow, Jira) implementando la interfaz base ProveedorCarga definida en service/proveedores.py. Cualquier clase nueva que cumpla este contrato puede ser inyectada en el balanceador.
   * **Mapeo:** Utiliza la tabla de mapeos (gestionada en la Web) para traducir los nombres externos (ej. *"Robot\_Facturas\_V2"*) a los nombres internos de SAM.
2. **Algoritmo de Balanceo (service/algoritmo\_balanceo.py) \- El Cerebro:**
   * Recibe los datos de carga.
   * Compara la demanda con la capacidad actual de los equipos.
   * Decide si un robot necesita más equipos (Scaling Out) o si debe liberar recursos (Scaling In).
   * Respeta las reglas de **Prioridad** definidas en la Web.
3. **Cooling Manager (service/cooling\_manager.py) \- El Estabilizador:**
   * Evita cambios bruscos y repetitivos ("Flapping").
   * Si el balanceador modifica un Pool (ej. agrega un robot), ese Pool entra en estado de **Enfriamiento (Cooling)** por un tiempo configurable. Durante este periodo, **no se aceptan nuevos cambios** para dar tiempo a que el sistema se estabilice.

## **3\. Conceptos Clave para Soporte**

### **A. ¿Por qué el Balanceador no asigna equipos inmediatamente? (Cooling)**

Si un usuario reporta que *"hay mucha carga pero el balanceador no asigna máquinas"*, lo primero a verificar es el **Cooling**.

* Si el pool fue modificado hace menos de BALANCEADOR\_PERIODO\_ENFRIAMIENTO\_SEG (ej. 300 segundos), el sistema estará en pausa intencional.
* **Acción:** Esperar unos minutos o verificar el log buscando el mensaje *"Pool en enfriamiento"*.

### **B. La Importancia de los Mapeos**

Si el Balanceador no "ve" la carga de un robot, suele ser un problema de nombres.

* Los sistemas externos (Clouders, AA) pueden llamar al proceso de una forma (ej. "Proc\_Pagos"), pero en SAM se llama diferente.
* **Acción:** Ir a la **Web \> Mapeos** y asegurar que el nombre externo esté vinculado correctamente al robot interno.

### **C. Prioridad Estricta (Preemption)**

El mecanismo de **Preemption** asegura que los procesos críticos (Prioridad Alta) siempre tengan recursos disponibles, incluso si eso significa quitarle recursos a procesos menos importantes que están ejecutándose.

* **Lógica de Prioridad:** En SAM, un número **menor** significa mayor prioridad (1 es la más alta, 10 la más baja).
* **Escenario de Conflicto:** Supongamos que no hay equipos libres en un Pool.
  * El Robot_A (Prioridad 1) tiene tickets pendientes.
  * El Robot_B (Prioridad 5) tiene asignados 3 equipos.
* **Acción del Balanceador:** Si `BALANCEO_PREEMPTION_MODE` está activo (true), el sistema detectará que Robot_A tiene mayor prioridad y necesidad. Procederá a **desasignar** uno o más equipos del Robot_B (aunque tenga trabajo pendiente) para asignárselos inmediatamente al Robot_A.
* **Síntoma en Soporte:** Es común que los dueños de robots de baja prioridad reporten que *"su capacidad fluctúa"* o que *"pierden máquinas"*. Esto es el comportamiento esperado del sistema para garantizar SLAs críticos.

### **D. Aislamiento de Pool Estricto**

Esta configuración define si los equipos de un Pool son exclusivos o compartidos. **Importante:** Este valor se lee de la base de datos (tabla ConfiguracionSistema), lo que permite cambiar la estrategia sin reiniciar el servicio.

* **Modo Estricto (true):** "Lo mío es mío". Los equipos de un Pool solo atienden a los robots explícitamente asignados a ese Pool. Si el Pool de "Finanzas" está vacío, sus máquinas se quedan ociosas aunque "RRHH" tenga cola de espera.
* **Modo Flexible (false):** "Solidaridad de equipos" (Overflow). Si un Pool tiene máquinas ociosas (sin tickets pendientes en sus robots asignados), el Balanceador puede tomarlas prestadas temporalmente para asignarlas a robots de otro Pool con alta demanda.
* **Nota:** Esto es diferente a la Preemption. El aislamiento flexible usa recursos *libres* de otros pools. La Preemption quita recursos *ocupados* a robots de menor prioridad.

## **4\. Ciclo de Ejecución**

El servicio ejecuta el siguiente flujo cada BALANCEADOR\_INTERVALO\_CICLO\_SEG (ej. 60 seg):

1. **Recolectar:** Consulta API Clouders \+ BD RPA360.
2. **Analizar:** Calcula demanda vs. capacidad.
3. **Filtrar:** Descarta Pools que estén en "Cooling".
4. **Ejecutar:** Aplica cambios en la base de datos (tabla Pool\_Robot).
5. **Enfriar:** Marca los Pools afectados para que "descansen".

## **5\. Configuración Dinámica (Tabla ConfiguracionSistema)**

A diferencia de las variables de entorno (.env) que requieren reinicio, SAM dispone de una tabla ConfiguracionSistema para ajustes en caliente. El servicio consulta estos valores en cada ciclo.

**Claves Críticas:**

| Clave (Key) | Valores Posibles | Descripción |
| :---- | :---- | :---- |
| BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO | true / false | Define si se permite el préstamo de equipos entre pools (Overflow). |
| BALANCEO_PREEMPTION_MODE | true / false | Define si se permite quitar equipos a robots de baja prioridad (Preemption). |
| BALANCEADOR_LOG_LEVEL | DEBUG, INFO | Permite aumentar la verbosidad del log temporalmente para diagnóstico sin reiniciar. |
| GLOBAL_MAINTENANCE_MODE | true / false | (Si aplica) Interruptor general para detener asignaciones en todo el sistema. |

**Nota:** Para modificar estos valores, se debe realizar un UPDATE directo en la base de datos o utilizar la sección de "Configuración Avanzada" en la Web (si está habilitada para el usuario).

## **6\. Variables de Entorno Requeridas (.env)**

Cualquier cambio requiere reiniciar el servicio SAM\_Balanceador.

### **Reglas de Negocio**

* BALANCEADOR\_INTERVALO\_CICLO\_SEG: Cada cuánto se ejecuta el análisis (ej. 120).
* BALANCEADOR\_PERIODO\_ENFRIAMIENTO\_SEG: Tiempo de bloqueo tras un cambio (ej. 300 \= 5 min).
* BALANCEADOR\_PROVEEDORES\_CARGA: Lista de fuentes activas (ej. clouders,rpa360).

### **Conectividad Externa**

* CLOUDERS\_API\_URL: Endpoint de la API de tickets.
* CLOUDERS\_AUTH: Token o credencial básica.
* SQL\_RPA360\_\*: Credenciales de lectura para la BD de Automation Anywhere (para ver colas).

## **7\. Diagnóstico de Fallos (Troubleshooting)**

* **Log:** balanceador.log
* **Caso: "El robot tiene 1000 tickets pero 0 máquinas"**
  1. **Log:** Buscar "Carga detectada para$$Robot$$
     ". Si no aparece, falla el **Proveedor** o el **Mapeo**.
  2. **Mapeo:** Verificar en la Web que el nombre coincida exactamente con el de Clouders/A360.
  3. **Configuración:** Verificar si el robot está activo y tiene un límite de equipos \> 0\.
* **Caso: "El sistema mueve los robots constantemente"**
  1. **Cooling:** Es posible que BALANCEADOR\_PERIODO\_ENFRIAMIENTO\_SEG sea muy bajo (ej. 10 seg). Aumentarlo para dar estabilidad.
* **Caso: "Error de conexión con Clouders"**
  1. **Log:** Buscar errores HTTP 401/403 (Credenciales) o 500 (Caída de Clouders).
  2. **Acción:** Si Clouders cae, el balanceador dejará de ver carga, pero los robots ya asignados seguirán trabajando.
