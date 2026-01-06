CREATE OR ALTER PROCEDURE [dbo].[AnalisisPatronesTemporales]
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
        DATEPART(WEEKDAY, FechaInicio) AS DiaSemana, -- 1=Domingo, 7=Sábado (depende de configuración, pero usaremos esto)
        DATEPART(HOUR, FechaInicio) AS HoraDia,
        COUNT(*) AS CantidadEjecuciones,
        AVG(DATEDIFF(MINUTE, FechaInicio, ISNULL(FechaFin, GETDATE()))) AS DuracionPromedioMinutos
    FROM TodasEjecuciones
    GROUP BY DATEPART(WEEKDAY, FechaInicio), DATEPART(HOUR, FechaInicio)
    ORDER BY DiaSemana, HoraDia;
END;
GO
