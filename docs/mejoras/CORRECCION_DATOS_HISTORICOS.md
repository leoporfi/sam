# Corrección: Inclusión de Datos Históricos en Analítica

**Fecha:** 2025-01-XX  
**Problema identificado:** Las vistas y SPs de analítica solo consultan `Ejecuciones`, no incluyen `Ejecuciones_Historico`

---

## 🔍 Problema Identificado

### Contexto
- La tabla `Ejecuciones` tiene un límite de capacidad
- Los datos antiguos se mueven diariamente a `Ejecuciones_Historico` a las 5am
- El SP `dbo.usp_MoverEjecucionesAHistorico` realiza el mantenimiento:
  - Mueve ejecuciones con más de 1 día de antigüedad (por defecto)
  - Purgar datos históricos con más de 15 días (por defecto)

### Impacto en Analítica
1. **Vista `AnalisisRendimientoCallbacks`**: Solo consulta `Ejecuciones`
   - Limita el análisis a datos recientes (últimos ~30 días o menos)
   - No incluye datos históricos más antiguos

2. **SP `dbo.ObtenerDashboardCallbacks`**: Usa la vista limitada
   - Los filtros de fecha pueden no encontrar datos si están en histórico
   - Inconsistencia en rangos de fechas

3. **Vista `EjecucionesActivas`**: Solo consulta `Ejecuciones` (correcto, solo activas)

---

## ✅ Solución Propuesta

### 1. Modificar Vista `AnalisisRendimientoCallbacks`

**Cambio necesario:** Incluir UNION ALL con `Ejecuciones_Historico`

```sql
WITH EjecucionesAnalizadas AS (
    -- Datos actuales
    SELECT ... FROM Ejecuciones
    WHERE FechaInicio >= DATEADD(DAY, -30, GETDATE())
    
    UNION ALL
    
    -- Datos históricos
    SELECT ... FROM Ejecuciones_Historico
    WHERE FechaInicio >= DATEADD(DAY, -30, GETDATE())
)
```

**Consideraciones:**
- Mantener el filtro de 30 días para performance
- Agregar campo `Origen` ('ACTUAL' o 'HISTORICA') para transparencia
- Asegurar que ambas tablas tengan la misma estructura

### 2. Agregar Información en Dashboards

**En frontend:**
- Mostrar claramente el rango de datos disponible
- Indicar si se están mostrando datos históricos
- Advertir sobre límites de retención (15 días por defecto)

### 3. Documentar en Descripciones

**Agregar texto explicativo:**
- "Los datos incluyen ejecuciones de las últimas 24 horas en tabla actual y datos históricos hasta 15 días"
- "El mantenimiento diario mueve datos antiguos a las 5am"

---

## 📋 Checklist de Corrección

- [ ] Modificar vista `AnalisisRendimientoCallbacks` para incluir histórico
- [ ] Verificar que el SP `dbo.ObtenerDashboardCallbacks` funcione correctamente
- [ ] Agregar información de rango de datos en `CallbacksDashboard`
- [ ] Agregar información de rango de datos en otros dashboards si aplica
- [ ] Actualizar documentación
- [ ] Probar con datos reales

---

## 🔗 Referencias

- SP de mantenimiento: `database/procedures/dbo_usp_MoverEjecucionesAHistorico.sql`
- Ejemplo de unificación: `database/procedures/dbo_usp_AnalizarLatenciaEjecuciones.sql`
- Vista actual: `database/views/dbo_AnalisisRendimientoCallbacks.sql`

