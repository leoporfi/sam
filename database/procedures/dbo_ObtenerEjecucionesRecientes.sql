SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerEjecucionesRecientes]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ObtenerEjecucionesRecientes] AS'
END
GO
ALTER PROCEDURE [dbo].[ObtenerEjecucionesRecientes]
    @Limit INT = 50,
    @CriticalOnly BIT = 1,
    @UmbralFijoMinutos INT = 25,
    @FactorUmbralDinamico FLOAT = 1.5
AS
BEGIN
    SET NOCOUNT ON;

    WITH TiemposPromedio AS (
        -- Calcular tiempo promedio por robot (solo si tiene suficiente historial)
        SELECT
            RobotId,
            AVG(DATEDIFF(MINUTE, FechaInicio, FechaFin)) AS TiempoPromedioMinutos,
            COUNT(*) AS CantidadEjecuciones
        FROM dbo.Ejecuciones
        WHERE FechaFin IS NOT NULL
          AND Estado = 'RUN_COMPLETED'
          AND DATEDIFF(MINUTE, FechaInicio, FechaFin) > 0
        GROUP BY RobotId
        HAVING COUNT(*) >= 5
    ),
    EjecucionesConEstado AS (
        SELECT
            e.EjecucionId AS Id,
            r.Robot,
            eq.Equipo,
            e.Estado,
            e.FechaInicio,
            e.FechaFin,
            DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) AS TiempoTranscurridoMinutos,
            CASE
                -- Fallos inmediatos
                WHEN e.Estado IN ('RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED') THEN 'Fallo'

                -- RUNNING o DEPLOYED demorados
                WHEN e.Estado IN ('RUNNING', 'DEPLOYED') AND (
                    (tp.TiempoPromedioMinutos IS NOT NULL AND
                     DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) > tp.TiempoPromedioMinutos * @FactorUmbralDinamico)
                    OR
                    (tp.TiempoPromedioMinutos IS NULL AND
                     DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) > @UmbralFijoMinutos)
                ) THEN 'Demorada'

                -- QUEUED huérfano (sin DEPLOYED/RUNNING correspondiente)
                WHEN e.Estado = 'QUEUED'
                     AND DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) > 5
                     AND NOT EXISTS (
                        SELECT 1 FROM dbo.Ejecuciones e2
                        WHERE e2.RobotId = e.RobotId
                          AND e2.EquipoId = e.EquipoId
                          AND e2.Estado IN ('DEPLOYED', 'RUNNING')
                          AND e2.FechaInicio >= e.FechaInicio
                     ) THEN 'Huerfana'

                ELSE NULL
            END AS TipoCritico,
            CASE
                WHEN tp.TiempoPromedioMinutos IS NOT NULL
                THEN tp.TiempoPromedioMinutos * @FactorUmbralDinamico
                ELSE @UmbralFijoMinutos
            END AS UmbralUtilizadoMinutos,
            CASE
                WHEN tp.TiempoPromedioMinutos IS NOT NULL THEN 'Dinámico'
                ELSE 'Fijo'
            END AS TipoUmbral,
            tp.TiempoPromedioMinutos AS TiempoPromedioRobotMinutos,
            CASE WHEN e.FechaFin IS NULL THEN 'Activa' ELSE 'Historico' END AS Origen
        FROM dbo.Ejecuciones e
        LEFT JOIN dbo.Robots r ON e.RobotId = r.RobotId
        LEFT JOIN dbo.Equipos eq ON e.EquipoId = eq.EquipoId
        LEFT JOIN TiemposPromedio tp ON e.RobotId = tp.RobotId
    )
    SELECT TOP (@Limit)
        *
    FROM EjecucionesConEstado
    WHERE
        (@CriticalOnly = 0 OR TipoCritico IS NOT NULL)
    ORDER BY
        CASE
            WHEN Estado IN ('RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED') THEN 1
            WHEN Estado IN ('RUNNING', 'DEPLOYED') THEN 2
            WHEN Estado = 'QUEUED' THEN 3
            ELSE 4
        END,
        FechaInicio DESC;
END
GO
