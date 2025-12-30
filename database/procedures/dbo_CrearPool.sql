SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CrearPool]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[CrearPool] AS'
END
-- =============================================
-- Author:      LP
-- Create date: 2025-08-01
-- Description: Inserta un nuevo pool en la tabla dbo.Pools
--              y devuelve el registro recién creado.
-- =============================================
ALTER PROCEDURE [dbo].[CrearPool]
    @Nombre NVARCHAR(100),
    @Descripcion NVARCHAR(500)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Verificar que no exista un pool con el mismo nombre
    IF EXISTS (SELECT 1 FROM dbo.Pools WHERE Nombre = @Nombre)
    BEGIN
        RAISERROR ('Ya existe un pool con el nombre "%s".', 16, 1, @Nombre);
        RETURN;
    END

    BEGIN TRY
        INSERT INTO dbo.Pools (Nombre, Descripcion)
        -- La cláusula OUTPUT devuelve los datos de la fila insertada
        OUTPUT INSERTED.PoolId, INSERTED.Nombre, INSERTED.Descripcion, INSERTED.Activo
        VALUES (@Nombre, @Descripcion);
    END TRY
    BEGIN CATCH
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        RAISERROR (@ErrorMessage, 16, 1);
    END CATCH
END
