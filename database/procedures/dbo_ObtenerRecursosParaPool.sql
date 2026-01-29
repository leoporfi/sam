SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerRecursosParaPool]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ObtenerRecursosParaPool] AS'
END


-- Corrección definitiva para el Stored Procedure ObtenerRecursosParaPool
-- Selecciona la columna de ID correcta para cada tipo de recurso y la renombra a 'ID'.

ALTER PROCEDURE [dbo].[ObtenerRecursosParaPool]
    @PoolId INT
AS
BEGIN
    SET NOCOUNT ON;

    -- Primer result set: Recursos ASIGNADOS
    -- Se selecciona RobotId o EquipoId según corresponda y se aliasa como 'ID'
    SELECT
        RobotId AS ID,
        Robot AS Nombre,
        'Robot' as Tipo,
        CAST(0 AS BIT) AS EsProgramado,
        CAST(0 AS BIT) AS Reservado,
        NULL AS RobotId
    FROM dbo.Robots WHERE PoolId = @PoolId
    UNION ALL
    SELECT
        E.EquipoId AS ID,
        E.Equipo AS Nombre,
        'Equipo' as Tipo,
        ISNULL(A.EsProgramado, CAST(0 AS BIT)) AS EsProgramado,
        ISNULL(A.Reservado, CAST(0 AS BIT)) AS Reservado,
        A.RobotId
    FROM dbo.Equipos E
    OUTER APPLY (
        SELECT TOP 1 RobotId, EsProgramado, Reservado
        FROM dbo.Asignaciones
        WHERE EquipoId = E.EquipoId
        ORDER BY EsProgramado DESC, Reservado DESC, FechaAsignacion DESC
    ) A
    WHERE E.PoolId = @PoolId;

    -- Segundo result set: Recursos DISPONIBLES
    -- Se hace lo mismo para los recursos sin pool
    SELECT
        RobotId AS ID,
        Robot AS Nombre,
        'Robot' as Tipo,
        CAST(0 AS BIT) AS EsProgramado,
        CAST(0 AS BIT) AS Reservado,
        NULL AS RobotId
    FROM dbo.Robots WHERE PoolId IS NULL AND Activo = 1
    UNION ALL
    SELECT
        E.EquipoId AS ID,
        E.Equipo AS Nombre,
        'Equipo' as Tipo,
        ISNULL(A.EsProgramado, CAST(0 AS BIT)) AS EsProgramado,
        ISNULL(A.Reservado, CAST(0 AS BIT)) AS Reservado,
        A.RobotId
    FROM dbo.Equipos E
    OUTER APPLY (
        SELECT TOP 1 RobotId, EsProgramado, Reservado
        FROM dbo.Asignaciones
        WHERE EquipoId = E.EquipoId
        ORDER BY EsProgramado DESC, Reservado DESC, FechaAsignacion DESC
    ) A
    WHERE E.PoolId IS NULL AND E.Activo_SAM = 1;

END

GO
