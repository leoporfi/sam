CREATE   VIEW [dbo].[EjecucionesActivas]
AS
SELECT TOP (100) PERCENT R.Robot, R.RobotId, CASE WHEN (r.EsOnline = 1) THEN 'ONLINE' ELSE 'PROGRAMADO' END AS Tipo, EQ.Equipo, EQ.EquipoId, EQ.UserId, EQ.UserName, E.DeploymentId, E.Hora, E.FechaInicio, E.FechaInicioReal,
                  E.FechaFin, E.Estado, E.FechaActualizacion, E.IntentosConciliadorFallidos, E.CallbackInfo
FROM     dbo.Ejecuciones AS E INNER JOIN
                  dbo.Equipos AS EQ ON E.EquipoId = EQ.EquipoId INNER JOIN
                  dbo.Robots AS R ON E.RobotId = R.RobotId
WHERE  (E.Estado IN ('PENDING_EXECUTION', 'DEPLOYED', 'RUNNING', 'UPDATE', 'RUN_PAUSED', 'QUEUED')) OR
                  (E.Estado = 'UNKNOWN') AND (E.FechaUltimoUNKNOWN > DATEADD(HOUR, - 2, GETDATE()))
ORDER BY E.EjecucionId DESC