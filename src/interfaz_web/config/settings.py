# src/interfaz_web/config/settings.py
import os


class Settings:
    """
    Configuraciones centralizadas para la aplicación web.
    Lee desde variables de entorno si están disponibles, si no, usa valores por defecto.
    """

    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
