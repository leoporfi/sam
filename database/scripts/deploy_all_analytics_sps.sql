-- Script Maestro de Despliegue de SPs de Analítica
-- Generado automáticamente
-- Inicio de dbo_Analisis_TasasExito.sql
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
GO
-- Inicio de dbo_Analisis_UtilizacionRecursos.sql
CREATE OR ALTER PROCEDURE [dbo].[Analisis_UtilizacionRecursos]
    @FechaInicio DATETIME = NULL,
    @FechaFin DATETIME = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- Si no se especifican fechas, usar los últimos 30 días
    IF @FechaInicio IS NULL
        SET @FechaInicio = DATEADD(DAY, -30, GETDATE());
    IF @FechaFin IS NULL
        SET @FechaFin = GETDATE();
    -- Calcular tiempo total disponible en minutos
    DECLARE @MinutosTotales INT;
    SET @MinutosTotales = DATEDIFF(MINUTE, @FechaInicio, @FechaFin);
    -- Evitar división por cero
    IF @MinutosTotales <= 0
        SET @MinutosTotales = 1;
    -- CTE para unir ejecuciones actuales e históricas
    WITH TodasEjecuciones AS (
        SELECT
            EquipoId,
            RobotId,
            FechaInicio,
            FechaFin
        FROM dbo.Ejecuciones
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND FechaFin IS NOT NULL -- Solo ejecuciones finalizadas
        UNION ALL
        SELECT
            EquipoId,
            RobotId,
            FechaInicio,
            FechaFin
        FROM dbo.Ejecuciones_Historico
        WHERE FechaInicio >= @FechaInicio AND FechaInicio <= @FechaFin
          AND FechaFin IS NOT NULL
    ),
    TiemposPorEquipo AS (
        SELECT
            e.EquipoId,
            e.RobotId,
            SUM(DATEDIFF(MINUTE, e.FechaInicio, e.FechaFin)) AS MinutosOcupados,
            COUNT(*) AS CantidadEjecuciones
        FROM TodasEjecuciones e
        GROUP BY e.EquipoId, e.RobotId
    )
    SELECT
        eq.Equipo,
        r.Robot,
        ISNULL(t.MinutosOcupados, 0) AS MinutosOcupados,
        @MinutosTotales AS MinutosDisponibles,
        CAST(ISNULL(t.MinutosOcupados, 0) * 100.0 / @MinutosTotales AS DECIMAL(5, 2)) AS PorcentajeUtilizacion,
        ISNULL(t.CantidadEjecuciones, 0) AS CantidadEjecuciones
    FROM dbo.Equipos eq
    CROSS JOIN dbo.Robots r -- Producto cartesiano para mostrar todos los pares posibles (opcional, o solo los que tienen actividad)
    LEFT JOIN TiemposPorEquipo t ON eq.EquipoId = t.EquipoId AND r.RobotId = t.RobotId
    WHERE
        eq.Activo_SAM = 1 -- Solo equipos activos
        AND r.Activo = 1 -- Solo robots activos
        AND (t.MinutosOcupados > 0 OR EXISTS (SELECT 1 FROM dbo.Asignaciones a WHERE a.EquipoId = eq.EquipoId AND a.RobotId = r.RobotId))
    ORDER BY PorcentajeUtilizacion DESC;
