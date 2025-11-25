# **Documento Funcional: Servicio Lanzador**

## **1. Descripción General**

El Servicio Lanzador es uno de los cuatro microservicios que componen el ecosistema SAM (Sistema Automático de Robots). Su función principal es gestionar el ciclo de vida de las ejecuciones de robots en la plataforma Automation 360, desde el despliegue hasta la conciliación de estados finales.

El servicio opera de forma autónoma mediante tres ciclos asíncronos independientes que se ejecutan en intervalos configurables.

## **2. Arquitectura del Servicio**

### **2.1 Componentes Principales**

El servicio se estructura siguiendo el patrón de Inyección de Dependencias y separación de responsabilidades entre orquestadores y lógica de negocio:

```
run_lanzador.py (Punto de Entrada)
    ├── LanzadorService (Orquestador)
    │   ├── Sincronizador (Lógica de Sincronización)
    │   ├── Desplegador (Lógica de Despliegue)
    │   └── Conciliador (Lógica de Conciliación)
    └── Dependencias Compartidas
        ├── DatabaseConnector
        ├── AutomationAnywhereClient
        ├── ApiGatewayClient
        └── EmailAlertClient
```

### **2.2 Responsabilidades**

* **run_lanzador.py**: Inicialización del servicio, creación de dependencias, gestión de señales del sistema operativo y limpieza de recursos.
* **LanzadorService**: Coordinación de los tres ciclos de tareas, gestión del ciclo de vida y tracking de errores persistentes.
* **Sincronizador**: Sincronización de entidades maestras (Robots y Equipos) entre A360 y la base de datos SAM.
* **Desplegador**: Lanzamiento de robots según programaciones y asignaciones configuradas.
* **Conciliador**: Actualización de estados de ejecuciones consultando la API de A360.

## **3. Componentes de Lógica de Negocio**

### **3.1 Sincronizador**

#### **3.1.1 Propósito**

Mantener la coherencia entre las entidades maestras de Automation 360 (Robots y Equipos) y las tablas correspondientes en la base de datos SAM.

#### **3.1.2 Funcionamiento**

El componente delega toda su lógica al módulo `SincronizadorComun` ubicado en `sam.common`, que:

1. Consulta la API de A360 para obtener la lista actualizada de robots y dispositivos (equipos).
2. Transforma los datos de la API al formato esperado por SAM.
3. Ejecuta operaciones MERGE en la base de datos utilizando stored procedures (`MergeRobots`, `MergeEquipos`).

#### **3.1.3 Particularidades**

* **Preservación de Configuración**: Al sincronizar equipos, el proceso conserva los campos de configuración propios de SAM (`PoolId`, `PermiteBalanceoDinamico`, `EstadoBalanceador`) incluso cuando el `EquipoId` cambia en A360.
* **Gestión de Conflictos**: Si un equipo con el mismo nombre (`Hostname`) reporta un `EquipoId` diferente, se actualiza la configuración del equipo nuevo con los valores del antiguo antes de eliminar el registro obsoleto.

#### **3.1.4 Intervalo de Ejecución**

Configurable mediante `LANZADOR_INTERVALO_SINCRONIZACION_SEG` (valor por defecto: 3600 segundos / 1 hora).

---

### **3.2 Desplegador**

#### **3.2.1 Propósito**

Ejecutar robots en los equipos asignados según las reglas de programación y asignación definidas en la base de datos.

#### **3.2.2 Funcionamiento**

El ciclo de despliegue consta de las siguientes fases:

1. **Validación de Ventana de Pausa**: Verifica si la hora actual se encuentra dentro de la ventana de pausa operacional configurada. Si es así, el ciclo se omite.

2. **Obtención de Robots Ejecutables**: Invoca el stored procedure `ObtenerRobotsEjecutables`, que aplica la siguiente lógica:
   * Robots programados dentro de su ventana de tolerancia.
   * Robots online sin ejecuciones activas en el equipo.
   * Exclusión de equipos ya ocupados.
   * Exclusión de ejecuciones ya registradas para la misma fecha y hora.

