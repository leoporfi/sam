-- =============================================
-- Stored Procedure: AnalisisTasasExito
-- Descripción: Análisis de tasas de éxito y tipos de error
--              en las ejecuciones de robots gestionadas por SAM.
--
-- IMPORTANTE: Este análisis mide el éxito/fallo de SAM en
--             lanzar y ejecutar robots (estados de A360),
--             NO el éxito/fallo del procesamiento de tickets
--             de negocio (que están en las bases de cada proveedor).
--
-- Estados de A360:
--   ÉXITO:  RUN_COMPLETED, COMPLETED
--   ERROR:  RUN_FAILED, DEPLOY_FAILED, RUN_ABORTED
--   OTROS:  RUNNING, DEPLOYED, QUEUED (se excluyen del análisis)
-- =============================================
CREATE OR ALTER PROCEDURE [dbo].[Analisis_TasasExito]
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
    -- Solo incluimos ejecuciones finalizadas (éxito o error)
    WITH TodasEjecuciones AS (
        SELECT
            RobotId,
            EquipoId,
            Estado
        FROM dbo.Ejecuciones
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND (@RobotId IS NULL OR RobotId = @RobotId)
          AND Estado IN ('RUN_COMPLETED', 'COMPLETED', 'RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED')

        UNION ALL

        SELECT
            RobotId,
            EquipoId,
            Estado
        FROM dbo.Ejecuciones_Historico
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND (@RobotId IS NULL OR RobotId = @RobotId)
          AND Estado IN ('RUN_COMPLETED', 'COMPLETED', 'RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED')
    )

    -- Result Set 1: Resumen Global de Estados
    SELECT
        Estado,
        COUNT(*) AS Cantidad,
        CAST(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM TodasEjecuciones), 0) AS DECIMAL(5,2)) AS Porcentaje
    FROM TodasEjecuciones
    GROUP BY Estado
    ORDER BY Cantidad DESC;

    -- Result Set 2: Top Tipos de Error/Fallo
    -- Analiza solo los estados de error/fallo de A360
    WITH TodasEjecucionesErrores AS (
        SELECT
            Estado
        FROM dbo.Ejecuciones
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND (@RobotId IS NULL OR RobotId = @RobotId)
          AND Estado IN ('RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED')

        UNION ALL

        SELECT
            Estado
        FROM dbo.Ejecuciones_Historico
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND (@RobotId IS NULL OR RobotId = @RobotId)
          AND Estado IN ('RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED')
    )
    SELECT TOP 10
        Estado AS MensajeError,
        COUNT(*) AS Cantidad
    FROM TodasEjecucionesErrores
    GROUP BY Estado
    ORDER BY Cantidad DESC;

    -- Result Set 3: Detalle por Robot
    -- Redefinir el CTE TodasEjecuciones para esta consulta
    WITH TodasEjecuciones AS (
        SELECT
            RobotId,
            EquipoId,
            Estado
        FROM dbo.Ejecuciones
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND (@RobotId IS NULL OR RobotId = @RobotId)
          AND Estado IN ('RUN_COMPLETED', 'COMPLETED', 'RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED')

        UNION ALL

        SELECT
            RobotId,
            EquipoId,
            Estado
        FROM dbo.Ejecuciones_Historico
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND (@RobotId IS NULL OR RobotId = @RobotId)
          AND Estado IN ('RUN_COMPLETED', 'COMPLETED', 'RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED')
    ),
    StatsPorRobot AS (
        SELECT
            r.Robot AS Robot,
            e.Equipo AS Equipo,
            COUNT(*) AS Total,
            SUM(CASE WHEN t.Estado IN ('RUN_COMPLETED', 'COMPLETED') THEN 1 ELSE 0 END) AS Exitos,
            SUM(CASE WHEN t.Estado IN ('RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED') THEN 1 ELSE 0 END) AS Errores
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
