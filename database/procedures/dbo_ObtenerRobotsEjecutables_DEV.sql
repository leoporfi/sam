SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerRobotsEjecutables_DEV]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ObtenerRobotsEjecutables_DEV] AS'
END

ALTER PROCEDURE [dbo].[ObtenerRobotsEjecutables_DEV]
@f datetime
AS
BEGIN
    SET NOCOUNT ON;
    SET LANGUAGE Spanish;

    DECLARE @FechaActual DATETIME = @f;
    DECLARE @HoraActual TIME(0) = CAST(@FechaActual AS TIME(0));
    DECLARE @DiaDelMesActual INT = DAY(@FechaActual);
    DECLARE @UltimoDiaDelMes INT = DAY(EOMONTH(@FechaActual));
    DECLARE @DiaSemanaActual NVARCHAR(2) = UPPER(LEFT(DATENAME(WEEKDAY, @FechaActual), 2) COLLATE Latin1_General_CI_AI);

    -- Tabla temporal para almacenar los resultados
    CREATE TABLE #ResultadosRobots (
        RobotId INT,
        EquipoId INT,
        UserId INT,
        Hora TIME(0),
        EsProgramado BIT
    );

    -- Insertar robots programados elegibles (CORREGIDO)
    INSERT INTO #ResultadosRobots (RobotId, EquipoId, UserId, Hora, EsProgramado)
    SELECT
        R.RobotId,
        A.EquipoId,
        E.UserId,
        P.HoraInicio,
        1 AS EsProgramado
    FROM Robots R
    INNER JOIN Asignaciones A ON R.RobotId = A.RobotId
    INNER JOIN Equipos E ON A.EquipoId = E.EquipoId
    INNER JOIN Programaciones P ON A.ProgramacionId = P.ProgramacionId
    -- CALCULOS AUXILIARES (APPLY)
    CROSS APPLY (
        SELECT
            -- 1. Calculamos la hora de fin real (sumando tolerancia)
            DATEADD(MINUTE, P.Tolerancia, P.HoraInicio) AS HoraFin,

            -- 2. Determinamos a qué FECHA pertenece esta ejecución teórica
            CASE
                WHEN @HoraActual < P.HoraInicio AND P.HoraInicio > '12:00'
                THEN CAST(DATEADD(DAY, -1, @FechaActual) AS DATE)
                ELSE CAST(@FechaActual AS DATE)
            END AS FechaTeoricaProgramacion
    ) Calc
    WHERE
        A.EsProgramado = 1
        AND R.Activo = 1
        AND P.Activo = 1
        -- Lógica de Tiempos (Ventana de Tolerancia con soporte para cruce de medianoche)
        AND (
            (
                (Calc.HoraFin >= P.HoraInicio AND @HoraActual BETWEEN P.HoraInicio AND Calc.HoraFin) -- Caso Normal
                OR
                (Calc.HoraFin < P.HoraInicio AND (@HoraActual >= P.HoraInicio OR @HoraActual <= Calc.HoraFin)) -- Caso Medianoche
            )
            AND
            (
                -- Diaria
                (P.TipoProgramacion = 'Diaria')
                -- Semanal
                OR (P.TipoProgramacion = 'Semanal' AND UPPER(P.DiasSemana COLLATE Latin1_General_CI_AI) LIKE '%' + @DiaSemanaActual + '%')
                -- Mensual
                OR (P.TipoProgramacion = 'Mensual' AND P.DiaDelMes = @DiaDelMesActual)
                -- Específica
                OR (P.TipoProgramacion = 'Especifica' AND P.FechaEspecifica = CAST(@FechaActual AS DATE))
                -- Rango Mensual
                OR (P.TipoProgramacion = 'RangoMensual'
                    AND ((P.DiaInicioMes IS NOT NULL AND P.DiaFinMes IS NOT NULL AND @DiaDelMesActual BETWEEN P.DiaInicioMes AND P.DiaFinMes)
                         OR (P.UltimosDiasMes IS NOT NULL AND @DiaDelMesActual > (@UltimoDiaDelMes - P.UltimosDiasMes))))
            )
        )
        -- *** VALIDACIÓN DE DUPLICADOS ***
        -- Alias corregido de 'Exec' a 'Ejec'
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones Ejec
            WHERE Ejec.RobotId = R.RobotId
              AND Ejec.EquipoId = A.EquipoId
              AND Ejec.Hora = P.HoraInicio
              AND CAST(Ejec.FechaInicio AS DATE) = Calc.FechaTeoricaProgramacion
        )
        -- No ejecutar si el equipo ya está ocupado (Status Check)
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones Ejec
            WHERE Ejec.EquipoId = A.EquipoId
              AND (Ejec.Estado IN ('DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 'RUNNING', 'UPDATE', 'RUN_PAUSED')
                   OR (Ejec.Estado = 'UNKNOWN' AND Ejec.FechaUltimoUNKNOWN > DATEADD(HOUR, -2, GETDATE())))
        )
        -- No duplicar equipos en la misma vuelta del SP
        AND NOT EXISTS (
            SELECT 1 FROM #ResultadosRobots RR WHERE RR.EquipoId = A.EquipoId
        );

    -- Insertar robots online elegibles (SIN CAMBIOS)
    INSERT INTO #ResultadosRobots (RobotId, EquipoId, UserId, Hora, EsProgramado)
    SELECT
        R.RobotId,
        A.EquipoId,
        E.UserId,
        NULL AS Hora,
        0 AS EsProgramado
    FROM Robots R
    INNER JOIN Asignaciones A ON R.RobotId = A.RobotId
    INNER JOIN Equipos E ON A.EquipoId = E.EquipoId
    WHERE
        R.EsOnline = 1
        AND R.Activo = 1
        AND A.EsProgramado = 0
        AND NOT EXISTS (SELECT 1 FROM #ResultadosRobots RR WHERE RR.EquipoId = A.EquipoId)
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones Ejec
            WHERE Ejec.EquipoId = A.EquipoId
              AND (Ejec.Estado IN ('DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 'RUNNING', 'UPDATE', 'RUN_PAUSED')
                   OR (Ejec.Estado = 'UNKNOWN' AND Ejec.FechaUltimoUNKNOWN > DATEADD(HOUR, -2, GETDATE())))
        );

    -- Devolver los resultados
    SELECT RobotId, EquipoId, UserId, Hora
    FROM #ResultadosRobots
    ORDER BY EsProgramado DESC, Hora;

    DROP TABLE #ResultadosRobots;
END
