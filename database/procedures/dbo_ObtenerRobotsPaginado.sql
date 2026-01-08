SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerRobotsPaginado]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ObtenerRobotsPaginado] AS'
END
GO
ALTER PROCEDURE [dbo].[ObtenerRobotsPaginado]
    @Nombre NVARCHAR(100) = NULL,
    @Activo BIT = NULL,
    @Online BIT = NULL,
    @Programado BIT = NULL,
    @Page INT = 1,
    @Size INT = 100,
    @SortBy NVARCHAR(50) = 'Robot',
    @SortDir NVARCHAR(4) = 'ASC'
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Offset INT = (@Page - 1) * @Size;
    DECLARE @SearchName NVARCHAR(102) = CASE WHEN @Nombre IS NULL THEN NULL ELSE '%' + @Nombre + '%' END;

    -- CTE para filtrar y contar
    WITH RobotsFiltrados AS (
        SELECT
            r.RobotId,
            r.Robot,
            r.Descripcion,
            r.MinEquipos,
            r.MaxEquipos,
            r.EsOnline,
            r.Activo,
            r.PrioridadBalanceo,
            r.TicketsPorEquipoAdicional,
            r.Parametros,
            ISNULL(ea.Equipos, 0) AS CantidadEquiposAsignados,
            CAST(CASE WHEN EXISTS (SELECT 1 FROM dbo.Programaciones p WHERE p.RobotId = r.RobotId AND p.Activo = 1)
                 THEN 1 ELSE 0 END AS BIT) AS TieneProgramacion
        FROM dbo.Robots r
        LEFT JOIN dbo.EquiposAsignados ea ON r.Robot = ea.Robot
        WHERE
            (@SearchName IS NULL OR r.Robot LIKE @SearchName)
            AND (@Activo IS NULL OR r.Activo = @Activo)
            AND (@Online IS NULL OR r.EsOnline = @Online)
            AND (
                @Programado IS NULL
                OR (@Programado = 1 AND EXISTS (SELECT 1 FROM dbo.Programaciones p WHERE p.RobotId = r.RobotId AND p.Activo = 1))
                OR (@Programado = 0 AND NOT EXISTS (SELECT 1 FROM dbo.Programaciones p WHERE p.RobotId = r.RobotId AND p.Activo = 1))
            )
    ),
    TotalCount AS (
        SELECT COUNT(*) AS Total FROM RobotsFiltrados
    )
    SELECT
        rf.*,
        tc.Total AS TotalCount
    FROM RobotsFiltrados rf
    CROSS JOIN TotalCount tc
    ORDER BY
        CASE WHEN @SortDir = 'ASC' THEN
            CASE @SortBy
                WHEN 'Robot' THEN rf.Robot
                WHEN 'Activo' THEN CAST(rf.Activo AS NVARCHAR(50))
                WHEN 'EsOnline' THEN CAST(rf.EsOnline AS NVARCHAR(50))
                WHEN 'TieneProgramacion' THEN CAST(rf.TieneProgramacion AS NVARCHAR(50))
                ELSE NULL
            END
        END ASC,
        CASE WHEN @SortDir = 'ASC' THEN
            CASE @SortBy
                WHEN 'CantidadEquiposAsignados' THEN rf.CantidadEquiposAsignados
                WHEN 'PrioridadBalanceo' THEN rf.PrioridadBalanceo
                WHEN 'TicketsPorEquipoAdicional' THEN rf.TicketsPorEquipoAdicional
                ELSE NULL
            END
        END ASC,
        CASE WHEN @SortDir = 'DESC' THEN
            CASE @SortBy
                WHEN 'Robot' THEN rf.Robot
                WHEN 'Activo' THEN CAST(rf.Activo AS NVARCHAR(50))
                WHEN 'EsOnline' THEN CAST(rf.EsOnline AS NVARCHAR(50))
                WHEN 'TieneProgramacion' THEN CAST(rf.TieneProgramacion AS NVARCHAR(50))
                ELSE NULL
            END
        END DESC,
        CASE WHEN @SortDir = 'DESC' THEN
            CASE @SortBy
                WHEN 'CantidadEquiposAsignados' THEN rf.CantidadEquiposAsignados
                WHEN 'PrioridadBalanceo' THEN rf.PrioridadBalanceo
                WHEN 'TicketsPorEquipoAdicional' THEN rf.TicketsPorEquipoAdicional
                ELSE NULL
            END
        END DESC,
        -- Default sort if nothing matches or as secondary sort
        rf.Robot ASC
    OFFSET @Offset ROWS FETCH NEXT @Size ROWS ONLY;
END
GO
