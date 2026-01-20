SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ActualizarRobotDetalle]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ActualizarRobotDetalle] AS'
END
GO
ALTER PROCEDURE [dbo].[ActualizarRobotDetalle]
    @RobotId NVARCHAR(50),
    @Robot NVARCHAR(100),
    @Descripcion NVARCHAR(MAX),
    @MinEquipos INT,
    @MaxEquipos INT,
    @PrioridadBalanceo INT,
    @TicketsPorEquipoAdicional INT,
    @Parametros NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE dbo.Robots
        SET
            Robot = @Robot,
            Descripcion = @Descripcion,
            MinEquipos = @MinEquipos,
            MaxEquipos = @MaxEquipos,
            PrioridadBalanceo = @PrioridadBalanceo,
            TicketsPorEquipoAdicional = @TicketsPorEquipoAdicional,
            Parametros = @Parametros
        WHERE RobotId = @RobotId;

        IF @@ROWCOUNT = 0
        BEGIN
            RAISERROR ('Robot no encontrado.', 16, 1);
        END

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        INSERT INTO dbo.ErrorLog (FechaHora, Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (GETDATE(), SUSER_NAME(), 'dbo.ActualizarRobotDetalle', @ErrorMessage,
                '@RobotId=' + ISNULL(@RobotId, 'NULL'));

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
