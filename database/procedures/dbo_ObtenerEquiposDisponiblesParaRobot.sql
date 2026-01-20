SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerEquiposDisponiblesParaRobot]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ObtenerEquiposDisponiblesParaRobot] AS'
END
GO
ALTER PROCEDURE [dbo].[ObtenerEquiposDisponiblesParaRobot]
    @RobotId INT  -- Mantenemos el parámetro aunque ya no se use en la lógica,
                  -- para no tener que modificar el código de Python.
AS
BEGIN
    SET NOCOUNT ON;

    -- REGLAS DE NEGOCIO ACTUALIZADAS:
    -- Un equipo está disponible para una NUEVA PROGRAMACIÓN si:
    -- 1. Está Activo_SAM = 1
    -- 2. Tiene la licencia correcta ('ATTENDEDRUNTIME' o 'RUNTIME')
    -- 3. NO está 'Reservado = 1' manualmente
    -- 4. NO está asignado dinámicamente (EsProgramado = 0 AND Reservado = 0)
    --
    -- NOTA: Se elimina la restricción que impedía asignarlo si ya
    -- estaba programado (EsProgramado = 1) para este mismo robot.

    WITH EquiposNoDisponibles AS (
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
      AND E.EquipoId NOT IN (SELECT EquipoId FROM EquiposNoDisponibles)
      AND E.EquipoId NOT IN (SELECT EquipoId FROM EquiposYaAsignados)
    ORDER BY E.Equipo;
END

GO
