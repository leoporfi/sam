SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerRobotPorId]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ObtenerRobotPorId] AS'
END
GO
ALTER PROCEDURE [dbo].[ObtenerRobotPorId]
    @RobotId NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT * FROM dbo.Robots WHERE RobotId = @RobotId;
END
GO
