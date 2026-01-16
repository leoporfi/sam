-- Inicio de dbo_Analisis_TiemposEjecucion.sql
CREATE   PROCEDURE [dbo].[Analisis_TiemposEjecucion]
    @ExcluirPorcentajeInferior DECIMAL(3,2) = 0.15,  -- 15% por defecto
    @ExcluirPorcentajeSuperior DECIMAL(3,2) = 0.85,  -- 85% por defecto
    @IncluirSoloCompletadas BIT = 1,                   -- 1 = Solo completadas, 0 = Todos los estados
    @MesesHaciaAtras INT = 1,
    @DefaultRepeticiones INT = 1                     -- Valor por defecto si no se encuentra en Parametros
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
    -- INCLUYE: Datos actuales e históricos, FechaInicioReal, y número de repeticiones
    WITH EjecucionesUnificadas AS (
        -- Datos actuales
        SELECT
            e.EjecucionId,
            e.RobotId,
            e.DeploymentId,
            e.FechaInicio,
            e.FechaInicioReal,  -- Inicio real reportado por A360 (actualizado por Conciliador)
            e.FechaFin,
            e.Estado,
            'ACTUAL' AS Origen
        FROM dbo.Ejecuciones e
        WHERE e.FechaInicio IS NOT NULL
            AND e.FechaFin IS NOT NULL
            AND e.FechaInicio >= DATEADD(MONTH, -@MesesHaciaAtras, GETDATE())
            AND (@IncluirSoloCompletadas = 0 OR e.Estado IN ('COMPLETED', 'RUN_COMPLETED'))
            AND DATEDIFF(SECOND, e.FechaInicio, e.FechaFin) > 0
        UNION ALL
        -- Datos históricos
        SELECT
            eh.EjecucionId,
            eh.RobotId,
            eh.DeploymentId,
            eh.FechaInicio,
            eh.FechaInicioReal,
            eh.FechaFin,
            eh.Estado,
            'HISTORICA' AS Origen
        FROM dbo.Ejecuciones_Historico eh
        WHERE eh.FechaInicio IS NOT NULL
            AND eh.FechaFin IS NOT NULL
            AND eh.FechaInicio >= DATEADD(MONTH, -@MesesHaciaAtras, GETDATE())
            AND (@IncluirSoloCompletadas = 0 OR eh.Estado IN ('COMPLETED', 'RUN_COMPLETED'))
            AND DATEDIFF(SECOND, eh.FechaInicio, eh.FechaFin) > 0
    ),
    EjecucionesConRepeticiones AS (
        SELECT
            eu.EjecucionId,
            eu.RobotId,
            eu.DeploymentId,
            eu.FechaInicio,
            eu.FechaInicioReal,
            eu.FechaFin,
            eu.Estado,
            eu.Origen,
            -- Extraer número de repeticiones del JSON en Robots.Parametros
            -- Si no existe o es inválido, usar el valor por defecto pasado por parámetro
            CASE
                WHEN r.Parametros IS NOT NULL AND r.Parametros != ''
                THEN COALESCE(TRY_CAST(JSON_VALUE(r.Parametros, '$.in_NumRepeticion.number') AS INT), @DefaultRepeticiones)
                ELSE @DefaultRepeticiones
            END AS NumRepeticiones,
            -- Usar FechaInicioReal si está disponible, sino FechaInicio
            COALESCE(eu.FechaInicioReal, eu.FechaInicio) AS FechaInicioCalculada,
            -- Calcular latencia (delay entre disparo e inicio real)
            CASE
                WHEN eu.FechaInicioReal IS NOT NULL
                THEN DATEDIFF(SECOND, eu.FechaInicio, eu.FechaInicioReal)
                ELSE NULL
            END AS LatenciaInicioSegundos
        FROM EjecucionesUnificadas eu
        INNER JOIN dbo.Robots r ON r.RobotId = eu.RobotId
    ),
    TiemposEjecucion AS (
        SELECT
            RobotId,
            DeploymentId,
            FechaInicio,
            FechaInicioReal,
            FechaFin,
            Estado,
            Origen,
            NumRepeticiones,
            LatenciaInicioSegundos,
            -- Duración total de la ejecución (desde inicio real hasta fin)
            DATEDIFF(SECOND, FechaInicioCalculada, FechaFin) AS DuracionTotalSegundos,
            DATEDIFF(MINUTE, FechaInicioCalculada, FechaFin) AS DuracionTotalMinutos,
            -- Duración por repetición (tiempo total / número de repeticiones)
            CAST(DATEDIFF(SECOND, FechaInicioCalculada, FechaFin) AS FLOAT) /
                NULLIF(NumRepeticiones, 0) AS DuracionPorRepeticionSegundos,
            CAST(DATEDIFF(MINUTE, FechaInicioCalculada, FechaFin) AS FLOAT) /
                NULLIF(NumRepeticiones, 0) AS DuracionPorRepeticionMinutos
        FROM EjecucionesConRepeticiones
        WHERE DATEDIFF(SECOND, FechaInicioCalculada, FechaFin) > 0
    ),
    TiemposConRanking AS (
        SELECT
            RobotId,
            DuracionTotalMinutos,
            DuracionTotalSegundos,
            DuracionPorRepeticionMinutos,
            DuracionPorRepeticionSegundos,
            NumRepeticiones,
            LatenciaInicioSegundos,
            Origen,
            -- Calcular posición y total de registros por robot (usando tiempo por repetición)
            ROW_NUMBER() OVER (PARTITION BY RobotId ORDER BY DuracionPorRepeticionSegundos) AS Posicion,
            COUNT(*) OVER (PARTITION BY RobotId) AS TotalRegistros
        FROM TiemposEjecucion
    ),
    TiemposFiltrados AS (
        SELECT
            RobotId,
            DuracionTotalMinutos,
            DuracionTotalSegundos,
            DuracionPorRepeticionMinutos,
            DuracionPorRepeticionSegundos,
            NumRepeticiones,
            LatenciaInicioSegundos,
            Origen,
            Posicion,
            TotalRegistros
        FROM TiemposConRanking
        WHERE Posicion > (TotalRegistros * @ExcluirPorcentajeInferior)
            AND Posicion <= (TotalRegistros * @ExcluirPorcentajeSuperior)
    )
    SELECT
        tf.RobotId,
        r.Robot AS RobotNombre,
        r.EsOnline,
        COUNT(*) AS EjecucionesAnalizadas,
        MAX(tf.TotalRegistros) AS TotalEjecucionesOriginales,
        CAST((COUNT(*) * 100.0 / MAX(tf.TotalRegistros)) AS DECIMAL(5,2)) AS PorcentajeIncluido,
        -- MÉTRICAS DE TIEMPO POR REPETICIÓN (lo más importante)
        AVG(CAST(tf.DuracionPorRepeticionMinutos AS FLOAT)) AS TiempoPromedioPorRepeticionMinutos,
        AVG(CAST(tf.DuracionPorRepeticionSegundos AS FLOAT)) AS TiempoPromedioPorRepeticionSegundos,
        MAX(tf.DuracionPorRepeticionMinutos) AS TiempoMaximoPorRepeticionMinutos,
        MIN(tf.DuracionPorRepeticionMinutos) AS TiempoMinimoPorRepeticionMinutos,
        CONVERT(VARCHAR(8), DATEADD(SECOND, AVG(CAST(tf.DuracionPorRepeticionSegundos AS FLOAT)), 0), 108) AS TiempoPromedioPorRepeticionFormateado,
        -- MÉTRICAS DE TIEMPO TOTAL (por ejecución completa)
        AVG(CAST(tf.DuracionTotalMinutos AS FLOAT)) AS TiempoPromedioTotalMinutos,
        AVG(CAST(tf.DuracionTotalSegundos AS FLOAT)) AS TiempoPromedioTotalSegundos,
        SUM(CAST(tf.DuracionTotalMinutos AS FLOAT)) AS TiempoTotalAcumuladoMinutos,
        -- MÉTRICAS DE REPETICIONES
        AVG(CAST(tf.NumRepeticiones AS FLOAT)) AS PromedioRepeticiones,
        MAX(tf.NumRepeticiones) AS MaxRepeticiones,
        MIN(tf.NumRepeticiones) AS MinRepeticiones,
        -- MÉTRICAS DE LATENCIA (delay entre disparo e inicio real)
        AVG(CAST(tf.LatenciaInicioSegundos AS FLOAT)) AS LatenciaPromedioSegundos,
        AVG(CAST(tf.LatenciaInicioSegundos AS FLOAT) / 60.0) AS LatenciaPromedioMinutos,
        MAX(tf.LatenciaInicioSegundos) AS LatenciaMaximaSegundos,
        COUNT(CASE WHEN tf.LatenciaInicioSegundos IS NOT NULL THEN 1 END) AS EjecucionesConLatencia,
        -- ESTADÍSTICAS
        STDEV(CAST(tf.DuracionPorRepeticionSegundos AS FLOAT)) AS DesviacionEstandarSegundos,
        CONCAT('P', CAST(@ExcluirPorcentajeInferior * 100 AS INT), ' - P', CAST(@ExcluirPorcentajeSuperior * 100 AS INT)) AS RangoPercentiles,
        -- INFORMACIÓN DE ORIGEN DE DATOS
        SUM(CASE WHEN tf.Origen = 'ACTUAL' THEN 1 ELSE 0 END) AS EjecucionesActuales,
        SUM(CASE WHEN tf.Origen = 'HISTORICA' THEN 1 ELSE 0 END) AS EjecucionesHistoricas,
        GETDATE() AS FechaAnalisis
    FROM TiemposFiltrados tf
    INNER JOIN dbo.Robots r ON r.RobotId = tf.RobotId
    GROUP BY tf.RobotId, r.Robot, r.EsOnline
    ORDER BY TiempoPromedioPorRepeticionSegundos DESC;
END;