--              Proporciona métricas de rendimiento y actividad del sistema
-- Modified:    2025-10-16 - Corrección de duplicación de robots
-- =============================================
CREATE   PROCEDURE [dbo].[Analisis_Balanceador]
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