# Checklist Rápido - Estandarización ReactPy

## FASE 1: Análisis y Preparación ⏱️ 1 día
- [ ] Auditoría de nomenclatura de archivos
- [ ] Auditoría de componentes (props, type hints, lógica)
- [ ] Auditoría de hooks (type hints, estructura)
- [ ] Verificar componentes base faltantes
- [ ] Crear `docs/audit_report.md`
- [ ] Crear `docs/migration_mapping.md`

## FASE 2: Infraestructura Base ⏱️ 2 días
- [ ] Crear `frontend/shared/styles.py` (constantes CSS)
- [ ] Crear `frontend/shared/data_table.py` (tabla genérica)
- [ ] Crear `frontend/shared/async_content.py` (estados async)
- [ ] Crear `frontend/state/app_context.py` (contexto global con DI)
- [ ] Refactorizar `frontend/api/api_client.py` (eliminar singleton, permitir DI)

## FASE 3: Refactorización Componentes ⏱️ 3 días
- [ ] `robots_components.py` → `robot_list.py` + refactor
- [ ] `equipos_components.py` → `equipo_list.py` + refactor
- [ ] `pools_components.py` → `pool_list.py` + refactor
- [ ] `schedules_components.py` → `schedule_list.py` + refactor
- [ ] `mappings_page.py` → refactorizar
- [ ] Actualizar `common_components.py`
- [ ] Actualizar todos los imports en `app.py`

## FASE 4: Refactorización Hooks ⏱️ 2 días
- [ ] `use_robots_hook.py` - type hints + estructura + DI (api_client inyectable)
- [ ] `use_equipos_hook.py` - type hints + estructura + DI
- [ ] `use_pools_hook.py` - type hints + estructura + DI
- [ ] `use_schedules_hook.py` - type hints + estructura + DI
- [ ] Hooks auxiliares (`use_debounced_value`, `use_safe_state`)
- [ ] Extraer funciones puras para testing (alineación con Guía General)

## FASE 5: Integración y Migración ⏱️ 2 días
- [ ] Actualizar `app.py` (imports, contexto con DI de api_client)
- [ ] Actualizar modales (imports, type hints)
- [ ] Actualizar utilidades (`exceptions.py`, `validation.py`)
- [ ] Verificar funcionalidad de todas las páginas
- [ ] Limpieza (eliminar duplicados, código comentado)
- [ ] Actualizar `__init__.py` en todos los módulos
- [ ] Asegurar que hooks usan api_client del contexto (no singleton)

## FASE 6: Testing y Documentación ⏱️ 2 días
- [ ] Configurar pytest para ReactPy
- [ ] Tests para funciones puras
- [ ] Tests para componentes base (`DataTable`, `AsyncContent`)
- [ ] Actualizar README
- [ ] Crear `docs/frontend/component_guide.md`
- [ ] Documentar convenciones y ejemplos

## FASE 7: Optimización ⏱️ 1 día
- [ ] Verificar keys únicas en todas las listas
- [ ] Aplicar `use_memo` donde sea necesario
- [ ] Optimizar dependencias de `use_effect`
- [ ] Performance testing con grandes volúmenes

---

## Verificación Final

### ✅ Nomenclatura
- [ ] Archivos: `snake_case`
- [ ] Componentes: `PascalCase`
- [ ] Funciones: `snake_case`
- [ ] Hooks: `use_*` prefix
- [ ] Constantes: `UPPER_SNAKE_CASE`

### ✅ Estructura
- [ ] `DataTable` creado y funcionando
- [ ] `AsyncContent` creado y funcionando
- [ ] `styles.py` con constantes
- [ ] `app_context.py` configurado
- [ ] `api_client.py` estandarizado

### ✅ Calidad
- [ ] Type hints completos (componentes)
- [ ] Type hints completos (hooks)
- [ ] Props explícitas (sin `**kwargs`)
- [ ] Lógica separada de presentación
- [ ] Keys en todas las listas
- [ ] **Inyección de Dependencias aplicada** (api_client inyectable)
- [ ] **Funciones puras extraídas** (facilitan testing)

### ✅ Funcionalidad
- [ ] Todas las páginas funcionan
- [ ] Manejo de errores consistente
- [ ] Estados async funcionan
- [ ] Sin imports rotos

### ✅ Testing
- [ ] Tests configurados
- [ ] Tests para funciones puras
- [ ] Tests para componentes base

### ✅ Documentación
- [ ] README actualizado
- [ ] Guía de componentes
- [ ] Ejemplos documentados

---

**Total estimado: 13 días hábiles**

