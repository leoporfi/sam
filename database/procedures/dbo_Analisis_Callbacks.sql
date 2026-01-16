-- Inicio de dbo_Analisis_Callbacks.sql
-- Autor: Sistema SAM
-- Fecha: 2025-09-25
-- =============================================
CREATE   PROCEDURE [dbo].[Analisis_Callbacks]
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