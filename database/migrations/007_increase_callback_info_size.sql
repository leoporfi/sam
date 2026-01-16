-- Migration 007: Aumentar tamaño de CallbackInfo en dbo.Ejecuciones
-- El tamaño actual de 500 caracteres es insuficiente para algunos payloads de A360.
IF EXISTS (SELECT * FROM sys.columns
           WHERE object_id = OBJECT_ID(N'[dbo].[Ejecuciones]')
           AND name = 'CallbackInfo')
BEGIN
    ALTER TABLE [dbo].[Ejecuciones] ALTER COLUMN [CallbackInfo] NVARCHAR(MAX) NULL;
END
GO