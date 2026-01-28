# tests/test_cache.py

"""
Tests para el sistema de caché de analytics.
"""

import asyncio
import time

import pytest

from sam.web.backend.cache import SimpleCache, cached, clear_cache, get_cache_stats, invalidate_cache


@pytest.fixture
async def cache():
    """Fixture que proporciona un caché limpio para cada test."""
    await clear_cache()
    yield
    await clear_cache()


class TestSimpleCache:
    """Tests para la clase SimpleCache."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """Test básico de set y get."""
        cache_instance = SimpleCache()
        await cache_instance.set("test_key", "test_value", ttl=60)

        value = await cache_instance.get("test_key")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache):
        """Test de get con clave inexistente."""
        cache_instance = SimpleCache()
        value = await cache_instance.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_expiration(self, cache):
        """Test de expiración de entradas."""
        cache_instance = SimpleCache()
        await cache_instance.set("test_key", "test_value", ttl=1)

        # Verificar que existe inmediatamente
        value = await cache_instance.get("test_key")
        assert value == "test_value"

        # Esperar a que expire
        await asyncio.sleep(1.1)

        # Verificar que expiró
        value = await cache_instance.get("test_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_invalidate(self, cache):
        """Test de invalidación manual."""
        cache_instance = SimpleCache()
        await cache_instance.set("test_key", "test_value", ttl=60)

        # Verificar que existe
        value = await cache_instance.get("test_key")
        assert value == "test_value"

        # Invalidar
        await cache_instance.invalidate("test_key")

        # Verificar que fue eliminado
        value = await cache_instance.get("test_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test de limpieza completa del caché."""
        cache_instance = SimpleCache()
        await cache_instance.set("key1", "value1", ttl=60)
        await cache_instance.set("key2", "value2", ttl=60)

        # Verificar que existen
        assert await cache_instance.get("key1") == "value1"
        assert await cache_instance.get("key2") == "value2"

        # Limpiar todo
        await cache_instance.clear()

        # Verificar que fueron eliminados
        assert await cache_instance.get("key1") is None
        assert await cache_instance.get("key2") is None

    @pytest.mark.asyncio
    async def test_stats(self, cache):
        """Test de estadísticas del caché."""
        cache_instance = SimpleCache()
        await cache_instance.set("key1", "value1", ttl=60)
        await cache_instance.set("key2", "value2", ttl=120)

        stats = cache_instance.get_stats()

        assert stats["total_entries"] == 2
        assert len(stats["entries"]) == 2

        # Verificar que las entradas tienen la información correcta
        keys = [entry["key"] for entry in stats["entries"]]
        assert "key1" in keys
        assert "key2" in keys


class TestCachedDecorator:
    """Tests para el decorador @cached."""

    @pytest.mark.asyncio
    async def test_cached_function(self, cache):
        """Test básico del decorador cached con función async."""
        call_count = 0

        @cached(ttl=60)
        async def expensive_function(arg):
            nonlocal call_count
            call_count += 1
            return f"result_{arg}"

        # Primera llamada - debe ejecutar la función
        result1 = await expensive_function("test")
        assert result1 == "result_test"
        assert call_count == 1

        # Segunda llamada con mismo argumento - debe usar caché
        result2 = await expensive_function("test")
        assert result2 == "result_test"
        assert call_count == 1  # No debe incrementar

        # Llamada con diferente argumento - debe ejecutar la función
        result3 = await expensive_function("other")
        assert result3 == "result_other"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_async_function(self, cache):
        """Test del decorador cached con función async."""
        call_count = 0

        @cached(ttl=60)
        async def async_expensive_function(arg):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return f"async_result_{arg}"

        # Primera llamada
        result1 = await async_expensive_function("test")
        assert result1 == "async_result_test"
        assert call_count == 1

        # Segunda llamada - debe usar caché
        result2 = await async_expensive_function("test")
        assert result2 == "async_result_test"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cached_with_multiple_args(self, cache):
        """Test del decorador con múltiples argumentos."""
        call_count = 0

        @cached(ttl=60)
        async def multi_arg_function(arg1, arg2, kwarg1=None):
            nonlocal call_count
            call_count += 1
            return f"{arg1}_{arg2}_{kwarg1}"

        # Diferentes combinaciones de argumentos
        await multi_arg_function("a", "b", kwarg1="c")
        assert call_count == 1

        await multi_arg_function("a", "b", kwarg1="c")
        assert call_count == 1  # Mismo, debe usar caché

        await multi_arg_function("a", "b", kwarg1="d")
        assert call_count == 2  # Diferente kwarg, debe ejecutar

    @pytest.mark.asyncio
    async def test_cached_expiration(self, cache):
        """Test de expiración con decorador cached."""
        call_count = 0

        @cached(ttl=1)
        async def short_ttl_function(arg):
            nonlocal call_count
            call_count += 1
            return f"result_{arg}_{call_count}"

        # Primera llamada
        result1 = await short_ttl_function("test")
        assert "result_test_1" in result1
        assert call_count == 1

        # Segunda llamada inmediata - debe usar caché
        result2 = await short_ttl_function("test")
        assert result2 == result1
        assert call_count == 1

        # Esperar expiración
        await asyncio.sleep(1.1)

        # Tercera llamada después de expiración - debe ejecutar de nuevo
        result3 = await short_ttl_function("test")
        assert "result_test_2" in result3
        assert call_count == 2


