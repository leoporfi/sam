SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ListarProgramacionesPaginadas]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ListarProgramacionesPaginadas] AS'
END

-- =============================================
-- 3. Actualizar ListarProgramacionesPaginadas
-- =============================================
ALTER PROCEDURE [dbo].[ListarProgramacionesPaginadas]
    @RobotId INT = NULL,
    @Tipo NVARCHAR(50) = NULL,
    @Activo BIT = NULL,
    @Search NVARCHAR(100) = NULL,
    @PageSize INT = 100,
    @Offset INT = 0
AS
BEGIN
    SET NOCOUNT ON;

    WITH ProgramasFiltradosCTE AS (
        SELECT
            p.ProgramacionId,
            p.RobotId,
            r.Robot AS RobotNombre,
            p.TipoProgramacion,
            CONVERT(VARCHAR(5), p.HoraInicio, 108) AS HoraInicio,
            p.DiasSemana,
            p.DiaDelMes,
            CONVERT(VARCHAR(10), p.FechaEspecifica, 23) AS FechaEspecifica,
			p.DiaInicioMes,
            p.DiaFinMes,
            p.UltimosDiasMes,
            p.Tolerancia,
            p.Activo,
            p.EsCiclico,
            CONVERT(VARCHAR(5), p.HoraFin, 108) AS HoraFin,
            CONVERT(VARCHAR(10), p.FechaInicioVentana, 23) AS FechaInicioVentana,
            CONVERT(VARCHAR(10), p.FechaFinVentana, 23) AS FechaFinVentana,
            p.IntervaloEntreEjecuciones,

            -- --- CAMBIO AQUÍ ---
            -- Usamos STRING_AGG para listar nombres, pero filtrando por p.ProgramacionId
            (
                SELECT STRING_AGG(CAST(eq.Equipo AS NVARCHAR(MAX)), ', ') WITHIN GROUP (ORDER BY eq.Equipo)
                FROM dbo.Asignaciones a
                INNER JOIN dbo.Equipos eq ON a.EquipoId = eq.EquipoId
                WHERE a.ProgramacionId = p.ProgramacionId  -- <--- FILTRO CORRECTO
                  AND eq.Activo_SAM = 1                    -- <--- Solo activos
            ) AS EquiposProgramados,
            -- -------------------

            COUNT(*) OVER() AS TotalRows
        FROM dbo.Programaciones p
        JOIN dbo.Robots r ON p.RobotId = r.RobotId
        WHERE
            (@RobotId IS NULL OR p.RobotId = @RobotId)
            AND (@Tipo IS NULL OR p.TipoProgramacion = @Tipo)
            AND (@Activo IS NULL OR p.Activo = @Activo)
            AND (
                @Search IS NULL OR
                r.Robot LIKE '%' + @Search + '%' OR
                p.TipoProgramacion LIKE '%' + @Search + '%'
            )
    )

    SELECT *
    FROM ProgramasFiltradosCTE
    ORDER BY RobotNombre, HoraInicio
    OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;
END

GO
