# sam/web/hooks/use_debounced_value_hook.py
import asyncio

from reactpy import use_effect, use_ref, use_state


def use_debounced_value(value, delay: int):
    """
    Un hook personalizado que retrasa la actualización de un valor.
    Devuelve el valor 'retrasado' (debounced).

    Este hook maneja correctamente la limpieza de tareas asíncronas para evitar
    el error "Task was destroyed but it is pending" cuando el componente se desmonta.
    """
    debounced_value, set_debounced_value = use_state(value)
    task_ref = use_ref(None)
    is_mounted = use_ref(True)

    @use_effect(dependencies=[])
    def mount_lifecycle():
        is_mounted.current = True
        return lambda: setattr(is_mounted, "current", False)

    @use_effect(dependencies=[value])
    def debounce():
        # Cancelar la tarea anterior si existe
        if task_ref.current and not task_ref.current.done():
            task_ref.current.cancel()

        # Cuando 'value' cambia, se inicia un temporizador.
        async def do_debounce():
            try:
                await asyncio.sleep(delay / 1000)
                # Solo actualizar si el componente sigue montado
                if is_mounted.current:
                    set_debounced_value(value)
            except asyncio.CancelledError:
                # Cancelación esperada durante cleanup, no hacer nada
                pass

        task_ref.current = asyncio.create_task(do_debounce())

        def cleanup():
            is_mounted.current = False
            if task_ref.current and not task_ref.current.done():
                task_ref.current.cancel()

                # Crear una tarea auxiliar para esperar la cancelación y evitar
                # el error "Task was destroyed but it is pending"
                async def wait_for_cancellation():
                    try:
                        await task_ref.current
                    except (asyncio.CancelledError, Exception):
                        pass

                try:
                    # Programar la espera de cancelación en el event loop actual
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Crear una tarea que espere la cancelación sin bloquear
                        asyncio.create_task(wait_for_cancellation())
                except Exception:
                    # Si falla, al menos la tarea está cancelada
                    pass

        return cleanup

    return debounced_value
