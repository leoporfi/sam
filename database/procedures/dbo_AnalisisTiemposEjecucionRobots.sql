SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[AnalisisTiemposEjecucionRobots]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[AnalisisTiemposEjecucionRobots] AS' 
END

-- Crear o actualizar el Stored Procedure para análisis de tiempos de ejecución por robot
ALTER   PROCEDURE [dbo].[AnalisisTiemposEjecucionRobots]
    @ExcluirPorcentajeInferior DECIMAL(3,2) = 0.15,  -- 15% por defecto
    @ExcluirPorcentajeSuperior DECIMAL(3,2) = 0.85,  -- 85% por defecto
    @IncluirSoloCompletadas BIT = 1,                   -- 1 = Solo completadas, 0 = Todos los estados
	@MesesHaciaAtras INT = 1 
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Validar parámetros
    IF @ExcluirPorcentajeInferior >= @ExcluirPorcentajeSuperior
    BEGIN
        RAISERROR('El porcentaje inferior debe ser menor que el superior', 16, 1);
        RETURN;
    END;
    
    -- Análisis de tiempos de ejecución por robot excluyendo extremos
    WITH TiemposEjecucion AS (
        SELECT 
            e.RobotId,
            e.DeploymentId,
            e.FechaInicio,
            e.FechaFin,
            e.Estado,
            -- Calcular duración en minutos
            DATEDIFF(MINUTE, e.FechaInicio, e.FechaFin) AS DuracionMinutos,
            -- Calcular duración en segundos para mayor precisión
            DATEDIFF(SECOND, e.FechaInicio, e.FechaFin) AS DuracionSegundos
        FROM Ejecuciones e
        WHERE e.FechaInicio IS NOT NULL 
            AND e.FechaFin IS NOT NULL
			AND e.FechaInicio >= DATEADD(MONTH, -@MesesHaciaAtras, GETDATE())
            AND (@IncluirSoloCompletadas = 0 OR e.Estado IN ('COMPLETED', 'RUN_COMPLETED'))
            AND DATEDIFF(SECOND, e.FechaInicio, e.FechaFin) > 0  -- Duración positiva
    ),
    TiemposConRanking AS (
        SELECT 
            RobotId,
            DuracionMinutos,
            DuracionSegundos,
            -- Calcular posición y total de registros por robot
            ROW_NUMBER() OVER (PARTITION BY RobotId ORDER BY DuracionSegundos) AS Posicion,
            COUNT(*) OVER (PARTITION BY RobotId) AS TotalRegistros
        FROM TiemposEjecucion
    ),
    TiemposFiltrados AS (
        SELECT 
            RobotId,
            DuracionMinutos,
            DuracionSegundos,
            Posicion,
            TotalRegistros
        FROM TiemposConRanking
        WHERE Posicion > (TotalRegistros * @ExcluirPorcentajeInferior)
            AND Posicion <= (TotalRegistros * @ExcluirPorcentajeSuperior)
    )
    SELECT 
        tf.RobotId,
        r.Robot,  -- Nombre del robot desde la tabla Robots
        r.EsOnline,  -- Si el robot está online (bit)
        COUNT(*) AS EjecucionesAnalizadas,
        -- Mostrar también el total original para comparación
        MAX(tf.TotalRegistros) AS TotalEjecucionesOriginales,
        -- Porcentaje de ejecuciones incluidas en el análisis
        CAST((COUNT(*) * 100.0 / MAX(tf.TotalRegistros)) AS DECIMAL(5,2)) AS PorcentajeIncluido,
        -- Tiempo promedio POR EJECUCIÓN (sin extremos)
        AVG(CAST(tf.DuracionMinutos AS FLOAT)) AS TiempoPromedioPorEjecucionMinutos,
        -- Tiempo total acumulado de todas las ejecuciones analizadas
        SUM(CAST(tf.DuracionMinutos AS FLOAT)) AS TiempoTotalAcumuladoMinutos,
        -- Tiempo promedio en segundos
        AVG(CAST(tf.DuracionSegundos AS FLOAT)) AS TiempoPromedioPorEjecucionSegundos,
        -- Tiempo máximo y mínimo (después del filtro)
        MAX(tf.DuracionMinutos) AS TiempoMaximoPorEjecucionMinutos,
        MIN(tf.DuracionMinutos) AS TiempoMinimoPorEjecucionMinutos,
        -- Formatear tiempo promedio como HH:MM:SS
        CONVERT(VARCHAR(8), DATEADD(SECOND, AVG(CAST(tf.DuracionSegundos AS FLOAT)), 0), 108) AS TiempoPromedioPorEjecucionFormateado,
        -- Formatear tiempo total acumulado (máximo 24 horas, sino mostrará días)
        CASE 
            WHEN SUM(CAST(tf.DuracionSegundos AS FLOAT)) < 86400 THEN 
                CONVERT(VARCHAR(8), DATEADD(SECOND, SUM(CAST(tf.DuracionSegundos AS FLOAT)), 0), 108)
            ELSE 
                CONCAT(
                    CAST(SUM(CAST(tf.DuracionSegundos AS FLOAT)) / 86400 AS INT), 'd ',
                    CONVERT(VARCHAR(8), DATEADD(SECOND, CAST(SUM(CAST(tf.DuracionSegundos AS FLOAT)) AS BIGINT) % 86400, 0), 108)
                )
        END AS TiempoTotalAcumuladoFormateado,
        -- Mostrar el rango de percentiles incluidos
        CONCAT('P', CAST(@ExcluirPorcentajeInferior * 100 AS INT), ' - P', CAST(@ExcluirPorcentajeSuperior * 100 AS INT)) AS RangoPercentiles,
        -- Información adicional de performance
        STDEV(CAST(tf.DuracionSegundos AS FLOAT)) AS DesviacionEstandarSegundos,
        -- Fecha del análisis
        GETDATE() AS FechaAnalisis
    FROM TiemposFiltrados tf 
    INNER JOIN Robots r ON r.RobotId = tf.RobotId
    GROUP BY tf.RobotId, r.Robot, r.EsOnline
    ORDER BY TiempoPromedioPorEjecucionSegundos DESC;
END;

