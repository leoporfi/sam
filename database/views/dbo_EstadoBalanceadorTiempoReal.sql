-- =============================================
-- VISTA COMPLEMENTARIA: Estado en tiempo real
-- =============================================
CREATE   VIEW [dbo].[EstadoBalanceadorTiempoReal]
AS
SELECT
    R.RobotId,
    R.Robot,
    R.EsOnline,
    R.Activo,
    R.MinEquipos,
    R.MaxEquipos,
    R.PrioridadBalanceo,
    R.TicketsPorEquipoAdicional,
    ISNULL(EA.Equipos, 0) AS EquiposAsignados,
    CASE
        WHEN R.EsOnline = 1 THEN 'Online'
        WHEN EXISTS(SELECT 1 FROM Programaciones P WHERE P.RobotId = R.RobotId AND P.Activo = 1) THEN 'Programado'
        WHEN R.Activo = 0 THEN 'Inactivo'
        ELSE 'Disponible'
    END AS EstadoActual,
    CASE
        WHEN ISNULL(EA.Equipos, 0) < R.MinEquipos THEN 'Necesita más equipos'
        WHEN R.MaxEquipos > 0 AND ISNULL(EA.Equipos, 0) > R.MaxEquipos THEN 'Exceso de equipos'
        ELSE 'Balanceado'
    END AS EstadoBalanceo,
    -- Indicador de carga basado en ejecuciones activas
    ISNULL(EjecActivas.EjecucionesActivas, 0) AS EjecucionesActivas,
    -- Última actividad del balanceador
    HB.UltimaActividad,
    HB.UltimaAccion,
    P.Nombre AS Pool
FROM Robots R
LEFT JOIN EquiposAsignados EA ON R.Robot = EA.Robot
LEFT JOIN (
    SELECT
        RobotId,
        MAX(FechaBalanceo) AS UltimaActividad,
        FIRST_VALUE(AccionTomada) OVER (PARTITION BY RobotId ORDER BY FechaBalanceo DESC) AS UltimaAccion
    FROM HistoricoBalanceo
    WHERE FechaBalanceo >= DATEADD(DAY, -7, GETDATE())
    GROUP BY RobotId, AccionTomada, FechaBalanceo
) HB ON R.RobotId = HB.RobotId
LEFT JOIN (
    SELECT
        RobotId,
        COUNT(*) AS EjecucionesActivas
    FROM Ejecuciones
    WHERE Estado IN ('DEPLOYED', 'RUNNING', 'QUEUED', 'PENDING_EXECUTION', 'UPDATE', 'RUN_PAUSED')
    GROUP BY RobotId
) EjecActivas ON R.RobotId = EjecActivas.RobotId
LEFT JOIN Pools P ON R.PoolId = P.PoolId
WHERE R.Activo = 1;
