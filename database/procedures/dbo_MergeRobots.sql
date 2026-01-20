SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[MergeRobots]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[MergeRobots] AS'
END
-- =============================================
-- Author:      LP
-- Create date: 2025-08-01
-- Description: Sincroniza (actualiza o inserta) la tabla dbo.Robots
--              usando una lista de robots proporcionada como un TVP.
--              Sigue el estándar de manejo de errores y transacciones.
-- =============================================
ALTER PROCEDURE [dbo].[MergeRobots]
    @RobotList dbo.RobotListType READONLY
AS
BEGIN
    -- --- Adiciones para robustez y estándar ---
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- --- Lógica principal del MERGE ---
        MERGE dbo.Robots AS TARGET
        USING @RobotList AS SOURCE
        ON (TARGET.RobotId = SOURCE.RobotId)

        -- CUANDO EL ROBOT YA EXISTE Y ALGO CAMBIÓ
        WHEN MATCHED AND (TARGET.Robot <> SOURCE.Robot OR ISNULL(TARGET.Descripcion, '') <> ISNULL(SOURCE.Descripcion, '')) THEN
            UPDATE SET
                TARGET.Robot = SOURCE.Robot,
                TARGET.Descripcion = SOURCE.Descripcion

        -- CUANDO EL ROBOT ES NUEVO
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (RobotId, Robot, Descripcion)
            VALUES (SOURCE.RobotId, SOURCE.Robot, SOURCE.Descripcion);
            -- Las demás columnas se llenan con los valores DEFAULT de la tabla.

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        -- --- Manejo de errores estándar ---
        -- Si hay una transacción activa, se revierte.
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        -- Declaración de variables para el mensaje de error
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        -- Insertar el error en la tabla de log
        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'dbo.MergeRobots', @ErrorMessage, 'Input: @RobotList (Table-Valued Parameter)');

        -- Relanzar el error para que la aplicación cliente lo reciba
        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END

GO
