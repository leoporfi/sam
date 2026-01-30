
IF OBJECT_ID('dbo.AuditoriaExtendida', 'V') IS NOT NULL
    DROP VIEW dbo.AuditoriaExtendida;
GO

IF OBJECT_ID('dbo.vAuditoria', 'V') IS NOT NULL
    DROP VIEW dbo.vAuditoria;
GO



CREATE VIEW [dbo].[AuditoriaExtendida]
AS
SELECT
    a.AuditoriaId,
    a.Fecha,
    a.Accion,
    a.Entidad,
    a.EntidadId,
    CASE
        WHEN a.Entidad = 'Robot' THEN r.Robot
        WHEN a.Entidad = 'Equipo' THEN e.Equipo
        WHEN a.Entidad = 'Programacion' THEN CONCAT(ISNULL(pr.Robot, 'RobotDesconocido'), ' - ', ISNULL(p.TipoProgramacion, 'TipoDesconocido'))
        ELSE a.EntidadId
    END as EntidadNombre,
    a.Detalle,
    a.Host,
    a.Usuario
FROM dbo.Auditoria a
LEFT JOIN dbo.Robots r ON a.Entidad = 'Robot' AND TRY_CAST(a.EntidadId AS INT) = r.RobotId
LEFT JOIN dbo.Equipos e ON a.Entidad = 'Equipo' AND TRY_CAST(a.EntidadId AS INT) = e.EquipoId
LEFT JOIN dbo.Programaciones p ON a.Entidad = 'Programacion' AND TRY_CAST(a.EntidadId AS INT) = p.ProgramacionId
LEFT JOIN dbo.Robots pr ON p.RobotId = pr.RobotId;
GO