3. **Preparación de Cabeceras de Callback**: Obtiene el token dinámico del API Gateway y combina con la API Key estática del servicio de callbacks.

4. **Despliegue Paralelo**: Ejecuta los despliegues en paralelo con un límite de concurrencia definido por `MAX_WORKERS_LANZADOR`.
El despliegue paralelo no es una cola continua, sino que procesa robots en lotes del tamaño de MAX_WORKERS. El servicio espera a que todo el lote (ej. 10 robots) termine sus intentos de despliegue antes de procesar el siguiente grupo.

5. **Registro en Base de Datos**: Inserta un registro en la tabla `Ejecuciones` con estado inicial `DEPLOYED` y el `DeploymentId` devuelto por A360.

#### **3.2.3 Gestión de Errores**

El componente implementa reintentos automáticos con lógica diferenciada según el tipo de error:

| Código HTTP | Tipo | Estrategia |
|-------------|------|------------|
| 412 | Temporal (Device Offline) | Reintentos con delay configurable |
| 400 | Permanente (Bad Request) | No reintenta. Elimina asignación. Envía alerta. |
| 5xx / Timeout | Temporal (Fallo de Red) | Reintentos con delay |
| Otros | Variable | No reintenta. Registra error. |

**Alertas por Error 400**:
* Se envía una alerta de correo la primera vez que un equipo presenta error 400.
* La asignación problemática se **elimina** de la tabla `Asignaciones` (mediante `DELETE`).
* El equipo queda marcado en memoria para evitar alertas duplicadas.

**Nota importante**: La tabla `Asignaciones` no contiene una columna `Activo`, por lo que las asignaciones problemáticas se eliminan completamente en lugar de desactivarse.

#### **3.2.4 Parámetros Configurables**

* `LANZADOR_INTERVALO_LANZAMIENTO_SEG`: Frecuencia del ciclo (default: 15 segundos).
* `LANZADOR_MAX_WORKERS`: Concurrencia máxima (default: 10).
* `LANZADOR_MAX_REINTENTOS_DEPLOY`: Intentos por robot (default: 2).
* `LANZADOR_DELAY_REINTENTO_DEPLOY_SEG`: Espera entre reintentos (default: 5 segundos).
* `LANZADOR_PAUSA_INICIO_HHMM` / `LANZADOR_PAUSA_FIN_HHMM`: Ventana horaria de pausa (formato HH:MM, defaults: 22:00 / 06:00).
* `LANZADOR_BOT_INPUT_VUELTAS`: Número de repeticiones que se pasa como input al bot (default: 3).

---

### **3.3 Conciliador**

#### **3.3.1 Propósito**

Sincronizar el estado de las ejecuciones entre SAM y Automation 360, actualizando la base de datos con los estados finales reportados por la API.

#### **3.3.2 Funcionamiento**

El ciclo de conciliación ejecuta las siguientes operaciones:

1. **Obtención de Ejecuciones Activas**: Consulta la tabla `Ejecuciones` para obtener registros en estados no finales y sin información de callback.

2. **Consulta Masiva a A360**: Agrupa los `DeploymentId` en lotes (tamaño configurable) y consulta su estado mediante el endpoint bulk de la API.

3. **Actualización de Estados**:
   * **Estados Finales**: `COMPLETED`, `RUN_COMPLETED`, `RUN_FAILED`, `DEPLOY_FAILED`, `RUN_ABORTED`, `RUN_TIMED_OUT`. Se actualiza el estado y se registra `FechaFin`.
   * **Estado UNKNOWN**: Se marca como transitorio **sin** `FechaFin`. Se registra `FechaUltimoUNKNOWN` para control de antigüedad. Se incrementa el contador de intentos.
   * **Deployments No Encontrados**: Si A360 no devuelve información sobre un DeploymentId (posible latencia de indexación en A360), el servicio simplemente incrementa el contador IntentosConciliadorFallidos. No existe un límite de reintentos para este caso específico; el registro permanecerá activo hasta que aparezca en la API o sea limpiado por antigüedad.

