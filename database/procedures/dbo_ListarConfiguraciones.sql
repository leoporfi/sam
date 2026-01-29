CREATE PROCEDURE [dbo].[ListarConfiguraciones]
AS
BEGIN
    SET NOCOUNT ON;
    SELECT Clave, Valor, Descripcion, FechaActualizacion, RequiereReinicio
    FROM dbo.ConfiguracionSistema;
END
GO
