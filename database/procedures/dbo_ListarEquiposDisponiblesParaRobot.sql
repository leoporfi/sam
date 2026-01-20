SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ListarEquiposDisponiblesParaRobot]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ListarEquiposDisponiblesParaRobot] AS'
END
GO
ALTER PROCEDURE [dbo].[ListarEquiposDisponiblesParaRobot]
    @RobotId NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    WITH EquiposReservados AS (
        -- Equipos reservados manualmente o asignados dinámicamente por CUALQUIER robot
        SELECT DISTINCT EquipoId
        FROM dbo.Asignaciones
        WHERE Reservado = 1
           OR (EsProgramado = 0 AND Reservado = 0)
    ),
    EquiposYaAsignados AS (
        -- Equipos ya asignados (de cualquier forma) A ESTE robot específico
        SELECT DISTINCT EquipoId
        FROM dbo.Asignaciones
        WHERE RobotId = @RobotId
    ),
    EquiposProgramadosEnOtrosRobots AS (
        -- Equipos programados en otros robots (no en este)
        SELECT DISTINCT EquipoId, CAST(1 AS BIT) AS EsProgramado
        FROM dbo.Asignaciones
        WHERE EsProgramado = 1
          AND RobotId != @RobotId
    )
    SELECT
        E.EquipoId,
        E.Equipo,
        ISNULL(P.EsProgramado, CAST(0 AS BIT)) AS EsProgramado,
        CAST(0 AS BIT) AS Reservado
    FROM dbo.Equipos E
    LEFT JOIN EquiposProgramadosEnOtrosRobots P ON E.EquipoId = P.EquipoId
    WHERE E.Activo_SAM = 1
      AND E.Licencia IN ('ATTENDEDRUNTIME', 'RUNTIME')
      AND E.EquipoId NOT IN (SELECT EquipoId FROM EquiposReservados)
      AND E.EquipoId NOT IN (SELECT EquipoId FROM EquiposYaAsignados)
    ORDER BY E.Equipo;
END
GO
