CREATE   PROCEDURE [dbo].[ObtenerRobotsEjecutables]
AS
BEGIN
    SET NOCOUNT ON;
    SET LANGUAGE Spanish;
    DECLARE @FechaActual DATETIME = GETDATE();
    DECLARE @HoraActual TIME(0) = CAST(@FechaActual AS TIME(0));
    DECLARE @DiaDelMesActual INT = DAY(@FechaActual);
    DECLARE @UltimoDiaDelMes INT = DAY(EOMONTH(@FechaActual));
    DECLARE @DiaSemanaActual NVARCHAR(2) = UPPER(LEFT(DATENAME(WEEKDAY, @FechaActual), 2) COLLATE Latin1_General_CI_AI);
    DECLARE @FechaActualDate DATE = CAST(@FechaActual AS DATE);
    -- Tabla temporal para almacenar los resultados
    CREATE TABLE #ResultadosRobots (
        RobotId INT,
        EquipoId INT,
        UserId INT,
        Hora TIME(0),
        EsProgramado BIT,
        PrioridadBalanceo INT  -- Para ordenar por prioridad en caso de conflictos
    );
    -- =============================================
    -- PARTE 1: Robots Programados (Tradicionales - Una vez)
    -- =============================================
    INSERT INTO #ResultadosRobots (RobotId, EquipoId, UserId, Hora, EsProgramado, PrioridadBalanceo)
    SELECT
        R.RobotId,
        A.EquipoId,
        E.UserId,
        P.HoraInicio,
        1 AS EsProgramado,
        R.PrioridadBalanceo
    FROM Robots R
    INNER JOIN Asignaciones A ON R.RobotId = A.RobotId
    INNER JOIN Equipos E ON A.EquipoId = E.EquipoId
    INNER JOIN Programaciones P ON A.ProgramacionId = P.ProgramacionId
    CROSS APPLY (
        SELECT
            DATEADD(MINUTE, P.Tolerancia, P.HoraInicio) AS HoraFin,
            CASE
                WHEN @HoraActual < P.HoraInicio AND P.HoraInicio > '12:00'
                THEN CAST(DATEADD(DAY, -1, @FechaActual) AS DATE)
                ELSE @FechaActualDate
            END AS FechaTeoricaProgramacion
    ) Calc
    WHERE
        A.EsProgramado = 1
        AND R.Activo = 1
        AND P.Activo = 1
        AND (P.EsCiclico = 0 OR P.EsCiclico IS NULL)  -- Solo programaciones tradicionales (una vez)
        -- Validar ventana de fechas (si está definida)
        AND (
            (P.FechaInicioVentana IS NULL AND P.FechaFinVentana IS NULL)
            OR
            (@FechaActualDate >= ISNULL(P.FechaInicioVentana, @FechaActualDate)
             AND @FechaActualDate <= ISNULL(P.FechaFinVentana, @FechaActualDate))
        )
        -- Validar rango horario (si está definido)
        AND (
            (P.HoraFin IS NULL)
            OR
            (@HoraActual >= P.HoraInicio AND @HoraActual <= P.HoraFin)
            OR
            (P.HoraFin < P.HoraInicio AND (@HoraActual >= P.HoraInicio OR @HoraActual <= P.HoraFin))  -- Cruce medianoche
        )
        -- Lógica de Tiempos (Ventana de Tolerancia)
        AND (
            (
                (Calc.HoraFin >= P.HoraInicio AND @HoraActual BETWEEN P.HoraInicio AND Calc.HoraFin)
                OR
                (Calc.HoraFin < P.HoraInicio AND (@HoraActual >= P.HoraInicio OR @HoraActual <= Calc.HoraFin))
            )
            AND
            (
                (P.TipoProgramacion = 'Diaria')
                OR (P.TipoProgramacion = 'Semanal' AND UPPER(P.DiasSemana COLLATE Latin1_General_CI_AI) LIKE '%' + @DiaSemanaActual + '%')
                OR (P.TipoProgramacion = 'Mensual' AND P.DiaDelMes = @DiaDelMesActual)
                OR (P.TipoProgramacion = 'Especifica' AND P.FechaEspecifica = @FechaActualDate)
                OR (P.TipoProgramacion = 'RangoMensual'
                    AND ((P.DiaInicioMes IS NOT NULL AND P.DiaFinMes IS NOT NULL AND @DiaDelMesActual BETWEEN P.DiaInicioMes AND P.DiaFinMes)
                         OR (P.UltimosDiasMes IS NOT NULL AND @DiaDelMesActual > (@UltimoDiaDelMes - P.UltimosDiasMes))))
            )
        )
        -- Validación de duplicados
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones Ejec
            WHERE Ejec.RobotId = R.RobotId
              AND Ejec.EquipoId = A.EquipoId
              AND Ejec.Hora = P.HoraInicio
              AND CAST(Ejec.FechaInicio AS DATE) = Calc.FechaTeoricaProgramacion
        )
        -- No ejecutar si el equipo ya está ocupado
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
    -- =============================================
    -- PARTE 2: Robots Cíclicos con Ventanas
    -- =============================================
    INSERT INTO #ResultadosRobots (RobotId, EquipoId, UserId, Hora, EsProgramado, PrioridadBalanceo)
    SELECT
        R.RobotId,
        A.EquipoId,
        E.UserId,
        CASE WHEN P.IntervaloEntreEjecuciones IS NOT NULL THEN NULL ELSE P.HoraInicio END AS Hora,
        1 AS EsProgramado,
        R.PrioridadBalanceo
    FROM Robots R
    INNER JOIN Asignaciones A ON R.RobotId = A.RobotId
    INNER JOIN Equipos E ON A.EquipoId = E.EquipoId
    INNER JOIN Programaciones P ON A.ProgramacionId = P.ProgramacionId
    WHERE
        A.EsProgramado = 1
        AND R.Activo = 1
        AND P.Activo = 1
        AND P.EsCiclico = 1  -- Solo robots cíclicos
        -- Validar ventana de fechas
        AND (
            (P.FechaInicioVentana IS NULL AND P.FechaFinVentana IS NULL)
            OR
            (@FechaActualDate >= ISNULL(P.FechaInicioVentana, @FechaActualDate)
             AND @FechaActualDate <= ISNULL(P.FechaFinVentana, @FechaActualDate))
        )
        -- Validar rango horario
        AND (
            (P.HoraFin IS NULL)
            OR
            (@HoraActual >= P.HoraInicio AND @HoraActual <= P.HoraFin)
            OR
            (P.HoraFin < P.HoraInicio AND (@HoraActual >= P.HoraInicio OR @HoraActual <= P.HoraFin))
        )
        -- Validar tipo de programación (días de la semana, día del mes, etc.)
        AND (
            (P.TipoProgramacion = 'Diaria')
            OR (P.TipoProgramacion = 'Semanal' AND UPPER(P.DiasSemana COLLATE Latin1_General_CI_AI) LIKE '%' + @DiaSemanaActual + '%')
            OR (P.TipoProgramacion = 'Mensual' AND P.DiaDelMes = @DiaDelMesActual)
            OR (P.TipoProgramacion = 'RangoMensual'
                AND ((P.DiaInicioMes IS NOT NULL AND P.DiaFinMes IS NOT NULL AND @DiaDelMesActual BETWEEN P.DiaInicioMes AND P.DiaFinMes)
                     OR (P.UltimosDiasMes IS NOT NULL AND @DiaDelMesActual > (@UltimoDiaDelMes - P.UltimosDiasMes))))
        )
        -- Validar intervalo entre ejecuciones (si está definido)
        AND (
            P.IntervaloEntreEjecuciones IS NULL
            OR
            NOT EXISTS (
                SELECT 1
                FROM Ejecuciones Ejec
                WHERE Ejec.RobotId = R.RobotId
                  AND Ejec.EquipoId = A.EquipoId
                  AND Ejec.Estado IN ('COMPLETED', 'RUN_COMPLETED', 'RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED', 'COMPLETED_INFERRED')
                  AND Ejec.FechaFin IS NOT NULL
                  AND DATEDIFF(MINUTE, Ejec.FechaFin, @FechaActual) < P.IntervaloEntreEjecuciones
            )
        )
        -- No ejecutar si el equipo ya está ocupado
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
    -- =============================================
    -- PARTE 3: Robots Online (SIN CAMBIOS)
    -- =============================================
    INSERT INTO #ResultadosRobots (RobotId, EquipoId, UserId, Hora, EsProgramado, PrioridadBalanceo)
    SELECT
        R.RobotId,
        A.EquipoId,
        E.UserId,
        NULL AS Hora,
        0 AS EsProgramado,
        R.PrioridadBalanceo
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
    -- =============================================
    -- RESULTADO FINAL: Ordenar por prioridad y tipo
    -- =============================================
    SELECT
        Ord.RobotId,
        Rob.Robot,
        Ord.EquipoId,
        Eq.Equipo,
        Ord.UserId,
        Eq.UserName,
        Ord.Hora
    FROM (
        SELECT
            RobotId,
            EquipoId,
            UserId,
            Hora,
            EsProgramado,
            PrioridadBalanceo,
            ROW_NUMBER() OVER (
                PARTITION BY EquipoId
                ORDER BY EsProgramado DESC, PrioridadBalanceo ASC, Hora ASC
            ) AS RN
        FROM #ResultadosRobots
    ) AS Ord
    INNER JOIN dbo.Robots Rob ON Ord.RobotId = Rob.RobotId
    INNER JOIN dbo.Equipos Eq ON Ord.EquipoId = Eq.EquipoId
    WHERE Ord.RN = 1  -- Solo el de mayor prioridad por equipo
    ORDER BY Ord.EsProgramado DESC, Ord.PrioridadBalanceo ASC, Ord.Hora;
    DROP TABLE #ResultadosRobots;
END
