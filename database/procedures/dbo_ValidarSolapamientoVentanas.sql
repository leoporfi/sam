SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ValidarSolapamientoVentanas]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ValidarSolapamientoVentanas] AS' 
END

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
    @ProgramacionId INT = NULL  -- Para excluir en actualizaciones
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Si HoraFin es NULL, asumimos que es el final del día (23:59:59)
    DECLARE @HoraFinCalculada TIME = ISNULL(@HoraFin, '23:59:59');
    
    -- Buscar programaciones activas del mismo equipo que puedan solaparse
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
    INNER JOIN dbo.Robots R ON P.RobotId = R.RobotId
    INNER JOIN dbo.Asignaciones A ON P.ProgramacionId = A.ProgramacionId
    WHERE A.EquipoId = @EquipoId
        AND P.Activo = 1
        AND (@ProgramacionId IS NULL OR P.ProgramacionId <> @ProgramacionId)
        -- Validar solapamiento de rango horario
        AND (
            -- Caso 1: HoraInicio nueva está dentro del rango existente
            (@HoraInicio >= P.HoraInicio AND @HoraInicio <= ISNULL(P.HoraFin, '23:59:59'))
            OR
            -- Caso 2: HoraFin nueva está dentro del rango existente
            (@HoraFinCalculada >= P.HoraInicio AND @HoraFinCalculada <= ISNULL(P.HoraFin, '23:59:59'))
            OR
            -- Caso 3: El rango nuevo contiene completamente el rango existente
            (@HoraInicio <= P.HoraInicio AND @HoraFinCalculada >= ISNULL(P.HoraFin, '23:59:59'))
        )
        -- Validar solapamiento de fechas (si ambas tienen ventanas de fecha)
        AND (
            (@FechaInicioVentana IS NULL AND @FechaFinVentana IS NULL)
            OR
            (P.FechaInicioVentana IS NULL AND P.FechaFinVentana IS NULL)
            OR
            (@FechaInicioVentana IS NOT NULL AND @FechaFinVentana IS NOT NULL 
             AND P.FechaInicioVentana IS NOT NULL AND P.FechaFinVentana IS NOT NULL
             AND NOT (@FechaFinVentana < P.FechaInicioVentana OR @FechaInicioVentana > P.FechaFinVentana))
        )
        -- Validar solapamiento según tipo de programación
        AND (
            -- Diaria: siempre se solapa si el rango horario coincide
            (@TipoProgramacion = 'Diaria' AND P.TipoProgramacion = 'Diaria')
            OR
            -- Semanal: verificar días de la semana
            (@TipoProgramacion = 'Semanal' AND P.TipoProgramacion = 'Semanal'
             AND (@DiasSemana IS NULL OR P.DiasSemana IS NULL 
                  OR EXISTS (SELECT 1 FROM STRING_SPLIT(@DiasSemana, ',') s1
                            CROSS JOIN STRING_SPLIT(P.DiasSemana, ',') s2
                            WHERE LTRIM(RTRIM(s1.value)) = LTRIM(RTRIM(s2.value))))
            )
            OR
            -- Mensual: verificar día del mes
            (@TipoProgramacion = 'Mensual' AND P.TipoProgramacion = 'Mensual'
             AND (@DiaDelMes IS NULL OR P.DiaDelMes IS NULL OR @DiaDelMes = P.DiaDelMes))
            OR
            -- RangoMensual: verificar rangos
            (@TipoProgramacion = 'RangoMensual' AND P.TipoProgramacion = 'RangoMensual'
             AND (
                 -- Solapamiento de rangos
                 (@DiaInicioMes IS NOT NULL AND @DiaFinMes IS NOT NULL
                  AND P.DiaInicioMes IS NOT NULL AND P.DiaFinMes IS NOT NULL
                  AND NOT (@DiaFinMes < P.DiaInicioMes OR @DiaInicioMes > P.DiaFinMes))
                 OR
                 -- Solapamiento con últimos días
                 (@UltimosDiasMes IS NOT NULL AND P.UltimosDiasMes IS NOT NULL)
                 OR
                 -- Rango vs últimos días (simplificado: siempre conflicto potencial)
                 ((@DiaInicioMes IS NOT NULL OR @DiaFinMes IS NOT NULL) 
                  AND P.UltimosDiasMes IS NOT NULL)
                 OR
                 (@UltimosDiasMes IS NOT NULL 
                  AND (P.DiaInicioMes IS NOT NULL OR P.DiaFinMes IS NOT NULL))
             )
            )
            OR
            -- Específica: verificar fecha específica
            (@TipoProgramacion = 'Especifica' AND P.TipoProgramacion = 'Especifica'
             AND P.FechaEspecifica IS NOT NULL
             AND (@FechaInicioVentana IS NULL OR P.FechaEspecifica BETWEEN @FechaInicioVentana AND ISNULL(@FechaFinVentana, P.FechaEspecifica)))
        )
    ORDER BY R.Robot, P.HoraInicio;
END