4. **Gestión de Ejecuciones Antiguas**: Marca como `UNKNOWN` (final) las ejecuciones que superan el umbral de días de tolerancia sin respuesta de A360.

#### **3.3.3 Lógica de Estados UNKNOWN**

**CAMBIO IMPORTANTE**: El estado `UNKNOWN` ahora se trata de forma diferente:

* **UNKNOWN Transitorio**: Ejecuciones que reportan `UNKNOWN` desde A360 se consideran activas si no han superado el umbral de antigüedad. Se registra `FechaUltimoUNKNOWN` para tracking. **No se establece `FechaFin`**, permitiendo que el Conciliador las reintente en ciclos posteriores.

* **UNKNOWN Final**: Solo cuando una ejecución supera el umbral de `CONCILIADOR_DIAS_TOLERANCIA_UNKNOWN` días sin actualización, se marca como `UNKNOWN` final estableciendo `FechaFin = GETDATE()`.

Esta lógica permite que ejecuciones con estado temporal `UNKNOWN` (por ejemplo, por latencia de la API) puedan actualizarse correctamente una vez que A360 reporte su estado real.

#### **3.3.4 Conversión de Fechas**

Las fechas devueltas por A360 en formato UTC (ISO 8601) se convierten a la zona horaria `America/Argentina/Buenos_Aires` antes de almacenarse en `FechaFin`.

**Nota**: La zona horaria está actualmente hardcoded en el código y no es configurable.

#### **3.3.5 Parámetros Configurables**

* `LANZADOR_INTERVALO_CONCILIACION_SEG`: Frecuencia del ciclo (default: 900 segundos / 15 minutos).
* `CONCILIADOR_DIAS_TOLERANCIA_UNKNOWN`: Días antes de marcar como UNKNOWN final (default: 30).
* `LANZADOR_CONCILIADOR_BATCH_SIZE`: Tamaño de lote para consultas bulk (default: 25).

---

## **4. Dependencias Externas**

### **4.1 DatabaseConnector**

Proporciona acceso a la base de datos SQL Server mediante los siguientes métodos:

* `obtener_robots_ejecutables()`: SP `ObtenerRobotsEjecutables`
* `insertar_registro_ejecucion()`: Inserta en tabla `Ejecuciones`
* `obtener_ejecuciones_en_curso()`: Filtra estados activos
* `ejecutar_consulta()`: Ejecución genérica de queries
* `ejecutar_consulta_multiple()`: Ejecución batch con `fast_executemany`

### **4.2 AutomationAnywhereClient**

Cliente HTTP asíncrono para la API de Automation 360:

* `autenticar()`: Obtiene token OAuth2
* `desplegar_bot_v4()`: Endpoint `/v4/automations/deploy`
* `obtener_detalles_por_deployment_ids()`: Endpoint bulk de consulta de deployments
* `obtener_devices()`: Endpoint `/v2/devices/list`
* `obtener_robots()`: Endpoint `/v2/repository/workspaces/public/files/list`

### **4.3 ApiGatewayClient**

Cliente para la autenticación con el API Gateway interno:

* `get_auth_header()`: Obtiene token JWT dinámico para callbacks

### **4.4 EmailAlertClient**

Cliente SMTP para envío de alertas:

* `send_alert(subject, message)`: Envía correo electrónico a destinatarios configurados

---

## **5. Gestión del Ciclo de Vida**

### **5.1 Arranque**

1. `ConfigLoader.initialize_service()`: Carga variables de entorno desde `.env`.
2. `setup_logging()`: Configura el sistema de logging con `RelativePathFormatter`.
3. Creación de dependencias en `run_lanzador.py`.
4. Inyección de dependencias en componentes de lógica.
5. Inicialización de `LanzadorService` con validación de configuración.
6. Registro de manejadores de señales (SIGINT, SIGTERM/SIGBREAK).
7. Arranque de los tres ciclos asíncronos con `asyncio.create_task()`.

### **5.2 Cierre Ordenado (Graceful Shutdown)**

