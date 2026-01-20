SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerConfiguracion]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ObtenerConfiguracion] AS'
END
GO
ALTER PROCEDURE [dbo].[ObtenerConfiguracion]
    @Clave NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT Valor FROM dbo.ConfiguracionSistema WHERE Clave = @Clave;
END
GO
