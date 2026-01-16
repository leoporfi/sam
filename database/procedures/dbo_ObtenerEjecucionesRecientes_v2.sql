CREATE   PROCEDURE [dbo].[ObtenerEjecucionesRecientes_v2]
    @Limit INT = 50,
    @CriticalOnly BIT = 1,
    @UmbralFijoMinutos INT = 25,
    @FactorUmbralDinamico FLOAT = 1.5
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('tempdb..#ResultadosAnalisis') IS NOT NULL DROP TABLE #ResultadosAnalisis;
    WITH TiemposPromedio AS (
        SELECT
            RobotId,
            AVG(DATEDIFF(MINUTE, FechaInicio, FechaFin)) AS TiempoPromedioMinutos,
            COUNT(*) AS CantidadEjecuciones
        FROM dbo.Ejecuciones
        WHERE FechaFin IS NOT NULL
            AND Estado IN ('RUN_COMPLETED', 'COMPLETED_INFERRED') -- Incluimos inferidos para promedio
            AND DATEDIFF(MINUTE, FechaInicio, FechaFin) > 0
        GROUP BY RobotId
        HAVING COUNT(*) >= 5
    ),
    CalculoEstado AS (
        SELECT
            e.EjecucionId AS Id,
            r.Robot,
            eq.Equipo,
            e.Estado,
            e.FechaInicio,
            e.FechaFin,
            DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) AS TiempoTranscurridoMinutos,
            CASE
                WHEN e.Estado IN ('RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED') THEN 'Fallo'
                WHEN e.Estado IN ('RUNNING', 'DEPLOYED') AND (
                    (tp.TiempoPromedioMinutos IS NOT NULL AND
                     DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) > tp.TiempoPromedioMinutos * @FactorUmbralDinamico)
                    OR
                    (tp.TiempoPromedioMinutos IS NULL AND
                     DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) > @UmbralFijoMinutos)
                ) THEN 'Demorada'
                WHEN e.Estado = 'QUEUED'
                     AND DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) > 5
                     AND NOT EXISTS (
                        SELECT 1 FROM dbo.Ejecuciones e2
                        WHERE e2.RobotId = e.RobotId AND e2.EquipoId = e.EquipoId
                            AND e2.Estado IN ('DEPLOYED', 'RUNNING') AND e2.FechaInicio >= e.FechaInicio
                     ) THEN 'Huerfana'
                ELSE 'Normal'
            END AS TipoCritico,
            CASE
                WHEN tp.TiempoPromedioMinutos IS NOT NULL THEN tp.TiempoPromedioMinutos * @FactorUmbralDinamico
                ELSE @UmbralFijoMinutos
            END AS UmbralUtilizadoMinutos,
            tp.TiempoPromedioMinutos
        FROM dbo.Ejecuciones e
        LEFT JOIN dbo.Robots r ON e.RobotId = r.RobotId
        LEFT JOIN dbo.Equipos eq ON e.EquipoId = eq.EquipoId
        LEFT JOIN TiemposPromedio tp ON e.RobotId = tp.RobotId
    )
    SELECT * INTO #ResultadosAnalisis FROM CalculoEstado;
    SELECT TOP (@Limit)
        Id, Robot, Equipo, Estado, FechaInicio, TipoCritico, 'ERROR RECIENTE' as Categoria
    FROM #ResultadosAnalisis
    WHERE TipoCritico = 'Fallo'
    ORDER BY FechaInicio DESC;
    SELECT TOP (@Limit)
        Id, Robot, Equipo, Estado, FechaInicio, TiempoTranscurridoMinutos,
        UmbralUtilizadoMinutos, TiempoPromedioMinutos, TipoCritico, 'POSIBLE DEMORA' as Categoria
    FROM #ResultadosAnalisis
    WHERE TipoCritico IN ('Demorada', 'Huerfana')
    ORDER BY TiempoTranscurridoMinutos DESC;
    DROP TABLE #ResultadosAnalisis;
END