-- Reemplaza los SPs de la respuesta anterior con estos:
-- 1. STORED PROCEDURE PARA ELIMINAR UN POOL (VERSIÓN CORREGIDA)
CREATE PROCEDURE [dbo].[EliminarPool]
    @PoolId INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF NOT EXISTS (SELECT 1 FROM dbo.Pools WHERE PoolId = @PoolId)
    BEGIN
        RAISERROR ('No se encontró un pool con el ID %d para eliminar.', 16, 1, @PoolId);
        RETURN;
    END
    BEGIN TRY
        BEGIN TRANSACTION;
        UPDATE dbo.Equipos SET PoolId = NULL WHERE PoolId = @PoolId;
        UPDATE dbo.Robots SET PoolId = NULL WHERE PoolId = @PoolId;
        DELETE FROM dbo.Pools WHERE PoolId = @PoolId;
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        -- Log del error
        DECLARE @ErrorMessage_DEL NVARCHAR(4000) = ERROR_MESSAGE();
        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'dbo.EliminarPool', @ErrorMessage_DEL, CONCAT('@PoolId=', @PoolId));
        -- Re-lanzar el error
        THROW;
    END CATCH
END
