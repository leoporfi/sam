CREATE VIEW dbo.AsignacionesView
AS
SELECT R.Robot, EQ.Equipo, A.RobotId, A.EquipoId, A.EsProgramado, A.Reservado
FROM     dbo.Asignaciones AS A INNER JOIN
                  dbo.Equipos AS EQ ON A.EquipoId = EQ.EquipoId INNER JOIN
                  dbo.Robots AS R ON A.RobotId = R.RobotId