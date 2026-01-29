IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID(N'[dbo].[ConfiguracionSistema]')
    AND name = 'RequiereReinicio'
)
BEGIN
    ALTER TABLE [dbo].[ConfiguracionSistema]
    ADD [RequiereReinicio] BIT NOT NULL DEFAULT 1;
END
GO

-- Actualizar variables dinámicas conocidas
UPDATE [dbo].[ConfiguracionSistema]
SET [RequiereReinicio] = 0
WHERE [Clave] IN ('BALANCEO_PREEMPTION_MODE', 'BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO');
GO
