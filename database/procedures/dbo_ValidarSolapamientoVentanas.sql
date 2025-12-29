SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ValidarSolapamientoVentanas]') AND type in (N'P', N'PC'))
BEGIN
    EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ValidarSolapamientoVentanas] AS' 
END
GO

ALTER PROCEDURE [dbo].[ValidarSolapamientoVentanas]
    @EquipoId INT,
    @HoraInicio TIME,
    @HoraFin TIME = NULL,
    @FechaInicioVentana DATE = NULL,
    @FechaFinVentana DATE = NULL,
    @DiasSemana NVARCHAR(20) = NULL,
    @TipoProgramacion NVARCHAR(20),
    @DiaDelMes INT = NULL,
    @DiaInicioMes INT = NULL,
    @DiaFinMes INT = NULL,
    @UltimosDiasMes INT = NULL,
    @FechaEspecifica DATE = NULL,
    @ProgramacionId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    ---------------------------------------------------------------------------
    -- 1. PREPARACIÓN DE DATOS
    ---------------------------------------------------------------------------
    -- NOTA: Si @HoraFin es NULL, se asume que el proceso ocupa hasta el final del día.
    -- El SP padre (CrearProgramacion) debe calcular @HoraFin usando la Tolerancia
    -- antes de llamar a este procedimiento.
    DECLARE @HoraFinCalculada TIME = ISNULL(@HoraFin, '23:59:59');

    ---------------------------------------------------------------------------
    -- 2. BUSCAR CONFLICTOS
    ---------------------------------------------------------------------------
    -- Devuelve todas las programaciones existentes que causan conflicto
    -- con la nueva programación que se está intentando crear.
    SELECT 
        A.EquipoId,
        P.ProgramacionId,
        R.Robot AS RobotNombre,
        P.TipoProgramacion,
        P.HoraInicio,
        ISNULL(P.HoraFin, '23:59:59') AS HoraFin,
        P.FechaInicioVentana,
        P.FechaFinVentana,
        P.DiasSemana,
        P.DiaDelMes,
        P.DiaInicioMes,
        P.DiaFinMes,
        P.UltimosDiasMes,
        CASE 
            WHEN P.EsCiclico = 1 THEN 'Cíclico'
            ELSE 'Una vez'
        END AS TipoEjecucion
    FROM dbo.Programaciones P
    INNER JOIN dbo.Asignaciones A ON P.ProgramacionId = A.ProgramacionId
    INNER JOIN dbo.Robots R ON P.RobotId = R.RobotId
    WHERE 
        -- Filtro básico: mismo equipo, programaciones activas
        A.EquipoId = @EquipoId
        AND P.Activo = 1
        AND (@ProgramacionId IS NULL OR P.ProgramacionId <> @ProgramacionId)

        -----------------------------------------------------------------------
        -- 3. VALIDACIÓN DE FECHAS (VIGENCIA)
        -----------------------------------------------------------------------
        -- Verificamos si los rangos de fechas de vigencia se solapan.
        -- Lógica: (StartA <= EndB) AND (EndA >= StartB)
        -- NULL = fecha infinita (siempre activa)
        AND (
            (@FechaInicioVentana IS NULL OR P.FechaFinVentana IS NULL OR @FechaInicioVentana <= P.FechaFinVentana)
            AND 
            (@FechaFinVentana IS NULL OR P.FechaInicioVentana IS NULL OR @FechaFinVentana >= P.FechaInicioVentana)
        )

        -----------------------------------------------------------------------
        -- 4. VALIDACIÓN DE HORARIOS (TIEMPO)
        -----------------------------------------------------------------------
        -- Verificamos intersección de horas en el día.
        -- Lógica: (StartA < EndB) AND (EndA > StartB)
        AND (
            @HoraInicio < ISNULL(P.HoraFin, '23:59:59') 
            AND 
            @HoraFinCalculada > P.HoraInicio
        )

        -----------------------------------------------------------------------
        -- 5. VALIDACIÓN DE TIPOS Y PATRONES (LÓGICA CRUZADA)
        -----------------------------------------------------------------------
        AND (
            -- CASO A: DIARIA choca con todo
            -- Una programación Diaria ejecuta todos los días, por lo que colisiona
            -- con cualquier otra programación que tenga solapamiento de horario.
            (@TipoProgramacion = 'Diaria' OR P.TipoProgramacion = 'Diaria')
            
            OR

            -- CASO B: SEMANAL vs SEMANAL
            -- Dos programaciones semanales chocan solo si tienen al menos un día en común.
            -- Ejemplo: Lu,Ma,Mi choca con Mi,Ju,Vi (tienen Mi en común)
            (@TipoProgramacion = 'Semanal' AND P.TipoProgramacion = 'Semanal'
             AND EXISTS (
                SELECT 1 
                FROM STRING_SPLIT(@DiasSemana, ',') s1
                JOIN STRING_SPLIT(P.DiasSemana, ',') s2 ON LTRIM(RTRIM(s1.value)) = LTRIM(RTRIM(s2.value))
             )
            )

            OR

            -- CASO C: MENSUAL vs MENSUAL
            -- Dos programaciones mensuales chocan solo si ejecutan el mismo día del mes.
            -- Ejemplo: día 5 choca con día 5, pero no con día 10
            (@TipoProgramacion = 'Mensual' AND P.TipoProgramacion = 'Mensual' 
             AND @DiaDelMes = P.DiaDelMes)

            OR

            -- CASO D: RANGO MENSUAL vs RANGO MENSUAL
            -- Dos rangos mensuales chocan si sus intervalos de días se solapan.
            (@TipoProgramacion = 'RangoMensual' AND P.TipoProgramacion = 'RangoMensual'
             AND (
                 -- Solapamiento de días numéricos (ej. 1-15 vs 10-20 → solapan del 10 al 15)
                 (@DiaInicioMes IS NOT NULL AND @DiaFinMes IS NOT NULL
                  AND P.DiaInicioMes IS NOT NULL AND P.DiaFinMes IS NOT NULL
                  AND NOT (@DiaFinMes < P.DiaInicioMes OR @DiaInicioMes > P.DiaFinMes))
                 OR
                 -- Solapamiento con "Últimos días del mes"
                 -- Si ambos usan "últimos X días", se asume conflicto potencial
                 (@UltimosDiasMes IS NOT NULL AND P.UltimosDiasMes IS NOT NULL)
             )
            )

            OR 

            -- CASO E: ESPECÍFICA vs ESPECÍFICA
            -- Dos programaciones específicas chocan solo si son para la misma fecha exacta.
            (@TipoProgramacion = 'Especifica' AND P.TipoProgramacion = 'Especifica'
             AND P.FechaEspecifica = @FechaEspecifica
            )
            
            -----------------------------------------------------------------------
            -- NOTA SOBRE LIMITACIONES:
            -----------------------------------------------------------------------
            -- Actualmente NO se validan cruces híbridos complejos como:
            -- - Semanal (Lunes) vs Específica (5/Enero/2026 que cae Lunes)
            -- - Mensual (día 15) vs Específica (15/Marzo/2026)
            -- - RangoMensual (1-15) vs Semanal (Lunes-Viernes)
            --
            -- Para implementar estos cruces se requeriría:
            -- 1. Lógica de calendario para determinar qué día de la semana cae una fecha
            -- 2. Validación de si una fecha específica cae dentro de un rango mensual
            -- 3. Mayor complejidad computacional
            --
            -- Por ahora, 'Diaria' es el único tipo que valida transversalmente contra
            -- todos los demás tipos. El resto de validaciones híbridas se gestionan
            -- manualmente o mediante políticas de uso.
        );

END
GO