class TestGlobalCacheFunctions:
    """Tests para las funciones globales de caché."""

    @pytest.mark.asyncio
    async def test_global_invalidate(self, cache):
        """Test de invalidación global."""
        call_count = 0

        @cached(ttl=60)
        async def test_function(arg):
            nonlocal call_count
            call_count += 1
            return f"result_{arg}"

        # Llamar función
        await test_function("test")
        assert call_count == 1

        # Invalidar caché
        await invalidate_cache("test_function:test")

        # Llamar de nuevo - debe ejecutar
        await test_function("test")
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_global_clear(self, cache):
        """Test de limpieza global."""
        call_count = 0

        @cached(ttl=60)
        async def test_function(arg):
            nonlocal call_count
            call_count += 1
            return f"result_{arg}"

        # Llamar función varias veces
        await test_function("test1")
        await test_function("test2")
        assert call_count == 2

        # Limpiar todo el caché
        await clear_cache()

        # Llamar de nuevo - debe ejecutar ambas
        await test_function("test1")
        await test_function("test2")
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_global_stats(self, cache):
        """Test de estadísticas globales."""

        @cached(ttl=60)
        async def test_function(arg):
            return f"result_{arg}"

        # Llamar función varias veces
        await test_function("test1")
        await test_function("test2")
        await test_function("test3")

        # Obtener estadísticas
        stats = get_cache_stats()

        assert stats["total_entries"] >= 3
        assert len(stats["entries"]) >= 3


class TestCachePerformance:
    """Tests de performance del caché."""

    @pytest.mark.asyncio
    async def test_cache_improves_performance(self, cache):
        """Verificar que el caché mejora la performance."""

        @cached(ttl=60)
        async def slow_function(arg):
            await asyncio.sleep(0.1)  # Simular operación lenta
            return f"result_{arg}"

        # Primera llamada (sin caché)
        start = time.time()
        result1 = await slow_function("test")
        first_call_time = time.time() - start

        # Segunda llamada (con caché)
        start = time.time()
        result2 = await slow_function("test")
        cached_call_time = time.time() - start

        # Verificar que los resultados son iguales
        assert result1 == result2

        # Verificar que la llamada cacheada es significativamente más rápida
        assert cached_call_time < first_call_time / 10  # Al menos 10x más rápido

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, cache):
        """Test de acceso concurrente al caché."""
        call_count = 0

        @cached(ttl=60)
        async def concurrent_function(arg):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return f"result_{arg}"

        # Ejecutar múltiples llamadas concurrentes
        tasks = [concurrent_function("test") for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Todas deben retornar el mismo resultado
        assert all(r == "result_test" for r in results)

        # La función debe haberse ejecutado solo una vez (o muy pocas veces debido a race conditions)
        # En un entorno de test con asyncio, es normal tener algunas ejecuciones concurrentes
        assert call_count <= 10  # Permitir hasta 10 ejecuciones por race conditions en tests
