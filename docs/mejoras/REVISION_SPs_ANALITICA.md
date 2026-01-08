# Revisión de Stored Procedures de Analítica

**Fecha:** 2025-01-XX  
**Objetivo:** Verificar que los SPs usados para analítica son correctos, usables y se ajustan a la realidad del sistema.

---

## Resumen Ejecutivo

✅ **Estado General:** Los SPs están bien definidos y son usables  
⚠️ **Problemas Menores:** Algunos ajustes recomendados  
✅ **Vistas y Tablas:** Todas existen y están correctamente definidas

---

## 1. Stored Procedures Analizados

### 1.1 `dbo.ObtenerDashboardCallbacks`

**Estado:** ✅ **CORRECTO Y USABLE**

**Parámetros:**
- `@FechaInicio DATETIME2(0) = NULL` ✅
- `@FechaFin DATETIME2(0) = NULL` ✅
- `@RobotId INT = NULL` ✅
- `@IncluirDetalleHorario BIT = 1` ✅

**Result Sets (6):**
1. ✅ Métricas Generales (1 fila)
2. ✅ Rendimiento Distribución (múltiples filas)
3. ✅ Análisis por Robot (múltiples filas)
4. ✅ Tendencia Diaria (múltiples filas)
5. ✅ Patrón Horario (múltiples filas, condicional)
6. ✅ Casos Problemáticos (máx. 20 filas)

**Vista Dependiente:**
- ✅ `dbo.AnalisisRendimientoCallbacks` - **EXISTE** y está correctamente definida

**Uso en Python:**
```python
# src/sam/web/backend/database.py:1056-1082
def get_callbacks_dashboard(...)
```
✅ Los parámetros se pasan correctamente  
✅ Los result sets se mapean correctamente  
✅ Los campos esperados en el frontend coinciden con los del SP

**Campos Esperados en Frontend:**
- `metricas_generales`: ✅ Todos los campos coinciden
- `tendencia_diaria`: ✅ Campos `Fecha`, `CallbacksExitosos`, `ConciliadorExitosos`, `LatenciaPromedioMinutos` coinciden
- `casos_problematicos`: ✅ Campos coinciden

---

### 1.2 `dbo.ObtenerDashboardBalanceador`

**Estado:** ✅ **CORRECTO Y USABLE**

**Parámetros:**
- `@FechaInicio DATETIME2(0) = NULL` ✅
- `@FechaFin DATETIME2(0) = NULL` ✅
- `@PoolId INT = NULL` ✅

**Result Sets (6):**
1. ✅ Métricas Generales (1 fila)
2. ✅ Trazabilidad (múltiples filas)
3. ✅ Resumen Diario (múltiples filas)
4. ✅ Análisis por Robot (múltiples filas)
5. ✅ Estado Actual (1 fila)
6. ✅ Thrashing Events (1 fila)

**Tabla Dependiente:**
- ✅ `dbo.HistoricoBalanceo` - **EXISTE** y está correctamente definida
- ✅ Relación con `dbo.Robots` mediante FK

**Uso en Python:**
```python
# src/sam/web/backend/database.py:1085-1108
def get_balanceador_dashboard(...)
```
✅ Los parámetros se pasan correctamente  
✅ Los result sets se mapean correctamente  
✅ Los campos esperados en el frontend coinciden con los del SP

**Campos Esperados en Frontend:**
- `resumen_diario`: ✅ Campos `Fecha`, `Asignaciones`, `Desasignaciones` coinciden
- `analisis_robots`: ✅ Campo `TotalAcciones` coincide, `RobotNombre` se obtiene del JOIN

---

## 2. Vistas y Tablas Verificadas

### 2.1 `dbo.AnalisisRendimientoCallbacks` (Vista)

**Estado:** ✅ **EXISTE Y CORRECTA**

**Ubicación:** `database/views/dbo_AnalisisRendimientoCallbacks.sql`

