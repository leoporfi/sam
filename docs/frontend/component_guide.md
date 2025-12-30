# Guía de Componentes del Frontend ReactPy

Esta guía documenta cómo usar los componentes base, hooks y patrones establecidos en el frontend de ReactPy, siguiendo los estándares definidos en `docs/estándar específico para el servicio web de ReactPy.json`.

## Tabla de Contenidos

1. [Componentes Base](#componentes-base)
2. [Hooks](#hooks)
3. [Patrones de Diseño](#patrones-de-diseño)
4. [Convenciones de Nomenclatura](#convenciones-de-nomenclatura)
5. [Ejemplos de Uso](#ejemplos-de-uso)

---

## Componentes Base

### AsyncContent

Componente wrapper para manejar estados asíncronos de manera consistente.

**Ubicación:** `sam.web.frontend.shared.async_content`

**Uso:**
```python
from sam.web.frontend.shared.async_content import AsyncContent

@component
def RobotList():
    robots, loading, error = use_robots_data()

    return AsyncContent(
        loading=loading,
        error=error,
        data=robots,
        empty_message="No hay robots disponibles",
        children=html.div(
            [RobotCard(robot) for robot in robots]
        )
    )
```

**Props:**
- `loading: bool` - Si True, muestra LoadingSpinner
- `error: Optional[str]` - Mensaje de error a mostrar
- `data: Optional[List]` - Datos a verificar si están vacíos
- `loading_component` - Componente personalizado para carga (opcional)
- `error_component` - Componente personalizado para error (opcional)
- `empty_component` - Componente personalizado para vacío (opcional)
- `empty_message: str` - Mensaje cuando no hay datos (default: "No hay datos disponibles")
- `children` - Contenido a mostrar cuando hay datos

**Prioridad de estados:**
1. Error (si `error` está presente)
2. Loading (si `loading=True`)
3. Empty (si `data` está vacío)
4. Children (contenido normal)

---

### DataTable

Componente genérico para mostrar tablas de datos.

**Ubicación:** `sam.web.frontend.shared.data_table`

**Uso:**
```python
from sam.web.frontend.shared.data_table import DataTable

columns = [
    {
        "key": "Robot",
        "label": "Nombre",
        "render": lambda row: html.span(row["Robot"]),
    },
    {
        "key": "Activo",
        "label": "Estado",
        "render": lambda row: StatusBadge(active=row["Activo"]),
        "sortable": True,
    },
]

return DataTable(
    data=robots,
    columns=columns,
    loading=is_loading,
    error=error_message,
    on_row_click=lambda row: handle_robot_click(row),
    actions=[
        {
            "label": "Editar",
            "icon": "✏️",
            "on_click": lambda row: open_edit_modal(row),
            "class_name": "btn btn-primary",
        }
    ],
    sort_by=sort_by,
    sort_dir=sort_dir,
    on_sort=handle_sort,
    empty_message="No hay robots disponibles",
)
```

**Props:**
- `data: List[Dict[str, Any]]` - Lista de datos a mostrar
- `columns: List[Dict[str, Any]]` - Definición de columnas
- `loading: bool` - Estado de carga
- `error: Optional[str]` - Mensaje de error
- `on_row_click: Optional[Callable]` - Callback al hacer click en fila
- `actions: Optional[List[Dict]]` - Acciones por fila
- `empty_message: str` - Mensaje cuando no hay datos
- `sort_by: Optional[str]` - Columna actual de ordenamiento
- `sort_dir: Optional[str]` - Dirección ("asc" o "desc")
- `on_sort: Optional[Callable]` - Callback para ordenamiento

**Definición de columnas:**
```python
{
    "key": "campo_en_data",  # Campo a mostrar
    "label": "Etiqueta",     # Etiqueta de la columna
    "render": lambda row: ...,  # Función de renderizado (opcional)
    "sortable": True,        # Si la columna es ordenable (default: True)
}
```

---

### LoadingSpinner

Spinner de carga reutilizable.

**Ubicación:** `sam.web.frontend.shared.async_content`

**Uso:**
```python
from sam.web.frontend.shared.async_content import LoadingSpinner

return LoadingSpinner(size="medium")  # "small", "medium", "large"
```

---

### ErrorAlert

Alerta de error consistente.

**Ubicación:** `sam.web.frontend.shared.async_content`

**Uso:**
```python
from sam.web.frontend.shared.async_content import ErrorAlert

return ErrorAlert(message="Error al cargar datos")
```

---

### EmptyState

Estado vacío cuando no hay datos.

**Ubicación:** `sam.web.frontend.shared.async_content`

**Uso:**
```python
from sam.web.frontend.shared.async_content import EmptyState

return EmptyState(message="No hay robots disponibles")
```

---

## Hooks

### use_robots

Hook para gestionar el estado del dashboard de robots.

**Ubicación:** `sam.web.frontend.hooks.use_robots_hook`

**Uso:**
```python
from sam.web.frontend.hooks.use_robots_hook import use_robots

# En un componente
robots_state = use_robots()

# Acceder a datos
robots = robots_state["robots"]
loading = robots_state["loading"]
error = robots_state["error"]

# Acciones
robots_state["refresh"]()
robots_state["set_filters"]({"name": "test"})
robots_state["trigger_sync"]()
```

**Retorna:**
```python
{
    "robots": List[Dict],           # Lista de robots
    "loading": bool,                 # Estado de carga
    "is_syncing": bool,              # Si está sincronizando
    "error": Optional[str],          # Mensaje de error
    "total_count": int,              # Total de robots
    "filters": Dict,                 # Filtros actuales
    "set_filters": Callable,         # Actualizar filtros
    "update_robot_status": Callable, # Actualizar estado de robot
    "refresh": Callable,            # Recargar robots
    "trigger_sync": Callable,        # Iniciar sincronización
    "current_page": int,             # Página actual
    "set_current_page": Callable,    # Cambiar página
    "total_pages": int,              # Total de páginas
    "page_size": int,                # Tamaño de página
    "sort_by": str,                  # Columna de ordenamiento
    "sort_dir": str,                 # Dirección ("asc" o "desc")
    "handle_sort": Callable,         # Manejar ordenamiento
}
```

**Inyección de Dependencias:**
```python
# Para testing, puedes inyectar un mock de APIClient
mock_client = MagicMock(spec=APIClient)
robots_state = use_robots(api_client=mock_client)
```

---

### use_equipos

Hook para gestionar equipos. Similar a `use_robots`.

**Ubicación:** `sam.web.frontend.hooks.use_equipos_hook`

---

### use_pools_management

Hook para gestionar pools.

**Ubicación:** `sam.web.frontend.hooks.use_pools_hook`

---

### use_schedules

Hook para gestionar programaciones.

**Ubicación:** `sam.web.frontend.hooks.use_schedules_hook`

---

## Patrones de Diseño

### Inyección de Dependencias (DI)

Todos los hooks y componentes que necesitan `APIClient` lo reciben a través de:

1. **Parámetro opcional** (para testing):
   ```python
   def use_robots(api_client: Optional[APIClient] = None):
       if api_client is None:
           api_client = use_app_context()["api_client"]
   ```

2. **AppContext** (en producción):
   ```python
   # En app.py (componente raíz)
   api_client = APIClient(base_url="http://127.0.0.1:8000")
   app_context_value = {"api_client": api_client}
   return AppContext(children=..., value=app_context_value)

   # En hooks o componentes
   from sam.web.frontend.state.app_context import use_app_context
   api_client = use_app_context()["api_client"]
   ```

**Beneficios:**
- Facilita testing con mocks
- Permite cambiar implementación sin modificar código
- Sigue el principio de Inversión de Dependencias

---

### Separación de Responsabilidades

**Componentes:** Solo presentación (UI)
```python
@component
def RobotCard(robot: Dict[str, Any]):
    """Solo renderiza UI, no maneja lógica de negocio."""
    return html.div(
        {"class_name": ROBOT_CARD},
        html.h3(robot["Robot"]),
        html.p(robot.get("Descripcion", "")),
    )
```

**Hooks:** Lógica de estado y efectos
```python
def use_robots():
    """Maneja estado, efectos, y llamadas a API."""
    robots, set_robots = use_state([])
    # ... lógica de carga, filtrado, etc.
    return {"robots": robots, ...}
```

**Funciones Puras:** Transformaciones de datos
```python
def filter_robots_by_pool(robots: List[Dict], pool_id: int) -> List[Dict]:
    """Función pura, fácil de testear."""
    return [r for r in robots if r.get("PoolId") == pool_id]
```

---

### Estilos Centralizados

Usa constantes de `styles.py` en lugar de strings hardcodeados.

**Ubicación:** `sam.web.frontend.shared.styles`

**Uso:**
```python
from sam.web.frontend.shared.styles import (
    BUTTON_PRIMARY,
    ROBOT_CARD,
    STATUS_RUNNING,
)

return html.button(
    {"class_name": BUTTON_PRIMARY},
    "Guardar"
)
```

**Beneficios:**
- Consistencia visual
- Fácil mantenimiento
- Refactoring seguro

---

## Convenciones de Nomenclatura

### Archivos
- **snake_case**: `robot_list.py`, `use_robots_hook.py`

### Componentes
- **PascalCase**: `RobotCard`, `DataTable`, `AsyncContent`

### Funciones y Variables
- **snake_case**: `get_robots`, `filter_data`, `is_loading`

### Hooks
- **use_ prefix**: `use_robots`, `use_equipos`, `use_debounced_value`

### Constantes
- **UPPER_SNAKE_CASE**: `PAGE_SIZE`, `BUTTON_PRIMARY`, `STATUS_RUNNING`

---

## Ejemplos de Uso

### Ejemplo Completo: Lista de Robots

```python
from reactpy import component, html
from sam.web.frontend.hooks.use_robots_hook import use_robots
from sam.web.frontend.shared.async_content import AsyncContent
from sam.web.frontend.shared.data_table import DataTable
from sam.web.frontend.shared.styles import ROBOT_CARD

@component
def RobotsPage():
    """Página principal de robots."""
    robots_state = use_robots()

    columns = [
        {
            "key": "Robot",
            "label": "Nombre",
            "render": lambda row: html.strong(row["Robot"]),
        },
        {
            "key": "Activo",
            "label": "Estado",
            "render": lambda row: "✅ Activo" if row["Activo"] else "❌ Inactivo",
        },
    ]

    return html.div(
        html.h1("Robots"),
        DataTable(
            data=robots_state["robots"],
            columns=columns,
            loading=robots_state["loading"],
            error=robots_state["error"],
            on_row_click=lambda row: handle_robot_click(row),
            sort_by=robots_state["sort_by"],
            sort_dir=robots_state["sort_dir"],
            on_sort=robots_state["handle_sort"],
        ),
    )
```

---

### Ejemplo: Crear Nuevo Componente

```python
# frontend/features/components/my_feature.py
from typing import Dict, Any
from reactpy import component, html
from ...shared.styles import CARD, BUTTON_PRIMARY

@component
def MyFeatureCard(data: Dict[str, Any]):
    """
    Componente de ejemplo siguiendo estándares.

    Args:
        data: Diccionario con datos del feature
    """
    return html.article(
        {"class_name": CARD},
        html.h3(data.get("title", "Sin título")),
        html.p(data.get("description", "")),
        html.button(
            {"class_name": BUTTON_PRIMARY, "on_click": lambda: handle_click(data)},
            "Acción",
        ),
    )
```

---

### Ejemplo: Crear Nuevo Hook

```python
# frontend/hooks/use_my_feature_hook.py
from typing import Any, Dict, Optional
from reactpy import use_effect, use_state
from ..api.api_client import APIClient
from ..state.app_context import use_app_context

def use_my_feature(api_client: Optional[APIClient] = None) -> Dict[str, Any]:
    """
    Hook para gestionar feature.

    Args:
        api_client: Cliente API opcional para inyección de dependencias.

    Returns:
        Dict con datos y funciones del hook.
    """
    # Obtener api_client del contexto si no se proporciona
    if api_client is None:
        app_context = use_app_context()
        api_client = app_context.get("api_client")

    # Estados
    data, set_data = use_state([])
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)

    # Efecto para cargar datos
    @use_effect(dependencies=[])
    def load_data():
        async def fetch():
            try:
                set_loading(True)
                result = await api_client.get_my_feature()
                set_data(result)
            except Exception as e:
                set_error(str(e))
            finally:
                set_loading(False)

        task = asyncio.create_task(fetch())
        return lambda: task.cancel()

    return {
        "data": data,
        "loading": loading,
        "error": error,
    }
```

---

## Testing

### Testing de Funciones Puras

```python
# tests/frontend/test_validation.py
from sam.web.frontend.utils.validation import validate_robot_data

def test_valid_robot_data():
    data = {
        "Robot": "Test Robot",
        "MinEquipos": 1,
        "MaxEquipos": 5,
    }
    result = validate_robot_data(data)
    assert result.is_valid is True
```

### Testing con Mocks (DI)

```python
# tests/frontend/test_hooks.py
from unittest.mock import AsyncMock, MagicMock
from sam.web.frontend.hooks.use_robots_hook import use_robots

def test_use_robots_with_mock():
    mock_client = MagicMock(spec=APIClient)
    mock_client.get_robots = AsyncMock(return_value={"robots": [], "total": 0})

    # Inyectar mock
    robots_state = use_robots(api_client=mock_client)

    assert robots_state["robots"] == []
```

---

## Recursos Adicionales

- **Estándar ReactPy:** `docs/estándar específico para el servicio web de ReactPy.json`
- **Guía General:** `docs/Guia de Arquitectura y Desarrollo.json`
- **Plan de Estandarización:** `docs/plan_estandarizacion_reactpy.md`

---

**Última actualización:** Fase 6 - Testing y Documentación
