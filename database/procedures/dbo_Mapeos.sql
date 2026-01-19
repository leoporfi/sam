CREATE PROCEDURE [dbo].[ListarMapeos]
AS
BEGIN
    SET NOCOUNT ON;
    SELECT M.*, R.Robot AS RobotNombre
    FROM dbo.MapeoRobots M
    LEFT JOIN dbo.Robots R ON M.RobotId = R.RobotId;
END
GO

CREATE PROCEDURE [dbo].[CrearMapeo]
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

CREATE PROCEDURE [dbo].[EliminarMapeo]
    @MapeoId INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        DELETE FROM dbo.MapeoRobots WHERE MapeoId = @MapeoId;

        IF @@ROWCOUNT = 0
        BEGIN
            RAISERROR ('Mapeo no encontrado.', 16, 1);
        END

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        INSERT INTO dbo.ErrorLog (FechaHora, Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (GETDATE(), SUSER_NAME(), 'dbo.EliminarMapeo', @ErrorMessage,
                '@MapeoId=' + CAST(@MapeoId AS VARCHAR));

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
