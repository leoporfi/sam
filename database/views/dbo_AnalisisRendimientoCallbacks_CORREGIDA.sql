SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
-- =============================================
-- Vista: AnalisisRendimientoCallbacks (CORREGIDA)
-- Descripción: Analiza el rendimiento del sistema de callbacks vs conciliador
--              basándose en los patrones de datos de las tablas Ejecuciones y Ejecuciones_Historico
-- IMPORTANTE: Incluye datos históricos para análisis completo
-- Autor: Sistema SAM
-- Fecha: 2025-01-XX (Corrección)
-- =============================================

-- Nota: Esta es una versión corregida que incluye datos históricos
-- La vista original solo consultaba Ejecuciones, limitando el análisis a datos recientes

IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID(N'[dbo].[AnalisisRendimientoCallbacks]'))
    DROP VIEW [dbo].[AnalisisRendimientoCallbacks]
GO

CREATE VIEW [dbo].[AnalisisRendimientoCallbacks] AS
WITH EjecucionesUnificadas AS (
    -- Datos actuales (últimas 24 horas aproximadamente, antes del mantenimiento diario)
    SELECT
        EjecucionId,
        DeploymentId,
        RobotId,
        EquipoId,
        UserId,
        FechaInicio,
        FechaFin,
        Estado,
        FechaActualizacion,
        IntentosConciliadorFallidos,
        CallbackInfo,
        'ACTUAL' AS Origen
    FROM dbo.Ejecuciones
    WHERE FechaInicio >= DATEADD(DAY, -30, GETDATE())

    UNION ALL

    -- Datos históricos (ejecuciones movidas por mantenimiento diario a las 5am)
    SELECT
        EjecucionId,
        DeploymentId,
        RobotId,
        EquipoId,
        UserId,
        FechaInicio,
        FechaFin,
        Estado,
        FechaActualizacion,
        IntentosConciliadorFallidos,
        CallbackInfo,
        'HISTORICA' AS Origen
    FROM dbo.Ejecuciones_Historico
    WHERE FechaInicio >= DATEADD(DAY, -30, GETDATE())
        -- Solo incluir datos que aún no han sido purgados (por defecto se purgan después de 15 días)
        AND FechaInicio >= DATEADD(DAY, -15, GETDATE())
),
EjecucionesAnalizadas AS (
    SELECT
        EjecucionId,
        DeploymentId,
        RobotId,
        EquipoId,
        UserId,
        FechaInicio,
        FechaFin,
        Estado,
        FechaActualizacion,
        IntentosConciliadorFallidos,
        CallbackInfo,
        Origen,

        -- CLASIFICACIÓN DEL MECANISMO DE FINALIZACIÓN
        CASE
            -- Callback exitoso: Estado final + CallbackInfo presente
            WHEN Estado IN ('COMPLETED', 'RUN_COMPLETED', 'RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED')
                 AND CallbackInfo IS NOT NULL
                 AND CallbackInfo != ''
            THEN 'CALLBACK_EXITOSO'

            -- Conciliador exitoso: Estado final + Sin CallbackInfo + Intentos fallidos > 0
            WHEN Estado IN ('COMPLETED', 'RUN_COMPLETED', 'RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED')
                 AND (CallbackInfo IS NULL OR CallbackInfo = '')
                 AND IntentosConciliadorFallidos > 0
            THEN 'CONCILIADOR_EXITOSO'

            -- Estado UNKNOWN: Conciliador agotó intentos
            WHEN Estado = 'UNKNOWN'
            THEN 'CONCILIADOR_AGOTADO'

            -- Ejecución aún activa (solo en tabla actual)
            WHEN Estado IN ('DEPLOYED', 'RUNNING', 'QUEUED', 'PENDING_EXECUTION', 'UPDATE', 'RUN_PAUSED')
            THEN 'ACTIVA'

            -- Casos edge: Estado final sin CallbackInfo y sin intentos fallidos (posible conciliador inmediato)
            ELSE 'CONCILIADOR_INMEDIATO'
        END AS MecanismoFinalizacion,

        -- MÉTRICAS DE DURACIÓN
        CASE
            WHEN FechaInicio IS NOT NULL AND FechaFin IS NOT NULL
            THEN DATEDIFF(MINUTE, FechaInicio, FechaFin)
            ELSE NULL
        END AS DuracionEjecucionMinutos,

        -- MÉTRICAS DE LATENCIA DEL SISTEMA
        CASE
            WHEN FechaFin IS NOT NULL AND FechaActualizacion IS NOT NULL
            THEN DATEDIFF(MINUTE, FechaFin, FechaActualizacion)
            ELSE NULL
        END AS LatenciaActualizacionMinutos,

        -- INDICADORES DE PROBLEMAS
        CASE
            WHEN FechaFin IS NOT NULL AND FechaActualizacion IS NOT NULL
                 AND DATEDIFF(MINUTE, FechaFin, FechaActualizacion) > 15
            THEN 1
            ELSE 0
        END AS CallbackFallidoIndicador,

        CASE
            WHEN IntentosConciliadorFallidos >= 3
            THEN 1
            ELSE 0
        END AS ConciliadorProblemaIndicador,

        -- CLASIFICACIÓN DE RENDIMIENTO
        CASE
            WHEN FechaFin IS NOT NULL AND FechaActualizacion IS NOT NULL
            THEN
                CASE
                    WHEN DATEDIFF(MINUTE, FechaFin, FechaActualizacion) <= 2 THEN 'EXCELENTE'
                    WHEN DATEDIFF(MINUTE, FechaFin, FechaActualizacion) <= 5 THEN 'BUENO'
                    WHEN DATEDIFF(MINUTE, FechaFin, FechaActualizacion) <= 15 THEN 'REGULAR'
                    ELSE 'DEFICIENTE'
                END
            ELSE 'NO_APLICABLE'
        END AS ClasificacionRendimiento

    FROM EjecucionesUnificadas
)

SELECT
    EjecucionId,
    DeploymentId,
    RobotId,
    EquipoId,
    UserId,
    FechaInicio,
    FechaFin,
    Estado,
    FechaActualizacion,
    IntentosConciliadorFallidos,
    CallbackInfo,
    Origen,
    MecanismoFinalizacion,
    DuracionEjecucionMinutos,
    LatenciaActualizacionMinutos,
    CallbackFallidoIndicador,
    ConciliadorProblemaIndicador,
    ClasificacionRendimiento,

    -- MÉTRICAS ADICIONALES CALCULADAS
    CASE
        WHEN MecanismoFinalizacion = 'CALLBACK_EXITOSO' THEN 1
        ELSE 0
    END AS EsCallbackExitoso,

    CASE
        WHEN MecanismoFinalizacion IN ('CONCILIADOR_EXITOSO', 'CONCILIADOR_INMEDIATO') THEN 1
        ELSE 0
    END AS EsConciliadorExitoso,

    CASE
        WHEN MecanismoFinalizacion = 'CONCILIADOR_AGOTADO' THEN 1
        ELSE 0
    END AS EsConciliadorAgotado,

    -- INDICADORES DE SALUD DEL SISTEMA
    CASE
        WHEN Estado IN ('COMPLETED', 'RUN_COMPLETED') THEN 1
        ELSE 0
    END AS EjecucionExitosa,

    CASE
        WHEN Estado IN ('RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED') THEN 1
        ELSE 0
    END AS EjecucionFallida

FROM EjecucionesAnalizadas;
GO
