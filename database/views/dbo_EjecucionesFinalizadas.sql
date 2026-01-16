CREATE   VIEW [dbo].[EjecucionesFinalizadas]
AS
SELECT TOP (100) PERCENT r.Robot, r.RobotId, CASE WHEN (r.EsOnline = 1) THEN 'ONLINE' ELSE 'PROGRAMADO' END AS Tipo, eq.Equipo, eq.EquipoId, eq.UserId, eq.UserName, e.DeploymentId, e.Hora, e.FechaInicio, e.FechaInicioReal,e.FechaFin, e.Estado,
                  e.FechaActualizacion, e.IntentosConciliadorFallidos, e.CallbackInfo
FROM     dbo.Ejecuciones AS e INNER JOIN
                  dbo.Equipos AS eq ON e.EquipoId = eq.EquipoId INNER JOIN
                  dbo.Robots AS r ON e.RobotId = r.RobotId
WHERE  (e.Estado NOT IN ('DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 'RUNNING', 'UPDATE', 'RUN_PAUSED')) AND (NOT (e.Estado = 'UNKNOWN')) OR
                  (e.Estado NOT IN ('DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 'RUNNING', 'UPDATE', 'RUN_PAUSED')) AND (NOT (e.FechaUltimoUNKNOWN > DATEADD(HOUR, - 2, GETDATE())))
ORDER BY e.EjecucionId DESC