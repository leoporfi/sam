CREATE PROCEDURE [dbo].[ObtenerConfiguracion]
    @Clave NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT Valor FROM dbo.ConfiguracionSistema WHERE Clave = @Clave;
END
GO

CREATE PROCEDURE [dbo].[ActualizarConfiguracion]
    @Clave NVARCHAR(100),
    @Valor NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE dbo.ConfiguracionSistema
        SET Valor = @Valor
        WHERE Clave = @Clave;

        IF @@ROWCOUNT = 0
        BEGIN
            INSERT INTO dbo.ConfiguracionSistema (Clave, Valor)
            VALUES (@Clave, @Valor);
        END

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        INSERT INTO dbo.ErrorLog (FechaHora, Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (GETDATE(), SUSER_NAME(), 'dbo.ActualizarConfiguracion', @ErrorMessage,
                '@Clave=' + ISNULL(@Clave, 'NULL'));

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
