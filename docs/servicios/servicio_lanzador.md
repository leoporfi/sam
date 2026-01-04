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
   * Obtiene los parámetros de entrada (bot_input) específicos de cada robot o usa valores por defecto.
   * Solicita el despliegue a la API de A360, inyectando cabeceras de autenticación para el Callback (token estático + token dinámico del API Gateway).
   * Registra el deploymentId en la tabla Ejecuciones con estado DEPLOYED.
   * Implementa reintentos inteligentes según el tipo de error (ver sección de Errores 412).
2. **Conciliador (service/conciliador.py) \- El Auditor**:
   * Monitorea las ejecuciones que siguen activas en SAM.
   * Pregunta a A360: *"¿En qué estado está el deployment X?"*.
   * Si detecta discrepancias (ej. el robot murió sin avisar), actualiza la BD para cerrar la ejecución.
   * **Gestión de ejecuciones antiguas:** Marca como UNKNOWN ejecuciones que superan el umbral de días de tolerancia (configurable, por defecto 30 días).
3. **Sincronizador (service/sincronizador.py) \- El Actualizador**:
   * Mantiene los catálogos al día. Trae de A360 la lista completa de:
     * **Robots** (Taskbots).
     * **Equipos** (Bot Runners).
     * **Usuarios**.
   * Permite que SAM "vea" los nuevos robots creados en A360 sin intervención manual.

## **3\. Lógica Crítica: Manejo de Errores 412**

El error **412 Precondition Failed** tiene **DOS causas distintas** que el sistema maneja de forma diferente:

### **3.1. Error 412 - Problema del Robot**
**Mensaje de A360:** `"No compatible targets found in automation"`

**Significado:** El robot NO tiene configurados targets compatibles en A360. Es un problema de configuración del propio bot, **NO del dispositivo**.

**Comportamiento del Sistema:**
- ✋ **NO reintenta** (es un error permanente de configuración)
- 🚨 **Alerta INMEDIATA por email** con todos los detalles:
  - 🤖 **Robot:** Nombre (ID)
  - 💻 **Equipo:** Nombre (ID)
  - 👤 **Usuario:** Nombre (ID)
  - 📋 Mensaje de error completo de A360
  - ⚠️ Acción requerida: "Revisar configuración del robot '{RobotNombre}' en A360"
- 📝 El deployment NO se registra en la BD

**Acción de Soporte:**
1. Verificar en A360 Control Room la configuración de "Compatible Targets" del robot
2. Asegurarse de que el robot tenga al menos un target compatible configurado

---

### **3.2. Error 412 - Dispositivo Offline/Ocupado**
**Mensaje de A360:** Otros mensajes 412 (device offline, device busy, etc.)

**Significado:** El Bot Runner no está disponible temporalmente.

**Comportamiento del Sistema:**
- 🔄 **Reintenta automáticamente** (configurable: `LANZADOR_MAX_REINTENTOS_DEPLOY`, por defecto 2 intentos)
- ⏱️ Espera entre reintentos: `LANZADOR_DELAY_REINTENTOS_DEPLOY_SEG` (por defecto 5 segundos)
- 📊 **Tracking de fallos persistentes:**
  - El orquestador cuenta fallos consecutivos por equipo
  - Al superar el umbral (`LANZADOR_UMBRAL_ALERTAS_412`, por defecto 20), envía alerta
  - Título: `"[SAM] Dispositivo Offline Persistente"`
  - Se resetea automáticamente cuando el equipo vuelve a funcionar

**Acción de Soporte:**
1. Verificar que el Bot Runner esté conectado al Control Room
2. Revisar logs del dispositivo en A360
3. Confirmar que no haya tareas en ejecución bloqueando el equipo

---

### **3.3. Error 400 - Configuración Inválida**
**Significado:** Error permanente de configuración (permisos, licencias, bot inexistente)

**Comportamiento del Sistema:**
- ✋ **NO reintenta** (es permanente)
- 🚨 **Alerta por email** (una sola vez por equipo en el ciclo) con formato enriquecido:
  - Subject: `[SAM CRÍTICO] Error 400 - Robot 'X' en Equipo 'Y'`
  - Cuerpo con nombres legibles y acciones recomendadas.
- ❌ **Desactiva la asignación** automáticamente (elimina registro de `dbo.Asignaciones`)

**Acción de Soporte:**
Verificar en A360:
- Permisos del usuario sobre el robot
- Licencias disponibles
- Existencia del robot en el Control Room

## **4\. Lógica Crítica: El Estado UNKNOWN**

Cuando A360 no responde claramente sobre el estado de un robot, SAM lo marca como UNKNOWN.

