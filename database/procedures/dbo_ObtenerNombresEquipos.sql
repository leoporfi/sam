SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerNombresEquipos]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ObtenerNombresEquipos] AS'
END
GO
ALTER PROCEDURE [dbo].[ObtenerNombresEquipos]
    @EquiposIds dbo.IdListType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SELECT STRING_AGG(CAST(Equipo AS NVARCHAR(MAX)), ',') AS Nombres
    FROM dbo.Equipos
    WHERE EquipoId IN (SELECT ID FROM @EquiposIds);
END
GO
