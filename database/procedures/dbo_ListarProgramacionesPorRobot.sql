-- =============================================
-- 2. Actualizar ListarProgramacionesPorRobot
-- =============================================
CREATE PROCEDURE [dbo].[ListarProgramacionesPorRobot]
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
