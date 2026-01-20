SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ActualizarProgramacionSimple]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ActualizarProgramacionSimple] AS'
END
GO
ALTER PROCEDURE [dbo].[ActualizarProgramacionSimple]
    @ProgramacionId INT,
    @TipoProgramacion NVARCHAR(20),
    @HoraInicio TIME,
    @DiasSemana NVARCHAR(20) = NULL,
    @DiaDelMes INT = NULL,
    @FechaEspecifica DATE = NULL,
    @Tolerancia INT = NULL,
    @Activo BIT,
    @DiaInicioMes INT = NULL,
    @DiaFinMes INT = NULL,
    @UltimosDiasMes INT = NULL,
    -- NUEVOS PARÁMETROS para robots cíclicos con ventanas
    @EsCiclico BIT = NULL,
    @HoraFin TIME = NULL,
    @FechaInicioVentana DATE = NULL,
    @FechaFinVentana DATE = NULL,
    @IntervaloEntreEjecuciones INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Variables para cálculo de HoraFin
    DECLARE @FechaBase DATETIME;
    DECLARE @InicioFull DATETIME;
    DECLARE @FinFull DATETIME;
    DECLARE @HoraFinCalculada TIME;

    -------------------------------------------------------------------------
    -- CÁLCULO DE @HoraFin
    -------------------------------------------------------------------------
    SET @HoraFinCalculada = @HoraFin;

    -- Si no se especificó HoraFin, calcularla usando la Tolerancia
    IF @HoraFinCalculada IS NULL AND @Tolerancia IS NOT NULL AND @Tolerancia > 0
    BEGIN
        SET @FechaBase = CAST(GETDATE() AS DATE);
        SET @InicioFull = DATEADD(MINUTE, DATEDIFF(MINUTE, 0, @HoraInicio), @FechaBase);
        SET @FinFull = DATEADD(MINUTE, @Tolerancia, @InicioFull);

        IF CAST(@FinFull AS DATE) > CAST(@InicioFull AS DATE)
            SET @HoraFinCalculada = '23:59:59';
        ELSE
            SET @HoraFinCalculada = CAST(@FinFull AS TIME);
    END
    -------------------------------------------------------------------------

    UPDATE dbo.Programaciones
    SET
        TipoProgramacion = @TipoProgramacion,
        HoraInicio = @HoraInicio,
        HoraFin = ISNULL(@HoraFinCalculada, @HoraFin),  -- ✅ Usar la calculada
        DiasSemana = CASE WHEN @TipoProgramacion = 'Semanal' THEN @DiasSemana ELSE NULL END,
        DiaDelMes = CASE WHEN @TipoProgramacion = 'Mensual' THEN @DiaDelMes ELSE NULL END,
        FechaEspecifica = CASE WHEN @TipoProgramacion = 'Especifica' THEN @FechaEspecifica ELSE NULL END,
        Tolerancia = @Tolerancia,
        Activo = @Activo,
        DiaInicioMes = CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @DiaInicioMes ELSE NULL END,
        DiaFinMes = CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @DiaFinMes ELSE NULL END,
        UltimosDiasMes = CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @UltimosDiasMes ELSE NULL END,
        EsCiclico = ISNULL(@EsCiclico, EsCiclico),
        FechaInicioVentana = @FechaInicioVentana,
        FechaFinVentana = @FechaFinVentana,
        IntervaloEntreEjecuciones = @IntervaloEntreEjecuciones,
        FechaModificacion = GETDATE()
    WHERE
        ProgramacionId = @ProgramacionId;

    IF @@ROWCOUNT = 0
    BEGIN
        RAISERROR('Programación no encontrada.', 16, 1);
    END
    ELSE
    BEGIN
        PRINT 'Programación actualizada exitosamente.';
    END
END

GO
