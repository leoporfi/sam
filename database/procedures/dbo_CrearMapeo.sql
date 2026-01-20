SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CrearMapeo]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[CrearMapeo] AS'
END
GO
ALTER PROCEDURE [dbo].[CrearMapeo]
    @Proveedor NVARCHAR(50),
    @NombreExterno NVARCHAR(255),
    @RobotId NVARCHAR(50),
    @Descripcion NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        INSERT INTO dbo.MapeoRobots (Proveedor, NombreExterno, RobotId, Descripcion)
        VALUES (@Proveedor, @NombreExterno, @RobotId, @Descripcion);

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        INSERT INTO dbo.ErrorLog (FechaHora, Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (GETDATE(), SUSER_NAME(), 'dbo.CrearMapeo', @ErrorMessage,
                '@Proveedor=' + ISNULL(@Proveedor, 'NULL') + ', @NombreExterno=' + ISNULL(@NombreExterno, 'NULL'));

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