1. El orquestador realiza una validación crítica (`_validar_configuracion_critica`) antes de iniciar los ciclos. Si faltan variables esenciales (intervalo_lanzamiento, intervalo_sincronizacion, intervalo_conciliacion), el servicio lanza una excepción y se detiene inmediatamente para evitar comportamientos erráticos.
2. Captura de señal del sistema operativo (SIGINT, SIGTERM/SIGBREAK).
3. Activación del evento `_shutdown_event`.
4. Espera de finalización de tareas asíncronas (con timeout configurable).
5. Cierre de conexiones HTTP (`aa_client.close()`, `gateway_client.close()`).
6. Cierre de conexiones de base de datos (`db_connector.cerrar_conexion_hilo_actual()`).
7. Finalización del proceso.

**Timeout de Cierre**: Configurable mediante `LANZADOR_SHUTDOWN_TIMEOUT_SEG` (default: 60).

---

## **6. Logging y Monitoreo**

### **6.1 Niveles de Log**

* **INFO**: Inicio/fin de ciclos, operaciones exitosas, contadores de registros procesados.
* **WARNING**: Errores recuperables (412, reintentos), configuraciones faltantes no críticas.
* **ERROR**: Fallos en despliegues, errores de red, excepciones en ciclos.
* **CRITICAL**: Errores irrecuperables que impiden el funcionamiento del servicio.

### **6.2 Formato de Log**

```
2025-11-21 14:30:15 [INFO] lanzador.desplegador: Robot 123 desplegado con ID: abc-def-ghi en Equipo 456 (Intento 1/2)
```

Incluye timestamp, nivel, módulo relativo y mensaje.

### **6.3 Destinos de Log**

* **Consola**: Nivel INFO en adelante.
* **Archivo**: `C:\RPA\Logs\SAM\sam_lanzador_app.log` (rotación diaria).
* **Alertas Email**: Errores críticos se notifican vía `EmailAlertClient`.

---

## **7. Configuración**

Todas las variables de configuración se definen en el archivo `.env` y se acceden exclusivamente mediante `ConfigManager`.

### **7.1 Variables Principales**

| Variable | Descripción | Default |
|----------|-------------|---------|
| `LANZADOR_INTERVALO_LANZAMIENTO_SEG` | Frecuencia ciclo despliegue | 15 |
| `LANZADOR_INTERVALO_SINCRONIZACION_SEG` | Frecuencia ciclo sync | 3600 |
| `LANZADOR_INTERVALO_CONCILIACION_SEG` | Frecuencia ciclo conciliación | 900 |
| `LANZADOR_HABILITAR_SYNC` | Activar/desactivar sync | True |
| `LANZADOR_MAX_WORKERS` | Concurrencia despliegue | 10 |
| `LANZADOR_BOT_INPUT_VUELTAS` | Input para bots | 3 |
| `CONCILIADOR_DIAS_TOLERANCIA_UNKNOWN` | Días antes de UNKNOWN final | 30 |
| `LANZADOR_PAUSA_INICIO_HHMM` | Hora inicio pausa (HH:MM) | 22:00 |
| `LANZADOR_PAUSA_FIN_HHMM` | Hora fin pausa (HH:MM) | 06:00 |
| `LANZADOR_MAX_REINTENTOS_DEPLOY` | Reintentos por robot | 2 |
| `LANZADOR_DELAY_REINTENTO_DEPLOY_SEG` | Delay entre reintentos | 5 |

---

## **8. Estados de Ejecución**

### **8.1 Estados Reconocidos**

