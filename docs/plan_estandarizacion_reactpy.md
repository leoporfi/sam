# Plan de Estandarización - Servicio Web ReactPy

## Resumen Ejecutivo

Este documento detalla el plan por fases para estandarizar el código del servicio web de SAM siguiendo el estándar definido en `docs/estándar específico para el servicio web de ReactPy.json`.

**⚠️ IMPORTANTE - Alineación con Guía General de SAM:**

Este plan **mantiene y respeta** los principios definidos en `docs/Guia de Arquitectura y Desarrollo.json`:

- ✅ **Inyección de Dependencias (DI)**: Los componentes y hooks permitirán inyección de dependencias (ej. `api_client`) a través del contexto de ReactPy para facilitar testing y mantener consistencia con el backend.
- ✅ **Separación de Responsabilidades**: Los componentes se enfocan en presentación, los hooks en lógica de estado, y las funciones puras en transformaciones de datos.
- ✅ **Nomenclatura Consistente**: Se respetan las convenciones de Python (PEP 8) y se mantiene consistencia con el resto del proyecto.
- ✅ **Estructura de Servicios**: El frontend respeta la estructura del servicio web (`src/sam/web/`) y se integra correctamente con el backend que sigue DI.
- ✅ **Preparación para Testing**: El código estará preparado para testing unitario siguiendo los mismos principios del backend (inyección de dependencias, funciones puras).

**Estado Actual:**
- ✅ Estructura básica de directorios existente
- ✅ Hooks personalizados implementados
- ✅ Componentes compartidos básicos
- ✅ Cliente API funcional
- ⚠️ Nomenclatura inconsistente (archivos en plural)
- ⚠️ Falta componentes base genéricos (DataTable, AsyncContent)
- ⚠️ Falta estilos centralizados
- ⚠️ Falta contexto global de aplicación
- ⚠️ Type hints incompletos en algunos componentes
- ⚠️ `api_client` usa patrón singleton en lugar de DI

**Objetivo:** Alinear completamente el código con el estándar definido, mejorando mantenibilidad, reutilización y preparación para testing, **manteniendo consistencia con la guía general de desarrollo de SAM**.

---

## FASE 1: Análisis y Preparación (1 día)

### Objetivos
- Auditar el código actual
- Identificar todas las desviaciones del estándar
- Crear checklist detallado de cambios

### Tareas

#### 1.1 Auditoría de Nomenclatura
- [ ] Listar todos los archivos en `features/components/` que necesitan renombrarse
  - `robots_components.py` → `robot_list.py` (o separar en múltiples archivos)
  - `equipos_components.py` → `equipo_list.py`
  - `pools_components.py` → `pool_list.py`
  - `schedules_components.py` → `schedule_list.py`
  - `mappings_page.py` → `mapping_list.py` (o mantener como página completa)

#### 1.2 Auditoría de Componentes
- [ ] Revisar cada componente para identificar:
  - Props sin type hints
  - Uso de `**kwargs` en lugar de props explícitas
  - Lógica mezclada con presentación
  - Falta de keys en listas renderizadas

#### 1.3 Auditoría de Hooks
- [ ] Revisar todos los hooks en `hooks/`:
  - Type hints completos en parámetros y retorno
  - Separación correcta de lógica
  - Manejo de errores consistente

#### 1.4 Auditoría de Estructura
- [ ] Verificar existencia de:
  - `frontend/shared/styles.py` (NO existe)
  - `frontend/shared/data_table.py` (NO existe)
  - `frontend/shared/async_content.py` (NO existe)
  - `frontend/state/app_context.py` (NO existe)

#### 1.5 Crear Documento de Mapeo
- [ ] Crear `docs/migration_mapping.md` con:
  - Mapeo de nombres antiguos → nuevos
  - Lista de imports a actualizar
  - Componentes que se fusionarán/separarán

**Entregables:**
- `docs/audit_report.md` - Reporte completo de desviaciones
- `docs/migration_mapping.md` - Mapeo de cambios
- Checklist detallado por archivo

---

## FASE 2: Infraestructura Base (2 días)

### Objetivos
- Crear componentes base reutilizables
- Establecer sistema de estilos centralizado
- Configurar contexto global de aplicación

### Tareas

