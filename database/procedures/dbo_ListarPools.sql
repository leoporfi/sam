SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ListarPools]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ListarPools] AS'
END
-- =============================================
-- Author:      LP
-- Create date: 2025-08-01
-- Description: Obtiene una lista de todos los pools de recursos
--              junto con la cantidad de robots y equipos
--              asignados a cada uno. Incluye manejo de errores.
-- =============================================
ALTER PROCEDURE [dbo].[ListarPools]
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON; -- Asegura que la sesión se cierre si hay un error grave

    BEGIN TRY
        -- Lógica principal de la consulta
        SELECT
            p.PoolId,
            p.Nombre,
            p.Descripcion,
            p.Activo,
            (SELECT COUNT(*) FROM dbo.Robots r WHERE r.PoolId = p.PoolId) AS CantidadRobots,
            (SELECT COUNT(*) FROM dbo.Equipos e WHERE e.PoolId = p.PoolId) AS CantidadEquipos
        FROM
            dbo.Pools p
        ORDER BY
            p.Nombre ASC;

    END TRY
    BEGIN CATCH
        -- Manejo de errores estándar del proyecto
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        -- Insertar el error en la tabla de log
        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'dbo.ListarPools', @ErrorMessage, NULL);

        -- Relanzar el error para que la aplicación cliente lo reciba
        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END

GO
