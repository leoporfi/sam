# sam/web/hooks/use_debounced_value_hook.py
import asyncio

from reactpy import use_effect, use_state


def use_debounced_value(value, delay: int):
    """
    Un hook personalizado que retrasa la actualización de un valor.
    Devuelve el valor 'retrasado' (debounced).
    """
    debounced_value, set_debounced_value = use_state(value)

    @use_effect(dependencies=[value])
    def debounce():
        # Cuando 'value' cambia, se inicia un temporizador.
        async def do_debounce():
            await asyncio.sleep(delay / 1000)
            set_debounced_value(value)

        task = asyncio.create_task(do_debounce())

        def cleanup():
            task.cancel()

        return cleanup

    return debounced_value
