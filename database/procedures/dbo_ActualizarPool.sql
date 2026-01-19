CREATE PROCEDURE dbo.ActualizarPool
    @PoolId INT,
    @Nombre NVARCHAR(100),
    @Descripcion NVARCHAR(500)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    -- 1. Validar que el PoolId exista. Si no, lanzar un error claro.
    IF NOT EXISTS (SELECT 1 FROM dbo.Pools WHERE PoolId = @PoolId)
    BEGIN
        RAISERROR ('No se encontró un pool con el ID %d.', 16, 1, @PoolId);
        RETURN;
    END
    -- 2. Validar que el nuevo nombre no esté en uso por OTRO pool.
    IF EXISTS (SELECT 1 FROM dbo.Pools WHERE Nombre = @Nombre AND PoolId <> @PoolId)
    BEGIN
        RAISERROR ('El nombre "%s" ya está en uso por otro pool.', 16, 1, @Nombre);
        RETURN;
    END
    -- 3. Simplemente ejecutar el UPDATE. No necesitamos TRY/CATCH aquí
    --    porque XACT_ABORT ya maneja los errores, y las validaciones previenen
    --    los casos más comunes.
    UPDATE dbo.Pools
    SET
        Nombre = @Nombre,
        Descripcion = @Descripcion,
        FechaModificacion = GETDATE()
    WHERE
        PoolId = @PoolId;
END
