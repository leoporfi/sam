# sam/web/backend/cache.py

"""
Sistema de caché en memoria para endpoints de analytics.
Implementa un decorador simple con TTL configurable.
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class CacheEntry:
    """Entrada de caché con timestamp y TTL."""

    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.timestamp = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Verifica si la entrada ha expirado."""
        return (time.time() - self.timestamp) > self.ttl


class SimpleCache:
    """Caché simple en memoria con soporte para TTL."""

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor del caché si existe y no ha expirado."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            if entry.is_expired():
                del self._cache[key]
                logger.debug(f"Cache expired for key: {key}")
                return None

            logger.debug(f"Cache hit for key: {key}")
            return entry.value

    async def set(self, key: str, value: Any, ttl: int):
        """Almacena un valor en el caché con el TTL especificado."""
        async with self._lock:
            self._cache[key] = CacheEntry(value, ttl)
            logger.debug(f"Cache set for key: {key} with TTL: {ttl}s")

    async def invalidate(self, key: str):
        """Invalida una entrada específica del caché."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache invalidated for key: {key}")

    async def clear(self):
        """Limpia todo el caché."""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché."""
        return {
            "total_entries": len(self._cache),
            "entries": [
                {
                    "key": key,
                    "age_seconds": time.time() - entry.timestamp,
                    "ttl": entry.ttl,
                    "expired": entry.is_expired(),
                }
                for key, entry in self._cache.items()
            ],
        }


# Instancia global del caché
_cache = SimpleCache()


def cached(ttl: int = 300):
    """
    Decorador para cachear resultados de funciones con TTL.

    Args:
        ttl: Tiempo de vida en segundos (default: 300 = 5 minutos)

    Uso:
        @cached(ttl=300)
        def my_function(arg1, arg2):
            return expensive_operation(arg1, arg2)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generar clave de caché basada en función y argumentos
            cache_key = _generate_cache_key(func.__name__, args, kwargs)

            # Intentar obtener del caché
            cached_value = await _cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Si no está en caché, ejecutar función
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Guardar en caché
            await _cache.set(cache_key, result, ttl)

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Para funciones síncronas, necesitamos manejar el event loop cuidadosamente
            cache_key = _generate_cache_key(func.__name__, args, kwargs)

            # Intentar obtener del caché
            try:
                # Intentar obtener el loop actual
                try:
                    loop = asyncio.get_running_loop()
                    # Si hay un loop corriendo, no podemos usar run_until_complete
                    # En su lugar, simplemente ejecutamos la función sin caché
                    # (esto ocurre típicamente en tests)
                    logger.warning(
                        f"Event loop already running for sync function {func.__name__}, executing without cache"
                    )
                    return func(*args, **kwargs)
                except RuntimeError:
                    # No hay loop corriendo, podemos crear uno
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        cached_value = loop.run_until_complete(_cache.get(cache_key))
                        if cached_value is not None:
                            return cached_value

                        # Ejecutar función
                        result = func(*args, **kwargs)

                        # Guardar en caché
                        loop.run_until_complete(_cache.set(cache_key, result, ttl))

                        return result
                    finally:
                        loop.close()
            except Exception as e:
                logger.error(f"Error in cache wrapper: {e}")
                # En caso de error, ejecutar función sin caché
                return func(*args, **kwargs)

        # Retornar el wrapper apropiado según si la función es async o no
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _generate_cache_key(func_name: str, args: Tuple, kwargs: Dict) -> str:
    """
    Genera una clave única para el caché basada en el nombre de la función y sus argumentos.

    Nota: Solo considera argumentos serializables. Los objetos complejos (como db connections)
    son ignorados para la generación de la clave.
    """
    # Filtrar argumentos que no son serializables (como DatabaseConnector)
    serializable_args = []
    for arg in args:
        if isinstance(arg, (str, int, float, bool, type(None))):
            serializable_args.append(str(arg))

    serializable_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, (str, int, float, bool, type(None))):
            serializable_kwargs[key] = str(value)

    # Generar clave
    args_str = "_".join(serializable_args)
    kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(serializable_kwargs.items()))

    parts = [func_name]
    if args_str:
        parts.append(args_str)
    if kwargs_str:
        parts.append(kwargs_str)

    cache_key = ":".join(parts)
    return cache_key


async def invalidate_cache(key: str):
    """Invalida una entrada específica del caché."""
    await _cache.invalidate(key)


async def clear_cache():
    """Limpia todo el caché."""
    await _cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del caché."""
    return _cache.get_stats()
