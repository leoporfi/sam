# Análisis de Esfuerzo: Refactor "Online" → "Ciclico"

## Resumen Ejecutivo

El refactor implica cambiar la terminología que describe robots de ejecución cíclica de **"Online"** a **"Ciclico"** en todo el proyecto SAM.

**Impacto Total:**
- **129+ referencias** identificadas en el proyecto
- **~3-5 días** de esfuerzo estimado (con testing completo)
- **Riesgo**: Medio-Alto (cambios en BD requieren migración y puede afectar servicios)

---

## Mapeo de Cambios Propuesto

| Actual | Nuevo |
|--------|-------|
| `EsOnline` | `EsCiclico` |
| `RobotsOnline` | `RobotsCiclicos` |
| `RobotsActivosOnline` | `RobotActivosCiclicos` |
| `AsignarRobotOnline` (SP) | `AsignarRobotCiclico` |
| "Online" (UI/docs) | "Cíclico" |
| "Programados" (UI/docs) | "Programados" (sin cambio) |

---

## Desglose por Componente

### 1. Base de Datos (Alto Impacto) 
**Esfuerzo: 1-2 días** | **Riesgo: Alto**

#### 1.1 Tabla `dbo.Robots`
- **Columna**: `EsOnline` → `EsCiclico`
- **Índice**: `IX_Robots_Activo_EsOnline` → `IX_Robots_Activo_EsCiclico`
- **Archivo**: [dbo_Robots.sql](file:///c:/Users/lporfiri/RPA/sam/database/tables/dbo_Robots.sql)

#### 1.2 Stored Procedures (12 archivos)
1. [dbo_AsignarRobotOnline.sql](file:///c:/Users/lporfiri/RPA/sam/database/procedures/dbo_AsignarRobotOnline.sql) → Renombrar y actualizar
2. [dbo_ObtenerDashboardBalanceador.sql](file:///c:/Users/lporfiri/RPA/sam/database/procedures/dbo_ObtenerDashboardBalanceador.sql)
3. [dbo_ObtenerRobotsDetalle.sql](file:///c:/Users/lporfiri/RPA/sam/database/procedures/dbo_ObtenerRobotsDetalle.sql)
4. [dbo_ObtenerRobotsEjecutables.sql](file:///c:/Users/lporfiri/RPA/sam/database/procedures/dbo_ObtenerRobotsEjecutables.sql)
5. [dbo_CrearProgramacion.sql](file:///c:/Users/lporfiri/RPA/sam/database/procedures/dbo_CrearProgramacion.sql)
6. [dbo_CargarProgramacionDiaria.sql](file:///c:/Users/lporfiri/RPA/sam/database/procedures/dbo_CargarProgramacionDiaria.sql)
7. [dbo_CargarProgramacionSemanal.sql](file:///c:/Users/lporfiri/RPA/sam/database/procedures/dbo_CargarProgramacionSemanal.sql)
8. [dbo_CargarProgramacionMensual.sql](file:///c:/Users/lporfiri/RPA/sam/database/procedures/dbo_CargarProgramacionMensual.sql)
9. [dbo_CargarProgramacionEspecifica.sql](file:///c:/Users/lporfiri/RPA/sam/database/procedures/dbo_CargarProgramacionEspecifica.sql)
10. [dbo_CargarProgramacionRangoMensual.sql](file:///c:/Users/lporfiri/RPA/sam/database/procedures/dbo_CargarProgramacionRangoMensual.sql)
11. [dbo_AnalisisTiemposEjecucionRobots.sql](file:///c:/Users/lporfiri/RPA/sam/database/procedures/dbo_AnalisisTiemposEjecucionRobots.sql)

**Cambios típicos**:
```sql
-- ANTES
UPDATE dbo.Robots SET EsOnline = 0 WHERE RobotId = @RobotId;
SELECT COUNT(*) FROM Robots WHERE EsOnline = 1;
@EsOnline NVARCHAR(5) = 'todos'

-- DESPUÉS
UPDATE dbo.Robots SET EsCiclico = 0 WHERE RobotId = @RobotId;
SELECT COUNT(*) FROM Robots WHERE EsCiclico = 1;
@EsCiclico NVARCHAR(5) = 'todos'
```

#### 1.3 Vistas (3 archivos)
1. [dbo_EjecucionesActivas.sql](file:///c:/Users/lporfiri/RPA/sam/database/views/dbo_EjecucionesActivas.sql)
2. [dbo_EjecucionesFinalizadas.sql](file:///c:/Users/lporfiri/RPA/sam/database/views/dbo_EjecucionesFinalizadas.sql)
3. [dbo_EstadoBalanceadorTiempoReal.sql](file:///c:/Users/lporfiri/RPA/sam/database/views/dbo_EstadoBalanceadorTiempoReal.sql)

**Cambios típicos**:
```sql
-- ANTES
CASE WHEN (r.EsOnline = 1) THEN 'ONLINE' ELSE 'PROGRAMADO' END AS Tipo

-- DESPUÉS
CASE WHEN (r.EsCiclico = 1) THEN 'CICLICO' ELSE 'PROGRAMADO' END AS Tipo
```

#### 1.4 Migración Requerida
Crear script de migración:
```sql
-- Renombrar columna
EXEC sp_rename 'dbo.Robots.EsOnline', 'EsCiclico', 'COLUMN';

-- Renombrar índice
EXEC sp_rename 'IX_Robots_Activo_EsOnline', 'IX_Robots_Activo_EsCiclico', 'INDEX';

-- Renombrar SP
EXEC sp_rename 'dbo.AsignarRobotOnline', 'dbo.AsignarRobotCiclico';
```

---

### 2. Backend Python (8 archivos)
**Esfuerzo: 1 día** | **Riesgo: Medio**

#### 2.1 Core Backend (4 archivos)
1. [database.py](file:///c:/Users/lporfiri/RPA/sam/src/sam/web/backend/database.py) - **18 referencias**
   - Mapeo de columnas
   - Queries SQL embebidas
   - Lógica de validación
   
2. [api.py](file:///c:/Users/lporfiri/RPA/sam/src/sam/web/backend/api.py) - **1 referencia**
   - Validación de campos permitidos

3. [schemas.py](file:///c:/Users/lporfiri/RPA/sam/src/sam/web/backend/schemas.py) - **2 referencias**
   - Modelos Pydantic

#### 2.2 Servicio Balanceador (2 archivos)
1. [algoritmo_balanceo.py](file:///c:/Users/lporfiri/RPA/sam/src/sam/balanceador/service/algoritmo_balanceo.py) - **3 referencias**
2. [proveedores.py](file:///c:/Users/lporfiri/RPA/sam/src/sam/balanceador/service/proveedores.py) - **5 referencias**

**Cambios típicos**:
```python
# ANTES
"EsOnline": "r.EsOnline"
if field == "EsOnline" and value is True:
robot_config.get("EsOnline")

# DESPUÉS
"EsCiclico": "r.EsCiclico"
if field == "EsCiclico" and value is True:
robot_config.get("EsCiclico")
```

---

### 3. Frontend ReactPy (4 archivos)
**Esfuerzo: 1 día** | **Riesgo: Bajo-Medio**

#### 3.1 Componentes (4 archivos)
1. [robot_list.py](file:///c:/Users/lporfiri/RPA/sam/src/sam/web/frontend/features/components/robot_list.py) - **13 referencias**
   - Etiquetas de tabla
   - Checkboxes
   - Tooltips
   
2. [status_dashboard.py](file:///c:/Users/lporfiri/RPA/sam/src/sam/web/frontend/features/components/analytics/status_dashboard.py) - **2 referencias**
   - Métricas de dashboard

3. [balanceador_dashboard.py](file:///c:/Users/lporfiri/RPA/sam/src/sam/web/frontend/features/components/analytics/balanceador_dashboard.py) - **2 referencias**

4. [app.py](file:///c:/Users/lporfiri/RPA/sam/src/sam/web/frontend/app.py) - **5 referencias**
   - Lógica de filtros

#### 3.2 Utilities & Modals (2 archivos)
1. [filtering.py](file:///c:/Users/lporfiri/RPA/sam/src/sam/web/frontend/utils/filtering.py) - **1 referencia**
2. [robots_modals.py](file:///c:/Users/lporfiri/RPA/sam/src/sam/web/frontend/features/modals/robots_modals.py) - **1 referencia**

**Cambios típicos**:
```python
# ANTES
html.option({"value": "true"}, "Solo Online")
{"key": "EsOnline", "label": "Online"}
"title": "No se puede marcar como Online si tiene programaciones"

# DESPUÉS
html.option({"value": "true"}, "Solo Cíclicos")
{"key": "EsCiclico", "label": "Cíclico"}
"title": "No se puede marcar como Cíclico si tiene programaciones"
```

---

### 4. Documentación (3 archivos)
**Esfuerzo: 0.5 días** | **Riesgo: Bajo**

1. [servicio_web.md](file:///c:/Users/lporfiri/RPA/sam/docs/servicios/servicio_web.md) - **16 referencias**
2. [README_ROBOTS_CICLICOS.md](file:///c:/Users/lporfiri/RPA/sam/docs/robots-ciclicos/README_ROBOTS_CICLICOS.md) - **3 referencias**
3. [Documentación del Modelo de Datos y Reglas de Negocio.md](file:///c:/Users/lporfiri/RPA/sam/docs/arquitectura/Documentación del Modelo de Datos y Reglas de Negocio.md) - **2 referencias**
4. [VERIFICACION_CAMBIOS.md](file:///c:/Users/lporfiri/RPA/sam/docs/robots-ciclicos/referencia/VERIFICACION_CAMBIOS.md) - **2 referencias**

**Cambios típicos**:
```markdown
<!-- ANTES -->
- Robots **Online** (`EsOnline = 1`): Se ejecutan cíclicamente
- **"Solo Online"**: Muestra solo robots con `EsOnline=1`

<!-- DESPUÉS -->
- Robots **Cíclicos** (`EsCiclico = 1`): Se ejecutan cíclicamente
- **"Solo Cíclicos"**: Muestra solo robots con `EsCiclico=1`
```

---

### 5. Migraciones (2 archivos)
**Esfuerzo: 0.5 días** | **Riesgo: Bajo**

1. [FIX_COMPLETO_CrearProgramacion.sql](file:///c:/Users/lporfiri/RPA/sam/migrations/robots-ciclicos/sql/FIX_COMPLETO_CrearProgramacion.sql)
2. [update_stored_procedures_ciclicos.sql](file:///c:/Users/lporfiri/RPA/sam/migrations/robots-ciclicos/sql/update_stored_procedures_ciclicos.sql)

> **Nota**: Estos archivos ya contienen lógica relacionada con robots cíclicos, sería coherente actualizarlos.

---

## Estimación de Esfuerzo

| Fase | Componente | Archivos | Esfuerzo | Riesgo | Reversible |
|------|-----------|----------|----------|--------|-----------|
| **1** | **Base de Datos** | 16 | 1-2 días | ⚠️ Alto | ❌ No |
| | Migración de columnas/índices | 1 | 2-4 horas | ⚠️ Alto | ❌ No |
| | Stored Procedures | 12 | 6-8 horas | ⚠️ Medio | ✅ Sí |
| | Vistas | 3 | 1-2 horas | ⚠️ Bajo | ✅ Sí |
| **2** | **Backend Python** | 8 | 1 día | ⚠️ Medio | ✅ Sí |
| | Core Backend | 3 | 4-5 horas | ⚠️ Medio | ✅ Sí |
| | Balanceador | 2 | 2-3 horas | ⚠️ Medio | ✅ Sí |
| | Schemas | 1 | 1 hora | ⚠️ Bajo | ✅ Sí |
| **3** | **Frontend ReactPy** | 6 | 1 día | ⚠️ Bajo-Medio | ✅ Sí |
| | Componentes | 4 | 4-6 horas | ⚠️ Medio | ✅ Sí |
| | Utils/Modals | 2 | 1-2 horas | ⚠️ Bajo | ✅ Sí |
| **4** | **Documentación** | 4 | 0.5 días | ⚠️ Bajo | ✅ Sí |
| **5** | **Testing & QA** | - | 1-2 días | ⚠️ Alto | - |
| | Testing manual completo | - | 1 día | ⚠️ Alto | - |
| | Validación en dev/staging | - | 0.5-1 día | ⚠️ Medio | - |
| **TOTAL** | | **34+** | **5-7 días** | ⚠️ Medio-Alto | - |

---

## Consideraciones Críticas

### ⚠️ Riesgos Principales

1. **Migración de Base de Datos**
   - `sp_rename` de columnas requiere **downtime** o manejo cuidadoso
   - Indices y constraints podrían tener dependencias ocultas
   - **Rollback complejo** si falla

2. **Compatibilidad Backward**
   - Si hay servicios externos consultando `EsOnline`, se romperán
   - Posibles queries ad-hoc o reportes externos afectados

3. **Testing Exhaustivo Requerido**
   - Validar TODOS los flujos:
     - Creación de robots
     - Asignación de programaciones
     - Balanceador (algoritmo usa `EsOnline`)
     - Dashboards analíticos
     - Filtros en UI

### ✅ Beneficios

1. **Claridad Conceptual**
   - Terminología más descriptiva del comportamiento real
   - Mejor experiencia de usuario (menos confusión)
   - Código más auto-documentado

2. **Coherencia**
   - Archivos de migración ya hablan de "robots-ciclicos"
   - Alinearía código con la documentación existente

---

## Estrategia de Implementación Recomendada

### Opción 1: Migración Completa (Recomendada)
**Pros**: Limpia, sin deuda técnica  
**Cons**: Alto esfuerzo, riesgo de downtime

**Fases**:
1. Crear rama `refactor/ciclico-nomenclature`
2. Desarrollo + testing en entorno local (3-4 días)
3. Deploy en staging + validación (1 día)
4. Ventana de mantenimiento para producción (0.5 días)

### Opción 2: Alias de Compatibilidad
**Pros**: Menor riesgo, migración gradual  
**Cons**: Deuda técnica temporal

**Estrategia**:
1. Agregar columna `EsCiclico` en BD (sin eliminar `EsOnline`)
2. Trigger/view para mantener ambas sincronizadas
3. Migrar código gradualmente
4. Deprecar `EsOnline` después de 6 meses

### Opción 3: Solo UI/Docs (Rápida)
**Pros**: Mínimo riesgo, cambio inmediato  
**Cons**: Inconsistencia código/UI

**Cambios**:
- Solo labels de frontend ("Online" → "Cíclico")
- Actualizar documentación
- Backend/BD sin cambios (variables siguen siendo `EsOnline`)

---

## Recomendación Final

### 💡 Mi Recomendación: **Opción 3 (Solo UI/Docs) + Plan futuro para Opción 1**

**Razones**:
1. **Impacto inmediato**: Usuario ve "Cíclico" hoy (mejora UX)
2. **Bajo riesgo**: Sin tocar BD ni lógica crítica
3. **Reversible**: Cambios son solo texto
4. **Planificar bien**: Usar próxima ventana de mantenimiento mayor para Opción 1

**Esfuerzo Opción 3**: **4-6 horas** (vs 5-7 días de Opción 1)

### 📋 Próximos Pasos Sugeridos

1. ¿Aprobar Opción 3 (cambios solo en UI/docs)?
2. Si sí → Implemento hoy
3. Si quieres Opción 1 completa → Crear plan detallado con ventana de mantenimiento

---

## Listado Completo de Archivos Afectados

<details>
<summary><strong>Backend Python (8 archivos)</strong></summary>

1. `src/sam/web/frontend/app.py`
2. `src/sam/web/frontend/utils/filtering.py`
3. `src/sam/web/frontend/features/components/analytics/balanceador_dashboard.py`
4. `src/sam/web/backend/api.py`
5. `src/sam/web/frontend/features/modals/robots_modals.py`
6. `src/sam/web/backend/database.py`
7. `src/sam/web/backend/schemas.py`
8. `src/sam/web/frontend/features/components/robot_list.py`
9. `src/sam/web/frontend/features/components/analytics/status_dashboard.py`
10. `src/sam/balanceador/service/algoritmo_balanceo.py`
11. `src/sam/balanceador/service/proveedores.py`
</details>

<details>
<summary><strong>SQL (18 archivos)</strong></summary>

**Tablas**:
1. `database/tables/dbo_Robots.sql`

**Stored Procedures**:
2. `database/procedures/dbo_AsignarRobotOnline.sql`
3. `database/procedures/dbo_CargarProgramacionDiaria.sql`
4. `database/procedures/dbo_CargarProgramacionMensual.sql`
5. `database/procedures/dbo_CargarProgramacionEspecifica.sql`
6. `database/procedures/dbo_CargarProgramacionRangoMensual.sql`
7. `database/procedures/dbo_CargarProgramacionSemanal.sql`
8. `database/procedures/dbo_CrearProgramacion.sql`
9. `database/procedures/dbo_ObtenerDashboardBalanceador.sql`
10. `database/procedures/dbo_ObtenerRobotsDetalle.sql`
11. `database/procedures/dbo_ObtenerRobotsEjecutables.sql`
12. `database/procedures/dbo_AnalisisTiemposEjecucionRobots.sql`

**Vistas**:
13. `database/views/dbo_EjecucionesActivas.sql`
14. `database/views/dbo_EjecucionesFinalizadas.sql`
15. `database/views/dbo_EstadoBalanceadorTiempoReal.sql`

**Migraciones**:
16. `migrations/robots-ciclicos/sql/FIX_COMPLETO_CrearProgramacion.sql`
17. `migrations/robots-ciclicos/sql/update_stored_procedures_ciclicos.sql`
</details>

<details>
<summary><strong>Documentación (4 archivos)</strong></summary>

1. `docs/servicios/servicio_web.md`
2. `docs/robots-ciclicos/README_ROBOTS_CICLICOS.md`
3. `docs/arquitectura/Documentación del Modelo de Datos y Reglas de Negocio.md`
4. `docs/robots-ciclicos/referencia/VERIFICACION_CAMBIOS.md`
</details>

**Total**: **34 archivos** | **129+ referencias**
