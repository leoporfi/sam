# Mapeo de Cambios - Estandarización ReactPy

Este documento mapea todos los cambios de nombres, imports y estructuras necesarios para la estandarización.

**Última actualización:** 2024-12-19

---

## 1. Mapeo de Renombrado de Archivos

### 1.1 Componentes

| Archivo Actual | Archivo Nuevo | Componentes Contenidos | Acción |
|----------------|---------------|------------------------|--------|
| `robots_components.py` | `robot_list.py` | `RobotsControls`, `RobotsDashboard`, `RobotTable`, `RobotRow`, `RobotCard` | Renombrar y posiblemente separar |
| `equipos_components.py` | `equipo_list.py` | `EquiposControls`, `EquiposDashboard` | Renombrar |
| `pools_components.py` | `pool_list.py` | `PoolsControls`, `PoolsDashboard`, `BalanceadorStrategyPanel` | Renombrar |
| `schedules_components.py` | `schedule_list.py` | `SchedulesControls`, `SchedulesDashboard` | Renombrar |
| `mappings_page.py` | `mapping_list.py` o mantener | `MappingsPage` | Evaluar si mantener como página completa |

### 1.2 Hooks

| Archivo Actual | Archivo Nuevo | Acción |
|----------------|---------------|--------|
| `use_robots_hook.py` | `use_robots_hook.py` | ✅ Mantener nombre (ya correcto) |
| `use_equipos_hook.py` | `use_equipos_hook.py` | ✅ Mantener nombre (ya correcto) |
| `use_pools_hook.py` | `use_pools_hook.py` | ✅ Mantener nombre (ya correcto) |
| `use_schedules_hook.py` | `use_schedules_hook.py` | ✅ Mantener nombre (ya correcto) |
| `use_schedules_hook copy.py` | ❌ ELIMINAR | Eliminar duplicado |

### 1.3 Archivos Nuevos a Crear

| Archivo Nuevo | Ubicación | Propósito |
|---------------|-----------|-----------|
| `data_table.py` | `frontend/shared/data_table.py` | Componente DataTable genérico |
| `async_content.py` | `frontend/shared/async_content.py` | Componentes para estados async |
| `styles.py` | `frontend/shared/styles.py` | Constantes de clases CSS |
| `app_context.py` | `frontend/state/app_context.py` | Contexto global de aplicación |

---

## 2. Mapeo de Imports a Actualizar

### 2.1 En `app.py`

#### Imports Actuales:
```python
from .features.components.robots_components import RobotsControls, RobotsDashboard
from .features.components.equipos_components import EquiposControls, EquiposDashboard
from .features.components.pools_components import BalanceadorStrategyPanel, PoolsControls, PoolsDashboard
from .features.components.schedules_components import SchedulesControls, SchedulesDashboard
from .features.components.mappings_page import MappingsPage
```

#### Imports Nuevos:
```python
from .features.components.robot_list import RobotsControls, RobotsDashboard
from .features.components.equipo_list import EquiposControls, EquiposDashboard
from .features.components.pool_list import BalanceadorStrategyPanel, PoolsControls, PoolsDashboard
from .features.components.schedule_list import SchedulesControls, SchedulesDashboard
from .features.components.mapping_list import MappingsPage  # o mantener mappings_page
```

### 2.2 En Modales

#### Archivos a Revisar:
- `features/modals/robots_modals.py`
- `features/modals/equipos_modals.py`
- `features/modals/pool_modals.py`
- `features/modals/schedule_modal.py`

**Acción:** Actualizar imports de componentes renombrados.

### 2.3 En Otros Componentes

Cualquier archivo que importe desde `robots_components`, `equipos_components`, etc. debe actualizarse.

---

## 3. Mapeo de Cambios en Componentes

### 3.1 Componentes que Usarán DataTable

| Componente Actual | Tabla Actual | Reemplazo con DataTable |
|-------------------|--------------|-------------------------|
| `RobotTable` | Tabla custom en `robots_components.py` | Usar `DataTable` genérica |
| `EquiposDashboard` | Tabla custom | Usar `DataTable` genérica |
| `PoolsDashboard` | Tabla custom | Usar `DataTable` genérica |
| `SchedulesDashboard` | Tabla custom | Usar `DataTable` genérica |

### 3.2 Componentes que Usarán AsyncContent

| Componente Actual | Lógica Actual | Reemplazo con AsyncContent |
|-------------------|---------------|---------------------------|
| `RobotsDashboard` | Manejo manual de `loading`, `error` | Usar `AsyncContent` wrapper |
| `EquiposDashboard` | Manejo manual de estados | Usar `AsyncContent` wrapper |
| `PoolsDashboard` | Manejo manual de estados | Usar `AsyncContent` wrapper |
| `SchedulesDashboard` | Manejo manual de estados | Usar `AsyncContent` wrapper |

---

## 4. Mapeo de Cambios en Hooks

### 4.1 Cambios en Signatura de Hooks

#### Antes:
```python
def use_robots():
    api_client = get_api_client()  # Singleton
    # ...
```

#### Después:
```python
def use_robots(api_client: Optional[APIClient] = None) -> Dict[str, Any]:
    client = api_client or use_app_context()["api_client"]
    # ...
    return {
        "robots": robots,
        "loading": loading,
        "error": error,
        "refetch": load_robots,
        # ...
    }
```

**Aplicar a:**
- `use_robots_hook.py`
- `use_equipos_hook.py`
- `use_pools_hook.py`
- `use_schedules_hook.py`

