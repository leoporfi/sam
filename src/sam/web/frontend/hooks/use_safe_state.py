# frontend/hooks/use_safe_state.py (Sugerencia para el futuro)
from reactpy import use_effect, use_ref


def use_safe_async():
    """Retorna una función que verifica si el componente sigue montado."""
    is_mounted = use_ref(True)

    @use_effect(dependencies=[])
    def lifecycle():
        is_mounted.current = True
        return lambda: setattr(is_mounted, "current", False)

    def safe_check():
        return is_mounted.current

    return safe_check
