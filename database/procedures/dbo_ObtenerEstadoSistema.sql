SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerEstadoSistema]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ObtenerEstadoSistema] AS'
END
GO
ALTER PROCEDURE [dbo].[ObtenerEstadoSistema]
    @PoolId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        'ESTADO_ACTUAL' AS TipoResultado,
        (SELECT COUNT(*) FROM Robots WHERE (@PoolId IS NULL OR PoolId = @PoolId)) AS TotalRobots,
        (SELECT COUNT(*) FROM Robots WHERE Activo = 1 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS RobotsActivos,
        (SELECT COUNT(*) FROM Robots WHERE Activo = 1 AND EsOnline = 1 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS RobotsOnline,
        (SELECT COUNT(*) FROM Robots WHERE Activo = 1 AND EsOnline = 0 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS RobotsProgramados,
        (SELECT COUNT(*) FROM Equipos WHERE (@PoolId IS NULL OR PoolId = @PoolId)) AS TotalEquipos,
        (SELECT COUNT(*) FROM Equipos WHERE Activo_SAM = 1 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS EquiposActivos,
        (SELECT COUNT(*) FROM Equipos WHERE PermiteBalanceoDinamico = 1 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS EquiposBalanceables,
        (SELECT COUNT(*) FROM Equipos WHERE Activo_SAM = 1 AND Equipo LIKE '%-VIA-%' AND (@PoolId IS NULL OR PoolId = @PoolId)) AS EquiposViale,
        (SELECT COUNT(*) FROM Equipos WHERE Activo_SAM = 1 AND Equipo LIKE '%-VEL-%' AND (@PoolId IS NULL OR PoolId = @PoolId)) AS EquiposVelez,
        (SELECT COUNT(*) FROM Programaciones P
            LEFT JOIN Robots R ON P.RobotId = R.RobotId
            WHERE P.Activo = 1 AND (@PoolId IS NULL OR R.PoolId = @PoolId)) AS ProgramacionesActivas,
        (SELECT COUNT(*) FROM Asignaciones A
            INNER JOIN Robots R ON A.RobotId = R.RobotId
            WHERE A.EsProgramado = 1 AND (@PoolId IS NULL OR R.PoolId = @PoolId)) AS AsignacionesProgramadas,
        (SELECT COUNT(*) FROM Asignaciones A
            INNER JOIN Robots R ON A.RobotId = R.RobotId
            WHERE A.Reservado = 1 AND (@PoolId IS NULL OR R.PoolId = @PoolId)) AS AsignacionesReservadas,
        (SELECT COUNT(*) FROM Ejecuciones E
            INNER JOIN Robots R ON E.RobotId = R.RobotId
            WHERE E.Estado IN ('DEPLOYED', 'RUNNING', 'QUEUED', 'PENDING_EXECUTION')
            AND (@PoolId IS NULL OR R.PoolId = @PoolId)) AS EjecucionesActivas,
        (SELECT COUNT(DISTINCT E.RobotId) FROM Ejecuciones E
            INNER JOIN Robots R ON E.RobotId = R.RobotId
            WHERE E.Estado IN ('DEPLOYED', 'RUNNING', 'QUEUED', 'PENDING_EXECUTION')
            AND (@PoolId IS NULL OR R.PoolId = @PoolId)) AS RobotsEjecutando,
        (SELECT COUNT(DISTINCT E.EquipoId) FROM Ejecuciones E
            INNER JOIN Robots R ON E.RobotId = R.RobotId
            WHERE E.Estado IN ('DEPLOYED', 'RUNNING', 'QUEUED', 'PENDING_EXECUTION')
            AND (@PoolId IS NULL OR R.PoolId = @PoolId)) AS EquiposEjecutando;
END

GO
