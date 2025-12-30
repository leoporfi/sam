-- Migration: Add FechaInicioReal column to Ejecuciones and Ejecuciones_Historico
-- Description: Stores the actual start time reported by A360 to measure latency.

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[Ejecuciones]') AND name = 'FechaInicioReal')
BEGIN
    ALTER TABLE [dbo].[Ejecuciones] ADD [FechaInicioReal] DATETIME NULL;
    PRINT 'Column FechaInicioReal added to dbo.Ejecuciones';
END
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[Ejecuciones_Historico]') AND name = 'FechaInicioReal')
BEGIN
    ALTER TABLE [dbo].[Ejecuciones_Historico] ADD [FechaInicioReal] DATETIME NULL;
    PRINT 'Column FechaInicioReal added to dbo.Ejecuciones_Historico';
END
GO
