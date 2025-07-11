# src/interfaz_web/config/settings.py
from common.utils.config_manager import ConfigManager


class Settings:
    """
    Configuraciones centralizadas para la aplicación web.
    Lee desde la configuración del servicio 'interfaz_web' gestionada por ConfigManager.
    """

    # Obtenemos la configuración específica del servicio web
    _web_config = ConfigManager.get_interfaz_web_config()

    # Leemos el host y el puerto desde la configuración, con valores por defecto seguros
    _host = _web_config.get("host", "127.0.0.1")
    _port = _web_config.get("port", 8000)

    # Construimos la URL base de la API dinámicamente
    API_BASE_URL: str = f"http://{_host}:{_port}"