#### 2.1 Crear Sistema de Estilos Centralizado
- [ ] Crear `frontend/shared/styles.py`
  - Constantes para clases de botones (PRIMARY, DANGER, SECONDARY)
  - Constantes para estados (RUNNING, STOPPED, UNKNOWN, COOLING)
  - Constantes para layout (CARD, GRID, CONTAINER)
  - Documentar uso en docstrings

#### 2.2 Crear Componente DataTable Genérico
- [ ] Crear `frontend/shared/data_table.py`
  - Props: `data`, `columns`, `loading`, `on_row_click`, `actions`, `empty_message`
  - Soporte para renderizado personalizado por columna
  - Integración con estados de carga/error/vacío
  - Type hints completos
  - Documentación con ejemplos

#### 2.3 Crear Componente AsyncContent
- [ ] Crear `frontend/shared/async_content.py`
  - Componente `AsyncContent` wrapper
  - Componentes auxiliares: `LoadingSpinner`, `ErrorAlert`, `EmptyState`
  - Props personalizables para cada estado
  - Type hints completos

#### 2.4 Crear Contexto Global de Aplicación
- [ ] Crear `frontend/state/app_context.py`
  - `AppContext` usando `create_context`
  - `AppProvider` component
  - Hook `use_app_context()`
  - Incluir: usuario, notificaciones, **api_client (inyectado)**, configuraciones
  - **Aplicar principio de Inyección de Dependencias**: El `api_client` debe ser inyectado en el contexto, no ser un singleton global
  - Migrar lógica de `NotificationContext` si es necesario
  - **Alineación con Guía General**: Permitir inyección de dependencias para facilitar testing

#### 2.5 Actualizar Cliente API
- [ ] Refactorizar `frontend/api/api_client.py` según estándar:
  - Clase `APIClient` (renombrar de `ApiClient`)
  - Métodos `get()`, `post()`, `put()`, `delete()` genéricos
  - Manejo centralizado de errores con `APIError`
  - Type hints completos
  - Mantener compatibilidad con métodos específicos existentes
  - **Aplicar Inyección de Dependencias**: Eliminar patrón singleton, permitir creación de instancias múltiples
  - **Alineación con Guía General**: El cliente debe poder ser inyectado a través del contexto de la aplicación

**Entregables:**
- `frontend/shared/styles.py`
- `frontend/shared/data_table.py`
- `frontend/shared/async_content.py`
- `frontend/state/app_context.py`
- `frontend/api/api_client.py` refactorizado

---

## FASE 3: Refactorización de Componentes (3 días)

### Objetivos
- Renombrar y reorganizar componentes
- Separar lógica de presentación
- Aplicar type hints completos
- Usar componentes base creados

### Tareas

#### 3.1 Refactorizar Componentes de Robots
- [ ] Renombrar `robots_components.py` → `robot_list.py` (o separar)
- [ ] Separar en componentes más pequeños si es necesario:
  - `RobotList` (tabla principal)
  - `RobotControls` (controles y filtros)
  - `RobotCard` (si aplica)
- [ ] Extraer lógica a `use_robots_hook.py` (ya existe, mejorar)
- [ ] Aplicar type hints completos a todos los componentes
- [ ] Reemplazar tabla custom por `DataTable` genérica
- [ ] Usar `AsyncContent` para estados de carga/error
- [ ] Asegurar keys únicas en todas las listas
- [ ] Actualizar imports en `app.py`

#### 3.2 Refactorizar Componentes de Equipos
- [ ] Renombrar `equipos_components.py` → `equipo_list.py`
- [ ] Aplicar mismos principios que robots
- [ ] Usar `DataTable` y `AsyncContent`
- [ ] Type hints completos
- [ ] Actualizar imports

#### 3.3 Refactorizar Componentes de Pools
- [ ] Renombrar `pools_components.py` → `pool_list.py`
- [ ] Aplicar mismos principios
- [ ] Usar componentes base
- [ ] Type hints completos
- [ ] Actualizar imports

#### 3.4 Refactorizar Componentes de Schedules
- [ ] Renombrar `schedules_components.py` → `schedule_list.py`
- [ ] Aplicar mismos principios
- [ ] Usar componentes base
- [ ] Type hints completos
- [ ] Actualizar imports

