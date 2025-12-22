# Reporte de Auditoría - Estandarización ReactPy

**Fecha:** 2024-12-19  
**Rama:** `feat/estandarizacion-reactpy`  
**Fase:** 1 - Análisis y Preparación

---

## Resumen Ejecutivo

Este documento detalla todas las desviaciones encontradas del estándar definido en `docs/estándar específico para el servicio web de ReactPy.json` y de la guía general de desarrollo de SAM.

**Total de archivos auditados:** 11 componentes, 6 hooks, 4 archivos compartidos

---

## 1. Auditoría de Nomenclatura

### 1.1 Archivos que Necesitan Renombrarse

| Archivo Actual | Nombre Propuesto | Razón | Prioridad |
|----------------|------------------|-------|-----------|
| `robots_components.py` | `robot_list.py` | Debe usar singular y separar responsabilidades | Alta |
| `equipos_components.py` | `equipo_list.py` | Debe usar singular | Alta |
| `pools_components.py` | `pool_list.py` | Debe usar singular | Alta |
| `schedules_components.py` | `schedule_list.py` | Debe usar singular | Alta |
| `mappings_page.py` | `mapping_list.py` o mantener como página | Evaluar si es página completa o componente | Media |

**Total de archivos a renombrar:** 4-5 archivos

### 1.2 Archivos con Nomenclatura Correcta

- ✅ `use_robots_hook.py` - Sigue convención `use_*`
- ✅ `use_equipos_hook.py` - Sigue convención `use_*`
- ✅ `use_pools_hook.py` - Sigue convención `use_*`
- ✅ `use_schedules_hook.py` - Sigue convención `use_*`
- ✅ `use_debounced_value_hook.py` - Sigue convención `use_*`
- ✅ `common_components.py` - snake_case correcto

### 1.3 Archivos Duplicados a Eliminar

- ❌ `use_schedules_hook copy.py` - Archivo duplicado, debe eliminarse

---

## 2. Auditoría de Componentes

### 2.1 Type Hints

#### ✅ Componentes con Type Hints Completos

- `RobotsControls` - ✅ Tiene type hints en todas las props
- `RobotsDashboard` - ✅ Tiene type hints
- `RobotTable` - ✅ Tiene type hints
- `RobotRow` - ✅ Tiene type hints
- `EquiposControls` - ✅ Tiene type hints
- `PoolsControls` - ✅ Tiene type hints
- `SchedulesControls` - ✅ Tiene type hints

#### ⚠️ Componentes con Type Hints Parciales

- Algunos componentes usan `Callable` sin especificar firma completa
- Algunos usan `Dict` sin especificar tipos de keys/values

**Recomendación:** Mejorar type hints usando `Callable[[ParamTypes], ReturnType]` y `Dict[str, Any]` explícitamente.

### 2.2 Props Explícitas

✅ **Todos los componentes usan props explícitas** - No se encontró uso de `**kwargs` en componentes.

### 2.3 Separación de Lógica y Presentación

#### ✅ Componentes Bien Separados

- `RobotsControls` - Solo presentación
- `RobotTable` - Solo presentación
- `RobotRow` - Solo presentación con handlers simples

#### ⚠️ Componentes con Lógica Mezclada

- `RobotsDashboard` - Tiene lógica de renderizado condicional (loading, error) que debería usar `AsyncContent`
- `PoolsDashboard` - Similar, maneja estados de carga manualmente

**Recomendación:** Extraer lógica de estados async a componente `AsyncContent`.

### 2.4 Keys en Listas

#### ✅ Uso Correcto de Keys

- `RobotRow` - ✅ Usa `{"key": robot["RobotId"]}` (línea 214)
- `schedules_components.py` - ✅ Usa `key=s["ProgramacionId"]` (línea 131)

#### ⚠️ Posibles Problemas

- `RobotCard` en list comprehension (línea 125 de `robots_components.py`):
  ```python
  *[RobotCard(robot=robot, on_action=on_action) for robot in robots]
  ```
  **Problema:** No se ve key explícita en el componente `RobotCard`. Necesita verificación.

**Recomendación:** Auditar todos los componentes de lista para asegurar keys únicas.

---

## 3. Auditoría de Hooks

### 3.1 Type Hints en Hooks

#### ⚠️ Hooks sin Type Hints Completos

| Hook | Type Hints Parámetros | Type Hints Retorno | Estado |
|------|----------------------|-------------------|--------|
| `use_robots()` | ❌ No tiene parámetros | ❌ No especifica tipo de retorno | ⚠️ Incompleto |
| `use_equipos()` | ❌ No tiene parámetros | ❌ No especifica tipo de retorno | ⚠️ Incompleto |
| `use_pools_management()` | ❌ No tiene parámetros | ❌ No especifica tipo de retorno | ⚠️ Incompleto |
| `use_schedules()` | ❌ No tiene parámetros | ❌ No especifica tipo de retorno | ⚠️ Incompleto |
| `use_debounced_value()` | ✅ Tiene type hints | ❌ No especifica tipo de retorno | ⚠️ Parcial |

**Recomendación:** Agregar type hints completos:
```python
def use_robots(api_client: Optional[APIClient] = None) -> Dict[str, Any]:
    ...
```

### 3.2 Inyección de Dependencias

#### ❌ Problema Crítico: Uso de Singleton

**Todos los hooks usan `get_api_client()` que es un singleton:**

- `use_robots_hook.py` línea 21: `api_client = get_api_client()`
- `use_equipos_hook.py` - Similar
- `use_pools_hook.py` - Similar
- `use_schedules_hook.py` - Similar

