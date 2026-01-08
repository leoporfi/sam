SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerEquiposParaProgramacion]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ObtenerEquiposParaProgramacion] AS'
END
GO
ALTER PROCEDURE [dbo].[ObtenerEquiposParaProgramacion]
    @ProgramacionId INT
AS
BEGIN
    SET NOCOUNT ON;

    -- 1. Equipos Asignados a esta programación
    SELECT
        e.EquipoId AS ID,
        e.Equipo AS Nombre,
        e.Licencia,
        CAST(1 AS BIT) AS EsProgramado,
        CAST(0 AS BIT) AS Reservado
    FROM dbo.Equipos e
    INNER JOIN dbo.Asignaciones a ON e.EquipoId = a.EquipoId
    WHERE a.ProgramacionId = @ProgramacionId;

    -- 2. Equipos Disponibles
    -- Excluyendo:
    -- - Asignados a esta programación (ya devueltos arriba)
    -- - Reservados manualmente
    -- - Asignados dinámicamente
    WITH EquiposReservadosODinamicos AS (
        SELECT DISTINCT EquipoId
        FROM dbo.Asignaciones
        WHERE Reservado = 1
           OR (EsProgramado = 0 AND Reservado = 0)
    ),
    EquiposProgramadosEnOtrasProgramaciones AS (
        SELECT DISTINCT EquipoId, CAST(1 AS BIT) AS EsProgramado
        FROM dbo.Asignaciones
        WHERE EsProgramado = 1
          AND ProgramacionId != @ProgramacionId
    ),
    EquiposAsignadosEstaProgramacion AS (
        SELECT DISTINCT EquipoId
        FROM dbo.Asignaciones
        WHERE ProgramacionId = @ProgramacionId
    )
    SELECT
        e.EquipoId AS ID,
        e.Equipo AS Nombre,
        e.Licencia,
        ISNULL(P.EsProgramado, CAST(0 AS BIT)) AS EsProgramado,
        CAST(0 AS BIT) AS Reservado
    FROM dbo.Equipos e
    LEFT JOIN EquiposProgramadosEnOtrasProgramaciones P ON e.EquipoId = P.EquipoId
    WHERE e.Activo_SAM = 1
      AND e.EquipoId NOT IN (SELECT EquipoId FROM EquiposAsignadosEstaProgramacion)
      AND e.EquipoId NOT IN (SELECT EquipoId FROM EquiposReservadosODinamicos)
    ORDER BY e.Equipo ASC;
END
GO