#### 3.5 Refactorizar Mappings Page
- [ ] Evaluar si mantener como página completa o separar en componentes
- [ ] Aplicar type hints
- [ ] Usar componentes base donde aplique
- [ ] Actualizar imports

#### 3.6 Actualizar Componentes Compartidos Existentes
- [ ] Revisar `common_components.py`
- [ ] Aplicar type hints completos
- [ ] Asegurar consistencia con nuevos componentes base
- [ ] Documentar props y uso

**Entregables:**
- Componentes renombrados y refactorizados
- Todos los imports actualizados
- Type hints completos en todos los componentes
- Uso consistente de componentes base

---

## FASE 4: Refactorización de Hooks (2 días)

### Objetivos
- Mejorar type hints en todos los hooks
- Estandarizar estructura y manejo de errores
- Separar lógica pura para testing

### Tareas

#### 4.1 Refactorizar `use_robots_hook.py`
- [ ] Agregar type hints completos:
  - Parámetros (si los hay)
  - Retorno: `Dict[str, Any]` con keys documentadas
- [ ] Estandarizar estructura de retorno:
  ```python
  return {
      "robots": robots,
      "loading": loading,
      "error": error,
      "refetch": fetch_robots,
      # ... otros estados
  }
  ```
- [ ] Mejorar manejo de errores con `APIError`
- [ ] Extraer funciones puras si es necesario
- [ ] Documentar con docstrings completos
- [ ] **Aplicar Inyección de Dependencias**: Permitir inyectar `api_client` como parámetro opcional para testing:
  ```python
  def use_robots(api_client: Optional[APIClient] = None) -> Dict[str, Any]:
      client = api_client or use_app_context()["api_client"]
      # ... resto del hook
  ```
- [ ] **Alineación con Guía General**: Hooks deben permitir inyección de dependencias para facilitar testing unitario

#### 4.2 Refactorizar `use_equipos_hook.py`
- [ ] Aplicar mismos principios que `use_robots_hook`
- [ ] Type hints completos
- [ ] Estructura de retorno estandarizada
- [ ] Manejo de errores consistente
- [ ] **Aplicar Inyección de Dependencias**: Permitir inyectar `api_client` para testing

#### 4.3 Refactorizar `use_pools_hook.py`
- [ ] Aplicar mismos principios
- [ ] Type hints completos
- [ ] Estructura estandarizada
- [ ] **Aplicar Inyección de Dependencias**: Permitir inyectar `api_client` para testing

#### 4.4 Refactorizar `use_schedules_hook.py`
- [ ] Aplicar mismos principios
- [ ] Type hints completos
- [ ] Estructura estandarizada
- [ ] **Aplicar Inyección de Dependencias**: Permitir inyectar `api_client` para testing
- [ ] Eliminar `use_schedules_hook copy.py` si existe

#### 4.5 Revisar Hooks Auxiliares
- [ ] `use_debounced_value_hook.py` - Verificar type hints
- [ ] `use_safe_state.py` - Verificar type hints y documentación
- [ ] Estandarizar todos los hooks auxiliares

#### 4.6 Crear Funciones Puras para Testing
- [ ] Extraer lógica de filtrado a funciones puras
- [ ] Extraer lógica de transformación de datos
- [ ] Documentar funciones puras
- [ ] Ejemplo: `filter_robots_by_pool(robots, pool) -> List[dict]`
- [ ] **Alineación con Guía General**: Las funciones puras facilitan testing unitario sin dependencias de I/O, siguiendo el principio de "Separación de Responsabilidades"

**Entregables:**
- Todos los hooks con type hints completos
- Estructura de retorno estandarizada
- Manejo de errores consistente
- Funciones puras extraídas y documentadas

---

## FASE 5: Integración y Migración (2 días)

### Objetivos
- Integrar todos los cambios
- Migrar uso de componentes antiguos a nuevos
- Actualizar todos los imports
- Verificar que todo funciona

### Tareas

#### 5.1 Actualizar `app.py`
- [ ] Actualizar todos los imports de componentes renombrados
- [ ] Integrar `AppContext` con inyección de dependencias:
  - Crear instancia de `APIClient` en el componente raíz
  - Inyectar `api_client` en el contexto de la aplicación
  - **Alineación con Guía General**: Aplicar patrón de inyección de dependencias desde el punto más alto (componente raíz)
