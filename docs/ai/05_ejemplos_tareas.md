# 📋 EJEMPLOS DE TAREAS COMUNES - PROYECTO SAM

---
**Versión:** 1.0.0
**Última Actualización:** 2025-01-19
---

## 🎯 PROPÓSITO

Este documento proporciona **guías paso a paso** para tareas comunes que un Agente IA puede encontrar al trabajar con SAM. Cada ejemplo incluye:
- ✅ Pasos concretos a seguir
- 📚 Documentación relevante a consultar
- ⚠️ Precauciones importantes
- 💡 Salida esperada

---

## 📋 ÍNDICE

1. [Agregar un Nuevo Robot](#1-agregar-un-nuevo-robot)
2. [Diagnosticar Robot que No Arranca](#2-diagnosticar-robot-que-no-arranca)
3. [Configurar Programación Semanal](#3-configurar-programación-semanal)
4. [Resolver Error 412 Persistente](#4-resolver-error-412-persistente)
5. [Balancear Carga Manualmente](#5-balancear-carga-manualmente)
6. [Investigar Estado UNKNOWN](#6-investigar-estado-unknown)
7. [Verificar Conectividad A360](#7-verificar-conectividad-a360)
8. [Optimizar Prioridades](#8-optimizar-prioridades)

---

## 1. AGREGAR UN NUEVO ROBOT

### Contexto
Usuario reporta: *"Creé un nuevo bot en A360 llamado 'Proceso_Facturas'. ¿Cómo lo agrego a SAM?"*

### Pasos del Agente

#### Paso 1: Verificar Sincronización con A360

**Acción:**
```markdown
"Primero verificaré si SAM ya detectó tu robot mediante la sincronización automática."
```

**Comando de diagnóstico:**
```sql
-- Buscar robot en catálogo SAM
SELECT RobotId, Nombre, ActivoSAM
FROM dbo.Robots
WHERE Nombre LIKE '%Facturas%';
```

**Resultados posibles:**

**Caso A: Robot encontrado**
```
RobotId | Nombre              | ActivoSAM
--------|---------------------|----------
12345   | Proceso_Facturas    | 1
```

**Respuesta:**
```markdown
✅ Buenas noticias: SAM ya detectó tu robot.
- Robot ID: 12345
- Nombre: Proceso_Facturas
- Estado: Activo

El robot está listo para configurarse. Continúo con el siguiente paso.
```

**Caso B: Robot NO encontrado**
```
(Sin resultados)
```

**Respuesta:**
```markdown
⏳ El robot aún no está sincronizado en SAM.

**Opciones:**
1. **Esperar el próximo ciclo de sincronización** (ocurre cada 1 hora por defecto)
2. **Forzar sincronización** (requiere reiniciar servicio Lanzador)

¿Cuál prefieres? Si es urgente, puedo guiarte para reiniciar el servicio.
```

#### Paso 2: Configurar Parámetros Básicos

**Acción:**
```markdown
"Ahora configuraremos los parámetros operativos del robot."
```

**Guía para el usuario:**
```markdown
Accede a la Interfaz Web de SAM:
1. Abre http://[SAM-SERVER]:8000
2. Ve a la sección **"Robots"**
3. Busca "Proceso_Facturas" en la tabla
4. Haz clic en **"Editar"** (ícono de lápiz)

**Configuración Recomendada para Iniciar:**
- ✅ Prioridad Balanceo: **50** (media)
  - Rango: 1-100 (menor = más prioritario)
  - Usa 1-20 para procesos críticos, 80-100 para secundarios

- ✅ Min Equipos: **1**
  - Garantiza al menos 1 máquina disponible

- ✅ Max Equipos: **5**
  - Límite máximo de escalamiento
  - Usa -1 para "sin límite"

- ✅ Tickets por Equipo Adicional: **10**
  - Define cuántos tickets justifican asignar otra máquina

5. Haz clic en **"Guardar"**
```

#### Paso 3: Asignar a un Pool (Opcional)

**Acción:**
```markdown
"Si deseas que este robot pertenezca a un pool específico (ej. Pool 'Finanzas'),
puedo guiarte. ¿Tienes un pool asignado o debo usar el pool por defecto?"
```

**Si el usuario confirma un pool:**
```markdown
En la Interfaz Web:
1. Ve a **"Pools"**
2. Selecciona el pool deseado (ej. "Finanzas")
3. Haz clic en **"Asignar Robots"**
4. Busca "Proceso_Facturas" y selecciónalo
5. Haz clic en **"Guardar"**
```

#### Paso 4: Verificar Configuración

**Comando de verificación:**
```sql
SELECT
    r.RobotId,
    r.Nombre,
    r.PrioridadBalanceo,
    r.MinEquipos,
    r.MaxEquipos,
    r.EsOnline,
    p.Nombre AS Pool
FROM dbo.Robots r
LEFT JOIN dbo.Pool_Robot pr ON r.RobotId = pr.RobotId
LEFT JOIN dbo.Pools p ON pr.PoolId = p.PoolId
WHERE r.Nombre = 'Proceso_Facturas';
```

**Salida Esperada:**
```markdown
✅ Robot configurado exitosamente:

| Campo                    | Valor              |
|--------------------------|-------------------|
| Robot ID                 | 12345             |
| Nombre                   | Proceso_Facturas  |
| Prioridad Balanceo       | 50                |
| Min Equipos              | 1                 |
| Max Equipos              | 5                 |
| Es Online                | 1 (Sí)            |
| Pool                     | Finanzas          |

**Próximos Pasos:**
- ✅ El Balanceador considerará este robot en el próximo ciclo (cada ~2 min)
- ✅ Si hay carga (tickets pendientes), asignará equipos automáticamente
- ⚠️ Si necesitas programarlo (ej. diariamente a las 9am), dímelo y te guío
```

---

## 2. DIAGNOSTICAR ROBOT QUE NO ARRANCA

### Contexto
Usuario reporta: *"El robot 'Proceso_Pagos' tiene tickets pero no se está ejecutando."*

### Pasos del Agente

#### Paso 1: Verificar Estado del Robot

```sql
SELECT
    r.Nombre,
    r.ActivoSAM,
    r.EsOnline,
    r.MinEquipos,
    r.MaxEquipos,
    COUNT(a.EquipoId) AS EquiposAsignados
FROM dbo.Robots r
LEFT JOIN dbo.Asignaciones a ON r.RobotId = a.RobotId AND a.EsProgramado = 0
WHERE r.Nombre = 'Proceso_Pagos'
GROUP BY r.Nombre, r.ActivoSAM, r.EsOnline, r.MinEquipos, r.MaxEquipos;
```

**Análisis de Resultados:**

**Problema Común #1: Robot Inactivo**
```
Nombre         | ActivoSAM | EsOnline | MinEquipos | MaxEquipos | EquiposAsignados
---------------|-----------|----------|------------|------------|------------------
Proceso_Pagos  | 0         | 1        | 1          | 5          | 0
```

**Diagnóstico:**
```markdown
❌ **Problema Detectado:** Robot marcado como INACTIVO

**Causa:** El robot fue desactivado manualmente en SAM.

**Solución:**
En la Interfaz Web:
1. Ve a "Robots"
2. Busca "Proceso_Pagos"
3. Activa el toggle "Activo SAM"

O ejecuta:
```sql
UPDATE dbo.Robots
SET ActivoSAM = 1
WHERE Nombre = 'Proceso_Pagos';
```
```

**Problema Común #2: Robot Programado (No Online)**
```
Nombre         | ActivoSAM | EsOnline | MinEquipos | MaxEquipos | EquiposAsignados
---------------|-----------|----------|------------|------------|------------------
Proceso_Pagos  | 1         | 0        | 1          | 5          | 2
```

**Diagnóstico:**
```markdown
⚠️ **Problema Detectado:** Robot configurado como PROGRAMADO (no responde a demanda)

**Causa:** El robot tiene programaciones activas (ej. ejecutar diariamente a las 9am).
Esto hace que SAM lo ignore para ejecución bajo demanda.

**Soluciones:**

**Opción A:** Si debe responder a tickets (cambiarlo a Online):
```sql
-- ⚠️ Esto DESACTIVARÁ las programaciones
UPDATE dbo.Robots
SET EsOnline = 1
WHERE Nombre = 'Proceso_Pagos';
```

**Opción B:** Si debe ejecutarse solo según agenda:
- Verificar que la programación esté activa
- Esperar a la hora programada
```

**Problema Común #3: Sin Equipos Asignados**
```
Nombre         | ActivoSAM | EsOnline | MinEquipos | MaxEquipos | EquiposAsignados
---------------|-----------|----------|------------|------------|------------------
Proceso_Pagos  | 1         | 1        | 1          | 5          | 0
```

**Diagnóstico:**
```markdown
⚠️ **Problema Detectado:** Robot activo pero SIN equipos asignados

**Causas Posibles:**
1. El Balanceador no detecta carga (tickets pendientes)
2. El robot está en Cooling (recientemente modificado)
3. Problema de mapeo (nombre externo ≠ nombre interno)

**Diagnóstico Adicional:**
```

#### Paso 2: Verificar Carga Detectada

```markdown
"Verificaré si el Balanceador está detectando tickets para este robot."
```

**Revisar logs del Balanceador:**
```powershell
Select-String -Path "C:\RPA\Logs\SAM\balanceador.log" -Pattern "Proceso_Pagos" | Select-Object -Last 10
```

**Resultado Esperado:**
```
INFO - Carga detectada para 'Proceso_Pagos': 150 tickets pendientes
```

**Si NO aparece:**
```markdown
❌ **Problema:** El Balanceador NO ve carga para este robot.

**Causas:**
1. **Mapeo Incorrecto:** El nombre en Clouders/RPA360 no coincide con "Proceso_Pagos"
2. **Proveedor Caído:** Clouders o RPA360 no responde

**Solución - Verificar Mapeos:**
En la Interfaz Web:
1. Ve a "Mapeos"
2. Busca si existe un mapeo para "Proceso_Pagos"
3. Verifica que el "Nombre Externo" coincida exactamente con el nombre en Clouders/RPA360

Ejemplo:
| Nombre Externo      | Nombre Interno SAM |
|---------------------|-------------------|
| ROBOT_PAGOS_V2      | Proceso_Pagos     |
```

#### Paso 3: Revisar Logs del Lanzador

```powershell
Get-Content C:\RPA\Logs\SAM\lanzador.log -Tail 50 | Select-String "Proceso_Pagos"
```

**Buscar errores específicos:**

**Error 412 - Dispositivo Offline:**
```
ERROR - Fallo al desplegar 'Proceso_Pagos' en Equipo 5: Error 412 - Device offline
```

**Diagnóstico:**
```markdown
❌ **Problema:** El Bot Runner asignado está apagado/desconectado

**Solución:**
1. Verificar en A360 Control Room que el dispositivo esté conectado
2. Si está offline, reiniciarlo o asignar otro equipo manualmente
```

**Error 400 - Robot sin Targets o Error de Código:**
```
ERROR - Fallo al desplegar 'Proceso_Pagos': Error 400 - Bad Request
```

**Diagnóstico:**
```markdown
❌ **Problema:** El robot tiene un error de configuración o de integridad en A360.

**Causas Posibles:**
1. **Sin Targets:** El robot NO tiene targets compatibles configurados.
2. **Error de Código (Integridad):** El Taskbot tiene errores internos (paquetes inexistentes, variables rotas).

**Solución:**
En A360 Control Room:
1. Ir a "Automation" > Buscar "Proceso_Pagos".
2. **Verificar Targets:** En "Run Settings", asegurar que tenga un Device Pool o Device asignado.
3. **Verificar Código:** Abrir el bot en el editor y buscar alertas de error (íconos rojos).
   - Revisar que todos los **Packages** usados estén disponibles.
   - Revisar que no haya variables con errores de referencia.
4. Guardar y volver a intentar.
```

---

## 3. CONFIGURAR PROGRAMACIÓN SEMANAL

### Contexto
Usuario: *"Necesito que 'Robot_Reportes' se ejecute de lunes a viernes a las 8:00 AM."*

### Pasos del Agente

```markdown
**Respuesta:**
"Te guiaré para crear una programación semanal para 'Robot_Reportes'."
```

#### Paso 1: Acceder a la Interfaz Web

```markdown
1. Abre la Interfaz Web: http://[SAM-SERVER]:8000
2. Ve a la sección **"Programaciones"**
3. Haz clic en **"Programación"** > **"Crear Nueva Programación"**
```

#### Paso 2: Configurar Programación

```markdown
**Formulario de Creación:**

📋 **Robot:**
- Busca y selecciona "Robot_Reportes"

⏰ **Tipo de Programación:**
- Selecciona **"Semanal"**

🕐 **Hora de Inicio:**
- Ingresa: **08:00**

⏱️ **Tolerancia (minutos):**
- Ingresa: **30**
  (Significa: Si falla a las 8:00, reintentar hasta las 8:30)

📅 **Días de la Semana:**
- ✅ Marca: Lunes, Martes, Miércoles, Jueves, Viernes
- ⬜ Desmarca: Sábado, Domingo

✅ **Activo:**
- Deja el toggle en **ON**
```

#### Paso 3: Asignar Equipos

```markdown
Después de crear la programación:

1. En la tabla de "Programaciones", busca "Robot_Reportes"
2. Haz clic en **"Asignar Equipos"** (ícono de computadora)
3. Selecciona los equipos que deben ejecutar el robot (ej. Equipo_1, Equipo_2)
4. Haz clic en **"Guardar"**

**Importante:**
- Los equipos asignados quedarán **reservados** para esta programación
- No recibirán asignaciones dinámicas del Balanceador
```

#### Paso 4: Verificar Configuración

```sql
SELECT
    p.ProgramacionId,
    r.Nombre AS Robot,
    p.TipoProgramacion,
    p.HoraInicio,
    p.Tolerancia,
    p.DiasSemana,
    p.Activo,
    COUNT(a.EquipoId) AS EquiposAsignados
FROM dbo.Programaciones p
INNER JOIN dbo.Robots r ON p.RobotId = r.RobotId
LEFT JOIN dbo.Asignaciones a ON p.ProgramacionId = a.ProgramacionId
WHERE r.Nombre = 'Robot_Reportes'
GROUP BY p.ProgramacionId, r.Nombre, p.TipoProgramacion, p.HoraInicio, p.Tolerancia, p.DiasSemana, p.Activo;
```

**Salida Esperada:**
```markdown
✅ Programación creada exitosamente:

| Campo              | Valor              |
|--------------------|--------------------|
| Programación ID    | 42                 |
| Robot              | Robot_Reportes     |
| Tipo               | Semanal            |
| Hora Inicio        | 08:00              |
| Tolerancia         | 30 min             |
| Días Semana        | Lu,Ma,Mi,Ju,Vi     |
| Activo             | 1 (Sí)             |
| Equipos Asignados  | 2                  |

**Comportamiento Esperado:**
- 🕐 Todos los días laborables a las 8:00 AM, SAM desplegará el robot
- ⏳ Si falla a las 8:00, reintentará hasta las 8:30
- ⚠️ El robot ya NO responderá a tickets (EsOnline=0 automáticamente)
```

---

## 4. RESOLVER ERROR 412 PERSISTENTE

### Contexto
Usuario: *"Recibí alerta: 'Equipo_5 tiene 25 fallos 412 consecutivos para Robot_X'"*

### Pasos del Agente

#### Paso 1: Diagnosticar Tipo de Error 412

**Revisar logs:**
```powershell
Select-String -Path "C:\RPA\Logs\SAM\lanzador.log" -Pattern "412.*Equipo_5" | Select-Object -Last 5
```

**Resultado Posible #1:**
```
ERROR - Fallo 412: Device offline (Equipo_5, Robot_X)
```

**Diagnóstico:**
```markdown
❌ **Problema:** El Bot Runner (Equipo_5) está desconectado o apagado

**Verificación:**
1. En A360 Control Room > "Devices"
2. Buscar el dispositivo correspondiente a Equipo_5
3. Verificar columna "Status"

**Soluciones:**

**Opción A: Si el dispositivo está offline permanentemente:**
- Marcarlo como inactivo en SAM:
```sql
UPDATE dbo.Equipos
SET Activo_SAM = 0
WHERE Nombre = 'Equipo_5';
```
- El Balanceador reasignará automáticamente a otro equipo

**Opción B: Si está temporalmente offline:**
- Esperar a que se reconecte
- El contador de errores 412 se reseteará automáticamente
```

**Resultado Posible #2:**
```
ERROR - Fallo 412: No compatible targets found in automation (Robot_X)
```

**Diagnóstico:**
```markdown
❌ **Problema:** El robot NO tiene targets configurados en A360

**Este NO es un problema del equipo, es del robot mismo.**

**Solución:**
En A360 Control Room:
1. Ir a "Automation" > Buscar "Robot_X"
2. Editar > "Run Settings"
3. Configurar "Compatible Targets":
   - Opción 1: Seleccionar un Device Pool
   - Opción 2: Seleccionar dispositivos específicos
4. Guardar

**Importante:** Después de configurar targets, el robot debería desplegarse correctamente.
```

#### Paso 2: Verificar Estado del Dispositivo en SAM

```sql
SELECT
    e.Nombre,
    e.Activo_SAM,
    e.PermiteBalanceoDinamico,
    COUNT(a.RobotId) AS RobotsAsignados
FROM dbo.Equipos e
LEFT JOIN dbo.Asignaciones a ON e.EquipoId = a.EquipoId
WHERE e.Nombre = 'Equipo_5'
GROUP BY e.Nombre, e.Activo_SAM, e.PermiteBalanceoDinamico;
```

**Salida:**
```markdown
| Campo                  | Valor |
|------------------------|-------|
| Nombre                 | Equipo_5 |
| Activo_SAM             | 1 (Activo) |
| PermiteBalanceoDinamico| 1 (Sí) |
| Robots Asignados       | 3 |
```

#### Paso 3: Reasignar Carga si es Necesario

```markdown
Si el equipo sigue offline y hay urgencia:

**Opción: Desasignar temporalmente el equipo problemático**
En la Interfaz Web:
1. Ve a "Robots"
2. Busca los robots afectados (ej. Robot_X)
3. Haz clic en "Asignación de Equipos"
4. Desasigna "Equipo_5"
5. Asigna otro equipo disponible

El Balanceador redistribuirá la carga automáticamente en el próximo ciclo (~2 min).
```

---

## 5. BALANCEAR CARGA MANUALMENTE

### Contexto
Usuario: *"Tengo 200 tickets en Robot_A pero solo 1 máquina asignada. Necesito más recursos YA."*

### Pasos del Agente

```markdown
**Respuesta:**
"Entiendo la urgencia. Hay dos formas de asignar más equipos:
1. **Manual (Inmediato):** Tú asignas equipos específicos
2. **Automático (Esperan ~2 min):** El Balanceador detecta la carga y asigna

¿Prefieres hacerlo manualmente o esperar el balanceo automático?"
```

#### Opción A: Asignación Manual

```markdown
**Pasos:**

1. Abre la Interfaz Web: http://[SAM-SERVER]:8000
2. Ve a "Robots"
3. Busca "Robot_A"
4. Haz clic en **"Asignación de Equipos"**

**Interfaz de Asignación:**
```
┌─────────────────────────────┬─────────────────────────────┐
│ Equipos Disponibles         │ Equipos Asignados (Robot_A) │
├─────────────────────────────┼─────────────────────────────┤
│ ☐ Equipo_2                  │ ☑ Equipo_1                  │
│ ☐ Equipo_3                  │                             │
│ ☐ Equipo_4                  │                             │
│ ☐ Equipo_5                  │                             │
└─────────────────────────────┴─────────────────────────────┘

         [Asignar →]   [← Desasignar]
```

5. **Selecciona** los equipos que quieres agregar (ej. Equipo_2, Equipo_3, Equipo_4)
6. Haz clic en **"Asignar →"**
7. Haz clic en **"Guardar"**

**Resultado:**
- ✅ Inmediato: Los 4 equipos estarán disponibles para Robot_A
- ✅ El Lanzador los usará en el próximo ciclo (~15 seg)
```

#### Opción B: Verificar Balanceo Automático

```markdown
**Pasos:**

1. **Verificar que el Balanceador detecta la carga:**

Revisar logs:
```powershell
Select-String -Path "C:\RPA\Logs\SAM\balanceador.log" -Pattern "Robot_A" | Select-Object -Last 5
```

**Salida Esperada:**
```
INFO - Carga detectada para 'Robot_A': 200 tickets pendientes
INFO - Escalando Robot_A: de 1 a 5 equipos (Demanda alta)
```

2. **Si NO aparece "Carga detectada":**
   - **Problema:** Falla en el mapeo o el proveedor de carga
   - Ve a "Mapeos" en la Web
   - Verifica que el nombre externo coincida con "Robot_A"

3. **Si aparece pero NO asigna:**
   - **Problema:** Posible Cooling o MaxEquipos alcanzado
   - Verificar configuración del robot:
```sql
SELECT Nombre, MaxEquipos, MinEquipos
FROM dbo.Robots
WHERE Nombre = 'Robot_A';
```

**Resultado Esperado:**
- ✅ En ~2 minutos, el Balanceador asignará equipos adicionales automáticamente
```

---

## 6. INVESTIGAR ESTADO UNKNOWN

### Contexto
Usuario: *"Tengo 10 ejecuciones en estado UNKNOWN hace días. ¿Qué hago?"*

### Pasos del Agente

#### Paso 1: Consultar Ejecuciones UNKNOWN

```sql
SELECT
    e.EjecucionId,
    r.Nombre AS Robot,
    eq.Nombre AS Equipo,
    e.FechaInicio,
    e.FechaUltimoUNKNOWN,
    DATEDIFF(HOUR, e.FechaUltimoUNKNOWN, GETDATE()) AS HorasEnUNKNOWN,
    e.IntentosConciliadorFallidos
FROM dbo.Ejecuciones e
INNER JOIN dbo.Robots r ON e.RobotId = r.RobotId
INNER JOIN dbo.Equipos eq ON e.EquipoId = eq.EquipoId
WHERE e.Estado = 'UNKNOWN'
AND e.FechaFin IS NULL
ORDER BY e.FechaUltimoUNKNOWN ASC;
```

**Salida Ejemplo:**
```markdown
| EjecucionId | Robot        | Equipo   | Horas en UNKNOWN | Intentos Fallidos |
|-------------|--------------|----------|------------------|-------------------|
| 1234        | Robot_A      | Equipo_1 | 72               | 15                |
| 1235        | Robot_B      | Equipo_2 | 48               | 10                |
| 1236        | Robot_C      | Equipo_3 | 24               | 5                 |
```

#### Paso 2: Diagnosticar Causa

**Revisar logs del Conciliador:**
```powershell
Select-String -Path "C:\RPA\Logs\SAM\lanzador.log" -Pattern "1234.*UNKNOWN" | Select-Object -Last 10
```

**Resultado Posible #1:**
```
WARNING - EjecuciónID 1234: API A360 no devuelve datos (timeout)
```

**Diagnóstico:**
```markdown
⚠️ **Problema:** A360 no responde o la ejecución fue purgada

**Causa:** Si la ejecución es muy antigua (>30 días por defecto), A360 la elimina de su historial.

**Acción Recomendada:**
El sistema marcará automáticamente como UNKNOWN final después de superar el umbral configurado (CONCILIADOR_DIAS_TOLERANCIA_UNKNOWN).

**Acción Manual Inmediata (si es urgente):**
```sql
-- Marcar como completado inferido
UPDATE dbo.Ejecuciones
SET
    Estado = 'COMPLETED_INFERRED',
    FechaFin = FechaUltimoUNKNOWN,
    CallbackInfo = JSON_MODIFY(
        ISNULL(CallbackInfo, '{}'),
        '$.ResolucionManual',
        'Cerrado por timeout prolongado - No hay datos en A360'
    )
WHERE EjecucionId = 1234;
```
```

**Resultado Posible #2:**
```
INFO - EjecuciónID 1234: Estado en A360 = COMPLETED
```

**Diagnóstico:**
```markdown
✅ **Problema Resuelto:** El Conciliador ya detectó que terminó

**Acción:** El próximo ciclo de conciliación actualizará automáticamente el estado.

**Verificar:**
```sql
SELECT Estado, FechaFin
FROM dbo.Ejecuciones
WHERE EjecucionId = 1234;
```

Si aún aparece UNKNOWN, esperar 5-15 minutos (intervalo del Conciliador).
```

#### Paso 3: Forzar Conciliación (Si es Urgente)

```markdown
⚠️ **Requiere Confirmación Humana**

Si necesitas actualizar el estado inmediatamente:

**Opción: Reiniciar el servicio Lanzador para forzar ciclo de conciliación**
```powershell
Restart-Service SAM_Lanzador
```

**Impacto:**
- ⚠️ Nuevos lanzamientos se detendrán ~30 segundos
- ✅ El Conciliador se ejecutará inmediatamente al reiniciar
- ✅ Robots en ejecución NO se ven afectados (A360 los controla)

¿Confirmas que deseas proceder? (Sí/No)
```

---

## 7. VERIFICAR CONECTIVIDAD A360

### Contexto
Usuario: *"SAM no puede comunicarse con A360. ¿Cómo verifico la conexión?"*

### Pasos del Agente

#### Paso 1: Verificar Variables de Entorno

```markdown
"Verificaré si las credenciales de A360 están configuradas correctamente."
```

**Revisar .env (SIN mostrar valores):**
```powershell
# Verificar existencia de variables críticas
Select-String -Path ".env" -Pattern "^AA_CR_" | ForEach-Object { $_.Line -replace '=.*', '= [OCULTO]' }
```

**Salida Esperada:**
```
AA_CR_URL= [OCULTO]
AA_CR_USER= [OCULTO]
AA_CR_API_KEY= [OCULTO]
```

**Si falta alguna:**
```markdown
❌ **Problema:** Falta configurar variables de A360

**Solución:**
Edita el archivo .env y agrega:
```
AA_CR_URL=https://[TU-CONTROL-ROOM].automationanywhere.com
AA_CR_USER=[USUARIO-SERVICIO]
AA_CR_API_KEY=[TU-API-KEY]
```

**Reiniciar servicios:**
```powershell
Restart-Service SAM_Lanzador
Restart-Service SAM_Conciliador
```

**Verificar:**
```sql
SELECT TOP 10 * FROM dbo.Ejecuciones WHERE Estado = 'UNKNOWN';
```
