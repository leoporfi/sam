CREATE VIEW dbo.EquiposAsignados AS
SELECT
    r.Robot,
    COUNT(DISTINCT a.EquipoId) AS Equipos  -- Cambiar COUNT(*) por COUNT(DISTINCT a.EquipoId)
FROM dbo.Robots r
LEFT JOIN dbo.Asignaciones a ON r.RobotId = a.RobotId
GROUP BY r.Robot;