- [ ] Verificar que todas las rutas funcionan
- [ ] Actualizar uso de hooks si cambiaron interfaces
- [ ] Asegurar que hooks usan `api_client` del contexto en lugar de singleton

#### 5.2 Actualizar Modales
- [ ] Revisar todos los modales en `features/modals/`
- [ ] Aplicar type hints si faltan
- [ ] Actualizar imports de componentes renombrados
- [ ] Verificar uso de estilos centralizados

#### 5.3 Actualizar Utilidades
- [ ] Revisar `utils/exceptions.py` - Asegurar que `APIError` existe
- [ ] Revisar `utils/validation.py` - Verificar type hints
- [ ] Actualizar manejo de errores en toda la app

#### 5.4 Verificación de Funcionalidad
- [ ] Probar cada página de la aplicación
- [ ] Verificar que los componentes base funcionan correctamente
- [ ] Verificar que los hooks retornan datos correctamente
- [ ] Verificar manejo de errores
- [ ] Verificar estados de carga/vacío/error

#### 5.5 Limpieza
- [ ] Eliminar archivos duplicados (ej: `use_schedules_hook copy.py`)
- [ ] Eliminar código comentado innecesario
- [ ] Actualizar `__init__.py` en todos los módulos
- [ ] Verificar que no hay imports rotos

**Entregables:**
- Aplicación funcionando completamente
- Todos los imports actualizados
- Código limpio sin duplicados

---

## FASE 6: Testing y Documentación (2 días)

### Objetivos
- Configurar testing para ReactPy
- Crear tests para funciones puras
- Documentar cambios y uso de nuevos componentes

### Tareas

#### 6.1 Configurar Testing
- [ ] Configurar pytest para ReactPy
- [ ] Crear `tests/frontend/` si no existe
- [ ] Crear `tests/frontend/conftest.py` con fixtures
- [ ] Documentar cómo escribir tests para componentes ReactPy

#### 6.2 Tests para Funciones Puras
- [ ] Crear tests para funciones de filtrado
- [ ] Crear tests para funciones de transformación
- [ ] Crear tests para utilidades de validación
- [ ] Ejemplo: `test_filter_robots_by_pool()`
- [ ] **Alineación con Guía General**: Las funciones puras son fáciles de testear sin mocks, siguiendo el principio de "Separación de Responsabilidades"

#### 6.3 Tests para Componentes Base
- [ ] Crear tests para `DataTable`
- [ ] Crear tests para `AsyncContent`
- [ ] Crear tests para componentes de estado (Loading, Error, Empty)
- [ ] **Aplicar Inyección de Dependencias en Tests**: Usar mocks de `api_client` inyectados para testear componentes que dependen de él
- [ ] **Alineación con Guía General**: Los tests deben poder inyectar dependencias mockeadas, facilitando testing aislado

#### 6.4 Tests para Hooks (Opcional - Avanzado)
- [ ] Investigar cómo testear hooks de ReactPy
- [ ] Crear tests básicos si es posible
- [ ] Documentar limitaciones

#### 6.5 Documentación
- [ ] Actualizar README con nueva estructura
- [ ] Crear `docs/frontend/component_guide.md` con:
  - Cómo usar `DataTable`
  - Cómo usar `AsyncContent`
  - Cómo crear nuevos componentes
  - Cómo crear nuevos hooks
- [ ] Documentar convenciones de nomenclatura
- [ ] Crear ejemplos de código para cada patrón

**Entregables:**
- Tests configurados y funcionando
- Tests para funciones puras
- Tests para componentes base
- Documentación completa

---

## FASE 7: Optimización y Performance (1 día)

### Objetivos
- Aplicar optimizaciones de performance
- Verificar uso de keys en listas
- Aplicar memoización donde sea necesario

### Tareas

#### 7.1 Verificación de Keys
- [ ] Auditar todas las listas renderizadas
- [ ] Asegurar que todas tienen keys únicas
- [ ] Usar IDs cuando sea posible, índices solo si es necesario

#### 7.2 Aplicar Memoización
- [ ] Identificar cálculos costosos en componentes
- [ ] Aplicar `use_memo` donde sea necesario
- [ ] Ejemplo: estadísticas calculadas, listas filtradas

