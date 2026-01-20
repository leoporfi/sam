SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CrearRobot]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[CrearRobot] AS'
END
GO
ALTER PROCEDURE [dbo].[CrearRobot]
    @RobotId NVARCHAR(50),
    @Robot NVARCHAR(100),
    @Descripcion NVARCHAR(MAX),
    @MinEquipos INT,
    @MaxEquipos INT,
    @PrioridadBalanceo INT,
    @TicketsPorEquipoAdicional INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        IF EXISTS (SELECT 1 FROM dbo.Robots WHERE RobotId = @RobotId)
        BEGIN
            RAISERROR ('El RobotId ya existe.', 16, 1);
        END

        INSERT INTO dbo.Robots (
            RobotId, Robot, Descripcion, MinEquipos, MaxEquipos,
            PrioridadBalanceo, TicketsPorEquipoAdicional, Activo, EsOnline
        )
        VALUES (
            @RobotId, @Robot, @Descripcion, @MinEquipos, @MaxEquipos,
            @PrioridadBalanceo, @TicketsPorEquipoAdicional, 1, 0
        );

        SELECT * FROM dbo.Robots WHERE RobotId = @RobotId;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        INSERT INTO dbo.ErrorLog (FechaHora, Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (GETDATE(), SUSER_NAME(), 'dbo.CrearRobot', @ErrorMessage,
                '@RobotId=' + ISNULL(@RobotId, 'NULL') + ', @Robot=' + ISNULL(@Robot, 'NULL'));

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