* **UNKNOWN Transitorio (reciente):**
  * **Significado:** "Perdí contacto con A360 para este deployment".
  * **Acción del Sistema:** SAM registra el estado UNKNOWN y actualiza `FechaUltimoUNKNOWN`. El sistema incrementa el contador `IntentosConciliadorFallidos` y reintentará en el próximo ciclo de conciliación.
  * **Nota importante:** El estado UNKNOWN transitorio NO bloquea automáticamente el equipo para nuevos lanzamientos en la implementación actual.

* **UNKNOWN Final (antigüedad > umbral de días):**
  * **Significado:** "La ejecución lleva demasiado tiempo sin respuesta definitiva".
  * **Acción del Sistema:** Después de superar el umbral configurable (`LANZADOR_DIAS_TOLERANCIA_UNKNOWN`, por defecto 30 días), SAM marca definitivamente como UNKNOWN con `FechaFin`, cerrando la ejecución.

**Nota para Soporte:** El umbral de tolerancia para marcar UNKNOWN final es configurable (por defecto 30 días).

## **5\. Parámetros de Entrada a Robots (Bot Input)**

SAM permite configurar parámetros personalizados para cada robot que se envían al momento del despliegue en A360.

### **5.1. Configuración de Parámetros**

Los parámetros se almacenan en el campo **`Parametros`** de la tabla **`dbo.Robots`** en formato JSON.

**Estructura esperada:**
```json
{
  "nombre_variable": {
    "type": "TIPO_DATO",
    "valor_clave": "valor"
  }
}
```

**Ejemplo - Parámetro numérico:**
```json
{
  "in_NumRepeticion": {
    "type": "NUMBER",
    "number": "5"
  }
}
```

**Ejemplo - Parámetro string:**
```json
{
  "in_Ambiente": {
    "type": "STRING",
    "string": "PRODUCCION"
  }
}
```

**Ejemplo - Múltiples parámetros:**
```json
{
  "in_NumRepeticion": {
    "type": "NUMBER",
    "number": "3"
  },
  "in_TipoDocumento": {
    "type": "STRING",
    "string": "FACTURA"
  }
}
```

### **5.2. Lógica de Aplicación**

1. **Con Parámetros Personalizados:** Si el robot tiene el campo `Parametros` con JSON válido, SAM usa esos valores al desplegar.

2. **Sin Parámetros (Valor por Defecto):** Si el campo está vacío o el JSON es inválido, SAM usa el parámetro por defecto:
   ```json
   {
     "in_NumRepeticion": {
       "type": "NUMBER",
       "number": "1"
     }
   }
   ```
   El valor `"1"` proviene de la configuración `LANZADOR_REPETICIONES` (por defecto 1).

### **5.3. Configuración en Base de Datos**

**Para asignar parámetros personalizados a un robot:**

```sql
UPDATE dbo.Robots
SET Parametros = '{"in_NumRepeticion": {"type": "NUMBER", "number": "5"}}'
WHERE RobotId = 123;
```

**Para quitar parámetros personalizados (volver a usar por defecto):**

```sql
UPDATE dbo.Robots
SET Parametros = NULL
WHERE RobotId = 123;
```

### **5.4. Validación y Logs**

- Si el JSON en `Parametros` es inválido, el sistema lo registra en el log y usa el valor por defecto
- El log indica: `"Robot {RobotId} tiene parámetros personalizados"` o `"Robot {RobotId} usando parámetros por defecto"`

**Nota importante:** Los nombres de las variables (ej. `in_NumRepeticion`) deben coincidir EXACTAMENTE con los nombres de las variables de entrada definidas en el bot de A360.

## **6\. Ciclos de Ejecución (Loops)**

El servicio corre 3 bucles infinitos con intervalos configurables:

| Ciclo | Frecuencia Típica | Qué hace |
| :---- | :---- | :---- |
| **Launcher** | Cada 15 seg | Busca pendientes y dispara robots. |
| **Conciliador** | Cada 5-15 min | Revisa estados de robots corriendo. |
| **Sync** | Cada 1 hora | Actualiza nombres de robots y equipos nuevos. |

## **7\. Captura de Latencia y Análisis de Tiempos**

SAM implementa un mecanismo para medir la latencia real entre el momento en que se ordena la ejecución y el momento en que A360 efectivamente inicia el robot.

### **7.1. Captura de Datos**
*   **FechaInicio (SAM):** Momento en que el Desplegador envía la solicitud a la API.
*   **FechaInicioReal (A360):** Momento exacto (`startDateTime`) reportado por A360 cuando el robot comienza a ejecutarse en el dispositivo.
*   **FechaFin (A360):** Momento exacto (`endDateTime`) reportado por A360 al finalizar.