#### 7.3 Optimización de Re-renders
- [ ] Revisar dependencias de `use_effect`
- [ ] Asegurar que no hay dependencias innecesarias
- [ ] Verificar que los callbacks están memoizados si es necesario

#### 7.4 Performance Testing
- [ ] Probar con grandes volúmenes de datos
- [ ] Verificar que no hay renders innecesarios
- [ ] Optimizar si es necesario

**Entregables:**
- Código optimizado
- Keys en todas las listas
- Memoización aplicada donde corresponde

---

## Resumen de Fases

| Fase | Duración | Prioridad | Dependencias |
|------|----------|-----------|--------------|
| Fase 1: Análisis | 1 día | Alta | - |
| Fase 2: Infraestructura Base | 2 días | Alta | Fase 1 |
| Fase 3: Refactorización Componentes | 3 días | Alta | Fase 2 |
| Fase 4: Refactorización Hooks | 2 días | Alta | Fase 2 |
| Fase 5: Integración | 2 días | Alta | Fases 3, 4 |
| Fase 6: Testing y Documentación | 2 días | Media | Fase 5 |
| Fase 7: Optimización | 1 día | Baja | Fase 5 |

**Total estimado: 13 días hábiles**

---

## Checklist de Verificación Final

Al completar todas las fases, verificar:

### Nomenclatura
- [ ] Todos los archivos en `snake_case`
- [ ] Todos los componentes en `PascalCase`
- [ ] Todas las funciones en `snake_case`
- [ ] Todos los hooks con prefijo `use_`
- [ ] Todas las constantes en `UPPER_SNAKE_CASE`

### Estructura
- [ ] Componentes base creados (`DataTable`, `AsyncContent`)
- [ ] Estilos centralizados en `styles.py`
- [ ] Contexto global configurado
- [ ] Cliente API estandarizado

### Calidad de Código
- [ ] Type hints completos en todos los componentes
- [ ] Type hints completos en todos los hooks
- [ ] Props explícitas (sin `**kwargs`)
- [ ] Separación de lógica y presentación
- [ ] Keys únicas en todas las listas
- [ ] **Inyección de Dependencias aplicada**: Componentes y hooks permiten inyección de `api_client` para testing
- [ ] **Funciones puras extraídas**: Lógica de transformación separada para facilitar testing

### Funcionalidad
- [ ] Todas las páginas funcionan correctamente
- [ ] Manejo de errores consistente
- [ ] Estados de carga/error/vacío funcionan
- [ ] No hay imports rotos

### Testing
- [ ] Tests configurados
- [ ] Tests para funciones puras
- [ ] Tests para componentes base

### Documentación
- [ ] README actualizado
- [ ] Guía de componentes creada
- [ ] Ejemplos de código documentados

---

## Notas Importantes

1. **Compatibilidad**: Durante la migración, mantener compatibilidad temporal si es necesario para no romper funcionalidad.

2. **Commits Incrementales**: Hacer commits por fase o por componente para facilitar rollback si es necesario.

3. **Testing Continuo**: Probar después de cada fase para detectar problemas temprano.

4. **Documentación en Progreso**: Actualizar documentación mientras se avanza, no al final.

5. **Priorización**: Si hay limitaciones de tiempo, priorizar Fases 1-5. Las fases 6 y 7 pueden hacerse después.

6. **Alineación con Guía General de SAM**: 
   - **Inyección de Dependencias**: Todos los componentes y hooks deben permitir inyección de dependencias (especialmente `api_client`) para facilitar testing y mantener consistencia con el backend.
   - **Separación de Responsabilidades**: Los componentes se enfocan en presentación, los hooks en lógica de estado, y las funciones puras en transformaciones.
   - **Estructura de Servicios**: El frontend respeta la estructura del servicio web y se integra correctamente con el backend que sigue DI.
   - **Preparación para Testing**: El código debe estar preparado para testing unitario siguiendo los mismos principios del backend.

---

## Próximos Pasos

1. Revisar y aprobar este plan
2. Asignar recursos y tiempos
3. Comenzar con Fase 1: Análisis y Preparación
4. Establecer reuniones de seguimiento semanales

---

**Última actualización:** [Fecha]
**Versión del plan:** 1.0
