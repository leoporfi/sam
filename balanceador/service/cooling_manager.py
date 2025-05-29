# SAM/balanceador/service/cooling_manager.py

import time
import logging
from typing import Dict, Set, Tuple, Any
from threading import RLock

logger = logging.getLogger("SAM.Balanceador.CoolingManager")

class CoolingManager:
    """
    Gestor de períodos de enfriamiento para evitar thrashing en las asignaciones/desasignaciones.
    
    Esta clase mantiene un registro de las operaciones recientes de asignación/desasignación
    y previene cambios frecuentes en la misma dirección para un mismo robot.
    """
    
    def __init__(self, cooling_period_seconds: int = 300):
        """
        Inicializa el gestor de enfriamiento.
        
        Args:
            cooling_period_seconds: Período de enfriamiento en segundos (default: 5 minutos)
        """
        self.cooling_period = cooling_period_seconds
        self._lock = RLock()
        
        # Mapas para registrar las últimas operaciones
        # {robot_id: (timestamp, operación, cantidad)}
        self._last_scale_up: Dict[int, Tuple[float, str, int]] = {}
        self._last_scale_down: Dict[int, Tuple[float, str, int]] = {}
        
        # Umbrales para considerar un cambio significativo
        self.scale_up_threshold = 0.3  # 30% más tickets justifica escalar
        self.scale_down_threshold = 0.4  # 40% menos tickets justifica desescalar
        
    def can_scale_up(self, robot_id: int, current_tickets: int, current_equipos: int) -> Tuple[bool, str]:
        """
        Determina si un robot puede escalar hacia arriba (asignar más equipos).
        
        Args:
            robot_id: ID del robot
            current_tickets: Cantidad actual de tickets
            current_equipos: Cantidad actual de equipos asignados
            
        Returns:
            Tuple[bool, str]: (puede_escalar, justificación)
        """
        with self._lock:
            now = time.time()
            
            # Si no hay equipos asignados y hay tickets, siempre permitir asignar al menos uno
            if current_equipos == 0 and current_tickets > 0:
                return True, "No hay equipos asignados y existen tickets pendientes"
            
            # Verificar si está en período de enfriamiento tras una asignación reciente
            if robot_id in self._last_scale_up:
                last_time, _, last_tickets = self._last_scale_up[robot_id]
                time_elapsed = now - last_time
                
                if time_elapsed < self.cooling_period:
                    # Verificar si el aumento de tickets justifica ignorar el enfriamiento
                    if last_tickets > 0 and current_tickets / last_tickets >= (1 + self.scale_up_threshold):
                        return True, f"Aumento significativo de tickets ({last_tickets} -> {current_tickets})"
                    
                    return False, f"En período de enfriamiento tras asignación reciente ({int(time_elapsed)}s < {self.cooling_period}s)"
            
            # Verificar si está en período de enfriamiento tras una desasignación reciente
            if robot_id in self._last_scale_down:
                last_time, _, _ = self._last_scale_down[robot_id]
                time_elapsed = now - last_time
                
                if time_elapsed < self.cooling_period:
                    return False, f"En período de enfriamiento tras desasignación reciente ({int(time_elapsed)}s < {self.cooling_period}s)"
            
            return True, "Fuera de período de enfriamiento"
    
    def can_scale_down(self, robot_id: int, current_tickets: int, current_equipos: int) -> Tuple[bool, str]:
        """
        Determina si un robot puede escalar hacia abajo (desasignar equipos).
        
        Args:
            robot_id: ID del robot
            current_tickets: Cantidad actual de tickets
            current_equipos: Cantidad actual de equipos asignados
            
        Returns:
            Tuple[bool, str]: (puede_desescalar, justificación)
        """
        with self._lock:
            now = time.time()
            
            # Si no hay tickets, siempre permitir desasignar
            if current_tickets == 0:
                return True, "No hay tickets pendientes"
            
            # Verificar si está en período de enfriamiento tras una desasignación reciente
            if robot_id in self._last_scale_down:
                last_time, _, last_tickets = self._last_scale_down[robot_id]
                time_elapsed = now - last_time
                
                if time_elapsed < self.cooling_period:
                    # Verificar si la disminución de tickets justifica ignorar el enfriamiento
                    if last_tickets > 0 and current_tickets / last_tickets <= (1 - self.scale_down_threshold):
                        return True, f"Disminución significativa de tickets ({last_tickets} -> {current_tickets})"
                    
                    return False, f"En período de enfriamiento tras desasignación reciente ({int(time_elapsed)}s < {self.cooling_period}s)"
            
            # Verificar si está en período de enfriamiento tras una asignación reciente
            if robot_id in self._last_scale_up:
                last_time, _, _ = self._last_scale_up[robot_id]
                time_elapsed = now - last_time
                
                if time_elapsed < self.cooling_period:
                    return False, f"En período de enfriamiento tras asignación reciente ({int(time_elapsed)}s < {self.cooling_period}s)"
            
            return True, "Fuera de período de enfriamiento"
    
    def register_scale_up(self, robot_id: int, tickets: int, equipos_asignados: int) -> None:
        """
        Registra una operación de escalado hacia arriba.
        
        Args:
            robot_id: ID del robot
            tickets: Cantidad de tickets en el momento de la asignación
            equipos_asignados: Cantidad de equipos asignados
        """
        with self._lock:
            self._last_scale_up[robot_id] = (time.time(), "ASIGNAR", tickets)
            logger.debug(f"Registrada operación de escalado UP para RobotId {robot_id}: {tickets} tickets, {equipos_asignados} equipos")
    
    def register_scale_down(self, robot_id: int, tickets: int, equipos_desasignados: int) -> None:
        """
        Registra una operación de escalado hacia abajo.
        
        Args:
            robot_id: ID del robot
            tickets: Cantidad de tickets en el momento de la desasignación
            equipos_desasignados: Cantidad de equipos desasignados
        """
        with self._lock:
            self._last_scale_down[robot_id] = (time.time(), "DESASIGNAR", tickets)
            logger.debug(f"Registrada operación de escalado DOWN para RobotId {robot_id}: {tickets} tickets, {equipos_desasignados} equipos")
