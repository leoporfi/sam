SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ActualizarRobotEstado]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ActualizarRobotEstado] AS'
END
GO
ALTER PROCEDURE [dbo].[ActualizarRobotEstado]
    @RobotId NVARCHAR(50),
    @Campo NVARCHAR(50),
    @Valor BIT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        IF @Campo NOT IN ('Activo', 'EsOnline')
        BEGIN
            RAISERROR ('Campo no válido.', 16, 1);
        END

        -- Regla de negocio: No se puede marcar como 'Online' si tiene programaciones activas
        IF @Campo = 'EsOnline' AND @Valor = 1
        BEGIN
            IF EXISTS (SELECT 1 FROM dbo.Programaciones WHERE RobotId = @RobotId AND Activo = 1)
            BEGIN
                RAISERROR ('No se puede marcar como Online un robot con programaciones activas.', 16, 1);
            END
        END

        DECLARE @SQL NVARCHAR(MAX);
        SET @SQL = 'UPDATE dbo.Robots SET ' + QUOTENAME(@Campo) + ' = @p_Valor WHERE RobotId = @p_RobotId';

        EXEC sp_executesql @SQL, N'@p_Valor BIT, @p_RobotId NVARCHAR(50)', @p_Valor = @Valor, @p_RobotId = @RobotId;

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
        VALUES (GETDATE(), SUSER_NAME(), 'dbo.ActualizarRobotEstado', @ErrorMessage,
                '@RobotId=' + ISNULL(@RobotId, 'NULL') + ', @Campo=' + ISNULL(@Campo, 'NULL'));

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
