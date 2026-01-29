CREATE PROCEDURE [dbo].[ListarAsignacionesPorRobot]
    @RobotId INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT A.RobotId, A.EquipoId, A.Equipo, A.EsProgramado, A.Reservado
    FROM dbo.AsignacionesView AS A
    WHERE A.RobotId = @RobotId;
END
GO
