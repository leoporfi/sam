# ⏱️ Lógica de Ejecuciones (Demoras y Huérfanas)

Este documento detalla cómo SAM identifica ejecuciones que están tomando más tiempo del esperado o que han quedado en un estado inconsistente.

## 1. Ejecuciones Demoradas

La lógica principal reside en el Stored Procedure `dbo.ObtenerEjecucionesRecientes`.

### Cálculo del Tiempo Promedio
Para cada robot, se calcula un tiempo promedio de ejecución basado en su historial:
- **Estados considerados**: Solo ejecuciones con `Estado = 'RUN_COMPLETED'`.
- **Normalización por Ciclos**: El tiempo total se divide por la cantidad de ciclos (`vueltas`) configurados para el robot.
- **Filtro de duración**: Se excluyen ejecuciones menores a 2 minutos (para evitar sesgos por fallos tempranos o ejecuciones vacías).
- **Muestra mínima**: Se requieren al menos **5 ejecuciones** válidas para calcular un promedio dinámico.

### Umbrales de Demora
Una ejecución en estado `RUNNING` o `DEPLOYED` se marca como **"Demorada"** si supera uno de los siguientes umbrales (siempre normalizando el tiempo transcurrido por la cantidad de ciclos):

1.  **Umbral Dinámico (Recomendado)**:
    - Se usa si el robot tiene un promedio calculado.
    - **Fórmula**: `(TiempoTranscurrido / Ciclos) > TiempoPromedioPorCiclo * FactorUmbralDinamico` (Default: 1.5x).
    - **Piso**: Existe un valor mínimo (`PisoUmbralDinamicoMinutos`, Default: 10 min) para evitar alertas prematuras en robots muy rápidos.

2.  **Umbral Fijo (Fallback)**:
    - Se usa si el robot NO tiene suficiente historial.
    - **Valor**: `TiempoTranscurrido > UmbralFijoMinutos` (Default: 25 min).

## 2. Configuración de Ciclos ("Vueltas")

La cantidad de ciclos se determina en el siguiente orden de prioridad:
1.  **Parámetros del Robot**: Se busca en el campo `Parametros` (JSON) de la tabla `Robots`, específicamente la clave `$.in_NumRepeticion.number`.
2.  **Valor por Defecto**: Si no está en los parámetros, se usa el valor de la variable de entorno `LANZADOR_REPETICIONES_ROBOT` (configurado en `ConfigManager`).

## 3. Ejecuciones Huérfanas

Se consideran **"Huérfanas"** aquellas ejecuciones que parecen haber quedado atrapadas en la cola de A360 sin ser procesadas por un Bot Runner.

### Criterios de Identificación
Una ejecución se marca como **"Huerfana"** si:
- El estado es `QUEUED`.
- Han pasado más de **5 minutos** desde su creación.
- **No existe** ninguna ejecución posterior para el mismo Robot y Equipo en estados `DEPLOYED` o `RUNNING`.

## 4. Integración Técnica

### Base de Datos
- **SP Principal**: `dbo.ObtenerEjecucionesRecientes`
- **SP Alternativo**: `dbo.ObtenerEjecucionesRecientes_v2` (Incluye `COMPLETED_INFERRED` en los promedios, pero carece de algunas protecciones de la v1).

### Backend (Python)
- **Archivo**: `src/sam/web/backend/database.py`
- **Función**: `get_recent_executions`
- Esta función invoca al SP y separa los resultados en dos categorías: `fallos` y `demoras` (que incluye tanto demoradas como huérfanas).

### Frontend
Los datos se visualizan en el Dashboard de Estado, específicamente en la sección de **"Estado de Ejecuciones Recientes"**, permitiendo a los operadores identificar cuellos de botella o fallos silenciosos en tiempo real.

## 5. Verificación y Seguimiento

Para asegurar que la lógica de ciclos y demoras funcione correctamente, se han implementado pruebas unitarias que verifican la integración entre el backend Python y el Stored Procedure.

### Pruebas Automatizadas
- **Archivo**: `tests/test_ejecuciones_logic.py`
- **Comando**: `uv run pytest tests/test_ejecuciones_logic.py`
- **Cobertura**:
    - Verificación de paso de parámetros (`DefaultRepeticiones`) al SP.
    - Validación de la estructura de retorno (fallos y demoras).

### Verificación Manual (SQL)
Se recomienda verificar el SP `dbo.ObtenerEjecucionesRecientes` con diferentes valores de `Parametros` para asegurar que la división por ciclos sea exacta y maneje correctamente el caso de 0 ciclos (evitando división por cero mediante `NULLIF`).
