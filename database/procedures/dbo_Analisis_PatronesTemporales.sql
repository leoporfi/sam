SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Analisis_PatronesTemporales]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[Analisis_PatronesTemporales] AS'
END

-- Inicio de dbo_Analisis_PatronesTemporales.sql
ALTER   PROCEDURE [dbo].[Analisis_PatronesTemporales]
    @FechaInicio DATETIME = NULL,
    @FechaFin DATETIME = NULL,
    @RobotId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Si no se especifican fechas, usar los últimos 90 días para tener una buena muestra
    IF @FechaInicio IS NULL
        SET @FechaInicio = DATEADD(DAY, -90, GETDATE());

    IF @FechaFin IS NULL
        SET @FechaFin = GETDATE();

    -- CTE para unir ejecuciones actuales e históricas
    WITH TodasEjecuciones AS (
        SELECT
            RobotId,
            FechaInicio,
            FechaFin
        FROM dbo.Ejecuciones
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND (@RobotId IS NULL OR RobotId = @RobotId)

        UNION ALL

        SELECT
            RobotId,
            FechaInicio,
            FechaFin
        FROM dbo.Ejecuciones_Historico
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND (@RobotId IS NULL OR RobotId = @RobotId)
    )
    SELECT
        ((DATEPART(WEEKDAY, FechaInicio) + @@DATEFIRST - 2) % 7) + 1 AS DiaSemana, -- 1=Lunes, 7=Domingo (Normalizado)
        DATEPART(HOUR, FechaInicio) AS HoraDia,
        COUNT(*) AS CantidadEjecuciones,
        AVG(DATEDIFF(MINUTE, FechaInicio, ISNULL(FechaFin, GETDATE()))) AS DuracionPromedioMinutos
    FROM TodasEjecuciones
    GROUP BY ((DATEPART(WEEKDAY, FechaInicio) + @@DATEFIRST - 2) % 7) + 1, DATEPART(HOUR, FechaInicio)
    ORDER BY DiaSemana, HoraDia;
END;

GO
