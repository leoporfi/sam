-- Script para poblar la tabla ConfiguracionSistema con valores iniciales
-- Este script es idempotente: solo inserta si la clave no existe.

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- 1. Asegurar que la columna Valor sea NVARCHAR(MAX) si aÃºn no lo es (MigraciÃ³n en lÃ­nea)
IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[ConfiguracionSistema]') AND name = 'Valor' AND max_length != -1)
BEGIN
    ALTER TABLE [dbo].[ConfiguracionSistema] ALTER COLUMN [Valor] NVARCHAR(MAX) NULL;
    PRINT 'Columna Valor actualizada a NVARCHAR(MAX)';
END
GO

-- 2. Procedimiento auxiliar para insertar si no existe
CREATE OR ALTER PROCEDURE #InsertarConfigSiNoExiste
    @Clave VARCHAR(50),
    @Valor NVARCHAR(MAX),
    @Descripcion VARCHAR(500)
AS
BEGIN
    IF NOT EXISTS (SELECT 1 FROM [dbo].[ConfiguracionSistema] WHERE Clave = @Clave)
    BEGIN
        INSERT INTO [dbo].[ConfiguracionSistema] (Clave, Valor, Descripcion, FechaActualizacion)
        VALUES (@Clave, @Valor, @Descripcion, GETDATE());
        PRINT 'Insertada configuraciÃ³n: ' + @Clave;
    END
    ELSE
    BEGIN
        PRINT 'Ya existe configuraciÃ³n: ' + @Clave;
    END
END
GO

-- 3. Insertar variables de negocio
-- NOTA: Los valores aquÃ­ son los DEFAULT. Si el entorno ya tiene .env, el sistema usarÃ¡ .env hasta que se actualice la BD.
-- Para una migraciÃ³n real, se deberÃ­a leer del .env y generar este script, pero aquÃ­ usamos los defaults seguros.

-- Email
EXEC #InsertarConfigSiNoExiste 'EMAIL_RECIPIENTS', 'admin@example.com', 'Lista de correos separados por coma para alertas';

-- Lanzador
EXEC #InsertarConfigSiNoExiste 'LANZADOR_INTERVALO_LANZAMIENTO_SEG', '15', 'Intervalo en segundos entre ciclos de lanzamiento';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_INTERVALO_SINCRONIZACION_SEG', '3600', 'Intervalo en segundos para sincronizaciÃ³n completa con A360';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_INTERVALO_CONCILIACION_SEG', '300', 'Intervalo en segundos para conciliaciÃ³n de estados';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_PAUSA_INICIO_HHMM', '21:00', 'Hora de inicio de la pausa diaria de lanzamientos';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_PAUSA_FIN_HHMM', '21:15', 'Hora de fin de la pausa diaria de lanzamientos';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_HABILITAR_SYNC', 'True', 'Habilita o deshabilita la sincronizaciÃ³n automÃ¡tica';

-- Balanceador
EXEC #InsertarConfigSiNoExiste 'BALANCEADOR_COOLING_PERIOD_SEG', '300', 'Tiempo de espera en segundos tras un error antes de reintentar';
EXEC #InsertarConfigSiNoExiste 'BALANCEADOR_INTERVALO_CICLO_SEG', '120', 'Intervalo en segundos del ciclo del balanceador';
EXEC #InsertarConfigSiNoExiste 'BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO', 'True', 'Si es True, respeta estrictamente las asignaciones de pool';

-- Interfaz Web
EXEC #InsertarConfigSiNoExiste 'INTERFAZ_WEB_SESSION_TIMEOUT_MIN', '30', 'Tiempo de expiraciÃ³n de la sesiÃ³n web en minutos';

-- Limpieza
DROP PROCEDURE #InsertarConfigSiNoExiste;
GO