El servicio **Conciliador** se encarga de obtener estos datos de la API de A360 y actualizar la base de datos de SAM.

### **7.2. Análisis de Latencia (Stored Procedure)**
Se dispone de un procedimiento almacenado para consultar métricas de latencia a demanda:

```sql
EXEC dbo.usp_AnalizarLatenciaEjecuciones
    @Scope = 'TODAS',           -- 'ACTUALES', 'HISTORICAS', 'TODAS'
    @FechaDesde = '2025-01-01', -- Opcional
    @FechaHasta = NULL          -- Opcional (Default: GETDATE())
```

**Métricas Retornadas:**
*   **LatenciaInicioSegundos:** Diferencia entre `FechaInicio` (SAM) y `FechaInicioReal` (A360). Mide el overhead de la plataforma + red + disponibilidad del dispositivo.
*   **DuracionEjecucionSegundos:** Tiempo real de ejecución del robot (`FechaFin` - `FechaInicioReal`).
*   **DuracionTotalSegundos:** Tiempo total desde la orden de SAM hasta el fin (`FechaFin` - `FechaInicio`).

## **8\. Variables de Entorno Requeridas (.env)**

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

### **Autenticación Callback**

* CALLBACK\_TOKEN: Token estático (X-Authorization) para autenticación del callback.
* El sistema también obtiene dinámicamente un token del API Gateway para doble capa de seguridad.

### **Reglas de Negocio y Reintentos**

* LANZADOR\_MAX\_WORKERS: Cuántos deploys simultáneos puede hacer (ej. 10).
* LANZADOR\_PAUSA\_LANZAMIENTO: Tupla con ventana donde **NO** se lanzan robots (formato interno, ej. ("23:00", "06:00")).
* LANZADOR\_REPETICIONES: Valor por defecto para el parámetro `in_NumRepeticion` cuando un robot NO tiene parámetros personalizados (por defecto 1).
* LANZADOR\_MAX\_REINTENTOS\_DEPLOY: Intentos ante errores 412 temporales (por defecto 2).
* LANZADOR\_DELAY\_REINTENTOS\_DEPLOY\_SEG: Segundos de espera entre reintentos (por defecto 5).
* LANZADOR\_UMBRAL\_ALERTAS\_412: Fallos consecutivos 412 antes de alertar (por defecto 20).
* LANZADOR\_DIAS\_TOLERANCIA\_UNKNOWN: Días antes de marcar UNKNOWN definitivo (por defecto 30).

## **9\. Diagnóstico de Fallos (Troubleshooting)**

* **Log:** lanzador.log

### **Caso: "El robot no arranca"**

1. **Revisar el log del Desplegador:** Buscar trazas de errores en el ciclo de lanzamiento.

2. **Error 412 - Robot sin targets compatibles:**
   - Mensaje: `"No compatible targets found in automation"`
   - **Solución:** Configurar targets compatibles en A360 para ese robot
   - El sistema envía alerta inmediata con nombres legibles (Robot, Equipo, Usuario) y detalles completos

3. **Error 412 - Dispositivo Offline (con reintentos):**
   - El sistema reintenta automáticamente
   - Si persiste > 20 fallos consecutivos, recibirás alerta
   - **Solución:** Verificar que el Bot Runner esté conectado y disponible en A360

4. **Error 400 - Configuración inválida:**
   - Sistema desactiva la asignación automáticamente
   - **Solución:** Revisar permisos, licencias y existencia del robot en A360 (el email indica exactamente qué usuario y robot están afectados)

5. **Ventana de Pausa:**
   - Verificar si la hora actual está dentro de la ventana de pausa configurada
   - El log indicará: "Lanzador en PAUSA operativa configurada"

### **Caso: "El robot terminó pero sigue corriendo en SAM"**

1. **Revisar el log del Conciliador:** Reporta resultado de consultas a A360
2. **Conectividad A360:** Verificar excepciones de red o timeouts
3. **Estado UNKNOWN:** Si persiste > 30 días (configurable), se forzará cierre

### **Caso: "Muchas alertas de Error 412"**

1. **Alerta de "Dispositivo Offline Persistente":**
   - Se activa tras 20 fallos consecutivos (configurable)
   - Verificar conectividad del Bot Runner con Control Room
   - Revisar estado del dispositivo en A360
   - El contador se resetea automáticamente al recuperarse

2. **Alerta de "Robot sin Compatible Targets":**
   - Error permanente de configuración del robot
   - Revisar settings del bot en A360
   - Configurar al menos un target compatible
