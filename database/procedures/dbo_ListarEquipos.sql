SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ListarEquipos]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ListarEquipos] AS' 
END
/*
MODIFICACIÓN:
    - Se reemplazó el JOIN directo a Asignaciones/Robots con un OUTER APPLY.
    - Esto soluciona un bug que duplicaba Equipos si tenían múltiples asignaciones.
    - Se añade la columna 'EsProgramado' al SELECT, que reporta el estado
      de la asignación con mayor prioridad (Programado > Reservado > Dinámico).
*/
ALTER PROCEDURE [dbo].[ListarEquipos]
    @Nombre NVARCHAR(100) = NULL,
    @ActivoSAM BIT = NULL,
    @PermiteBalanceo BIT = NULL,
    @Page INT = 1,
    @Size INT = 20,
    @SortBy NVARCHAR(100) = 'Equipo',
    @SortDir NVARCHAR(4) = 'ASC'
AS
BEGIN
    SET NOCOUNT ON;

    -- Usamos OUTER APPLY para obtener la asignación de MAYOR prioridad
    -- Esto evita duplicados de equipos.
    DECLARE @SelectFromClause NVARCHAR(MAX) = 
        'FROM dbo.Equipos e
         LEFT JOIN dbo.Pools p ON e.PoolId = p.PoolId
         OUTER APPLY (
            -- Obtenemos la asignación de MAYOR prioridad para este equipo
            -- Prioridad: Programado (1) > Reservado (1) > Dinámico (0)
            SELECT TOP 1
                r.Robot,
                a.EsProgramado
            FROM dbo.Asignaciones a
            JOIN dbo.Robots r ON a.RobotId = r.RobotId
            WHERE a.EquipoId = e.EquipoId
            ORDER BY
                a.EsProgramado DESC, -- 1. Prioridad a Programado
                a.Reservado DESC,    -- 2. Prioridad a Reservado
                a.FechaAsignacion DESC -- 3. Luego al más reciente
         ) AS AsignacionInfo';
    
    DECLARE @WhereClause NVARCHAR(MAX) = 'WHERE 1=1';
    DECLARE @Params NVARCHAR(MAX) = '@p_Nombre NVARCHAR(100), @p_ActivoSAM BIT, @p_PermiteBalanceo BIT';

    IF @Nombre IS NOT NULL AND @Nombre != ''
        SET @WhereClause += ' AND e.Equipo LIKE ''%'' + @p_Nombre + ''%''';
    IF @ActivoSAM IS NOT NULL
        SET @WhereClause += ' AND e.Activo_SAM = @p_ActivoSAM';
    IF @PermiteBalanceo IS NOT NULL
        SET @WhereClause += ' AND e.PermiteBalanceoDinamico = @p_PermiteBalanceo';

    -- Conteo total (Ahora es un COUNT simple sobre el FROM/WHERE)
    DECLARE @CountQuery NVARCHAR(MAX) = 'SELECT COUNT(e.EquipoId) as total_count ' + @SelectFromClause + ' ' + @WhereClause;
    EXEC sp_executesql @CountQuery, @Params, @p_Nombre = @Nombre, @p_ActivoSAM = @ActivoSAM, @p_PermiteBalanceo = @PermiteBalanceo;

    -- Paginación y ordenamiento
    -- Añadimos 'EsProgramado' a las columnas ordenables
    DECLARE @SortableColumns TABLE (ColName NVARCHAR(100) PRIMARY KEY);
    INSERT INTO @SortableColumns VALUES ('Equipo'), ('Licencia'), ('Activo_SAM'), ('PermiteBalanceoDinamico'), ('RobotAsignado'), ('Pool'), ('EsProgramado');
    
    IF NOT EXISTS (SELECT 1 FROM @SortableColumns WHERE ColName = @SortBy)
        SET @SortBy = 'Equipo';

    -- Mapeo de SortBy a las columnas reales (incluyendo la del OUTER APPLY)
    DECLARE @SortColumnReal NVARCHAR(100) = 
        CASE @SortBy
            WHEN 'RobotAsignado' THEN 'AsignacionInfo.Robot'
            WHEN 'EsProgramado' THEN 'AsignacionInfo.EsProgramado'
            WHEN 'Pool' THEN 'p.Nombre'
            ELSE 'e.' + QUOTENAME(@SortBy)
        END;
    
    DECLARE @OrderByClause NVARCHAR(100) = @SortColumnReal + ' ' + @SortDir;
    DECLARE @Offset INT = (@Page - 1) * @Size;

    DECLARE @MainQuery NVARCHAR(MAX) = 
        'SELECT 
            e.EquipoId, e.Equipo, e.UserName, e.Licencia, e.Activo_SAM, e.PermiteBalanceoDinamico,
            ISNULL(AsignacionInfo.Robot, ''N/A'') as RobotAsignado,
            ISNULL(AsignacionInfo.EsProgramado, 0) as EsProgramado, -- <-- NUEVA COLUMNA
            ISNULL(p.Nombre, ''N/A'') as Pool
         ' + @SelectFromClause + ' ' + @WhereClause + 
        ' ORDER BY ' + @OrderByClause +
        ' OFFSET ' + CAST(@Offset AS NVARCHAR(10)) + ' ROWS FETCH NEXT ' + CAST(@Size AS NVARCHAR(10)) + ' ROWS ONLY';

    EXEC sp_executesql @MainQuery, @Params, @p_Nombre = @Nombre, @p_ActivoSAM = @ActivoSAM, @p_PermiteBalanceo = @PermiteBalanceo;
END

