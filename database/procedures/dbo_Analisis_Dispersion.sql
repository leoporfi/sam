-- Inicio de dbo_Analisis_Dispersion.sql
CREATE   PROCEDURE [dbo].[Analisis_Dispersion]
    @pRobot VARCHAR(100),
    @pFecha DATE = NULL,
    @pTop   INT  = NULL,
    @pModo  CHAR(1) = 'I' -- I = Inicio→Inicio (dispersión), F = Fin→Inicio (tiempo muerto)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @RobotId INT;
    -- Resolver RobotId a partir del nombre
    SELECT @RobotId = RobotId
    FROM   dbo.Robots
    WHERE  Robot = @pRobot;
    IF @RobotId IS NULL
    BEGIN
        RAISERROR('El robot ''%s'' no existe en la tabla maestra.', 16, 1, @pRobot);
        RETURN;
    END;
    /* 1. CTE base de ejecuciones */
    ;WITH Ejecs AS
    (
        SELECT  EjecucionID,
                UserId,
                EquipoId,
                RobotId,
                Estado,
                FechaInicio,
                FechaFin, -- <<< Se necesita el fin para el modo 'F'
                ROW_NUMBER() OVER (ORDER BY FechaInicio DESC) AS RN
        FROM    dbo.Ejecuciones
        WHERE   RobotId = @RobotId
          AND   (Estado = 'RUN_COMPLETED' OR Estado = 'COMPLETED')
          AND   (@pFecha IS NULL OR CAST(FechaInicio AS DATE) = @pFecha)
    ),
    Filtradas AS
    (
        SELECT * FROM Ejecs WHERE @pTop IS NULL OR RN <= @pTop
    ),
    ConDelta AS
    (
        SELECT *,
               /* ------- Lógica para elegir el tipo de delta ------- */
               CASE @pModo
                   WHEN 'I' THEN -- Modo 'I': Inicio -> Inicio (dispersión entre arranques)
                        DATEDIFF(SECOND,
                                 LAG(FechaInicio) OVER (PARTITION BY UserId ORDER BY FechaInicio),
                                 FechaInicio)
                   WHEN 'F' THEN -- Modo 'F': Fin -> Inicio (tiempo muerto real)
                        DATEDIFF(SECOND,
                                 LAG(FechaFin) OVER (PARTITION BY UserId ORDER BY FechaInicio),
                                 FechaInicio)
               END AS DeltaSec
        FROM Filtradas
    )
    SELECT * INTO #ConDelta FROM ConDelta;
    /* 2. RESUMEN: agrupado por equipo + robot */
    SELECT
            r.Robot,
            e.Equipo,
            COUNT(*)            AS Ejecuciones,
            MIN(cd.DeltaSec)    AS DeltaMin_Sec,
            MAX(cd.DeltaSec)    AS DeltaMax_Sec,
            AVG(cd.DeltaSec*1.0)   AS DeltaAvg_Sec,
            STDEV(cd.DeltaSec*1.0) AS DeltaDesv_Sec,
            @pModo              AS ModoCalculo
    INTO    #Resumen
    FROM    #ConDelta cd
    INNER JOIN dbo.Equipos e ON e.EquipoId = cd.EquipoId
    INNER JOIN dbo.Robots r ON r.RobotId = cd.RobotId
    WHERE   cd.DeltaSec IS NOT NULL
    GROUP BY r.Robot, e.Equipo;
	SELECT * FROM #Resumen ORDER BY Robot, Equipo;
    /* 3. DETALLE */
    SELECT
            cd.EjecucionID,
            cd.UserId,
            cd.EquipoId,
            e.Equipo,
            cd.RobotId,
            r.Robot,
            cd.Estado,
            cd.FechaInicio,
            cd.FechaFin,
            cd.DeltaSec,
            cd.DeltaSec / 60.0 AS DeltaMin,
            @pModo AS ModoCalculo
    FROM    #ConDelta cd
    INNER JOIN dbo.Equipos e ON e.EquipoId = cd.EquipoId
    INNER JOIN dbo.Robots r ON r.RobotId = cd.RobotId
    WHERE   cd.DeltaSec IS NOT NULL
    ORDER BY e.Equipo, cd.FechaInicio;
    DROP TABLE #Resumen;
    DROP TABLE #ConDelta;
END;