**Campos Clave:**
- ✅ `EsCallbackExitoso` (BIT calculado)
- ✅ `EsConciliadorExitoso` (BIT calculado)
- ✅ `EsConciliadorAgotado` (BIT calculado)
- ✅ `LatenciaActualizacionMinutos` (DECIMAL)
- ✅ `DuracionEjecucionMinutos` (DECIMAL)
- ✅ `ClasificacionRendimiento` (VARCHAR)
- ✅ `MecanismoFinalizacion` (VARCHAR)

**Tabla Base:** `dbo.Ejecuciones` ✅

---

### 2.2 `dbo.EstadoBalanceadorTiempoReal` (Vista)

**Estado:** ✅ **EXISTE Y CORRECTA**

**Ubicación:** `database/views/dbo_EstadoBalanceadorTiempoReal.sql`

**Uso en Python:**
```python
# src/sam/web/backend/database.py:937
query_balanceador = "SELECT * FROM dbo.EstadoBalanceadorTiempoReal"
```

**Nota:** ⚠️ La vista puede retornar múltiples filas (una por robot activo), pero el código Python solo toma `[0]`. Esto podría ser un problema si hay múltiples robots.

**Recomendación:** Considerar agregar un resumen agregado o tomar todos los registros.

---

### 2.3 `dbo.EjecucionesActivas` (Vista)

**Estado:** ✅ **EXISTE Y CORRECTA**

**Ubicación:** `database/views/dbo_EjecucionesActivas.sql`

**Uso en Python:**
```python
# src/sam/web/backend/database.py:942-949
query_ejecuciones = """
    SELECT
        COUNT(*) AS TotalActivas,
        COUNT(DISTINCT RobotId) AS RobotsActivos,
        COUNT(DISTINCT EquipoId) AS EquiposOcupados
    FROM dbo.EjecucionesActivas
"""
```
✅ Correcto - usa agregaciones sobre la vista

---

### 2.4 `dbo.HistoricoBalanceo` (Tabla)

**Estado:** ✅ **EXISTE Y CORRECTA**

**Ubicación:** `database/tables/dbo_HistoricoBalanceo.sql`

**Campos:**
- ✅ `HistoricoId` (PK, IDENTITY)
- ✅ `FechaBalanceo` (DATETIME2)
- ✅ `RobotId` (FK a Robots)
- ✅ `TicketsPendientes` (INT)
- ✅ `EquiposAsignadosAntes` (INT)
- ✅ `EquiposAsignadosDespues` (INT)
- ✅ `AccionTomada` (NVARCHAR(50))
- ✅ `Justificacion` (NVARCHAR(255), NULL)
- ✅ `PoolId` (INT, NULL)

**Uso:** ✅ Se usa correctamente en `dbo.ObtenerDashboardBalanceador`

---

## 3. Problemas Identificados

### 3.1 ✅ CORREGIDO: `EstadoBalanceadorTiempoReal` ahora retorna resumen agregado

**Ubicación:** `src/sam/web/backend/database.py:937-949`

**Problema Original:**
La vista `EstadoBalanceadorTiempoReal` retorna una fila por cada robot activo, pero el código solo tomaba la primera fila `[0]`.

**Solución Implementada:**
Se cambió la consulta para retornar un resumen agregado con métricas útiles:

```python
query_balanceador = """
    SELECT
        COUNT(*) AS TotalRobots,
        SUM(CASE WHEN EstadoActual = 'Online' THEN 1 ELSE 0 END) AS RobotsOnline,
        SUM(CASE WHEN EstadoActual = 'Programado' THEN 1 ELSE 0 END) AS RobotsProgramados,
        SUM(CASE WHEN EstadoBalanceo = 'Necesita más equipos' THEN 1 ELSE 0 END) AS RobotsNecesitanEquipos,
        SUM(CASE WHEN EstadoBalanceo = 'Exceso de equipos' THEN 1 ELSE 0 END) AS RobotsConExcesoEquipos,
        SUM(CASE WHEN EstadoBalanceo = 'Balanceado' THEN 1 ELSE 0 END) AS RobotsBalanceados,
        AVG(CAST(EquiposAsignados AS FLOAT)) AS PromedioEquiposAsignados,
        SUM(EjecucionesActivas) AS TotalEjecucionesActivas
    FROM dbo.EstadoBalanceadorTiempoReal
"""
```

