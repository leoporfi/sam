import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import urllib3

# Suprimir advertencias de SSL inseguro
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CloudersClient:
    """Cliente para acceder a la API de Clouders y obtener tickets pendientes."""

    def __init__(self, config: Dict[str, Any], mapa_robots: Dict[str, str], logger_instance: Optional[logging.Logger] = None):
        """
        Inicializa el cliente de Clouders.

        Args:
            config: Diccionario con la configuración necesaria
            mapa_robots: Diccionario de mapeo entre nombres de robots
            logger_instance: Logger opcional personalizado
        """
        self.logger = logger_instance or logging.getLogger(f"SAM.balanceador.clients.{Path(__file__).stem}")
        self.base_url = config.get("clouders_api_url", "https://clouders.telefonica.com.ar")

        if "clouders_auth" not in config:
            raise ValueError("Se requiere autenticación para Clouders API")

        self.auth_header = config["clouders_auth"]
        self.timeout = config.get("api_timeout", 30)
        self.mapa_robots = mapa_robots or {}
        self.verify_ssl = config.get("verify_ssl", False)  # Nuevo parámetro

        if not self.auth_header:
            raise ValueError("Se requiere autenticación para Clouders API")

        if not self.verify_ssl:
            self.logger.warning("La verificación SSL está deshabilitada. Esto no es recomendado para producción.")

    def obtener_tickets_pendientes(self) -> List[Dict[str, Any]]:
        """
        Obtiene la cantidad de tickets pendientes por robot desde Clouders API.
        Los tickets ya vienen filtrados por prioridad ONLINE (4) y estado PENDING.

        Returns:
            List[Dict[str, Any]]: Lista de diccionarios con formato:
                [{"robot_name": "nombre_robot", "CantidadTickets": cantidad}, ...]

        Raises:
            requests.exceptions.RequestException: Si hay error en la comunicación con la API
        """
        endpoint = f"{self.base_url}/automatizacion/task/api/stats/pending_by_robot"
        headers = {"Accept": "application/json", "Authorization": self.auth_header}

        try:
            self.logger.debug(f"Consultando tickets pendientes en: {endpoint}")
            response = requests.get(
                endpoint,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,  # Agregar parámetro verify
            )
            response.raise_for_status()

            data = response.json()
            resultados = []

            for item in data:
                for robot_name, cantidad in item.items():
                    resultado = {
                        "robot_name": robot_name,
                        "CantidadTickets": cantidad,
                        "Priority": 4,  # Siempre es 4 (ONLINE) según el filtro del backend
                    }

                    # Aplicar mapeo de robots si existe
                    robot_sam = self.mapa_robots.get(robot_name)
                    if robot_sam:
                        resultado["robot_name_sam"] = robot_sam
                        self.logger.debug(f"Robot mapeado: {robot_name} → {robot_sam}")

                    resultados.append(resultado)

            self.logger.info(f"Obtenidos {len(resultados)} robots con tickets pendientes")
            return resultados

        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout al consultar tickets pendientes ({self.timeout}s)")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error al obtener tickets pendientes: {str(e)}")
            raise
