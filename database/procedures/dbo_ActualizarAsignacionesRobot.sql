SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ActualizarAsignacionesRobot]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ActualizarAsignacionesRobot] AS'
END
GO
ALTER PROCEDURE [dbo].[ActualizarAsignacionesRobot]
    @RobotId NVARCHAR(50),
    @AssignIds dbo.IdListType READONLY,
    @UnassignIds dbo.IdListType READONLY,
    @AsignadoPor NVARCHAR(100) = 'WebApp'
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- 1. Verificar si el robot existe
        IF NOT EXISTS (SELECT 1 FROM dbo.Robots WHERE RobotId = @RobotId)
        BEGIN
            RAISERROR ('Robot no encontrado.', 16, 1);
        END

        -- 2. Desasignar equipos
        DELETE FROM dbo.Asignaciones
        WHERE RobotId = @RobotId
          AND EquipoId IN (SELECT ID FROM @UnassignIds);

        -- 3. Asignar nuevos equipos
        INSERT INTO dbo.Asignaciones (RobotId, EquipoId, EsProgramado, Reservado, AsignadoPor)
        SELECT @RobotId, ID, 0, 1, @AsignadoPor
        FROM @AssignIds
        WHERE ID NOT IN (SELECT EquipoId FROM dbo.Asignaciones WHERE RobotId = @RobotId);

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        INSERT INTO dbo.ErrorLog (FechaHora, Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (GETDATE(), SUSER_NAME(), 'dbo.ActualizarAsignacionesRobot', @ErrorMessage,
                '@RobotId=' + ISNULL(@RobotId, 'NULL'));

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
