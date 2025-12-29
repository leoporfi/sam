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
    @HoraFin TIME = NULL,          -- Si viene NULL, se asume fin del día (Cuidado: esto bloquea todo el día)
    @FechaInicioVentana DATE = NULL,
    @FechaFinVentana DATE = NULL,
    @DiasSemana NVARCHAR(20) = NULL, -- Ej: 'Lu,Ma,Mi'
    @TipoProgramacion NVARCHAR(20),  -- 'Diaria', 'Semanal', 'Mensual', 'Especifica', 'RangoMensual'
    @DiaDelMes INT = NULL,
    @DiaInicioMes INT = NULL,
    @DiaFinMes INT = NULL,
    @UltimosDiasMes INT = NULL,
    @FechaEspecifica DATE = NULL,
    @ProgramacionId INT = NULL       -- Para excluirse a sí mismo en caso de actualizaciones (Edit)
AS
BEGIN
    SET NOCOUNT ON;

    ---------------------------------------------------------------------------
    -- 1. PREPARACIÓN DE DATOS
    ---------------------------------------------------------------------------
    -- NOTA: Si @HoraFin es NULL, se asume que el proceso ocupa hasta el final del día.
    -- Para usar la "Tolerancia", el SP padre (CrearProgramacion) debe sumar 
    -- la tolerancia a la HoraInicio y pasarla aquí en @HoraFin.
    DECLARE @HoraFinCalculada TIME = ISNULL(@HoraFin, '23:59:59');

    -- Tabla para devolver los conflictos encontrados
    -- (El SP padre suele capturar esto con INSERT INTO #ConflictosDetectados EXEC...)
    SELECT 
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
        A.EquipoId = @EquipoId      -- Verificamos solapamiento en el MISMO EQUIPO
        AND P.Activo = 1            -- Solo contra programaciones activas
        AND (@ProgramacionId IS NULL OR P.ProgramacionId <> @ProgramacionId) -- Excluirse a sí mismo

        -----------------------------------------------------------------------
        -- 2. VALIDACIÓN DE FECHAS (VIGENCIA)
        -----------------------------------------------------------------------
        -- Verificamos si los rangos de fechas de vigencia se tocan.
        -- Lógica: (StartA <= EndB) AND (EndA >= StartB)
        -- Manejamos ISNULL para fechas infinitas (NULL = siempre activo)
        AND (
            (@FechaInicioVentana IS NULL OR P.FechaFinVentana IS NULL OR @FechaInicioVentana <= P.FechaFinVentana)
            AND 
            (@FechaFinVentana IS NULL OR P.FechaInicioVentana IS NULL OR @FechaFinVentana >= P.FechaInicioVentana)
        )

        -----------------------------------------------------------------------
        -- 3. VALIDACIÓN DE HORARIOS (TIEMPO)
        -----------------------------------------------------------------------
        -- Verificamos intersección de horas en el día.
        -- Lógica: (StartA < EndB) AND (EndA > StartB)
        AND (
            @HoraInicio < ISNULL(P.HoraFin, '23:59:59') 
            AND 
            @HoraFinCalculada > P.HoraInicio
        )

        -----------------------------------------------------------------------
        -- 4. VALIDACIÓN DE TIPOS Y PATRONES (LÓGICA CRUZADA MEJORADA)
        -----------------------------------------------------------------------
        AND (
            -- CASO A: CRUCES DIRECTOS (Cualquier cosa 'Diaria' choca con todo)
            (@TipoProgramacion = 'Diaria' OR P.TipoProgramacion = 'Diaria')
            
            OR

            -- CASO B: SEMANAL vs SEMANAL (Coincidencia de días)
            (@TipoProgramacion = 'Semanal' AND P.TipoProgramacion = 'Semanal'
             AND EXISTS (
                SELECT 1 
                FROM STRING_SPLIT(@DiasSemana, ',') s1
                JOIN STRING_SPLIT(P.DiasSemana, ',') s2 ON s1.value = s2.value
             )
            )

            OR

            -- CASO C: MENSUAL vs MENSUAL (Mismo día del mes)
            (@TipoProgramacion = 'Mensual' AND P.TipoProgramacion = 'Mensual' 
             AND @DiaDelMes = P.DiaDelMes)

            OR

            -- CASO D: RANGO MENSUAL (Complejo: Solapamiento de rangos de días)
            (@TipoProgramacion = 'RangoMensual' AND P.TipoProgramacion = 'RangoMensual'
             AND (
                 -- Solapamiento de días numéricos (ej. 1 al 15 vs 10 al 20)
                 (@DiaInicioMes IS NOT NULL AND @DiaFinMes IS NOT NULL
                  AND P.DiaInicioMes IS NOT NULL AND P.DiaFinMes IS NOT NULL
                  AND NOT (@DiaFinMes < P.DiaInicioMes OR @DiaInicioMes > P.DiaFinMes))
                 OR
                 -- Solapamiento con "Ultimos días" (simplificado: asume conflicto si ambos existen)
                 (@UltimosDiasMes IS NOT NULL AND P.UltimosDiasMes IS NOT NULL)
             )
            )

            OR 

            -- CASO E: ESPECÍFICA (Una sola fecha)
            -- Si la nueva es específica, validamos si su fecha cae dentro de la ventana de la existente
            (@TipoProgramacion = 'Especifica' AND P.TipoProgramacion = 'Especifica'
             AND P.FechaEspecifica = @FechaEspecifica
            )
            
            -- NOTA: Faltaría validar cruces híbridos complejos (ej. Semanal vs Especifica).
            -- Actualmente, si tienes Semanal (Lunes) y una Especifica (un Lunes concreto),
            -- este bloque NO lo detecta a menos que agregues lógica de calendario.
            -- Por seguridad, se recomienda que 'Diaria' sea la única que bloquee transversalmente
            -- o asumir que el usuario gestiona las excepciones manualmente.
        );

END
GO