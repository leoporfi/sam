-- =============================================
-- Script para actualizar los SPs de listado
-- para incluir los campos de robots cíclicos
-- =============================================
-- Ejecutar en la base de datos DEV
-- =============================================

USE DEV;
GO

-- =============================================
-- 1. Actualizar ListarProgramaciones
-- =============================================
ALTER PROCEDURE [dbo].[ListarProgramaciones]
AS
BEGIN
	SET NOCOUNT ON;

	SELECT
        P.ProgramacionId,
        P.RobotId,
        R.Robot AS RobotNombre,
        P.TipoProgramacion,
        P.HoraInicio,
        P.DiasSemana,
        P.DiaDelMes,
        P.FechaEspecifica,
        P.Tolerancia,
        P.Activo,
        P.FechaCreacion,
        P.FechaModificacion,
        P.EsCiclico,
        P.HoraFin,
        P.FechaInicioVentana,
        P.FechaFinVentana,
        P.IntervaloEntreEjecuciones,
         STRING_AGG(CAST(E.Equipo AS NVARCHAR(MAX)), ', ') WITHIN GROUP (ORDER BY E.Equipo) AS EquiposProgramados
    FROM
        Programaciones P
    INNER JOIN
        Robots R ON P.RobotId = R.RobotId
    LEFT JOIN
        Asignaciones A ON P.ProgramacionId = A.ProgramacionId
    LEFT JOIN
        Equipos E ON A.EquipoId = E.EquipoId
    GROUP BY
        P.ProgramacionId,
        P.RobotId,
        R.Robot,
        P.TipoProgramacion,
        P.HoraInicio,
        P.DiasSemana,
        P.DiaDelMes,
        P.FechaEspecifica,
        P.Tolerancia,
        P.Activo,
        P.FechaCreacion,
        P.FechaModificacion,
        P.EsCiclico,
        P.HoraFin,
        P.FechaInicioVentana,
        P.FechaFinVentana,
        P.IntervaloEntreEjecuciones
    ORDER BY
        P.ProgramacionId;
END
GO

-- =============================================
-- 2. Actualizar ListarProgramacionesPorRobot
-- =============================================
ALTER PROCEDURE [dbo].[ListarProgramacionesPorRobot]
    @RobotId INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        P.ProgramacionId,
        P.RobotId,
        R.Robot AS RobotNombre,
        P.TipoProgramacion,
        P.HoraInicio,
        P.DiasSemana,
        P.DiaDelMes,
        P.FechaEspecifica,
		P.DiaInicioMes,
        P.DiaFinMes,
        P.UltimosDiasMes,
        P.Tolerancia,
        P.Activo,
        P.FechaCreacion,
        P.FechaModificacion,
        P.EsCiclico,
        P.HoraFin,
        P.FechaInicioVentana,
        P.FechaFinVentana,
        P.IntervaloEntreEjecuciones,
        STRING_AGG(CAST(E.Equipo AS NVARCHAR(MAX)), ', ') WITHIN GROUP (ORDER BY E.Equipo) AS EquiposProgramados
    FROM
        dbo.Programaciones P
    INNER JOIN
        dbo.Robots R ON P.RobotId = R.RobotId
    LEFT JOIN
        dbo.Asignaciones A ON P.ProgramacionId = A.ProgramacionId AND A.EsProgramado = 1
    LEFT JOIN
        dbo.Equipos E ON A.EquipoId = E.EquipoId
    WHERE
        P.RobotId = @RobotId
    GROUP BY
        P.ProgramacionId,
        P.RobotId,
        R.Robot,
        P.TipoProgramacion,
        P.HoraInicio,
        P.DiasSemana,
        P.DiaDelMes,
        P.FechaEspecifica,
		P.DiaInicioMes,
        P.DiaFinMes,
        P.UltimosDiasMes,
        P.Tolerancia,
        P.Activo,
        P.FechaCreacion,
        P.FechaModificacion,
        P.EsCiclico,
        P.HoraFin,
        P.FechaInicioVentana,
        P.FechaFinVentana,
        P.IntervaloEntreEjecuciones
    ORDER BY
        P.ProgramacionId;
END
GO

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

PRINT '=============================================';
PRINT 'SPs de listado actualizados correctamente';
PRINT '=============================================';
PRINT '';
PRINT 'SPs actualizados:';
PRINT '  1. ListarProgramaciones';
PRINT '  2. ListarProgramacionesPorRobot';
PRINT '  3. ListarProgramacionesPaginadas';
PRINT '';
PRINT 'Campos agregados:';
PRINT '  - EsCiclico';
PRINT '  - HoraFin';
PRINT '  - FechaInicioVentana';
PRINT '  - FechaFinVentana';
PRINT '  - IntervaloEntreEjecuciones';
PRINT '';
PRINT '=============================================';

