CREATE PROCEDURE [dbo].[ObtenerRobotPorId]
    @RobotId NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT * FROM dbo.Robots WHERE RobotId = @RobotId;
END
