SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ListarMapeos]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ListarMapeos] AS'
END
GO
ALTER PROCEDURE [dbo].[ListarMapeos]
AS
BEGIN
    SET NOCOUNT ON;
    SELECT M.*, R.Robot AS RobotNombre
    FROM dbo.MapeoRobots M
    LEFT JOIN dbo.Robots R ON M.RobotId = R.RobotId;
END
GO
