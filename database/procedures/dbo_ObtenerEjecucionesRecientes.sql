SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerEjecucionesRecientes]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ObtenerEjecucionesRecientes] AS'
END
GO
ALTER PROCEDURE [dbo].[ObtenerEjecucionesRecientes]
    @Limit INT = 50,
    @CriticalOnly BIT = 1,
    @UmbralFijoMinutos INT = 25,
    @FactorUmbralDinamico FLOAT = 1.5,
    @RobotName NVARCHAR(255) = NULL,
    @EquipoName NVARCHAR(255) = NULL,
    @PisoUmbralDinamicoMinutos INT = 10,
    @FiltroEjecucionesCortasMinutos INT = 2,
    @DefaultRepeticiones INT = 1
AS
BEGIN

    WITH TiemposPromedio AS (
        -- Calcular tiempo promedio por robot (solo si tiene suficiente historial)
        -- Filtramos ejecuciones menores a 2 min para evitar que ejecuciones 'vacías' sesguen el promedio
        -- Normalizamos el tiempo dividiendo por la cantidad de repeticiones (vueltas)
        SELECT
            e.RobotId,
            AVG(CAST(DATEDIFF(MINUTE, e.FechaInicio, e.FechaFin) AS FLOAT) /
                NULLIF(
                    CASE
                        WHEN r.Parametros IS NOT NULL AND r.Parametros != ''
                        THEN COALESCE(TRY_CAST(JSON_VALUE(r.Parametros, '$.in_NumRepeticion.number') AS INT), @DefaultRepeticiones)
                        ELSE @DefaultRepeticiones
                    END, 0)
            ) AS TiempoPromedioPorCicloMinutos,
            COUNT(*) AS CantidadEjecuciones
        FROM dbo.Ejecuciones e
        INNER JOIN dbo.Robots r ON e.RobotId = r.RobotId
        WHERE e.FechaFin IS NOT NULL
          AND e.Estado = 'RUN_COMPLETED'
          AND DATEDIFF(MINUTE, e.FechaInicio, e.FechaFin) >= @FiltroEjecucionesCortasMinutos
        GROUP BY e.RobotId
    ),
    EjecucionesConEstado AS (
        SELECT
            e.EjecucionId AS Id,
            e.DeploymentId,
            r.Robot,
            eq.Equipo,
            e.Estado,
            e.FechaInicio,
            e.FechaFin,
            DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) AS TiempoTranscurridoMinutos,
            -- Extraer repeticiones actuales para normalizar el tiempo transcurrido
            CASE
                WHEN r.Parametros IS NOT NULL AND r.Parametros != ''
                THEN COALESCE(TRY_CAST(JSON_VALUE(r.Parametros, '$.in_NumRepeticion.number') AS INT), @DefaultRepeticiones)
                ELSE @DefaultRepeticiones
            END AS NumRepeticiones,
            CASE
                -- Fallos inmediatos (Excluyendo RUN_FAILED y RUN_ABORTED por pedido de usuario)
                WHEN e.Estado LIKE '%FAILED%' AND e.Estado NOT IN ('RUN_FAILED', 'RUN_ABORTED') THEN 'Fallo'

                -- RUNNING o DEPLOYED demorados
                -- Comparamos (TiempoTranscurrido / NumRepeticiones) contra el promedio por ciclo
                WHEN e.Estado IN ('RUNNING', 'DEPLOYED') AND (
                    (tp.TiempoPromedioPorCicloMinutos IS NOT NULL AND
                     (CAST(DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) AS FLOAT) /
                      NULLIF(
                        CASE
                            WHEN r.Parametros IS NOT NULL AND r.Parametros != ''
                            THEN COALESCE(TRY_CAST(JSON_VALUE(r.Parametros, '$.in_NumRepeticion.number') AS INT), @DefaultRepeticiones)
                            ELSE @DefaultRepeticiones
                        END, 0)) >
                        CASE
                            WHEN tp.TiempoPromedioPorCicloMinutos * @FactorUmbralDinamico < @PisoUmbralDinamicoMinutos
                            THEN @PisoUmbralDinamicoMinutos
                            ELSE tp.TiempoPromedioPorCicloMinutos * @FactorUmbralDinamico
                        END)
                    OR
                    (tp.TiempoPromedioPorCicloMinutos IS NULL AND
                     DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) > @UmbralFijoMinutos)
                ) THEN 'Demorada'

                -- QUEUED huérfano (sin DEPLOYED/RUNNING correspondiente)
                WHEN e.Estado = 'QUEUED'
                     AND DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) > 5
                     AND NOT EXISTS (
                        SELECT 1 FROM dbo.Ejecuciones e2
                        WHERE e2.RobotId = e.RobotId
                          AND e2.EquipoId = e.EquipoId
                          AND e2.Estado IN ('DEPLOYED', 'RUNNING')
                          AND e2.FechaInicio >= e.FechaInicio
                     ) THEN 'Huerfana'

                ELSE NULL
            END AS TipoCritico,
            CASE
                -- Mensaje para Fallos
                WHEN e.Estado LIKE '%FAILED%' AND e.Estado NOT IN ('RUN_FAILED', 'RUN_ABORTED')
                THEN ISNULL(CAST(e.CallbackInfo AS NVARCHAR(MAX)), 'Fallo técnico reportado por A360')

                -- Mensaje para Demoras
                WHEN e.Estado IN ('RUNNING', 'DEPLOYED') AND (
                    (tp.TiempoPromedioPorCicloMinutos IS NOT NULL AND
                     (CAST(DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) AS FLOAT) /
                      NULLIF(
                        CASE
                            WHEN r.Parametros IS NOT NULL AND r.Parametros != ''
                            THEN COALESCE(TRY_CAST(JSON_VALUE(r.Parametros, '$.in_NumRepeticion.number') AS INT), @DefaultRepeticiones)
                            ELSE @DefaultRepeticiones
                        END, 0)) >
                        CASE
                            WHEN tp.TiempoPromedioPorCicloMinutos * @FactorUmbralDinamico < @PisoUmbralDinamicoMinutos
                            THEN @PisoUmbralDinamicoMinutos
                            ELSE tp.TiempoPromedioPorCicloMinutos * @FactorUmbralDinamico
                        END)
                    OR
                    (tp.TiempoPromedioPorCicloMinutos IS NULL AND
                     DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) > @UmbralFijoMinutos)
                ) THEN 'Excede umbral de ' + CAST(CAST(
                    CASE
                        WHEN tp.TiempoPromedioPorCicloMinutos IS NOT NULL THEN
                            CASE
                                WHEN tp.TiempoPromedioPorCicloMinutos * @FactorUmbralDinamico < @PisoUmbralDinamicoMinutos
                                THEN @PisoUmbralDinamicoMinutos
                                ELSE tp.TiempoPromedioPorCicloMinutos * @FactorUmbralDinamico
                            END
                        ELSE @UmbralFijoMinutos
                    END AS DECIMAL(10,1)) AS VARCHAR(10)) + ' min por ciclo (' + CAST(
                        CASE
                            WHEN r.Parametros IS NOT NULL AND r.Parametros != ''
                            THEN COALESCE(TRY_CAST(JSON_VALUE(r.Parametros, '$.in_NumRepeticion.number') AS INT), @DefaultRepeticiones)
                            ELSE @DefaultRepeticiones
                        END AS VARCHAR(5)) + ' ciclos)'

                -- Mensaje para Huérfanas
                WHEN e.Estado = 'QUEUED'
                     AND DATEDIFF(MINUTE, e.FechaInicio, GETDATE()) > 5
                     AND NOT EXISTS (
                        SELECT 1 FROM dbo.Ejecuciones e2
                        WHERE e2.RobotId = e.RobotId
                          AND e2.EquipoId = e.EquipoId
                          AND e2.Estado IN ('DEPLOYED', 'RUNNING')
                          AND e2.FechaInicio >= e.FechaInicio
                     ) THEN 'Sin actividad detectada en DEPLOYED/RUNNING'

                ELSE NULL
            END AS MensajeError,
            CASE
                WHEN tp.TiempoPromedioPorCicloMinutos IS NOT NULL THEN
                    CASE
                        WHEN tp.TiempoPromedioPorCicloMinutos * @FactorUmbralDinamico < @PisoUmbralDinamicoMinutos
                        THEN @PisoUmbralDinamicoMinutos
                        ELSE tp.TiempoPromedioPorCicloMinutos * @FactorUmbralDinamico
                    END
                ELSE @UmbralFijoMinutos
            END AS UmbralUtilizadoMinutos,
            CASE
                WHEN tp.TiempoPromedioPorCicloMinutos IS NOT NULL THEN
                    CASE
                        WHEN tp.TiempoPromedioPorCicloMinutos * @FactorUmbralDinamico < @PisoUmbralDinamicoMinutos
                        THEN 'Dinámico (Piso)'
                        ELSE 'Dinámico'
                    END
                ELSE 'Fijo'
            END AS TipoUmbral,
            tp.TiempoPromedioPorCicloMinutos AS TiempoPromedioRobotMinutos,
            CASE WHEN e.FechaFin IS NULL THEN 'Activa' ELSE 'Historico' END AS Origen
        FROM dbo.Ejecuciones e
        LEFT JOIN dbo.Robots r ON e.RobotId = r.RobotId
        LEFT JOIN dbo.Equipos eq ON e.EquipoId = eq.EquipoId
        LEFT JOIN TiemposPromedio tp ON e.RobotId = tp.RobotId
        WHERE (@RobotName IS NULL OR r.Robot LIKE '%' + @RobotName + '%')
          AND (@EquipoName IS NULL OR eq.Equipo LIKE '%' + @EquipoName + '%')
    )
    -- Guardar resultados en tabla temporal para poder separar
    SELECT
        *
    INTO #ResultadosAnalisis
    FROM EjecucionesConEstado
    WHERE (@CriticalOnly = 0 OR TipoCritico IS NOT NULL);

    -- Result Set 1: FALLOS (Prioridad Alta)
    SELECT TOP (@Limit)
        *
    FROM #ResultadosAnalisis
    WHERE TipoCritico = 'Fallo'
    ORDER BY FechaInicio DESC;

    -- Result Set 2: DEMORAS y HUÉRFANAS (Prioridad Operativa)
    SELECT TOP (@Limit)
        *
    FROM #ResultadosAnalisis
    WHERE TipoCritico IN ('Demorada', 'Huerfana')
    ORDER BY TiempoTranscurridoMinutos DESC;

    -- Limpieza
    DROP TABLE #ResultadosAnalisis;
END

GO
