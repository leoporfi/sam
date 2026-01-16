-- Migration: Add configuration for critical executions detection
-- Date: 2026-01-07
-- Description: Adds UMBRAL_EJECUCION_DEMORADA_MINUTOS and FACTOR_UMBRAL_DINAMICO to ConfiguracionSistema
USE [SAM]
GO
-- Check if configurations already exist before inserting
IF NOT EXISTS (SELECT 1 FROM dbo.ConfiguracionSistema WHERE Clave = 'UMBRAL_EJECUCION_DEMORADA_MINUTOS')
BEGIN
    INSERT INTO dbo.ConfiguracionSistema (Clave, Valor, Descripcion, FechaActualizacion)
    VALUES (
        'UMBRAL_EJECUCION_DEMORADA_MINUTOS',
        '25',
        'Umbral fijo en minutos para detectar ejecuciones demoradas cuando no hay historial del robot',
        GETDATE()
    );
    PRINT 'Configuración UMBRAL_EJECUCION_DEMORADA_MINUTOS agregada exitosamente.';
END
ELSE
BEGIN
    PRINT 'Configuración UMBRAL_EJECUCION_DEMORADA_MINUTOS ya existe.';
END
GO
IF NOT EXISTS (SELECT 1 FROM dbo.ConfiguracionSistema WHERE Clave = 'FACTOR_UMBRAL_DINAMICO')
BEGIN
    INSERT INTO dbo.ConfiguracionSistema (Clave, Valor, Descripcion, FechaActualizacion)
    VALUES (
        'FACTOR_UMBRAL_DINAMICO',
        '1.5',
        'Factor multiplicador del tiempo promedio del robot para detectar ejecuciones demoradas (ej: 1.5 = 150% del tiempo normal)',
        GETDATE()
    );
    PRINT 'Configuración FACTOR_UMBRAL_DINAMICO agregada exitosamente.';
END
ELSE
BEGIN
    PRINT 'Configuración FACTOR_UMBRAL_DINAMICO ya existe.';
END
GO
PRINT 'Migración completada: Configuraciones para detección de ejecuciones críticas.';
GO