### 4.2 Cambios en Uso de Hooks

#### En `app.py` y páginas:

**Antes:**
```python
robots_state = use_robots()
```

**Después:**
```python
# api_client viene del contexto, no necesita pasarse explícitamente
robots_state = use_robots()
# O para testing:
# robots_state = use_robots(api_client=mock_client)
```

---

## 5. Mapeo de Cambios en Cliente API

### 5.1 Cambios en `api_client.py`

#### Antes:
```python
class ApiClient:
    # ...

_api_client_instance = None

def get_api_client() -> ApiClient:
    global _api_client_instance
    if _api_client_instance is None:
        _api_client_instance = ApiClient()
    return _api_client_instance
```

#### Después:
```python
class APIClient:  # Renombrar a PascalCase completo
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        # ...
    # ...

# Eliminar singleton
# Las instancias se crearán en el contexto de la app
```

### 5.2 Cambios en Uso del Cliente

#### En Hooks:

**Antes:**
```python
from ..api.api_client import get_api_client

def use_robots():
    api_client = get_api_client()
```

**Después:**
```python
from ..state.app_context import use_app_context
from ..api.api_client import APIClient

def use_robots(api_client: Optional[APIClient] = None) -> Dict[str, Any]:
    client = api_client or use_app_context()["api_client"]
```

---

## 6. Mapeo de Cambios en Contexto

### 6.1 Creación de AppContext

#### Nuevo archivo: `frontend/state/app_context.py`

```python
from reactpy import create_context, use_context
from typing import Dict, Any, Optional
from ..api.api_client import APIClient

AppContext = create_context({})

def AppProvider(children, value: Dict[str, Any]):
    return AppContext(value, children)

def use_app_context() -> Dict[str, Any]:
    return use_context(AppContext)
```

### 6.2 Cambios en `app.py`

#### Antes:
```python
@component
def App():
    notifications, set_notifications = use_state([])
    # ...
    context_value = {
        "notifications": notifications,
        "show_notification": show_notification,
        "dismiss_notification": dismiss_notification,
    }
    return NotificationContext(value=context_value, children=...)
```

#### Después:
```python
@component
def App():
    # Crear instancia de api_client (inyección desde el punto más alto)
    api_client = APIClient(base_url="http://127.0.0.1:8000")
    
    notifications, set_notifications = use_state([])
    # ...
    
    app_context_value = {
        "api_client": api_client,
        "notifications": notifications,
        "show_notification": show_notification,
        "dismiss_notification": dismiss_notification,
    }
    
    return AppProvider(
        value=app_context_value,
        children=NotificationContext(value=notification_context, children=...)
    )
```

---

## 7. Mapeo de Estilos

### 7.1 Nuevo Archivo: `frontend/shared/styles.py`

```python
# Botones
BUTTON_PRIMARY = "btn btn-primary"
BUTTON_DANGER = "btn btn-danger"
BUTTON_SECONDARY = "btn btn-secondary"

# Estados
STATUS_RUNNING = "badge bg-success"
STATUS_STOPPED = "badge bg-error"
STATUS_UNKNOWN = "badge bg-warning"
STATUS_COOLING = "badge bg-info"

# Layout
CARD = "card"
GRID = "grid"
CONTAINER = "container"
```

### 7.2 Componentes que Usarán Estilos Centralizados

Todos los componentes que definen clases CSS inline deberán importar desde `styles.py`:
- `RobotsControls`
- `RobotRow`
- `EquiposControls`
- `PoolsControls`
- `SchedulesControls`
- Y otros componentes que usen clases de estado o botones

---

## 8. Checklist de Migración

### Fase 1: Preparación
- [x] Crear `audit_report.md`
- [x] Crear `migration_mapping.md`
- [ ] Revisar y aprobar mapeo

### Fase 2: Infraestructura
- [ ] Crear `frontend/shared/styles.py`
- [ ] Crear `frontend/shared/data_table.py`
- [ ] Crear `frontend/shared/async_content.py`
- [ ] Crear `frontend/state/app_context.py`
- [ ] Refactorizar `frontend/api/api_client.py`

### Fase 3: Renombrado
- [ ] Renombrar `robots_components.py` → `robot_list.py`
- [ ] Renombrar `equipos_components.py` → `equipo_list.py`
- [ ] Renombrar `pools_components.py` → `pool_list.py`
- [ ] Renombrar `schedules_components.py` → `schedule_list.py`
- [ ] Actualizar todos los imports

### Fase 4: Refactorización
- [ ] Actualizar hooks para usar DI
- [ ] Actualizar componentes para usar DataTable
- [ ] Actualizar componentes para usar AsyncContent
- [ ] Actualizar componentes para usar estilos centralizados
- [ ] Actualizar `app.py` para usar AppContext

### Fase 5: Limpieza
- [ ] Eliminar `use_schedules_hook copy.py`
- [ ] Verificar que no hay imports rotos
- [ ] Ejecutar tests (cuando estén disponibles)

---

## 9. Notas Importantes

1. **Orden de Cambios:** Seguir el orden de las fases para evitar dependencias circulares.

2. **Commits Incrementales:** Hacer commits después de cada cambio importante para facilitar rollback.

3. **Testing Continuo:** Probar después de cada cambio para detectar problemas temprano.

4. **Compatibilidad Temporal:** Durante la migración, mantener compatibilidad temporal si es necesario.

---

**Última actualización:** 2024-12-19
