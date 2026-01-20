SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ListarProgramaciones]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ListarProgramaciones] AS'
END

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
