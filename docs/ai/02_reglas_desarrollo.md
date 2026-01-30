# 🐍 REGLAS DE DESARROLLO (PYTHON & WEB) - PROYECTO SAM

---
**Versión:** 2.1.0
**Última Actualización:** 2026-01-30
---

## 📋 ÍNDICE

1. [Estilo y Calidad](#1-estilo-y-calidad)
2. [Tipado Estático](#2-tipado-estático)
3. [Logging](#3-logging)
4. [Servicios Web (Frontend-Backend)](#4-servicios-web)
5. [Testing](#5-testing)
6. [Async/Await](#6-asyncawait)
7. [Manejo de Errores](#7-manejo-de-errores)
8. [Infraestructura Windows](#8-infraestructura-windows)
9. [Convención de Variables de Entorno](#9-convención-de-variables-de-entorno)

---


## 1. ESTILO Y CALIDAD

### Estándar de Código

Seguimos las reglas de **Ruff** definidas en `pyproject.toml`:

```toml
[tool.ruff]
line-length = 120
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
ignore = ["E501"]
```

### Reglas Específicas

#### Imports

```python
# ✅ BIEN: Imports ordenados automáticamente por Ruff
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import pyodbc

from sam.common.database import DatabaseRepository
from sam.common.logging_setup import setup_logger

# ❌ MAL: Imports desordenados
from sam.common.database import DatabaseRepository
import logging
from typing import Dict
import asyncio
```

#### Naming Conventions

```python
# ✅ BIEN
class RobotManager:                    # PascalCase para clases
    async def deploy_robot(self):     # snake_case para funciones
        max_workers = 10               # snake_case para variables
        TIMEOUT_SECONDS = 30           # UPPER_SNAKE_CASE para constantes

# ❌ MAL
class robot_manager:                   # Debería ser PascalCase
    async def DeployRobot(self):       # Debería ser snake_case
        MaxWorkers = 10                # Debería ser snake_case
```

#### Longitud de Línea

```python
# ✅ BIEN: Líneas < 120 caracteres
result = await database.execute_sp(
    "dbo.ObtenerRobotsEjecutables",
    {"param1": value1, "param2": value2}
)

# ❌ MAL: Línea muy larga
result = await database.execute_sp("dbo.ObtenerRobotsEjecutables", {"param1": value1, "param2": value2, "param3": value3, "param4": value4})
```

### Pre-commit Hooks

**SIEMPRE ejecutar antes de commit:**

```bash
uv run pre-commit run --all-files
```

Esto ejecuta automáticamente:
- `ruff check --fix`: Corrige errores de estilo
- `ruff format`: Formatea código
- `trailing-whitespace`: Limpia espacios en blanco
- `check-yaml`: Valida archivos YAML

---

## 2. TIPADO ESTÁTICO

### Uso Obligatorio

**TODO el código debe tener type hints.**

```python
# ✅ BIEN: Tipado completo
from typing import Dict, List, Optional

async def get_robots(
    active_only: bool = True,
    limit: Optional[int] = None
) -> List[Dict[str, any]]:
    """
    Obtiene lista de robots.

    Args:
        active_only: Si True, solo robots activos
        limit: Límite de resultados (None = sin límite)

    Returns:
        Lista de diccionarios con datos de robots
    """
    results: List[Dict[str, any]] = []
    # ...
    return results

# ❌ MAL: Sin tipado
async def get_robots(active_only=True, limit=None):
    results = []
    return results
```

### Tipos Comunes en SAM

```python
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path

# Tipos básicos
robot_id: int = 123
robot_name: str = "Proceso_Pagos"
is_active: bool = True
priority: Optional[int] = None  # Puede ser None

# Colecciones
equipos: List[int] = [1, 2, 3]
config: Dict[str, str] = {"key": "value"}

# Tuplas (estructuras inmutables)
time_window: Tuple[str, str] = ("09:00", "18:00")

# Union (múltiples tipos posibles)
result: Union[Dict, None] = get_data()

# Path (siempre usar pathlib, no strings)
log_path: Path = Path("C:/RPA/Logs/SAM/lanzador.log")

# Datetime
start_time: datetime = datetime.now()
```

### Type Aliases (para mejorar legibilidad)

```python
# Definir en módulo común
from typing import Dict, List, TypeAlias

RobotId: TypeAlias = int
EquipoId: TypeAlias = int
Carga: TypeAlias = Dict[str, int]  # {nombre_robot: tickets_pendientes}

# Usar en funciones
async def obtener_carga() -> Carga:
    return {"Robot_A": 100, "Robot_B": 50}

async def asignar_equipo(robot_id: RobotId, equipo_id: EquipoId) -> bool:
    # ...
    pass
```

---

## 3. LOGGING

### Regla de Oro

**PROHIBIDO usar `print()` para debugging o información.**

```python
# ❌ MAL
print("Iniciando despliegue...")
print(f"Error: {e}")

# ✅ BIEN
logger.info("Iniciando despliegue...")
logger.error("Error al desplegar robot", exc_info=True)
```

### Setup Centralizado

**SIEMPRE usar `src/sam/common/logging_setup.py`:**

```python
from sam.common.logging_setup import setup_logger

# Crear logger para el servicio
logger = setup_logger("lanzador")  # o "balanceador", "callback", "web"

# Niveles de logging
logger.debug("Información de debugging detallada")
logger.info("Información general del flujo")
logger.warning("Situación anormal pero recuperable")
logger.error("Error que requiere atención")
logger.critical("Error crítico que detiene el servicio")
```

### Buenas Prácticas

```python
# ✅ BIEN: Contexto rico
logger.info(
    "Robot desplegado exitosamente",
    extra={
        "robot_id": robot.id,
        "equipo_id": equipo.id,
        "deployment_id": deployment_id
    }
)

# ✅ BIEN: Captura de excepciones
try:
    await deploy_robot(robot)
except Exception as e:
    logger.error(
        f"Fallo al desplegar robot {robot.name}",
        exc_info=True  # Incluye stack trace
    )

# ❌ MAL: Información insuficiente
logger.info("Robot desplegado")
logger.error(f"Error: {e}")  # Sin stack trace
```

### Niveles por Entorno

```python
# Desarrollo
logger.setLevel(logging.DEBUG)  # Todo visible

# Producción (configurado en .env)
LOG_LEVEL=INFO  # Solo INFO y superiores
```

---

## 4. SERVICIOS WEB

### Patrón de Arquitectura

SAM utiliza **Server-Side Components** (Python genera la UI directamente).

```
┌─────────────────────────────────────────┐
│  Frontend (ReactPy)                     │
│  - Componentes en Python               │
│  - Renderizado server-side             │
│  - Estado manejado con hooks           │
└─────────────────────────────────────────┘
              ↓ HTTP/WebSocket
┌─────────────────────────────────────────┐
│  Backend (FastAPI)                      │
│  - REST API                             │
│  - Llama a Stored Procedures           │
│  - Sin lógica de negocio               │
└─────────────────────────────────────────┘
              ↓ SQL
┌─────────────────────────────────────────┐
│  SQL Server                             │
│  - Stored Procedures                    │
│  - TODA la lógica de negocio           │
└─────────────────────────────────────────┘
```

### Reglas del Frontend

#### ❌ NO Introducir

- React (npm/node)
- Vue.js
- Angular
- jQuery (usar HTMX si necesitas AJAX)
- Webpack/Vite

#### ✅ SÍ Usar

- **ReactPy**: Componentes en Python
- **HTMX**: Interactividad sin JS
- **PicoCSS**: Estilos semánticos

```python
# Ejemplo de componente ReactPy
from reactpy import component, html, use_state

@component
def RobotList():
    robots, set_robots = use_state([])

    async def load_robots():
        data = await api_client.get_robots()
        set_robots(data)

    return html.div(
        html.h1("Lista de Robots"),
        html.button({"onClick": load_robots}, "Cargar"),
        html.ul([
            html.li(robot["name"]) for robot in robots
        ])
    )
```

### Estilos

**Ubicación:** `src/sam/web/static/css/`
- `pico.violet.min.css`: Framework base
- `dashboard.css`: Estilos personalizados

```python
# ❌ MAL: Estilos inline
html.div({"style": "color: red; font-size: 16px"}, "Texto")

# ✅ BIEN: Usar clases CSS
html.div({"class": "error-message"}, "Texto")
```

### Contrato Frontend-Backend

**NO ROMPER** nombres de componentes en `features/components/`:

```python
# Si cambias el nombre de un componente, actualizar TODAS las referencias
# src/sam/web/frontend/features/components/robot_list.py
@component
def RobotList():  # ← Nombre usado en routing
    pass

# src/sam/web/frontend/app.py
routes = [
    Route("/robots", RobotList)  # ← Debe coincidir
]
```

---

## 5. TESTING

### Clasificación de Tests

```
tests/
├── unit/                  # Tests unitarios (lógica pura)
│   ├── test_balanceador.py
│   └── test_formatters.py
├── integration/           # Tests con BD
│   ├── test_database.py
│   └── test_api_client.py
└── features/              # Tests BDD (reglas de negocio)
    ├── balanceo.feature
    └── programaciones.feature
```

### Tests Unitarios

**Características:**
- ✅ Rápidos (< 1 segundo cada uno)
- ✅ Sin dependencias externas (BD, APIs)
- ✅ Usan mocks/stubs

```python
# tests/unit/test_balanceador.py
import pytest
from sam.balanceador.service.algoritmo_balanceo import calcular_equipos_necesarios

def test_calcular_equipos_basico():
    # Arrange
    carga = 100
    tickets_por_equipo = 10

    # Act
    equipos = calcular_equipos_necesarios(carga, tickets_por_equipo)

    # Assert
    assert equipos == 10

def test_calcular_equipos_redondeo():
    carga = 95
    tickets_por_equipo = 10

    equipos = calcular_equipos_necesarios(carga, tickets_por_equipo)

    assert equipos == 10  # Redondea hacia arriba
```

### Tests de Integración

**Características:**
- ⚠️ Requieren BD de prueba
- ⚠️ Más lentos (1-5 segundos)
- ✅ Verifican interacción Python ↔ SQL

```python
# tests/integration/test_database.py
import pytest
from sam.common.database import DatabaseRepository

@pytest.mark.asyncio
async def test_obtener_robots_ejecutables():
    # Arrange
    db = DatabaseRepository()

    # Act
    robots = await db.execute_sp("dbo.ObtenerRobotsEjecutables", {})

    # Assert
    assert isinstance(robots, list)
    assert all("RobotId" in r for r in robots)
```

### Tests BDD (Reglas de Negocio)

**Características:**
- 📖 Escritos en lenguaje natural (Gherkin)
- 🎯 Definen comportamiento esperado
- 🚨 **SON LA BIBLIA** del negocio

```gherkin
# tests/features/balanceo.feature
Feature: Balanceo Dinámico de Equipos

  Scenario: Asignar equipos cuando hay demanda
    Given un robot "Proceso_Pagos" con prioridad 5
    And el robot tiene 0 equipos asignados
    And hay 100 tickets pendientes
    When el balanceador ejecuta un ciclo
    Then el robot debe tener 10 equipos asignados
```

**Regla Crítica:**
Si cambias lógica de negocio, **DEBES actualizar el .feature correspondiente**.

### Ejecución de Tests

```bash
# Todos los tests
uv run pytest

# Solo unitarios (rápidos)
uv run pytest tests/unit

# Solo integración (requiere BD)
uv run pytest tests/integration

# Solo BDD
uv run pytest tests/features

# Con cobertura
uv run pytest --cov=sam --cov-report=term-missing

# Tests específicos
uv run pytest tests/unit/test_balanceador.py::test_calcular_equipos_basico
```

---

## 6. ASYNC/AWAIT

### Regla de Oro

**El núcleo de SAM es asíncrono.** No bloquees el event loop.

```python
# ✅ BIEN: Operaciones I/O asíncronas
async def deploy_robot(robot_id: int) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_URL}/deploy", json={"robotId": robot_id})
        return response.json()["deploymentId"]

# ❌ MAL: Operación bloqueante
def deploy_robot(robot_id: int) -> str:
    import requests  # Librería síncrona
    response = requests.post(f"{API_URL}/deploy", json={"robotId": robot_id})
    return response.json()["deploymentId"]
```

### Cuándo Usar Async

| Operación | ¿Async? | Razón |
|-----------|---------|-------|
| Llamadas HTTP | ✅ Sí | I/O de red |
| Consultas BD | ✅ Sí | I/O de disco/red |
| Lectura de archivos | ✅ Sí | I/O de disco |
| Cálculos matemáticos | ❌ No | CPU-bound |
| Logging | ❌ No | Ya está optimizado |

### Patrones Comunes

#### Ejecutar Múltiples Tareas en Paralelo

```python
# ✅ BIEN: Ejecutar deployments en paralelo
async def deploy_multiple_robots(robots: List[Robot]):
    tasks = [deploy_robot(robot) for robot in robots]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for robot, result in zip(robots, results):
        if isinstance(result, Exception):
            logger.error(f"Fallo deploying {robot.name}: {result}")
        else:
            logger.info(f"Deployed {robot.name}: {result}")

# ❌ MAL: Ejecutar secuencialmente
async def deploy_multiple_robots(robots: List[Robot]):
    for robot in robots:
        await deploy_robot(robot)  # Espera uno antes de lanzar el siguiente
```

#### Ejecutar Código Síncrono en Thread Pool

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Si DEBES usar código síncrono (ej: librería sin soporte async)
def proceso_bloqueante(data):
    import time
    time.sleep(5)  # Simulación de operación lenta
    return f"Procesado: {data}"

async def wrapper_async(data):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, proceso_bloqueante, data)
    return result
```

---

## 7. MANEJO DE ERRORES

### Jerarquía de Excepciones

```python
# src/sam/common/exceptions.py
class SAMException(Exception):
    """Base exception para SAM"""
    pass

class DeploymentError(SAMException):
    """Error en despliegue de robot"""
    pass

class Error412Temporal(DeploymentError):
    """Device offline/busy (reintentable)"""
    pass

class Error412Permanente(DeploymentError):
    """Robot sin targets configurados (no reintentable)"""
    pass

class DatabaseError(SAMException):
    """Error de base de datos"""
    pass
```

### Try/Except Patterns

```python
# ✅ BIEN: Captura específica con logging
from sam.common.exceptions import Error412Temporal, Error412Permanente

async def deploy_with_retry(robot: Robot):
    for intento in range(MAX_REINTENTOS):
        try:
            result = await api_client.deploy(robot)
            logger.info(f"Robot {robot.name} desplegado exitosamente")
            return result

        except Error412Temporal as e:
            logger.warning(
                f"Dispositivo ocupado (intento {intento+1}/{MAX_REINTENTOS})",
                extra={"robot_id": robot.id, "error": str(e)}
            )
            await asyncio.sleep(DELAY_REINTENTOS)

        except Error412Permanente as e:
            logger.error(
                f"Robot sin targets configurados: {robot.name}",
                exc_info=True
            )
            # No reintentar
            raise

        except Exception as e:
            logger.critical(
                f"Error inesperado desplegando {robot.name}",
                exc_info=True
            )
            raise

# ❌ MAL: Captura genérica sin logging
async def deploy_with_retry(robot: Robot):
    try:
        result = await api_client.deploy(robot)
        return result
    except:  # Nunca usar except sin tipo
        pass  # Nunca silenciar errores
```

### Context Managers para Recursos

```python
# ✅ BIEN: Cierre automático de recursos
async with httpx.AsyncClient() as client:
    response = await client.get(url)
    # client se cierra automáticamente al salir del bloque

# ❌ MAL: Gestión manual
client = httpx.AsyncClient()
response = await client.get(url)
await client.aclose()  # Fácil de olvidar
```

---

## 8. INFRAESTRUCTURA WINDOWS

### Rutas de Archivos

**SIEMPRE usar `pathlib.Path`, nunca strings.**

```python
from pathlib import Path

# ✅ BIEN
log_dir = Path("C:/RPA/Logs/SAM")
log_file = log_dir / "lanzador.log"

if log_file.exists():
    with log_file.open("r") as f:
        content = f.read()

# ❌ MAL
log_file = "C:\\RPA\\Logs\\SAM\\lanzador.log"  # Escapes tediosos
log_file = "C:/RPA/Logs/SAM" + "/" + "lanzador.log"  # Concatenación manual
```

### Variables de Entorno

```python
import os
from sam.common.config_manager import ConfigManager

# ✅ BIEN: Usar config_manager centralizado
config = ConfigManager()
api_url = config.get("AA_CR_URL")
max_workers = config.get_int("LANZADOR_MAX_WORKERS", default=10)

# ✅ BIEN alternativo: os.getenv con default
db_host = os.getenv("SQL_SAM_HOST", "localhost")

# ❌ MAL: Sin default (puede causar None)
api_url = os.getenv("AA_CR_URL")  # ¿Qué pasa si no existe?
```

### Rutas Relativas al Proyecto

```python
from pathlib import Path

# Obtener raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent.parent  # src/sam/common/xxx.py → raíz

# Rutas relativas
database_dir = PROJECT_ROOT / "database" / "procedures"
tests_dir = PROJECT_ROOT / "tests" / "features"

# ✅ BIEN: Funciona en cualquier entorno
sp_file = database_dir / "dbo_ObtenerRobotsEjecutables.sql"

# ❌ MAL: Ruta absoluta (solo funciona en un servidor)
sp_file = Path("C:/Proyectos/SAM/database/procedures/dbo_ObtenerRobotsEjecutables.sql")
```

---

## 9. CONVENCIÓN DE VARIABLES DE ENTORNO

### Regla de Oro

**TODAS las variables de entorno deben seguir la convención:**

```
{SERVICIO}_{TEMA}_{ACCION}[_{UNIDAD}]
```

Esto permite que al ordenarse alfabéticamente, las variables queden **agrupadas por servicio y tema**.

### Estructura

| Componente | Descripción | Ejemplo |
|------------|-------------|---------|
| `SERVICIO` | Nombre del servicio o módulo | `LANZADOR`, `BALANCEADOR`, `INTERFAZ_WEB` |
| `TEMA` | Área funcional o componente | `SYNC`, `CONCILIACION`, `POOL`, `DEPLOY` |
| `ACCION` | Qué hace o qué es | `HABILITAR`, `INTERVALO`, `MAX`, `UMBRAL` |
| `UNIDAD` | (Opcional) Unidad de medida | `SEG`, `MIN`, `MB` |

### Abreviaciones Estándar

| Abreviación | Significado |
|-------------|-------------|
| `SEG` | Segundos |
| `MIN` | Minutos |
| `MB` | Megabytes |
| `MAX` | Máximo |
| `SYNC` | Sincronización |
| `BD` | Base de Datos |

### Ejemplos

```python
# ✅ BIEN: Sigue la convención
LANZADOR_SYNC_HABILITAR=true                    # SERVICIO_TEMA_ACCION
LANZADOR_SYNC_INTERVALO_SEG=3600                # SERVICIO_TEMA_ACCION_UNIDAD
LANZADOR_CONCILIACION_INTERVALO_SEG=300
LANZADOR_DEPLOY_REINTENTOS_MAX=3
BALANCEADOR_POOL_ENFRIAMIENTO_SEG=300
INTERFAZ_WEB_EJECUCION_DEMORA_UMBRAL_MIN=25

# ❌ MAL: No sigue la convención
LANZADOR_HABILITAR_SINCRONIZACION=true          # Verbo antes de tema
LANZADOR_INTERVALO_SINCRONIZACION_SEG=3600      # Tema intercalado
BALANCEADOR_PERIODO_ENFRIAMIENTO_SEG=300        # Falta tema POOL
```

### Resultado del Orden Alfabético

Cuando las variables siguen la convención, el orden alfabético las agrupa naturalmente:

```
LANZADOR_ALERTAS_ERROR_412_UMBRAL
LANZADOR_CICLO_INTERVALO_SEG
LANZADOR_CONCILIACION_INFERENCIA_MAX_INTENTOS
LANZADOR_CONCILIACION_INFERENCIA_MENSAJE
LANZADOR_CONCILIACION_INTERVALO_SEG
LANZADOR_CONCILIACION_LOTE_TAMANO
LANZADOR_DEPLOY_REINTENTO_DELAY_SEG
LANZADOR_DEPLOY_REINTENTOS_MAX
LANZADOR_PAUSA_FIN_HHMM
LANZADOR_PAUSA_INICIO_HHMM
LANZADOR_SYNC_HABILITAR
LANZADOR_SYNC_INTERVALO_SEG
```

### Compatibilidad Hacia Atrás

Al renombrar variables, **SIEMPRE usar `_get_with_fallback()`** en `ConfigManager`:

```python
# ✅ BIEN: Soporta nombre nuevo y antiguo
habilitar_sync = cls._get_with_fallback(
    "LANZADOR_SYNC_HABILITAR",           # Nuevo nombre
    "LANZADOR_HABILITAR_SINCRONIZACION", # Nombre antiguo
    "True"                                # Valor por defecto
)

# ❌ MAL: Solo soporta un nombre
habilitar_sync = cls._get_config_value("LANZADOR_SYNC_HABILITAR", "True")
```

### Pre-commit Hook

El proyecto incluye un script de validación que verifica los nombres de variables en `.env.example`. Ejecuta:

```bash
uv run python scripts/check_env_naming.py
```

---

## 📋 CHECKLIST ANTES DE COMMIT

Usa esta checklist antes de cada commit:

- [ ] **Estilo:** Ejecuté `uv run pre-commit run --all-files`
- [ ] **Tipado:** Todas las funciones tienen type hints
- [ ] **Logging:** No uso `print()`, solo `logger.xxx()`
- [ ] **Tests:** Ejecuté `uv run pytest` y todos pasan
- [ ] **BDD:** Si cambié lógica de negocio, actualicé los `.feature`
- [ ] **Async:** No introduje código bloqueante en el event loop
- [ ] **Rutas:** Uso `pathlib.Path`, no strings
- [ ] **Excepciones:** Capturo excepciones específicas, no genéricas
- [ ] **Documentación:** Actualicé docstrings si cambié firma de funciones
- [ ] **Variables:** Nuevas variables de entorno siguen la convención `SERVICIO_TEMA_ACCION_UNIDAD`

---

## 📚 REFERENCIAS

- **Ruff Docs:** https://docs.astral.sh/ruff/
- **Type Hints (PEP 484):** https://peps.python.org/pep-0484/
- **AsyncIO:** https://docs.python.org/3/library/asyncio.html
- **ReactPy:** https://reactpy.dev/docs/index.html
- **Pathlib:** https://docs.python.org/3/library/pathlib.html

---

*Última revisión: 2026-01-30 (Python version defined in pyproject.toml)*
