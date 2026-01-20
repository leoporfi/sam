SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CrearEquipoManual]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[CrearEquipoManual] AS'
END
GO
ALTER PROCEDURE [dbo].[CrearEquipoManual]
    @EquipoId INT,
    @Equipo NVARCHAR(100),
    @UserId NVARCHAR(100),
    @UserName NVARCHAR(100),
    @Licencia NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        IF EXISTS (SELECT 1 FROM dbo.Equipos WHERE EquipoId = @EquipoId)
        BEGIN
            RAISERROR ('El EquipoId ya existe.', 16, 1);
        END

        INSERT INTO dbo.Equipos (
            EquipoId, Equipo, UserId, UserName, Licencia,
            Activo_SAM, PermiteBalanceoDinamico
        )
        VALUES (
            @EquipoId, UPPER(@Equipo), @UserId, @UserName, @Licencia,
            1, 0
        );

        SELECT
            EquipoId, Equipo, UserName, Licencia,
            Activo_SAM, PermiteBalanceoDinamico,
            'N/A' AS RobotAsignado, 'N/A' AS Pool
        FROM dbo.Equipos
        WHERE EquipoId = @EquipoId;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        INSERT INTO dbo.ErrorLog (FechaHora, Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (GETDATE(), SUSER_NAME(), 'dbo.CrearEquipoManual', @ErrorMessage,
                '@EquipoId=' + CAST(@EquipoId AS VARCHAR) + ', @Equipo=' + ISNULL(@Equipo, 'NULL'));

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
