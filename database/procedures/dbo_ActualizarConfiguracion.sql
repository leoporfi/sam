SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ActualizarConfiguracion]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ActualizarConfiguracion] AS'
END
GO
ALTER PROCEDURE [dbo].[ActualizarConfiguracion]
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
GO