END;
GO
GO
-- Inicio de dbo_Analisis_PatronesTemporales.sql
CREATE OR ALTER PROCEDURE [dbo].[Analisis_PatronesTemporales]
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
GO
-- Inicio de dbo_Analisis_TiemposEjecucion.sql
CREATE OR ALTER PROCEDURE [dbo].[Analisis_TiemposEjecucion]
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
GO
GO
-- Inicio de dbo_Analisis_Dispersion.sql
CREATE OR ALTER PROCEDURE [dbo].[Analisis_Dispersion]
    @pRobot VARCHAR(100),
    @pFecha DATE = NULL,
    @pTop   INT  = NULL,
    @pModo  CHAR(1) = 'I' -- I = Inicio→Inicio (dispersión), F = Fin→Inicio (tiempo muerto)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @RobotId INT;
    -- Resolver RobotId a partir del nombre
    SELECT @RobotId = RobotId
    FROM   dbo.Robots
    WHERE  Robot = @pRobot;
    IF @RobotId IS NULL
    BEGIN
        RAISERROR('El robot ''%s'' no existe en la tabla maestra.', 16, 1, @pRobot);
        RETURN;
    END;
    /* 1. CTE base de ejecuciones */
    ;WITH Ejecs AS
    (
        SELECT  EjecucionID,
                UserId,
                EquipoId,
                RobotId,
                Estado,
                FechaInicio,
                FechaFin, -- <<< Se necesita el fin para el modo 'F'
                ROW_NUMBER() OVER (ORDER BY FechaInicio DESC) AS RN
        FROM    dbo.Ejecuciones
        WHERE   RobotId = @RobotId
          AND   (Estado = 'RUN_COMPLETED' OR Estado = 'COMPLETED')
          AND   (@pFecha IS NULL OR CAST(FechaInicio AS DATE) = @pFecha)
    ),
    Filtradas AS
    (
        SELECT * FROM Ejecs WHERE @pTop IS NULL OR RN <= @pTop
    ),
    ConDelta AS
    (
        SELECT *,
               /* ------- Lógica para elegir el tipo de delta ------- */
               CASE @pModo
                   WHEN 'I' THEN -- Modo 'I': Inicio -> Inicio (dispersión entre arranques)
                        DATEDIFF(SECOND,
                                 LAG(FechaInicio) OVER (PARTITION BY UserId ORDER BY FechaInicio),
                                 FechaInicio)
                   WHEN 'F' THEN -- Modo 'F': Fin -> Inicio (tiempo muerto real)
                        DATEDIFF(SECOND,
                                 LAG(FechaFin) OVER (PARTITION BY UserId ORDER BY FechaInicio),
                                 FechaInicio)
               END AS DeltaSec
        FROM Filtradas
    )
    SELECT * INTO #ConDelta FROM ConDelta;
    /* 2. RESUMEN: agrupado por equipo + robot */
    SELECT
            r.Robot,
            e.Equipo,
            COUNT(*)            AS Ejecuciones,
            MIN(cd.DeltaSec)    AS DeltaMin_Sec,
            MAX(cd.DeltaSec)    AS DeltaMax_Sec,
            AVG(cd.DeltaSec*1.0)   AS DeltaAvg_Sec,
            STDEV(cd.DeltaSec*1.0) AS DeltaDesv_Sec,
            @pModo              AS ModoCalculo
    INTO    #Resumen
    FROM    #ConDelta cd
    INNER JOIN dbo.Equipos e ON e.EquipoId = cd.EquipoId
    INNER JOIN dbo.Robots r ON r.RobotId = cd.RobotId
    WHERE   cd.DeltaSec IS NOT NULL
    GROUP BY r.Robot, e.Equipo;
	SELECT * FROM #Resumen ORDER BY Robot, Equipo;
    /* 3. DETALLE */
    SELECT
            cd.EjecucionID,
            cd.UserId,
            cd.EquipoId,
            e.Equipo,
            cd.RobotId,
            r.Robot,
            cd.Estado,
            cd.FechaInicio,
            cd.FechaFin,
            cd.DeltaSec,
            cd.DeltaSec / 60.0 AS DeltaMin,
            @pModo AS ModoCalculo
    FROM    #ConDelta cd
    INNER JOIN dbo.Equipos e ON e.EquipoId = cd.EquipoId
    INNER JOIN dbo.Robots r ON r.RobotId = cd.RobotId
    WHERE   cd.DeltaSec IS NOT NULL
    ORDER BY e.Equipo, cd.FechaInicio;
    DROP TABLE #Resumen;
    DROP TABLE #ConDelta;
