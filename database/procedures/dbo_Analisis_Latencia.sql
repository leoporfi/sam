-- Inicio de dbo_Analisis_Latencia.sql
CREATE   PROCEDURE [dbo].[Analisis_Latencia]
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
