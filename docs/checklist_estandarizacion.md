# Checklist Rápido - Estandarización ReactPy

## FASE 1: Análisis y Preparación ⏱️ 1 día
- [x] Auditoría de nomenclatura de archivos
- [x] Auditoría de componentes (props, type hints, lógica)
- [x] Auditoría de hooks (type hints, estructura)
- [x] Verificar componentes base faltantes
- [x] Crear `docs/audit_report.md`
- [x] Crear `docs/migration_mapping.md`

## FASE 2: Infraestructura Base ⏱️ 2 días
- [x] Crear `frontend/shared/styles.py` (constantes CSS)
- [x] Crear `frontend/shared/data_table.py` (tabla genérica)
- [x] Crear `frontend/shared/async_content.py` (estados async)
- [x] Crear `frontend/state/app_context.py` (contexto global con DI)
- [x] Refactorizar `frontend/api/api_client.py` (eliminar singleton, permitir DI)

## FASE 3: Refactorización Componentes ⏱️ 3 días
- [x] `robots_components.py` → `robot_list.py` + refactor
- [x] `equipos_components.py` → `equipo_list.py` + refactor
- [x] `pools_components.py` → `pool_list.py` + refactor
- [x] `schedules_components.py` → `schedule_list.py` + refactor
- [x] `mappings_page.py` → refactorizar
- [x] Actualizar `common_components.py`
- [x] Actualizar todos los imports en `app.py`

## FASE 4: Refactorización Hooks ⏱️ 2 días
- [x] `use_robots_hook.py` - type hints + estructura + DI (api_client inyectable)
- [x] `use_equipos_hook.py` - type hints + estructura + DI
- [x] `use_pools_hook.py` - type hints + estructura + DI
- [x] `use_schedules_hook.py` - type hints + estructura + DI
- [x] Hooks auxiliares (`use_debounced_value`, `use_safe_state`)
- [x] Extraer funciones puras para testing (alineación con Guía General)

## FASE 5: Integración y Migración ⏱️ 2 días
- [x] Actualizar `app.py` (imports, contexto con DI de api_client)
- [x] Actualizar modales (imports, type hints)
- [x] Actualizar utilidades (`exceptions.py`, `validation.py`)
- [x] Verificar funcionalidad de todas las páginas
- [x] Limpieza (eliminar duplicados, código comentado)
- [x] Actualizar `__init__.py` en todos los módulos
- [x] Asegurar que hooks usan api_client del contexto (no singleton)

## FASE 6: Testing y Documentación ⏱️ 2 días
- [x] Configurar pytest para ReactPy
- [x] Tests para funciones puras
- [x] Tests para componentes base (`DataTable`, `AsyncContent`)
- [x] Actualizar README
- [x] Crear `docs/frontend/component_guide.md`
- [x] Documentar convenciones y ejemplos

## FASE 7: Optimización ⏱️ 1 día
- [x] Verificar keys únicas en todas las listas
- [x] Aplicar `use_memo` donde sea necesario
- [x] Optimizar dependencias de `use_effect`
- [x] Performance testing con grandes volúmenes

---

## Verificación Final

### ✅ Nomenclatura
- [x] Archivos: `snake_case`
- [x] Componentes: `PascalCase`
- [x] Funciones: `snake_case`
- [x] Hooks: `use_*` prefix
- [x] Constantes: `UPPER_SNAKE_CASE`

### ✅ Estructura
- [x] `DataTable` creado y funcionando
- [x] `AsyncContent` creado y funcionando
- [x] `styles.py` con constantes
- [x] `app_context.py` configurado
- [x] `api_client.py` estandarizado

### ✅ Calidad
- [x] Type hints completos (componentes)
- [x] Type hints completos (hooks)
- [x] Props explícitas (sin `**kwargs`)
- [x] Lógica separada de presentación
- [x] Keys en todas las listas
- [x] **Inyección de Dependencias aplicada** (api_client inyectable)
- [x] **Funciones puras extraídas** (facilitan testing)

### ✅ Funcionalidad
- [x] Todas las páginas funcionan
- [x] Manejo de errores consistente
- [x] Estados async funcionan
- [x] Sin imports rotos

### ✅ Testing
- [x] Tests configurados
- [x] Tests para funciones puras
- [x] Tests para componentes base

### ✅ Documentación
- [x] README actualizado
- [x] Guía de componentes
- [x] Ejemplos documentados

---

**Total estimado: 13 días hábiles**

