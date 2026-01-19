# 🛠️ GUÍA DE TROUBLESHOOTING - PROYECTO SAM

---
**Versión:** 1.0.0
**Última Actualización:** 2025-01-19
---

## 📋 ÍNDICE

1. [Diagnóstico Rápido](#diagnóstico-rápido)
2. [Tabla de Síntomas](#tabla-de-síntomas)
3. [Comandos de Diagnóstico](#comandos-de-diagnóstico)
4. [Árbol de Decisión](#árbol-de-decisión)
5. [Problemas Conocidos](#problemas-conocidos)

---

## 🚀 DIAGNÓSTICO RÁPIDO

### Checklist Inicial (5 minutos)

```powershell
# 1. Verificar estado de servicios
Get-Service SAM_* | Format-Table -AutoSize

# 2. Verificar logs recientes (últimos 20 errores)
Get-ChildItem C:\RPA\Logs\SAM\*.log | ForEach-Object {
    Write-Host "`n=== $($_.Name) ==="
    Select-String -Path $_.FullName -Pattern "ERROR|CRITICAL" | Select-Object -Last 5
}

# 3. Verificar conectividad BD
sqlcmd -S [SERVER] -d SAM -Q "SELECT TOP 1 * FROM dbo.ConfiguracionSistema"

# 4. Verificar ejecuciones problemáticas
sqlcmd -S [SERVER] -d SAM -Q "SELECT Estado, COUNT(*) AS Total FROM dbo.Ejecuciones WHERE FechaInicio > DATEADD(HOUR, -1, GETDATE()) GROUP BY Estado"
```

---

## 📊 TABLA DE SÍNTOMAS

| Síntoma | Causa Probable | Solución Rápida | Documento |
|---------|---------------|-----------------|-----------|
| **Robots no se lanzan** | Robot inactivo en SAM | Activar en Web UI | [05_ejemplos_tareas.md](05_ejemplos_tareas.md#2-diagnosticar-robot-que-no-arranca) |
| | Sin equipos asignados | Verificar balanceador | [05_ejemplos_tareas.md](05_ejemplos_tareas.md#5-balancear-carga-manualmente) |
| | Robot programado (no online) | Cambiar `EsOnline=1` | [05_ejemplos_tareas.md](05_ejemplos_tareas.md#2-diagnosticar-robot-que-no-arranca) |
| **Error 412 persistente** | Device offline | Verificar A360 Control Room | [05_ejemplos_tareas.md](05_ejemplos_tareas.md#4-resolver-error-412-persistente) |
| | Robot sin targets | Configurar targets en A360 | [05_ejemplos_tareas.md](05_ejemplos_tareas.md#4-resolver-error-412-persistente) |
| **Estado UNKNOWN** | Pérdida comunicación A360 | Esperar conciliador | [05_ejemplos_tareas.md](05_ejemplos_tareas.md#6-investigar-estado-unknown) |
| | Ejecución purgada (>30 días) | Marcar como `COMPLETED_INFERRED` | [05_ejemplos_tareas.md](05_ejemplos_tareas.md#6-investigar-estado-unknown) |
| **Servicio no arranca** | Puerto ocupado | Verificar `netstat -ano` | [Abajo](#servicio-no-arranca) |
| | Error en .env | Verificar variables | [04_seguridad.md](04_seguridad.md#2-manejo-de-credenciales) |
| **Balanceador no asigna** | Mapeo incorrecto | Verificar tabla `Mapeos` | [05_ejemplos_tareas.md](05_ejemplos_tareas.md#2-diagnosticar-robot-que-no-arranca) |
| | Pool en cooling | Esperar 5 minutos | [docs/servicios/servicio_balanceador.md](../servicios/servicio_balanceador.md) |
| **Callback no recibe** | Token inválido | Verificar `CALLBACK_TOKEN` | [04_seguridad.md](04_seguridad.md) |
| | Firewall bloqueando | Verificar puerto 5000 | [Abajo](#callback-no-recibe-notificaciones) |
| **BD lenta** | Tabla `Ejecuciones` grande | Particionar por fecha | [03_reglas_sql.md](03_reglas_sql.md) |
| | Índices faltantes | Ejecutar `sp_BlitzIndex` | [03_reglas_sql.md](03_reglas_sql.md) |

---

## 🔍 COMANDOS DE DIAGNÓSTICO

### Verificar Estado de Servicios

```powershell
# Estado actual
Get-Service SAM_* | Select-Object Name, Status, StartType

# Logs de eventos de Windows
Get-EventLog -LogName Application -Source "SAM_*" -Newest 10

# Verificar procesos Python
Get-Process | Where-Object { $_.ProcessName -like "*python*" } | Select-Object Id, ProcessName, StartTime, CPU
```

### Verificar Conectividad A360

```powershell
# Test HTTP básico
Invoke-WebRequest -Uri "https://[A360-URL]/v1/authentication/login" -Method GET -UseBasicParsing

# Verificar certificados SSL
$url = "https://[A360-URL]"
$req = [System.Net.HttpWebRequest]::Create($url)
$req.GetResponse() | Out-Null
$req.ServicePoint.Certificate | Format-List
```

### Verificar Base de Datos

```sql
-- Ejecuciones problemáticas (última hora)
SELECT
    Estado,
    COUNT(*) AS Total,
    MIN(FechaInicio) AS Primera,
    MAX(FechaInicio) AS Ultima
FROM dbo.Ejecuciones
WHERE FechaInicio > DATEADD(HOUR, -1, GETDATE())
GROUP BY Estado
ORDER BY Total DESC;

-- Robots sin actividad (últimas 24h)
SELECT
    r.Nombre,
    r.ActivoSAM,
    r.EsOnline,
    COUNT(e.EjecucionId) AS EjecucionesUltimas24h
FROM dbo.Robots r
LEFT JOIN dbo.Ejecuciones e ON r.RobotId = e.RobotId
    AND e.FechaInicio > DATEADD(DAY, -1, GETDATE())
WHERE r.ActivoSAM = 1
GROUP BY r.Nombre, r.ActivoSAM, r.EsOnline
HAVING COUNT(e.EjecucionId) = 0;

-- Equipos offline
SELECT
    e.Nombre,
    e.Activo_SAM,
    MAX(ej.FechaInicio) AS UltimaEjecucion,
    DATEDIFF(HOUR, MAX(ej.FechaInicio), GETDATE()) AS HorasSinUso
FROM dbo.Equipos e
LEFT JOIN dbo.Ejecuciones ej ON e.EquipoId = ej.EquipoId
WHERE e.Activo_SAM = 1
GROUP BY e.Nombre, e.Activo_SAM
HAVING MAX(ej.FechaInicio) < DATEADD(DAY, -1, GETDATE())
    OR MAX(ej.FechaInicio) IS NULL;
```

---

## 🌳 ÁRBOL DE DECISIÓN

### Robot No Se Ejecuta

```
¿El robot está activo en SAM?
├─ NO → Activar en Web UI (Robots > Toggle "Activo SAM")
└─ SÍ → ¿Tiene equipos asignados?
    ├─ NO → ¿Es robot online o programado?
    │   ├─ Online → Verificar balanceador (logs + mapeos)
    │   └─ Programado → Verificar programación activa
    └─ SÍ → ¿Hay errores en logs del Lanzador?
        ├─ Error 412 → Ver sección "Error 412"
        ├─ Error 400 → Configurar targets en A360
        └─ Sin errores → Verificar carga (tickets pendientes)
```

### Error 412

```
¿Qué dice el mensaje de error?
├─ "Device offline" → ¿El equipo está conectado en A360?
│   ├─ NO → Reiniciar Bot Runner o marcar inactivo
│   └─ SÍ → Verificar conectividad red
├─ "No compatible targets" → Configurar targets en A360
└─ "Device busy" → Esperar o asignar otro equipo
```

### Estado UNKNOWN

```
¿Cuánto tiempo lleva en UNKNOWN?
├─ < 1 hora → Esperar próximo ciclo conciliador (5-15 min)
├─ 1-24 horas → Verificar logs conciliador
│   ├─ "API timeout" → Verificar conectividad A360
│   └─ "No data" → Ejecución purgada, marcar inferido
└─ > 24 horas → Marcar manualmente como COMPLETED_INFERRED
```

---

## 🐛 PROBLEMAS CONOCIDOS

### Servicio No Arranca

**Síntoma:**
```
Error: Address already in use (puerto 8000/5000)
```

**Diagnóstico:**
```powershell
# Verificar qué proceso usa el puerto
netstat -ano | findstr ":8000"
netstat -ano | findstr ":5000"

# Matar proceso si es necesario
Stop-Process -Id [PID] -Force
```

**Solución:**
1. Cambiar puerto en `.env`:
   ```
   WEB_PORT=8001
   CALLBACK_PORT=5001
   ```
2. Reiniciar servicio

---

### Callback No Recibe Notificaciones

**Síntoma:**
- Ejecuciones quedan en `RUNNING` indefinidamente
- No se actualizan estados finales

**Diagnóstico:**
```powershell
# Verificar servicio activo
Get-Service SAM_Callback

# Verificar logs
Get-Content C:\RPA\Logs\SAM\callback.log -Tail 50

# Test manual de endpoint
Invoke-WebRequest -Uri "http://localhost:5000/health" -Method GET
```

**Causas Comunes:**
1. **Token inválido**: Verificar `CALLBACK_TOKEN` en `.env`
2. **Firewall**: Abrir puerto 5000
3. **URL incorrecta en A360**: Debe apuntar a `http://[SAM-SERVER]:5000/api/callback`

**Solución:**
```powershell
# Verificar configuración en A360
# Control Room > Admin > Settings > Callback URL
# Debe ser: http://[SAM-IP]:5000/api/callback
```

---

### Balanceador No Asigna Equipos

**Síntoma:**
- Hay carga (tickets) pero no se asignan equipos
- Logs muestran "Carga detectada" pero sin acción

**Diagnóstico:**
```sql
-- Verificar configuración del robot
SELECT
    Nombre,
    PrioridadBalanceo,
    MinEquipos,
    MaxEquipos,
    TicketsPorEquipoAdicional
FROM dbo.Robots
WHERE Nombre = '[ROBOT_NAME]';

-- Verificar pool en cooling
SELECT * FROM dbo.PoolCooling
WHERE FechaExpiracion > GETDATE();
```

**Causas Comunes:**
1. **MaxEquipos alcanzado**: Aumentar límite
2. **Pool en cooling**: Esperar 5 minutos
3. **Mapeo incorrecto**: Nombre externo ≠ interno

**Solución:**
```sql
-- Aumentar MaxEquipos
UPDATE dbo.Robots
SET MaxEquipos = 10
WHERE Nombre = '[ROBOT_NAME]';

-- Forzar salida de cooling (emergencia)
DELETE FROM dbo.PoolCooling
WHERE PoolId = [POOL_ID];
```

---

### Ejecuciones UNKNOWN Acumuladas

**Síntoma:**
- Múltiples ejecuciones en estado `UNKNOWN` por días

**Diagnóstico:**
```sql
SELECT
    COUNT(*) AS Total,
    MIN(FechaUltimoUNKNOWN) AS MasAntiguo,
    MAX(IntentosConciliadorFallidos) AS MaxIntentos
FROM dbo.Ejecuciones
WHERE Estado = 'UNKNOWN';
```

**Causas Comunes:**
1. **A360 purgó historial**: Ejecuciones >30 días
2. **Timeout API**: A360 no responde
3. **Conciliador deshabilitado**: Servicio detenido

**Solución:**
```sql
-- Marcar como inferidas (ejecuciones >7 días en UNKNOWN)
UPDATE dbo.Ejecuciones
SET
    Estado = 'COMPLETED_INFERRED',
    FechaFin = FechaUltimoUNKNOWN
WHERE Estado = 'UNKNOWN'
AND DATEDIFF(DAY, FechaUltimoUNKNOWN, GETDATE()) > 7;
```

---

### Base de Datos Lenta

**Síntoma:**
- Queries lentas (>5 segundos)
- Timeouts en servicios

**Diagnóstico:**
```sql
-- Verificar tamaño de tabla Ejecuciones
SELECT
    COUNT(*) AS TotalRegistros,
    MIN(FechaInicio) AS MasAntiguo,
    MAX(FechaInicio) AS MasReciente
FROM dbo.Ejecuciones;

-- Verificar índices faltantes
SELECT
    OBJECT_NAME(d.object_id) AS TableName,
    d.equality_columns,
    d.inequality_columns,
    d.included_columns
FROM sys.dm_db_missing_index_details d
INNER JOIN sys.dm_db_missing_index_groups g ON d.index_handle = g.index_handle
WHERE d.database_id = DB_ID('SAM');
```

**Solución:**
```sql
-- Particionar tabla Ejecuciones (si >1M registros)
-- Ver: 03_reglas_sql.md para procedimiento completo

-- Crear índices recomendados
CREATE NONCLUSTERED INDEX IX_Ejecuciones_Estado_Fecha
ON dbo.Ejecuciones (Estado, FechaInicio)
INCLUDE (RobotId, EquipoId);
```

---

## 📞 ESCALAMIENTO

### Cuándo Escalar

Escala **INMEDIATAMENTE** si:
- ✅ Múltiples servicios caídos (>2)
- ✅ Pérdida de datos o corrupción BD
- ✅ Errores de seguridad (credenciales expuestas)
- ✅ Discrepancias A360-SAM >30 minutos
- ✅ Errores 412 en >10 robots simultáneamente

### Información a Recopilar

```powershell
# Script de diagnóstico completo
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputDir = "C:\RPA\Diagnostico_$timestamp"
New-Item -ItemType Directory -Path $outputDir

# 1. Estado servicios
Get-Service SAM_* | Out-File "$outputDir\servicios.txt"

# 2. Logs (últimas 100 líneas)
Get-ChildItem C:\RPA\Logs\SAM\*.log | ForEach-Object {
    Get-Content $_.FullName -Tail 100 | Out-File "$outputDir\$($_.BaseName).txt"
}

# 3. Configuración (SIN credenciales)
Get-Content .env | ForEach-Object {
    $_ -replace '=.*', '=[OCULTO]'
} | Out-File "$outputDir\config.txt"

# 4. Procesos Python
Get-Process | Where-Object { $_.ProcessName -like "*python*" } | Out-File "$outputDir\procesos.txt"

Write-Host "Diagnóstico guardado en: $outputDir"
```

---

## 📚 REFERENCIAS RÁPIDAS

| Problema | Documento |
|----------|-----------|
| Robot no arranca | [05_ejemplos_tareas.md](05_ejemplos_tareas.md#2-diagnosticar-robot-que-no-arranca) |
| Error 412 | [05_ejemplos_tareas.md](05_ejemplos_tareas.md#4-resolver-error-412-persistente) |
| Estado UNKNOWN | [05_ejemplos_tareas.md](05_ejemplos_tareas.md#6-investigar-estado-unknown) |
| Conectividad A360 | [05_ejemplos_tareas.md](05_ejemplos_tareas.md#7-verificar-conectividad-a360) |
| Seguridad | [04_seguridad.md](04_seguridad.md) |
| SQL | [03_reglas_sql.md](03_reglas_sql.md) |

---

*Última revisión: 2025-01-19*