| Estado | Origen | Final | Descripción |
|--------|--------|-------|-------------|
| `DEPLOYED` | Desplegador | No | Robot desplegado, pendiente de ejecución |
| `QUEUED` | A360 | No | En cola de ejecución |
| `PENDING_EXECUTION` | A360 | No | Pendiente de inicio |
| `RUNNING` | A360 | No | En ejecución |
| `UPDATE` | A360 | No | Actualización en curso (mapeado a RUNNING) |
| `RUN_PAUSED` | A360 | No | Ejecución pausada |
| `COMPLETED` | A360/Callback | Sí | Finalizado exitosamente |
| `RUN_COMPLETED` | A360/Callback | Sí | Finalizado exitosamente |
| `RUN_FAILED` | A360/Callback | Sí | Finalizado con error |
| `DEPLOY_FAILED` | A360/Callback | Sí | Fallo en despliegue |
| `RUN_ABORTED` | A360/Callback | Sí | Abortado manualmente |
| `RUN_TIMED_OUT` | A360 | Sí | Timeout de ejecución |
| `UNKNOWN` | Conciliador | Variable | Sin respuesta de A360 |

### **8.2 Criterios de Actividad**

Una ejecución se considera activa si cumple **al menos una** de las siguientes condiciones:

1. `Estado IN ('DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 'RUNNING', 'UPDATE', 'RUN_PAUSED')`
2. `Estado = 'UNKNOWN' AND FechaUltimoUNKNOWN > DATEADD(HOUR, -2, GETDATE())`

**Nota**: `RUN_TIMED_OUT` se considera un estado final y no está incluido en los criterios de actividad.

---

## **9. Interacción con Otros Servicios**

### **9.1 Servicio Callback**

El Desplegador configura las cabeceras de autenticación que A360 utilizará para invocar el endpoint de callback cuando una ejecución finalice:

* **Token Dinámico**: Obtenido del API Gateway mediante `ApiGatewayClient`.
* **API Key Estática**: Definida en `CALLBACK_TOKEN`.

Ambas se envían como headers en el request de despliegue para que A360 las incluya al hacer el POST al callback.

### **9.2 Servicio Balanceador**

El Lanzador no interactúa directamente con el Balanceador. Ambos comparten la misma base de datos:

* El Balanceador modifica las asignaciones en `Asignaciones`.
* El Lanzador lee esas asignaciones mediante `ObtenerRobotsEjecutables`.

---

## **10. Procedimientos Almacenados Utilizados**

| Stored Procedure | Propósito | Invocado Por |
|-----------------|-----------|--------------|
| `ObtenerRobotsEjecutables` | Obtiene robots listos para ejecutar | Desplegador |
| `MergeRobots` | Sincroniza robots desde A360 | Sincronizador |
| `MergeEquipos` | Sincroniza equipos desde A360 | Sincronizador |

---

## **11. Casos de Uso**

### **11.1 Despliegue de Robot Programado**

1. Usuario crea una programación diaria en la interfaz web.
2. El SP `CargarProgramacionDiaria` inserta registros en `Programaciones` y `Asignaciones`.
3. Al llegar la hora configurada (dentro de la ventana de tolerancia), `ObtenerRobotsEjecutables` devuelve el robot.
4. El Desplegador invoca `desplegar_bot_v4()` en A360.
5. Se registra el `DeploymentId` en `Ejecuciones` con estado `DEPLOYED`.
6. El Conciliador actualiza el estado periódicamente hasta que la ejecución finaliza.

### **11.2 Robot Online Sin Programación**

1. Usuario asigna un robot online a un equipo mediante `AsignarRobotOnline`.
2. `ObtenerRobotsEjecutables` incluye el robot si el equipo no tiene ejecuciones activas.
3. El Desplegador lo ejecuta en cada ciclo (comportamiento "always-on").
4. El Conciliador gestiona el estado de cada ejecución.

### **11.3 Recuperación de Error 412 Persistente**

1. Un equipo falla con error 412 (Device Offline) durante múltiples ciclos.
2. El Desplegador reintenta según la configuración (`MAX_REINTENTOS_DEPLOY`).
3. El tracking interno del `LanzadorService` incrementa el contador de fallos.
4. Al alcanzar el umbral (`LANZADOR_UMBRAL_ALERTAS_412`), se envía una alerta.
5. Si el equipo se recupera, el contador se resetea automáticamente.

### **11.4 Manejo de Estado UNKNOWN Transitorio**

