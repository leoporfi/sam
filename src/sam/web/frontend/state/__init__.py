# sam/web/frontend/state/__init__.py
"""Módulo de estado global de la aplicación."""

from .app_context import AppContext, AppProvider, use_app_context

__all__ = ["AppContext", "AppProvider", "use_app_context"]

