-- =============================================
-- Actualizar SP: ActualizarProgramacionSimple
-- Para soportar robots cíclicos con ventanas
-- =============================================

USE [SAM]
GO

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ActualizarProgramacionSimple]') AND type in (N'P', N'PC'))
    DROP PROCEDURE [dbo].[ActualizarProgramacionSimple]
GO

CREATE PROCEDURE [dbo].[ActualizarProgramacionSimple]
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

    UPDATE dbo.Programaciones
    SET
        TipoProgramacion = @TipoProgramacion,
        HoraInicio = @HoraInicio,
        HoraFin = @HoraFin,
        DiasSemana = CASE WHEN @TipoProgramacion = 'Semanal' THEN @DiasSemana ELSE NULL END,
        DiaDelMes = CASE WHEN @TipoProgramacion = 'Mensual' THEN @DiaDelMes ELSE NULL END,
        FechaEspecifica = CASE WHEN @TipoProgramacion = 'Especifica' THEN @FechaEspecifica ELSE NULL END,
        Tolerancia = @Tolerancia,
        Activo = @Activo,
        DiaInicioMes = CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @DiaInicioMes ELSE NULL END,
        DiaFinMes = CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @DiaFinMes ELSE NULL END,
        UltimosDiasMes = CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @UltimosDiasMes ELSE NULL END,
        EsCiclico = ISNULL(@EsCiclico, EsCiclico),  -- Solo actualizar si se proporciona
        FechaInicioVentana = @FechaInicioVentana,
        FechaFinVentana = @FechaFinVentana,
        IntervaloEntreEjecuciones = @IntervaloEntreEjecuciones,
        FechaModificacion = GETDATE()
    WHERE
        ProgramacionId = @ProgramacionId;
END
GO

PRINT 'SP ActualizarProgramacionSimple actualizado.'
GO
