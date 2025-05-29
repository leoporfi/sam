# SAM/balanceador/database/historico_client.py

import logging
from typing import Dict, Any, Optional
from common.database.sql_client import DatabaseConnector

logger = logging.getLogger("SAM.Balanceador.HistoricoClient")

class HistoricoBalanceoClient:
    """
    Cliente para registrar el histórico de decisiones de balanceo.
    """
    
    def __init__(self, db_connector: DatabaseConnector):
        """
        Inicializa el cliente con un conector de base de datos.
        
        Args:
            db_connector: Conector a la base de datos SAM
        """
        self.db = db_connector
    
    def registrar_decision_balanceo(
        self, 
        robot_id: int, 
        tickets_pendientes: int, 
        equipos_antes: int, 
        equipos_despues: int, 
        accion: str, 
        justificacion: Optional[str] = None
    ) -> bool:
        """
        Registra una decisión de balanceo en la tabla HistoricoBalanceo.
        
        Args:
            robot_id: ID del robot
            tickets_pendientes: Cantidad de tickets pendientes
            equipos_antes: Cantidad de equipos asignados antes del balanceo
            equipos_despues: Cantidad de equipos asignados después del balanceo
            accion: Acción tomada (ej. "ASIGNAR", "DESASIGNAR", "MANTENER")
            justificacion: Justificación de la decisión
            
        Returns:
            bool: True si se registró correctamente, False en caso contrario
        """
        try:
            query = """
            INSERT INTO dbo.HistoricoBalanceo 
            (RobotId, TicketsPendientes, EquiposAsignadosAntes, EquiposAsignadosDespues, AccionTomada, Justificacion)
            VALUES (?, ?, ?, ?, ?, ?);
            """
            
            self.db.ejecutar_consulta(
                query, 
                (robot_id, tickets_pendientes, equipos_antes, equipos_despues, accion, justificacion),
                es_select=False
            )
            
            logger.info(f"Registrada decisión de balanceo para RobotId {robot_id}: {accion}")
            return True
        except Exception as e:
            logger.error(f"Error al registrar decisión de balanceo: {e}", exc_info=True)
            return False
    
    def obtener_historico_robot(self, robot_id: int, limite: int = 10) -> list:
        """
        Obtiene el histórico de decisiones de balanceo para un robot específico.
        
        Args:
            robot_id: ID del robot
            limite: Cantidad máxima de registros a retornar
            
        Returns:
            list: Lista de registros históricos
        """
        try:
            query = """
            SELECT TOP (?) HistoricoId, FechaBalanceo, TicketsPendientes, 
                   EquiposAsignadosAntes, EquiposAsignadosDespues, AccionTomada, Justificacion
            FROM dbo.HistoricoBalanceo
            WHERE RobotId = ?
            ORDER BY FechaBalanceo DESC;
            """
            
            return self.db.ejecutar_consulta(query, (limite, robot_id), es_select=True) or []
        except Exception as e:
            logger.error(f"Error al obtener histórico de balanceo: {e}", exc_info=True)
            return []
