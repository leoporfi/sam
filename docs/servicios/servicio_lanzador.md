# **Documentación Técnica: Servicio Lanzador (Core)**

**Módulo:** sam.lanzador

## **1\. Propósito**

El **Servicio Lanzador** es el motor principal ("Core") de SAM. Su función es orquestar el ciclo de vida de las ejecuciones, actuando como puente entre la base de datos de SAM (donde se decide qué hacer) y Automation 360 (donde se ejecuta).

Opera como un **demonio (servicio de fondo)** que nunca se detiene, ejecutando tres tareas críticas en paralelo.

## **2\. Arquitectura y Componentes**

El servicio está construido sobre asyncio para manejar múltiples tareas concurrentes sin bloquearse.

### **Componentes Principales**

1. **Desplegador (service/desplegador.py) \- El Brazo Ejecutor**:  
   * Consulta la BD (dbo.ObtenerRobotsEjecutables) buscando tareas pendientes.  
   * Verifica si estamos en **Pausa Operacional** (ventana de mantenimiento configurada).  
   * Solicita el despliegue a la API de A360, inyectando la URL del Callback para recibir avisos.  
   * Registra el deploymentId en la tabla Ejecuciones con estado DEPLOYED.  
2. **Conciliador (service/conciliador.py) \- El Auditor**:  
   * Monitorea las ejecuciones que siguen activas en SAM.  
   * Pregunta a A360: *"¿En qué estado está el deployment X?"*.  
   * Si detecta discrepancias (ej. el robot murió sin avisar), actualiza la BD para cerrar la ejecución.  
   * **Manejo de "Zombies":** Limpia ejecuciones extremadamente antiguas que quedaron huérfanas.  
3. **Sincronizador (service/sincronizador.py) \- El Actualizador**:  
   * Mantiene los catálogos al día. Trae de A360 la lista completa de:  
     * **Robots** (Taskbots).  
     * **Equipos** (Bot Runners).  
     * **Usuarios**.  
   * Permite que SAM "vea" los nuevos robots creados en A360 sin intervención manual.

## **3\. Lógica Crítica: El Estado UNKNOWN**

Este es el punto más importante para **Soporte**. Cuando A360 no responde claramente sobre el estado de un robot, SAM lo marca como UNKNOWN.

* **UNKNOWN Transitorio (\< 2 horas):**  
  * **Significado:** "Perdí contacto, pero puede que siga corriendo".  
  * **Acción del Sistema:** SAM **NO** lanza nuevos robots en ese equipo para evitar colisiones. El equipo se considera "Ocupado".  
* **UNKNOWN Final (\> 2 horas):**  
  * **Significado:** "Definitivamente se perdió la conexión hace mucho".  
  * **Acción del Sistema:** La base de datos libera el equipo. SAM puede volver a usarlo para nuevas tareas.

**Nota para Soporte:** Si un equipo no toma tareas, verificar si tiene una ejecución UNKNOWN reciente bloqueándolo.

## **4\. Ciclos de Ejecución (Loops)**

El servicio corre 3 bucles infinitos con intervalos configurables:

| Ciclo | Frecuencia Típica | Qué hace |
| :---- | :---- | :---- |
| **Launcher** | Cada 15 seg | Busca pendientes y dispara robots. |
| **Conciliador** | Cada 5-15 min | Revisa estados de robots corriendo. |
| **Sync** | Cada 1 hora | Actualiza nombres de robots y equipos nuevos. |

## **5\. Variables de Entorno Requeridas (.env)**

Cualquier cambio requiere reiniciar el servicio SAM\_Lanzador.

### **Intervalos de Tiempo**

* LANZADOR\_INTERVALO\_LANZAMIENTO\_SEG: Frecuencia de búsqueda de tareas (ej. 15).  
* LANZADOR\_INTERVALO\_CONCILIACION\_SEG: Frecuencia de auditoría (ej. 300).  
* LANZADOR\_INTERVALO\_SINCRONIZACION\_SEG: Frecuencia de actualización de maestros (ej. 3600).

### **Conexión A360**

* AA\_CR\_URL: URL del Control Room.  
* AA\_CR\_USER: Usuario de servicio (Bot Runner/Creator).  
* AA\_CR\_API\_KEY: API Key del usuario.  
* AA\_URL\_CALLBACK: La URL pública donde sam.callback escucha (inyectada en cada robot).

### **Reglas de Negocio**

* LANZADOR\_MAX\_WORKERS: Cuántos deploys simultáneos puede hacer (ej. 10).  
* LANZADOR\_PAUSA\_INICIO\_HHMM / LANZADOR\_PAUSA\_FIN\_HHMM: Ventana donde **NO** se lanzan robots (ej. 23:00 a 06:00).

## **6\. Diagnóstico de Fallos (Troubleshooting)**

* **Log:** lanzador.log  
* **Caso: "El robot no arranca"**  
  1. **Revisar el log del Desplegador:** Buscar trazas de errores en el ciclo de lanzamiento.  
  2. **Error de Dispositivo:** Si la API de A360 devuelve errores indicando que el equipo no está disponible (ej. *"Device is offline"*, *"Device not connected"* o códigos de error similares), verificar que el Bot Runner esté logueado y conectado al Control Room.  
  3. **Ventana de Pausa:** Verificar si la hora actual del servidor está dentro del rango definido por LANZADOR\_PAUSA\_INICIO\_HHMM y LANZADOR\_PAUSA\_FIN\_HHMM. Si es así, el log indicará que se omitió el lanzamiento por estar dentro de este horario restringido.  
* **Caso: "El robot terminó pero sigue corriendo en SAM"**  
  1. **Revisar el log del Conciliador:** Este componente reporta el resultado de la consulta de estados a A360.  
  2. **Conectividad A360:** Verificar si existen excepciones de red o *timeouts* al conectar con la API del Control Room.  
  3. **Estado UNKNOWN:** Confirmar si el robot ha entrado en estado UNKNOWN. Si persiste por más de 2 horas (valor configurable), el sistema lo forzará a finalizar para liberar recursos.