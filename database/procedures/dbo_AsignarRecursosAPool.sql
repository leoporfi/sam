-- 2. STORED PROCEDURE PARA ASIGNAR RECURSOS (VERSIÓN CORREGIDA)
CREATE PROCEDURE [dbo].[AsignarRecursosAPool]
    @PoolId INT,
    @RobotIds dbo.IdListType READONLY,
    @EquipoIds dbo.IdListType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF NOT EXISTS (SELECT 1 FROM dbo.Pools WHERE PoolId = @PoolId)
    BEGIN
        RAISERROR ('No se encontró un pool con el ID %d.', 16, 1, @PoolId);
        RETURN;
    END
    BEGIN TRY
        BEGIN TRANSACTION;
        -- Desasignar recursos que actualmente pertenecen a este pool
        UPDATE dbo.Robots SET PoolId = NULL WHERE PoolId = @PoolId;
        UPDATE dbo.Equipos SET PoolId = NULL WHERE PoolId = @PoolId;
        -- Asignar los nuevos recursos
        UPDATE R SET R.PoolId = @PoolId FROM dbo.Robots R INNER JOIN @RobotIds TVP ON R.RobotId = TVP.ID;
        UPDATE E SET E.PoolId = @PoolId, E.PermiteBalanceoDinamico = 1  FROM dbo.Equipos E INNER JOIN @EquipoIds TVP ON E.EquipoId = TVP.ID;
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        -- Log del error
        DECLARE @ErrorMessage_ASG NVARCHAR(4000) = ERROR_MESSAGE();
        -- No podemos serializar fácilmente los TVP, así que lo indicamos en el log.
        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'dbo.AsignarRecursosAPool', @ErrorMessage_ASG, CONCAT('@PoolId=', @PoolId, ', @RobotIds/EquipoIds: (TVP)'));
        -- Re-lanzar el error
        THROW;
    END CATCH
END