1. Una ejecución reporta estado `UNKNOWN` desde A360 (posible latencia de API).
2. El Conciliador actualiza el estado a `UNKNOWN` pero **sin** establecer `FechaFin`.
3. Se registra `FechaUltimoUNKNOWN = GETDATE()` para tracking.
4. En ciclos posteriores, el Conciliador reintenta la consulta.
5. Si A360 responde con el estado real (ej. `COMPLETED`), se actualiza normalmente.
6. Si pasan 30 días sin respuesta, se marca como `UNKNOWN` final con `FechaFin`.

---

## **12. Consideraciones de Despliegue**

### **12.1 Requisitos del Entorno**

* Python 3.9+
* SQL Server con base de datos SAM configurada
* Acceso de red a Automation 360 Control Room
* Configuración SMTP para alertas (opcional)

### **12.2 Instalación en Producción (Windows)**

1. Clonar el repositorio en el servidor.
2. Configurar las variables en `.env`.
3. Ejecutar `.\scripts\install_services.ps1` como Administrador.
4. El script configura el servicio mediante NSSM con:
   * Usuario de servicio configurado
   * Logs en `C:\RPA\Logs\SAM`
   * Reinicio automático en caso de fallo

### **12.3 Ejecución Manual (Desarrollo)**

```bash
# Opción 1: Usando UV
uv run -m sam.lanzador

# Opción 2: Ejecución directa
python src/sam/lanzador/run_lanzador.py
```

---

## **13. Métricas y Rendimiento**

### **13.1 Throughput Esperado**

* **Despliegue**: 1-2 robots/segundo (con `MAX_WORKERS=10`, limitado por latencia de A360)
* **Conciliación**: 25 ejecuciones/query (batch size configurable)
* **Sincronización**: ~2000 registros/ciclo (robots + equipos)

### **13.2 Consumo de Recursos**

* **CPU**: Bajo (<5%) en operación normal
* **RAM**: ~100-200 MB
* **Red**: Depende del volumen de ejecuciones (API calls a A360)
* **Disco**: Logs rotan diariamente

---

## **14. Limitaciones Conocidas**

1. **Concurrencia de Equipos**: Un equipo solo puede ejecutar un robot a la vez (validado por `ObtenerRobotsEjecutables`).
2. **Estados UNKNOWN**: Pueden requerir hasta 30 días (configurable) para determinar si son fallos definitivos.
3. **Zona Horaria**: Hardcoded a `America/Argentina/Buenos_Aires` en el Desplegador y Conciliador. No es configurable.
4. **Callback Fallback**: Si el callback falla, el Conciliador eventualmente sincronizará el estado, pero con mayor latencia.
5. **Eliminación de Asignaciones**: Las asignaciones problemáticas se eliminan completamente en errores 400, no se desactivan (la tabla no tiene columna `Activo`).

---

## **15. Troubleshooting**

### **15.1 El servicio no despliega robots**

* Validar la ventana de pausa (`LANZADOR_PAUSA_INICIO_HHMM/FIN_HHMM`).
* Revisar que `ObtenerRobotsEjecutables` devuelva resultados (ejecutar manualmente el SP).
* Confirmar conectividad con A360 (revisar logs del `aa_client`).

### **15.2 Estados no se actualizan**

* Verificar que el Conciliador esté activo (revisar logs de ciclo de conciliación).
* Confirmar que `CallbackInfo` esté NULL (de lo contrario, el callback ya actualizó el estado).
* Validar que los `DeploymentId` existan en A360.
* Revisar si hay ejecuciones en estado `UNKNOWN` transitorio (esperar próximo ciclo).

### **15.3 Errores 412 persistentes**

* Verificar que el Bot Runner esté online en A360.
* Confirmar que la licencia del equipo sea `ATTENDEDRUNTIME` o `RUNTIME`.
* Revisar si el dispositivo está bloqueado o ocupado por otra ejecución.

### **15.4 Asignaciones desaparecen**

* Los errores 400 causan la eliminación completa de asignaciones problemáticas.
* Revisar logs de alertas enviadas por email.
* Verificar configuración de permisos y licencias en A360.
* Recrear la asignación después de corregir el problema subyacente.
