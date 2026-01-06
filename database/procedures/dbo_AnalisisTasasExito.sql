CREATE OR ALTER PROCEDURE [dbo].[AnalisisTasasExito]
    @FechaInicio DATETIME = NULL,
    @FechaFin DATETIME = NULL,
    @RobotId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Si no se especifican fechas, usar los últimos 30 días
    IF @FechaInicio IS NULL
        SET @FechaInicio = DATEADD(DAY, -30, GETDATE());

    IF @FechaFin IS NULL
        SET @FechaFin = GETDATE();

    -- CTE para unir ejecuciones actuales e históricas
    WITH TodasEjecuciones AS (
        SELECT
            RobotId,
            EquipoId,
            Estado
        FROM dbo.Ejecuciones
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND (@RobotId IS NULL OR RobotId = @RobotId)

        UNION ALL

        SELECT
            RobotId,
            EquipoId,
            Estado
        FROM dbo.Ejecuciones_Historico
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND (@RobotId IS NULL OR RobotId = @RobotId)
    )

    -- Result Set 1: Resumen Global de Estados
    SELECT
        Estado,
        COUNT(*) AS Cantidad,
        CAST(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM TodasEjecuciones) AS DECIMAL(5,2)) AS Porcentaje
    FROM TodasEjecuciones
    GROUP BY Estado
    ORDER BY Cantidad DESC;

    -- Result Set 2: Top Tipos de Error (Basado en Estado)
    WITH TodasEjecucionesErrores AS (
        SELECT
            Estado
        FROM dbo.Ejecuciones
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND (@RobotId IS NULL OR RobotId = @RobotId)
          AND Estado IN ('ERROR', 'FINISHED_NOT_OK', 'CANCELED')

        UNION ALL

        SELECT
            Estado
        FROM dbo.Ejecuciones_Historico
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND (@RobotId IS NULL OR RobotId = @RobotId)
          AND Estado IN ('ERROR', 'FINISHED_NOT_OK', 'CANCELED')
    )
    SELECT TOP 10
        Estado AS MensajeError,
        COUNT(*) AS Cantidad
    FROM TodasEjecucionesErrores
    GROUP BY Estado
    ORDER BY Cantidad DESC;

    -- Result Set 3: Detalle por Robot
    WITH StatsPorRobot AS (
        SELECT
            r.Robot AS Robot,
            e.Equipo AS Equipo,
            COUNT(*) AS Total,
            SUM(CASE WHEN t.Estado = 'FINISHED' THEN 1 ELSE 0 END) AS Exitos,
            SUM(CASE WHEN t.Estado IN ('ERROR', 'FINISHED_NOT_OK', 'CANCELED') THEN 1 ELSE 0 END) AS Errores
        FROM TodasEjecuciones t
        LEFT JOIN dbo.Robots r ON t.RobotId = r.RobotId
        LEFT JOIN dbo.Equipos e ON t.EquipoId = e.EquipoId
        GROUP BY r.Robot, e.Equipo
    )
    SELECT
        ISNULL(Robot, 'Desconocido') AS Robot,
        ISNULL(Equipo, 'Desconocido') AS Equipo,
        Total,
        Exitos,
        Errores,
        CAST(Exitos * 100.0 / NULLIF(Total, 0) AS DECIMAL(5,2)) AS TasaExito
    FROM StatsPorRobot
    ORDER BY TasaExito ASC;

END;
GO