END;
GO
-- Inicio de dbo_Analisis_Balanceador.sql
--              Proporciona métricas de rendimiento y actividad del sistema
-- Modified:    2025-10-16 - Corrección de duplicación de robots
-- =============================================
CREATE OR ALTER PROCEDURE [dbo].[Analisis_Balanceador]
    @FechaInicio DATETIME2(0) = NULL,
    @FechaFin DATETIME2(0) = NULL,
    @PoolId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    -- Establecer fechas por defecto si no se proporcionan
    IF @FechaInicio IS NULL
        SET @FechaInicio = DATEADD(DAY, -30, GETDATE());
    IF @FechaFin IS NULL
        SET @FechaFin = GETDATE();
    BEGIN TRY
        -- =============================================
        -- RESULT SET 1: MÉTRICAS GENERALES (CORREGIDO)
        -- =============================================
        SELECT
            'METRICAS_GENERALES' AS TipoResultado,
            COUNT(*) AS TotalAcciones,
            -- Clasificación con prioridad: DESASIGNAR primero, luego ASIGNAR
            -- Esto evita que "DESASIGNAR" se cuente como "ASIGNAR"
            SUM(CASE
                WHEN AccionTomada LIKE 'DESASIGNAR%' OR AccionTomada LIKE '%QUITAR%' THEN 0
                WHEN AccionTomada LIKE 'ASIGNAR%' OR AccionTomada LIKE '%AGREGAR%' THEN 1
                ELSE 0
            END) AS TotalAsignaciones,
            SUM(CASE
                WHEN AccionTomada LIKE 'DESASIGNAR%' OR AccionTomada LIKE '%QUITAR%' THEN 1
                ELSE 0
            END) AS TotalDesasignaciones,
            -- Nueva métrica: acciones no clasificadas
            SUM(CASE
                WHEN AccionTomada NOT LIKE 'ASIGNAR%'
                 AND AccionTomada NOT LIKE 'DESASIGNAR%'
                 AND AccionTomada NOT LIKE '%AGREGAR%'
                 AND AccionTomada NOT LIKE '%QUITAR%'
                THEN 1
                ELSE 0
            END) AS AccionesOtras,
            -- Métricas basadas en el delta real de equipos
            SUM(CASE WHEN (EquiposAsignadosDespues - EquiposAsignadosAntes) > 0 THEN 1 ELSE 0 END) AS AsignacionesReales,
            SUM(CASE WHEN (EquiposAsignadosDespues - EquiposAsignadosAntes) < 0 THEN 1 ELSE 0 END) AS DesasignacionesReales,
            SUM(CASE WHEN (EquiposAsignadosDespues - EquiposAsignadosAntes) = 0 THEN 1 ELSE 0 END) AS AccionesSinCambio,
            AVG(CAST(EquiposAsignadosDespues - EquiposAsignadosAntes AS FLOAT)) AS PromedioMovimientoNeto,
            COUNT(DISTINCT RobotId) AS RobotsAfectados,
            AVG(CAST(TicketsPendientes AS FLOAT)) AS PromedioTicketsPendientes
        FROM HistoricoBalanceo
        WHERE FechaBalanceo BETWEEN @FechaInicio AND @FechaFin
            AND (@PoolId IS NULL OR PoolId = @PoolId);
        -- =============================================
        -- RESULT SET 2: TRAZABILIDAD PARA EL GRÁFICO
        -- =============================================
        SELECT
            'TRAZABILIDAD' AS TipoResultado,
            FORMAT(H.FechaBalanceo, 'yyyy-MM-dd HH:mm:ss') AS Timestamp,
            H.RobotId,
            R.Robot AS RobotNombre,
            H.AccionTomada AS Accion,
            H.EquiposAsignadosAntes,
            H.EquiposAsignadosDespues,
            (H.EquiposAsignadosDespues - H.EquiposAsignadosAntes) AS MovimientoNeto,
            H.TicketsPendientes,
            H.Justificacion
        FROM HistoricoBalanceo H
        INNER JOIN Robots R ON H.RobotId = R.RobotId  -- INNER JOIN para evitar nulls
        WHERE H.FechaBalanceo BETWEEN @FechaInicio AND @FechaFin
            AND (@PoolId IS NULL OR H.PoolId = @PoolId)
        ORDER BY H.FechaBalanceo ASC;
        -- =============================================
        -- RESULT SET 3: RESUMEN DIARIO
        -- =============================================
        SELECT
            'RESUMEN_DIARIO' AS TipoResultado,
            CAST(FechaBalanceo AS DATE) AS Fecha,
            COUNT(*) AS TotalAcciones,
            SUM(CASE WHEN AccionTomada LIKE 'DESASIGNAR%' OR AccionTomada LIKE '%QUITAR%' THEN 0
                     WHEN AccionTomada LIKE 'ASIGNAR%' OR AccionTomada LIKE '%AGREGAR%' THEN 1
                     ELSE 0 END) AS Asignaciones,
            SUM(CASE WHEN AccionTomada LIKE 'DESASIGNAR%' OR AccionTomada LIKE '%QUITAR%' THEN 1
                     ELSE 0 END) AS Desasignaciones,
            AVG(CAST(TicketsPendientes AS FLOAT)) AS PromedioTickets,
            COUNT(DISTINCT RobotId) AS RobotsActivos
        FROM HistoricoBalanceo
        WHERE FechaBalanceo BETWEEN @FechaInicio AND @FechaFin
            AND (@PoolId IS NULL OR PoolId = @PoolId)
        GROUP BY CAST(FechaBalanceo AS DATE)
        ORDER BY Fecha ASC;
        -- =============================================
        -- RESULT SET 4: ANÁLISIS POR ROBOT (CORREGIDO)
        -- =============================================
        SELECT
            'ANALISIS_ROBOTS' AS TipoResultado,
            R.RobotId,
            R.Robot AS RobotNombre,
            ISNULL(Stats.TotalAcciones, 0) AS TotalAcciones,
            ISNULL(Stats.Asignaciones, 0) AS Asignaciones,
            ISNULL(Stats.Desasignaciones, 0) AS Desasignaciones,
            ISNULL(Stats.PromedioEquiposAntes, 0) AS PromedioEquiposAntes,
            ISNULL(Stats.PromedioEquiposDespues, 0) AS PromedioEquiposDespues,
            ISNULL(Stats.PromedioTickets, 0) AS PromedioTickets,
            Stats.UltimaAccion,
            ISNULL(Stats.CambiosEquipos, 0) AS CambiosEquipos
        FROM Robots R
        LEFT JOIN (
            SELECT
                H.RobotId,
                COUNT(*) AS TotalAcciones,
                SUM(CASE WHEN H.AccionTomada LIKE 'DESASIGNAR%' OR H.AccionTomada LIKE '%QUITAR%' THEN 0
                         WHEN H.AccionTomada LIKE 'ASIGNAR%' OR H.AccionTomada LIKE '%AGREGAR%' THEN 1
                         ELSE 0 END) AS Asignaciones,
                SUM(CASE WHEN H.AccionTomada LIKE 'DESASIGNAR%' OR H.AccionTomada LIKE '%QUITAR%' THEN 1
                         ELSE 0 END) AS Desasignaciones,
                AVG(CAST(H.EquiposAsignadosAntes AS FLOAT)) AS PromedioEquiposAntes,
                AVG(CAST(H.EquiposAsignadosDespues AS FLOAT)) AS PromedioEquiposDespues,
                AVG(CAST(H.TicketsPendientes AS FLOAT)) AS PromedioTickets,
                MAX(H.FechaBalanceo) AS UltimaAccion,
                SUM(CASE WHEN ABS(H.EquiposAsignadosDespues - H.EquiposAsignadosAntes) > 0 THEN 1 ELSE 0 END) AS CambiosEquipos
            FROM HistoricoBalanceo H
            WHERE H.FechaBalanceo BETWEEN @FechaInicio AND @FechaFin
                AND (@PoolId IS NULL OR H.PoolId = @PoolId)
            GROUP BY H.RobotId
        ) Stats ON R.RobotId = Stats.RobotId
        WHERE R.Activo = 1  -- Solo robots activos
            AND (@PoolId IS NULL OR R.PoolId = @PoolId)
            AND Stats.TotalAcciones IS NOT NULL  -- Solo incluir robots con actividad
        ORDER BY Stats.TotalAcciones DESC;
        -- =============================================
        -- RESULT SET 5: ESTADO ACTUAL DEL SISTEMA (CORREGIDO)
        -- =============================================
        SELECT
            'ESTADO_ACTUAL' AS TipoResultado,
            (SELECT COUNT(*) FROM Robots WHERE Activo = 1 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS RobotsActivos,
            (SELECT COUNT(*) FROM Robots WHERE EsOnline = 1 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS RobotsOnline,
            (SELECT COUNT(*) FROM Equipos WHERE Activo_SAM = 1 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS EquiposActivos,
            (SELECT COUNT(*) FROM Equipos WHERE PermiteBalanceoDinamico = 1 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS EquiposBalanceables,
            (SELECT COUNT(*) FROM Asignaciones A
             INNER JOIN Robots R ON A.RobotId = R.RobotId
             WHERE A.EsProgramado = 1 AND (@PoolId IS NULL OR R.PoolId = @PoolId)) AS AsignacionesProgramadas,
            (SELECT COUNT(*) FROM Asignaciones A
             INNER JOIN Robots R ON A.RobotId = R.RobotId
             WHERE A.Reservado = 1 AND (@PoolId IS NULL OR R.PoolId = @PoolId)) AS AsignacionesReservadas,
            (SELECT COUNT(*) FROM Ejecuciones E
             INNER JOIN Robots R ON E.RobotId = R.RobotId
             WHERE E.Estado IN ('DEPLOYED', 'RUNNING', 'QUEUED', 'PENDING_EXECUTION')
             AND (@PoolId IS NULL OR R.PoolId = @PoolId)) AS EjecucionesActivas;
        -- =============================================
        -- RESULT SET 6: DETECCIÓN DE THRASHING
        -- =============================================
        WITH ThrashingAnalysis AS (
            SELECT
                RobotId,
                FechaBalanceo,
                AccionTomada,
                EquiposAsignadosAntes,
                EquiposAsignadosDespues,
                LAG(AccionTomada) OVER (PARTITION BY RobotId ORDER BY FechaBalanceo) AS AccionAnterior,
                LAG(FechaBalanceo) OVER (PARTITION BY RobotId ORDER BY FechaBalanceo) AS FechaAnterior,
                DATEDIFF(MINUTE, LAG(FechaBalanceo) OVER (PARTITION BY RobotId ORDER BY FechaBalanceo), FechaBalanceo) AS MinutosDesdeUltimaAccion
            FROM HistoricoBalanceo
            WHERE FechaBalanceo BETWEEN @FechaInicio AND @FechaFin
                AND (@PoolId IS NULL OR PoolId = @PoolId)
        )
        SELECT
            'THRASHING_EVENTS' AS TipoResultado,
            COUNT(*) AS EventosThrashing,
            COUNT(DISTINCT RobotId) AS RobotsAfectados,
            AVG(CAST(MinutosDesdeUltimaAccion AS FLOAT)) AS PromedioMinutosEntreAcciones
        FROM ThrashingAnalysis
        WHERE MinutosDesdeUltimaAccion <= 5
            AND ((AccionTomada LIKE '%ASIGNAR%' AND AccionAnterior LIKE '%DESASIGNAR%')
                 OR (AccionTomada LIKE '%DESASIGNAR%' AND AccionAnterior LIKE '%ASIGNAR%'));
    END TRY
    BEGIN CATCH
        -- Manejo de errores
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @Parametros NVARCHAR(MAX) = FORMATMESSAGE(
            '@FechaInicio=%s, @FechaFin=%s, @PoolId=%s',
            ISNULL(CONVERT(NVARCHAR(20), @FechaInicio, 120), 'NULL'),
            ISNULL(CONVERT(NVARCHAR(20), @FechaFin, 120), 'NULL'),
            ISNULL(CAST(@PoolId AS NVARCHAR(10)), 'NULL')
        );
        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'ObtenerDashboardBalanceador', @ErrorMessage, @Parametros);
        THROW;
    END CATCH
END
GO
-- Inicio de dbo_Analisis_Callbacks.sql
-- Autor: Sistema SAM
-- Fecha: 2025-09-25
-- =============================================
CREATE OR ALTER PROCEDURE [dbo].[Analisis_Callbacks]
    @FechaInicio DATETIME2(0) = NULL,
    @FechaFin DATETIME2(0) = NULL,
    @RobotId INT = NULL,
    @IncluirDetalleHorario BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    -- Establecer fechas por defecto si no se proporcionan
    IF @FechaInicio IS NULL
        SET @FechaInicio = DATEADD(DAY, -7, GETDATE()); -- Últimos 7 días por defecto
    IF @FechaFin IS NULL
        SET @FechaFin = GETDATE();
    BEGIN TRY
        -- =============================================
        -- RESULT SET 1: MÉTRICAS GENERALES DEL SISTEMA
        -- =============================================
        SELECT
            'METRICAS_GENERALES' AS TipoResultado,
            -- Totales por mecanismo de finalización
            COUNT(*) AS TotalEjecuciones,
            SUM(EsCallbackExitoso) AS CallbacksExitosos,
            SUM(EsConciliadorExitoso) AS ConciliadorExitosos,
            SUM(EsConciliadorAgotado) AS ConciliadorAgotados,
            COUNT(CASE WHEN MecanismoFinalizacion = 'ACTIVA' THEN 1 END) AS EjecucionesActivas,
            -- Porcentajes de efectividad
            CAST(SUM(EsCallbackExitoso) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeCallbackExitoso,
            CAST(SUM(EsConciliadorExitoso) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeConciliadorExitoso,
            CAST(SUM(EsConciliadorAgotado) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeConciliadorAgotado,
            -- Métricas de rendimiento
            AVG(CAST(LatenciaActualizacionMinutos AS FLOAT)) AS LatenciaPromedioMinutos,
            MAX(LatenciaActualizacionMinutos) AS LatenciaMaximaMinutos,
            MIN(LatenciaActualizacionMinutos) AS LatenciaMinimaMinutos,
            -- Indicadores de problemas
            SUM(CallbackFallidoIndicador) AS CallbacksFallidos,
            SUM(ConciliadorProblemaIndicador) AS ProblemasConciliador,
            CAST(SUM(CallbackFallidoIndicador) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeCallbacksFallidos,
            -- Métricas de duración de ejecuciones
            AVG(CAST(DuracionEjecucionMinutos AS FLOAT)) AS DuracionPromedioMinutos,
            MAX(DuracionEjecucionMinutos) AS DuracionMaximaMinutos,
            -- Salud del sistema
            SUM(EjecucionExitosa) AS EjecucionesExitosas,
            SUM(EjecucionFallida) AS EjecucionesFallidas,
            CAST(SUM(EjecucionExitosa) * 100.0 / NULLIF(SUM(EjecucionExitosa) + SUM(EjecucionFallida), 0) AS DECIMAL(5,2)) AS PorcentajeExito
        FROM dbo.AnalisisRendimientoCallbacks
        WHERE FechaInicio BETWEEN @FechaInicio AND @FechaFin
            AND (@RobotId IS NULL OR RobotId = @RobotId);
        -- =============================================
        -- RESULT SET 2: DISTRIBUCIÓN POR CLASIFICACIÓN DE RENDIMIENTO
        -- =============================================
        SELECT
            'RENDIMIENTO_DISTRIBUCION' AS TipoResultado,
            ClasificacionRendimiento,
            COUNT(*) AS Cantidad,
            CAST(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS DECIMAL(5,2)) AS Porcentaje,
            AVG(CAST(LatenciaActualizacionMinutos AS FLOAT)) AS LatenciaPromedioMinutos
        FROM dbo.AnalisisRendimientoCallbacks
        WHERE FechaInicio BETWEEN @FechaInicio AND @FechaFin
            AND (@RobotId IS NULL OR RobotId = @RobotId)
            AND ClasificacionRendimiento != 'NO_APLICABLE'
        GROUP BY ClasificacionRendimiento
        ORDER BY
            CASE ClasificacionRendimiento
                WHEN 'EXCELENTE' THEN 1
                WHEN 'BUENO' THEN 2
                WHEN 'REGULAR' THEN 3
                WHEN 'DEFICIENTE' THEN 4
            END;
        -- =============================================
        -- RESULT SET 3: ANÁLISIS POR ROBOT
        -- =============================================
        SELECT
            'ANALISIS_POR_ROBOT' AS TipoResultado,
            R.RobotId,
            R.Robot AS RobotNombre,
            COUNT(*) AS TotalEjecuciones,
            SUM(A.EsCallbackExitoso) AS CallbacksExitosos,
            SUM(A.EsConciliadorExitoso) AS ConciliadorExitosos,
            SUM(A.EsConciliadorAgotado) AS ConciliadorAgotados,
            CAST(SUM(A.EsCallbackExitoso) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeCallbackExito,
            AVG(CAST(A.LatenciaActualizacionMinutos AS FLOAT)) AS LatenciaPromedioMinutos,
            AVG(CAST(A.DuracionEjecucionMinutos AS FLOAT)) AS DuracionPromedioMinutos,
            SUM(A.CallbackFallidoIndicador) AS CallbacksFallidos,
            SUM(A.EjecucionExitosa) AS EjecucionesExitosas,
            CAST(SUM(A.EjecucionExitosa) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeExito
        FROM dbo.AnalisisRendimientoCallbacks A
        INNER JOIN dbo.Robots R ON A.RobotId = R.RobotId
        WHERE A.FechaInicio BETWEEN @FechaInicio AND @FechaFin
            AND (@RobotId IS NULL OR A.RobotId = @RobotId)
        GROUP BY R.RobotId, R.Robot
        HAVING COUNT(*) >= 5 -- Solo robots con al menos 5 ejecuciones
        ORDER BY COUNT(*) DESC;
        -- =============================================
        -- RESULT SET 4: TENDENCIA DIARIA
        -- =============================================
        SELECT
            'TENDENCIA_DIARIA' AS TipoResultado,
            CAST(FechaInicio AS DATE) AS Fecha,
            COUNT(*) AS TotalEjecuciones,
            SUM(EsCallbackExitoso) AS CallbacksExitosos,
            SUM(EsConciliadorExitoso) AS ConciliadorExitosos,
            SUM(EsConciliadorAgotado) AS ConciliadorAgotados,
            AVG(CAST(LatenciaActualizacionMinutos AS FLOAT)) AS LatenciaPromedioMinutos,
            AVG(CAST(DuracionEjecucionMinutos AS FLOAT)) AS DuracionPromedioMinutos,
            SUM(CallbackFallidoIndicador) AS CallbacksFallidos,
            CAST(SUM(EsCallbackExitoso) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeCallbackExito
        FROM dbo.AnalisisRendimientoCallbacks
        WHERE FechaInicio BETWEEN @FechaInicio AND @FechaFin
            AND (@RobotId IS NULL OR RobotId = @RobotId)
        GROUP BY CAST(FechaInicio AS DATE)
        ORDER BY Fecha ASC;
        -- =============================================
        -- RESULT SET 5: ANÁLISIS HORARIO (si se solicita)
        -- =============================================
        IF @IncluirDetalleHorario = 1
        BEGIN
            SELECT
                'PATRON_HORARIO' AS TipoResultado,
                DATEPART(HOUR, FechaInicio) AS Hora,
                COUNT(*) AS TotalEjecuciones,
                SUM(EsCallbackExitoso) AS CallbacksExitosos,
                SUM(EsConciliadorExitoso) AS ConciliadorExitosos,
                AVG(CAST(LatenciaActualizacionMinutos AS FLOAT)) AS LatenciaPromedioMinutos,
                SUM(CallbackFallidoIndicador) AS CallbacksFallidos,
                CAST(SUM(EsCallbackExitoso) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeCallbackExito
            FROM dbo.AnalisisRendimientoCallbacks
            WHERE FechaInicio BETWEEN @FechaInicio AND @FechaFin
                AND (@RobotId IS NULL OR RobotId = @RobotId)
            GROUP BY DATEPART(HOUR, FechaInicio)
            ORDER BY Hora;
        END
        -- =============================================
        -- RESULT SET 6: CASOS PROBLEMÁTICOS RECIENTES
        -- =============================================
        SELECT TOP 20
            'CASOS_PROBLEMATICOS' AS TipoResultado,
            EjecucionId,
            DeploymentId,
            R.Robot AS RobotNombre,
            E.Equipo AS EquipoNombre,
            FechaInicio,
            FechaFin,
            Estado,
            MecanismoFinalizacion,
            LatenciaActualizacionMinutos,
            IntentosConciliadorFallidos,
            ClasificacionRendimiento,
            CASE
                WHEN CallbackFallidoIndicador = 1 AND ConciliadorProblemaIndicador = 1
                THEN 'CALLBACK_Y_CONCILIADOR_PROBLEMA'
                WHEN CallbackFallidoIndicador = 1
                THEN 'CALLBACK_FALLIDO'
                WHEN ConciliadorProblemaIndicador = 1
                THEN 'CONCILIADOR_PROBLEMA'
                WHEN MecanismoFinalizacion = 'CONCILIADOR_AGOTADO'
                THEN 'CONCILIADOR_AGOTADO'
                ELSE 'OTRO'
            END AS TipoProblema
        FROM dbo.AnalisisRendimientoCallbacks A
        LEFT JOIN dbo.Robots R ON A.RobotId = R.RobotId
        LEFT JOIN dbo.Equipos E ON A.EquipoId = E.EquipoId
        WHERE A.FechaInicio BETWEEN @FechaInicio AND @FechaFin
            AND (@RobotId IS NULL OR A.RobotId = @RobotId)
            AND (A.CallbackFallidoIndicador = 1
                 OR A.ConciliadorProblemaIndicador = 1
                 OR A.MecanismoFinalizacion = 'CONCILIADOR_AGOTADO'
                 OR A.ClasificacionRendimiento = 'DEFICIENTE')
        ORDER BY A.FechaInicio DESC;
    END TRY
    BEGIN CATCH
        -- Manejo de errores
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @Parametros NVARCHAR(MAX) = FORMATMESSAGE(
            '@FechaInicio=%s, @FechaFin=%s, @RobotId=%s, @IncluirDetalleHorario=%s',
            ISNULL(CONVERT(NVARCHAR(20), @FechaInicio, 120), 'NULL'),
            ISNULL(CONVERT(NVARCHAR(20), @FechaFin, 120), 'NULL'),
            ISNULL(CAST(@RobotId AS NVARCHAR(10)), 'NULL'),
            ISNULL(CAST(@IncluirDetalleHorario AS NVARCHAR(1)), 'NULL')
        );
        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'ObtenerDashboardCallbacks', @ErrorMessage, @Parametros);
        THROW;
    END CATCH
END
GO
-- Inicio de dbo_Analisis_Latencia.sql
CREATE OR ALTER PROCEDURE [dbo].[Analisis_Latencia]
    @Scope VARCHAR(20) = 'TODAS', -- 'ACTUALES', 'HISTORICAS', 'TODAS'
    @FechaDesde DATETIME = NULL,
    @FechaHasta DATETIME = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- Validar parámetros
    IF @Scope NOT IN ('ACTUALES', 'HISTORICAS', 'TODAS')
        SET @Scope = 'TODAS';
    IF @FechaDesde IS NULL
        SET @FechaDesde = DATEADD(DAY, -30, GETDATE()); -- Default últimos 30 días
    IF @FechaHasta IS NULL
        SET @FechaHasta = GETDATE();
    -- CTE para unificar datos
    WITH AllExecutions AS (
        SELECT
            EjecucionId,
            RobotId,
            EquipoId,
            FechaInicio AS FechaLanzamientoSAM,
            FechaInicioReal AS FechaInicioA360,
            FechaFin AS FechaFinA360,
            Estado,
            'ACTUAL' AS Origen
        FROM dbo.Ejecuciones
        WHERE (@Scope IN ('ACTUALES', 'TODAS'))
        UNION ALL
        SELECT
            EjecucionId,
            RobotId,
            EquipoId,
            FechaInicio AS FechaLanzamientoSAM,
            FechaInicioReal AS FechaInicioA360,
            FechaFin AS FechaFinA360,
            Estado,
            'HISTORICA' AS Origen
        FROM dbo.Ejecuciones_Historico
        WHERE (@Scope IN ('HISTORICAS', 'TODAS'))
    )
    SELECT
        EjecucionId,
        RobotId,
        EquipoId,
        FechaLanzamientoSAM,
        FechaInicioA360,
        FechaFinA360,
        Estado,
        Origen,
        DATEDIFF(SECOND, FechaLanzamientoSAM, FechaInicioA360) AS LatenciaInicioSegundos,
        DATEDIFF(SECOND, FechaInicioA360, FechaFinA360) AS DuracionEjecucionSegundos,
        DATEDIFF(SECOND, FechaLanzamientoSAM, FechaFinA360) AS DuracionTotalSegundos
    FROM AllExecutions
    WHERE
        FechaLanzamientoSAM BETWEEN @FechaDesde AND @FechaHasta
        AND FechaInicioA360 IS NOT NULL -- Solo analizar si tenemos el dato real
    ORDER BY FechaLanzamientoSAM DESC;
END
GO
GO
-- Inicio de dbo_Mantenimiento_MoverAHistorico.sql
CREATE OR ALTER PROCEDURE [dbo].[Mantenimiento_MoverAHistorico]
    @BatchSizeParam INT = 1000,         -- Tamaño del lote para mover/eliminar
    @DiasRetencionMover INT = 1,        -- Mover ejecuciones con más de X días de antigüedad
    @DiasRetencionPurga INT = 15,       -- Purgar del histórico ejecuciones con más de X días de antigüedad
    @MaxIterationsParam INT = 20000     -- Límite de seguridad para evitar bucles infinitos (muy alto por defecto)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @usuario VARCHAR(255) = SUSER_SNAME();
    -- =================================================================================
    -- PARTE 1: MOVER REGISTROS DE 'Ejecuciones' A 'Ejecuciones_Historico'
    -- =================================================================================
    DECLARE @rowsAffected INT = @BatchSizeParam;
    DECLARE @totalRowsMoved INT = 0;
    DECLARE @iterationCount INT = 0;
    DECLARE @EstadosFinalizados TABLE (Estado NVARCHAR(20) PRIMARY KEY);
    INSERT INTO @EstadosFinalizados (Estado) VALUES
    ('DEPLOY_FAILED'), ('RUN_ABORTED'), ('COMPLETED'),
    ('RUN_COMPLETED'), ('RUN_FAILED'), ('UNKNOWN');
    PRINT 'Iniciando proceso de movimiento de ejecuciones a la tabla histórica.';
    PRINT 'Tamaño de lote: ' + CAST(@BatchSizeParam AS VARCHAR(10));
    -- Bucle para procesar por lotes, ahora con el límite de iteraciones como parámetro de seguridad
    WHILE @rowsAffected = @BatchSizeParam AND @iterationCount < @MaxIterationsParam
    BEGIN
        SET @iterationCount = @iterationCount + 1;
        BEGIN TRY
            -- Usamos una tabla temporal para el lote, más segura que verificar con OBJECT_ID y hacer DROP/CREATE
            IF OBJECT_ID('tempdb..#LoteActual') IS NOT NULL DROP TABLE #LoteActual;
            -- Paso 1: Seleccionar el lote a procesar
            SELECT TOP (@BatchSizeParam)
                EjecucionId,
				DeploymentId,
                RobotId,
                EquipoId,
                UserId,
                Hora,
                FechaInicio,
                FechaFin,
                FechaInicioReal,
                Estado,
                FechaActualizacion,
                IntentosConciliadorFallidos,
                CallbackInfo
            INTO #LoteActual
            FROM dbo.Ejecuciones
            WHERE
                Estado IN (SELECT Estado FROM @EstadosFinalizados)
                AND COALESCE(FechaFin, FechaInicio) < DATEADD(day, -@DiasRetencionMover, GETDATE())
            ORDER BY EjecucionId; -- Orden determinístico es crucial
            SET @rowsAffected = @@ROWCOUNT;
            IF @rowsAffected = 0 BREAK;
            -- Paso 2 y 3 en una sola transacción para garantizar consistencia
            BEGIN TRANSACTION T_Move;
            INSERT INTO dbo.Ejecuciones_Historico (
                EjecucionId,
				DeploymentId,
                RobotId,
                EquipoId,
                UserId,
                Hora,
                FechaInicio,
                FechaFin,
                FechaInicioReal,
                Estado,
                FechaActualizacion,
                IntentosConciliadorFallidos,
                CallbackInfo
            )
            SELECT
                EjecucionId,
				DeploymentId,
                RobotId,
                EquipoId,
                UserId,
                Hora,
                FechaInicio,
                FechaFin,
                FechaInicioReal,
                Estado,
                FechaActualizacion,
                IntentosConciliadorFallidos,
                CallbackInfo
            FROM #LoteActual;
            DELETE e
            FROM dbo.Ejecuciones e
            INNER JOIN #LoteActual l ON e.EjecucionID = l.EjecucionID;
            COMMIT TRANSACTION T_Move;
            SET @totalRowsMoved = @totalRowsMoved + @rowsAffected;
            IF @iterationCount % 10 = 0
                PRINT 'Procesados ' + CAST(@totalRowsMoved AS VARCHAR(10)) + ' registros en ' + CAST(@iterationCount AS VARCHAR(10)) + ' lotes.';
            IF @rowsAffected = @BatchSizeParam WAITFOR DELAY '00:00:02';
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
			INSERT INTO dbo.ErrorLog (FechaHora ,Usuario, SPNombre, ErrorMensaje, Parametros)
            VALUES (
				GETDATE(),
				@usuario,
				'usp_MoverEjecucionesAHistorico_Mover',
				ERROR_MESSAGE() + ' (Iteración: ' + CAST(@iterationCount AS VARCHAR) + ')',
				'Lote: ' + CAST(@BatchSizeParam AS VARCHAR) + ', Registros movidos hasta ahora: ' + CAST(@totalRowsMoved AS VARCHAR)
			);
            IF ERROR_NUMBER() = 9002 -- Log lleno
            BEGIN
                PRINT 'Error de log lleno detectado. Abortando proceso.';
                BREAK;
            END
            ELSE
            BEGIN
                PRINT 'Error en iteración ' + CAST(@iterationCount AS VARCHAR) + ': ' + ERROR_MESSAGE();
                SET @rowsAffected = @BatchSizeParam;
            END
        END CATCH
    END
    PRINT 'Movimiento finalizado. Total de registros movidos: ' + CAST(@totalRowsMoved AS VARCHAR(10));
    IF @iterationCount >= @MaxIterationsParam
        PRINT 'ADVERTENCIA: El proceso se detuvo al alcanzar el límite máximo de iteraciones (' + CAST(@MaxIterationsParam AS VARCHAR) + '). Podrían quedar registros por mover.';
    -- =================================================================================
    -- PARTE 2: PURGAR REGISTROS ANTIGUOS DE 'Ejecuciones_Historico'
    -- =================================================================================
    DECLARE @purgeDate DATE = DATEADD(day, -@DiasRetencionPurga, GETDATE());
    DECLARE @totalRowsPurged INT = 0;
    DECLARE @purgeIterations INT = 0;
    PRINT 'Iniciando purga de registros históricos con más de ' + CAST(@DiasRetencionPurga AS VARCHAR) + ' días de antigüedad.';
    SET @rowsAffected = @BatchSizeParam;
    WHILE @rowsAffected = @BatchSizeParam AND @purgeIterations < @MaxIterationsParam
    BEGIN
        SET @purgeIterations = @purgeIterations + 1;
        BEGIN TRY
            BEGIN TRANSACTION T_Purge;
            DELETE TOP (@BatchSizeParam)
            FROM dbo.Ejecuciones_Historico
            WHERE FechaInicio < @purgeDate;
            SET @rowsAffected = @@ROWCOUNT;
            COMMIT TRANSACTION T_Purge;
            SET @totalRowsPurged = @totalRowsPurged + @rowsAffected;
            IF @purgeIterations % 10 = 0 AND @rowsAffected > 0
                PRINT 'Purgados ' + CAST(@totalRowsPurged AS VARCHAR(10)) + ' registros históricos.';
            IF @rowsAffected = @BatchSizeParam WAITFOR DELAY '00:00:01';
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
            INSERT INTO dbo.ErrorLog (FechaHora, Usuario, SPNombre, ErrorMensaje, Parametros)
            VALUES (
				GETDATE(),
				@usuario,
				'usp_MoverEjecucionesAHistorico_Purga',
                ERROR_MESSAGE() + ' (Iteración purga: ' + CAST(@purgeIterations AS VARCHAR) + ')',
                'Fecha límite: ' + CONVERT(VARCHAR, @purgeDate, 120)
			);
            IF ERROR_NUMBER() = 9002
            BEGIN
                PRINT 'Error de log lleno en purga. Abortando proceso.';
                BREAK;
            END
            ELSE
            BEGIN
                PRINT 'Error en purga, iteración ' + CAST(@purgeIterations AS VARCHAR) + ': ' + ERROR_MESSAGE();
                SET @rowsAffected = @BatchSizeParam;
            END
        END CATCH
    END
    PRINT 'Purga finalizada. Total de registros eliminados del histórico: ' + CAST(@totalRowsPurged AS VARCHAR(10));
     IF @purgeIterations >= @MaxIterationsParam
        PRINT 'ADVERTENCIA: La purga se detuvo al alcanzar el límite máximo de iteraciones (' + CAST(@MaxIterationsParam AS VARCHAR) + '). Podrían quedar registros por purgar.';
    -- Estadísticas finales
    PRINT '=== RESUMEN DE EJECUCIÓN ===';
    PRINT 'Registros movidos a histórico: ' + CAST(@totalRowsMoved AS VARCHAR(10));
    PRINT 'Registros purgados del histórico: ' + CAST(@totalRowsPurged AS VARCHAR(10));
    PRINT 'Proceso SAM completado exitosamente.';
END
GO