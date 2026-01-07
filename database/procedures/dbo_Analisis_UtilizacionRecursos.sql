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
