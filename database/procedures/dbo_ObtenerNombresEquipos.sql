CREATE PROCEDURE [dbo].[ObtenerNombresEquipos]
    @EquiposIds dbo.IdListType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SELECT STRING_AGG(CAST(Equipo AS NVARCHAR(MAX)), ',') AS Nombres
    FROM dbo.Equipos
    WHERE EquipoId IN (SELECT ID FROM @EquiposIds);
END