**Problema:** Esto viola el principio de Inyección de Dependencias de la Guía General de SAM.

**Solución Requerida:**
1. Eliminar singleton de `api_client`
2. Inyectar `api_client` a través del contexto de ReactPy
3. Permitir inyección opcional en hooks para testing:
   ```python
   def use_robots(api_client: Optional[APIClient] = None) -> Dict[str, Any]:
       client = api_client or use_app_context()["api_client"]
   ```

### 3.3 Estructura de Retorno

#### ✅ Hooks con Estructura Consistente

Los hooks retornan diccionarios con keys consistentes:
- `robots` / `equipos` / `pools` / `schedules`
- `loading`
- `error`
- `refresh` / `refetch`

**Estado:** ✅ Bueno, pero necesita documentación explícita de tipo de retorno.

### 3.4 Manejo de Errores

#### ✅ Manejo de Errores Presente

- Todos los hooks tienen `try/except` blocks
- Usan `show_notification` para errores de usuario
- Manejan `asyncio.CancelledError` correctamente

**Mejora Sugerida:** Usar excepciones personalizadas (`APIError`) en lugar de strings genéricas.

---

## 4. Auditoría de Estructura

### 4.1 Componentes Base Faltantes

| Componente | Estado | Ubicación Esperada | Prioridad |
|------------|--------|-------------------|-----------|
| `DataTable` genérica | ❌ NO EXISTE | `frontend/shared/data_table.py` | Alta |
| `AsyncContent` | ❌ NO EXISTE | `frontend/shared/async_content.py` | Alta |
| `LoadingSpinner` | ✅ EXISTE | `frontend/shared/common_components.py` | - |
| `ErrorAlert` | ❌ NO EXISTE | Debe crearse en `async_content.py` | Alta |
| `EmptyState` | ❌ NO EXISTE | Debe crearse en `async_content.py` | Alta |

### 4.2 Sistema de Estilos

| Archivo | Estado | Prioridad |
|---------|--------|-----------|
| `frontend/shared/styles.py` | ❌ NO EXISTE | Alta |

**Problema:** No hay constantes centralizadas para clases CSS. Cada componente define sus propias clases.

**Impacto:** Inconsistencia visual, difícil mantenimiento.

### 4.3 Contexto Global

| Componente | Estado | Ubicación Actual | Ubicación Esperada |
|------------|--------|------------------|-------------------|
| `NotificationContext` | ✅ EXISTE | `frontend/shared/notifications.py` | ✅ Correcto |
| `AppContext` | ❌ NO EXISTE | - | `frontend/state/app_context.py` |

**Problema:** No hay contexto global para `api_client` y otras dependencias compartidas.

### 4.4 Cliente API

| Aspecto | Estado Actual | Estado Esperado |
|---------|---------------|-----------------|
| Nombre de clase | `ApiClient` | `APIClient` (PascalCase completo) |
| Patrón | Singleton | Instancias múltiples permitidas |
| Inyección | ❌ No permite | ✅ Debe permitir DI |
| Type hints | ⚠️ Parciales | ✅ Completos |

---

## 5. Auditoría de Funciones Puras

### 5.1 Funciones Puras Identificadas

✅ **No se encontraron funciones puras explícitas** - La lógica de transformación está mezclada en componentes y hooks.

**Recomendación:** Extraer funciones puras para:
- Filtrado de datos (ej: `filter_robots_by_pool(robots, pool) -> List[dict]`)
- Transformación de datos
- Validación de datos

**Beneficio:** Facilitar testing unitario sin dependencias de I/O.

---

## 6. Resumen de Problemas por Prioridad

### 🔴 Alta Prioridad (Bloqueantes)

1. **Inyección de Dependencias:** Todos los hooks usan singleton de `api_client`
2. **Componentes Base Faltantes:** `DataTable`, `AsyncContent`, `ErrorAlert`, `EmptyState`
3. **Sistema de Estilos:** Falta `styles.py` con constantes centralizadas
4. **Contexto Global:** Falta `AppContext` para inyección de dependencias
5. **Type Hints en Hooks:** Falta especificar tipos de retorno

### 🟡 Media Prioridad (Importantes)

1. **Renombrado de Archivos:** 4-5 archivos necesitan renombrarse
2. **Mejora de Type Hints:** Especificar tipos completos en `Callable` y `Dict`
3. **Extracción de Funciones Puras:** Para facilitar testing
4. **Verificación de Keys:** Asegurar keys en todas las listas renderizadas

### 🟢 Baja Prioridad (Mejoras)

1. **Eliminación de Duplicados:** `use_schedules_hook copy.py`
2. **Documentación:** Mejorar docstrings en hooks
3. **Optimización:** Aplicar `use_memo` donde sea necesario

---

## 7. Métricas

- **Total de archivos a modificar:** ~15-20 archivos
- **Total de archivos a crear:** 5 archivos nuevos
- **Total de archivos a eliminar:** 1 archivo duplicado
- **Total de archivos a renombrar:** 4-5 archivos

---

## 8. Próximos Pasos

1. ✅ Crear documento de mapeo de cambios (`migration_mapping.md`)
2. ⏭️ Comenzar Fase 2: Crear infraestructura base
3. ⏭️ Refactorizar hooks para aplicar DI
4. ⏭️ Crear componentes base faltantes

---

**Última actualización:** 2024-12-19  
**Próxima revisión:** Al completar Fase 1
