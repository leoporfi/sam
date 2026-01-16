CREATE PROCEDURE [dbo].[ObtenerRobotsDetalle]
    @Robot NVARCHAR(100) = NULL,
    @PoolId INT = NULL,
    @ActivoSAM NVARCHAR(5) = 'todos', -- 'true', 'false', 'todos'
    @EsOnline NVARCHAR(5) = 'todos'  -- 'true', 'false', 'todos'
AS
BEGIN
    SET NOCOUNT ON;
    -- Manejo de NULL para el string de búsqueda
    DECLARE @SearchRobot NVARCHAR(102) = CASE WHEN @Robot IS NULL THEN '%' ELSE '%' + @Robot + '%' END;
    -- Manejo de filtros booleanos
    DECLARE @FilterActivoSAM BIT = CASE @ActivoSAM WHEN 'true' THEN 1 WHEN 'false' THEN 0 ELSE NULL END;
    DECLARE @FilterEsOnline BIT = CASE @EsOnline WHEN 'true' THEN 1 WHEN 'false' THEN 0 ELSE NULL END;
    SELECT
        R.RobotId,
        R.Robot,
        R.Descripcion,
        R.EsOnline,
        R.Activo AS ActivoSAM,
        -- Campos reales de dbo.Robots
        ISNULL(PL.Nombre, 'Sin Asignar') AS Pool,
        ISNULL(R.PoolId, 0) AS PoolId,
        R.PrioridadBalanceo AS Prioridad,
        -- Corrección del bug de conteo usando subconsultas
        ISNULL(ProgCounts.CantidadProgramaciones, 0) AS CantidadProgramaciones,
        ISNULL(EquipoCounts.CantidadEquiposAsignados, 0) AS CantidadEquiposAsignados
    FROM
        dbo.Robots AS R
    LEFT JOIN
        -- Unir con la tabla real dbo.Pools y usar el campo real 'Nombre'
        dbo.Pools AS PL ON R.PoolId = PL.PoolId
    -- Subconsulta aislada para contar programaciones
    OUTER APPLY (
        SELECT COUNT(DISTINCT A_prog.ProgramacionId) AS CantidadProgramaciones
        FROM dbo.Asignaciones AS A_prog
        INNER JOIN dbo.Programaciones AS P ON A_prog.ProgramacionId = P.ProgramacionId
        WHERE A_prog.RobotId = R.RobotId AND P.Activo = 1
    ) AS ProgCounts
    -- Subconsulta aislada para contar equipos
    OUTER APPLY (
        SELECT COUNT(DISTINCT A_eq.EquipoId) AS CantidadEquiposAsignados
        FROM dbo.Asignaciones AS A_eq
        WHERE A_eq.RobotId = R.RobotId
    ) AS EquipoCounts
    WHERE
        -- Filtros (quitamos los campos que no existen como Activo_A360)
        (R.Robot LIKE @SearchRobot OR R.Descripcion LIKE @SearchRobot)
        AND (@PoolId IS NULL OR R.PoolId = @PoolId) -- Filtrar por el PoolId del Robot
        AND (@FilterActivoSAM IS NULL OR R.Activo = @FilterActivoSAM)
        AND (@FilterEsOnline IS NULL OR R.EsOnline = @FilterEsOnline)
    ORDER BY
        R.Robot;
END