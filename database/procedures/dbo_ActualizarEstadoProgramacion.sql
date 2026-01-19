CREATE PROCEDURE [dbo].[ActualizarEstadoProgramacion]
    @ProgramacionId INT,
    @Activo BIT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE dbo.Programaciones
        SET Activo = @Activo
        WHERE ProgramacionId = @ProgramacionId;

        IF @@ROWCOUNT = 0
        BEGIN
            RAISERROR ('Programación no encontrada.', 16, 1);
        END

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        INSERT INTO dbo.ErrorLog (FechaHora, Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (GETDATE(), SUSER_NAME(), 'dbo.ActualizarEstadoProgramacion', @ErrorMessage,
                '@ProgramacionId=' + CAST(@ProgramacionId AS VARCHAR));

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