**Estado:** ✅ **CORREGIDO** - Ahora retorna un resumen completo y útil

---

### 3.2 ✅ Sin Problemas: Manejo de Parámetros NULL

**Ubicación:** `src/sam/web/backend/database.py:995-1053`

**Estado:** ✅ **CORRECTO**

El código filtra correctamente los parámetros `None` antes de pasarlos al SP:
```python
if value is not None:
    param_placeholders.append(f"@{key} = ?")
```

Esto permite que los SPs usen sus valores por defecto cuando no se proporcionan parámetros.

---

### 3.3 ✅ Sin Problemas: Conversión de Tipos

**Estado:** ✅ **CORRECTO**

El código convierte correctamente `bool` a `int` para parámetros `BIT`:
```python
if isinstance(value, bool):
    param_values.append(1 if value else 0)
```

---

## 4. Verificación de Campos en Frontend

### 4.1 CallbacksDashboard

**Campos Usados:**
- ✅ `metricas_generales.PorcentajeCallbackExitoso`
- ✅ `metricas_generales.LatenciaPromedioMinutos`
- ✅ `metricas_generales.PorcentajeExito`
- ✅ `tendencia_diaria[].Fecha`
- ✅ `tendencia_diaria[].CallbacksExitosos`
- ✅ `tendencia_diaria[].ConciliadorExitosos`
- ✅ `tendencia_diaria[].LatenciaPromedioMinutos`

**Estado:** ✅ Todos los campos coinciden con los devueltos por el SP

---

### 4.2 BalanceadorDashboard

**Campos Usados:**
- ✅ `resumen_diario[].Fecha`
- ✅ `resumen_diario[].Asignaciones`
- ✅ `resumen_diario[].Desasignaciones`
- ✅ `analisis_robots[].RobotNombre`
- ✅ `analisis_robots[].TotalAcciones`

**Estado:** ✅ Todos los campos coinciden con los devueltos por el SP

---

## 5. Recomendaciones

### 5.1 Alta Prioridad

1. **Ninguna** - Los SPs están correctamente implementados

### 5.2 Media Prioridad

1. **Mejorar `get_system_status` para `EstadoBalanceadorTiempoReal`:**
   - Agregar resumen agregado en lugar de tomar solo `[0]`
   - O retornar todos los robots y mostrar un resumen en el frontend

### 5.3 Baja Prioridad

1. **Agregar validación de fechas:**
   - Verificar que `fecha_inicio < fecha_fin` en los endpoints
   - Agregar límites razonables (ej: máximo 1 año de diferencia)

2. **Agregar índices si es necesario:**
   - Verificar rendimiento de los SPs con grandes volúmenes de datos
   - Considerar índices en `FechaInicio`, `FechaBalanceo`, `RobotId`

---

## 6. Conclusión

✅ **Los SPs son correctos, usables y se ajustan a la realidad del sistema.**

**Puntos Fuertes:**
- ✅ Todos los SPs existen y están correctamente definidos
- ✅ Las vistas y tablas dependientes existen
- ✅ Los parámetros se pasan correctamente
- ✅ Los campos esperados en el frontend coinciden con los devueltos por los SPs
- ✅ El manejo de errores está implementado en los SPs

**Mejoras Sugeridas:**
- ⚠️ Mejorar el manejo de `EstadoBalanceadorTiempoReal` para mostrar un resumen completo
- 💡 Agregar validaciones de fechas en los endpoints
- 💡 Considerar índices para mejorar rendimiento

---

## 7. Pruebas Recomendadas

1. ✅ Ejecutar los SPs directamente en SQL Server Management Studio
2. ✅ Verificar que retornan los result sets esperados
3. ✅ Probar con diferentes rangos de fechas
4. ✅ Probar con `NULL` en todos los parámetros opcionales
5. ✅ Verificar que los campos del frontend se muestran correctamente

---

**Revisado por:** Sistema de Análisis Automático  
**Última actualización:** 2025-01-XX

