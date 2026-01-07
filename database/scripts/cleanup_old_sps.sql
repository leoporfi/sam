-- =============================================
-- Script de Limpieza: Eliminar Stored Procedures antiguos
-- Descripción: Elimina los SPs que han sido renombrados para evitar duplicados.
-- Fecha: 2026-01-07
-- =============================================

PRINT 'Iniciando limpieza de Stored Procedures antiguos...';

-- 1. AnalisisTasasExito -> Analisis_TasasExito
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[AnalisisTasasExito]') AND type in (N'P', N'PC'))
BEGIN
    DROP PROCEDURE [dbo].[AnalisisTasasExito];
    PRINT 'Eliminado: dbo.AnalisisTasasExito';
END

-- 2. AnalisisUtilizacionRecursos -> Analisis_UtilizacionRecursos
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[AnalisisUtilizacionRecursos]') AND type in (N'P', N'PC'))
BEGIN
    DROP PROCEDURE [dbo].[AnalisisUtilizacionRecursos];
    PRINT 'Eliminado: dbo.AnalisisUtilizacionRecursos';
END

-- 3. AnalisisPatronesTemporales -> Analisis_PatronesTemporales
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[AnalisisPatronesTemporales]') AND type in (N'P', N'PC'))
BEGIN
    DROP PROCEDURE [dbo].[AnalisisPatronesTemporales];
    PRINT 'Eliminado: dbo.AnalisisPatronesTemporales';
END

-- 4. AnalisisTiemposEjecucionRobots -> Analisis_TiemposEjecucion
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[AnalisisTiemposEjecucionRobots]') AND type in (N'P', N'PC'))
BEGIN
    DROP PROCEDURE [dbo].[AnalisisTiemposEjecucionRobots];
    PRINT 'Eliminado: dbo.AnalisisTiemposEjecucionRobots';
END

-- 5. AnalisisDispersionRobot -> Analisis_Dispersion
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[AnalisisDispersionRobot]') AND type in (N'P', N'PC'))
BEGIN
    DROP PROCEDURE [dbo].[AnalisisDispersionRobot];
    PRINT 'Eliminado: dbo.AnalisisDispersionRobot';
END

-- 6. ObtenerDashboardBalanceador -> Analisis_Balanceador
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerDashboardBalanceador]') AND type in (N'P', N'PC'))
BEGIN
    DROP PROCEDURE [dbo].[ObtenerDashboardBalanceador];
    PRINT 'Eliminado: dbo.ObtenerDashboardBalanceador';
END

-- 7. ObtenerDashboardCallbacks -> Analisis_Callbacks
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerDashboardCallbacks]') AND type in (N'P', N'PC'))
BEGIN
    DROP PROCEDURE [dbo].[ObtenerDashboardCallbacks];
    PRINT 'Eliminado: dbo.ObtenerDashboardCallbacks';
END

-- 8. usp_AnalizarLatenciaEjecuciones -> Analisis_Latencia
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[usp_AnalizarLatenciaEjecuciones]') AND type in (N'P', N'PC'))
BEGIN
    DROP PROCEDURE [dbo].[usp_AnalizarLatenciaEjecuciones];
    PRINT 'Eliminado: dbo.usp_AnalizarLatenciaEjecuciones';
END

-- 9. usp_MoverEjecucionesAHistorico -> Mantenimiento_MoverAHistorico
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[usp_MoverEjecucionesAHistorico]') AND type in (N'P', N'PC'))
BEGIN
    DROP PROCEDURE [dbo].[usp_MoverEjecucionesAHistorico];
    PRINT 'Eliminado: dbo.usp_MoverEjecucionesAHistorico';
END

PRINT 'Limpieza completada.';
