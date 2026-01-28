# Sistema de Caché para Analytics

## Descripción

Se ha implementado un sistema de caché en memoria para optimizar el rendimiento de los endpoints de analytics del dashboard SAM. El objetivo es reducir la carga en la base de datos y mejorar significativamente los tiempos de respuesta.

## Arquitectura

### Backend (`src/sam/web/backend/cache.py`)

Se implementó un sistema de caché simple pero efectivo con las siguientes características:

- **TTL Configurable**: Cada entrada de caché tiene un Time-To-Live (TTL) configurable
- **Thread-Safe**: Utiliza `asyncio.Lock` para operaciones seguras en entornos concurrentes
- **Auto-Expiración**: Las entradas expiradas se eliminan automáticamente al intentar acceder a ellas
- **Decorador `@cached`**: Permite cachear funciones de forma declarativa

### Endpoints Cacheados

| Endpoint | TTL | Justificación |
|----------|-----|---------------|
| `/api/analytics/status` | 10s | Datos casi en tiempo real del estado del sistema |
| `/api/analytics/executions` | 10s | Ejecuciones críticas, necesitan estar actualizadas |
| `/api/analytics/tiempos-ejecucion` | 5min | Datos analíticos que cambian lentamente |
| `/api/analytics/tasas-exito` | 5min | Estadísticas de éxito/error, estables en el tiempo |
| `/api/analytics/utilizacion` | 5min | Análisis de utilización de recursos |
| `/api/analytics/patrones-temporales` | 10min | Patrones temporales, muy estables |

### Frontend (`src/sam/web/frontend/features/components/analytics/analytics_summary.py`)

Se implementó carga progresiva en dos etapas:

1. **Etapa 1 - Datos Críticos** (rápidos):
   - Estado del sistema
   - Ejecuciones críticas recientes

2. **Etapa 2 - Datos Analíticos** (más lentos, cacheados):
   - Tiempos de ejecución
   - Tasas de éxito

### Mejoras de UX

- **Timestamp de Última Actualización**: Visible en el header del dashboard
- **Carga Progresiva**: Los datos críticos se muestran primero
- **Feedback Visual**: Indicadores de loading mejorados

## Uso

### Cachear una Función

```python
from sam.web.backend.cache import cached

@cached(ttl=300)  # 5 minutos
def my_expensive_function(arg1, arg2):
    # Operación costosa
    return result
```

### Invalidar Caché

```python
from sam.web.backend.cache import invalidate_cache, clear_cache

# Invalidar una entrada específica
await invalidate_cache("function_name:arg1_arg2")

# Limpiar todo el caché
await clear_cache()
```

### Obtener Estadísticas

```python
from sam.web.backend.cache import get_cache_stats

stats = get_cache_stats()
# Retorna: {"total_entries": 5, "entries": [...]}
```

O vía API:
```
GET /api/analytics/cache-stats
```

## Beneficios

### Performance

- **Reducción de Carga en BD**: Las consultas pesadas se ejecutan solo una vez por TTL
- **Tiempo de Respuesta**: Mejora significativa en tiempos de carga del dashboard
- **Escalabilidad**: Menor carga permite atender más usuarios concurrentes

### Experiencia de Usuario

- **Carga Rápida**: Datos críticos disponibles inmediatamente
- **Feedback Claro**: Timestamp muestra cuándo se actualizaron los datos
- **Sin Flickering**: Transiciones suaves entre estados

## Configuración

Los TTL están configurados directamente en el código:

```python
# Datos en tiempo real
@cached(ttl=10)  # 10 segundos

# Datos analíticos
@cached(ttl=300)  # 5 minutos

# Patrones estables
@cached(ttl=600)  # 10 minutos
```

Para ajustar los TTL, modificar los decoradores en `src/sam/web/backend/api.py`.

## Monitoreo

El endpoint `/api/analytics/cache-stats` proporciona información sobre:

- Número total de entradas en caché
- Edad de cada entrada
- TTL configurado
- Estado de expiración

## Consideraciones

### Datos en Tiempo Real vs Cacheados

- **Status y Executions**: TTL corto (10s) para mantener datos casi en tiempo real
- **Analytics**: TTL más largo (5-10min) ya que los datos históricos cambian lentamente

### Invalidación

Actualmente el caché se invalida automáticamente por TTL. En el futuro se podría implementar invalidación manual cuando se detecten cambios significativos.

### Memoria

El caché reside en memoria del proceso. En un entorno de producción con múltiples workers, cada worker tendrá su propio caché. Para compartir caché entre workers, considerar Redis u otra solución distribuida.

## Próximos Pasos

1. **Métricas**: Agregar contadores de cache hits/misses
2. **Caché Distribuido**: Evaluar Redis para entornos multi-worker
3. **Invalidación Inteligente**: Invalidar caché cuando se detecten cambios en la BD
4. **Compresión**: Comprimir datos grandes antes de cachear
