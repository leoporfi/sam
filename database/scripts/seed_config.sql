-- Script para poblar la tabla ConfiguracionSistema con valores iniciales
-- Este script es idempotente: solo inserta si la clave no existe.
-- Convención de nombres: {SERVICIO}_{TEMA}_{ACCION}[_{UNIDAD}]

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- 1. Asegurar que la columna Valor sea NVARCHAR(MAX) si aún no lo es (Migración en línea)
IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[ConfiguracionSistema]') AND name = 'Valor' AND max_length != -1)
BEGIN
    ALTER TABLE [dbo].[ConfiguracionSistema] ALTER COLUMN [Valor] NVARCHAR(MAX) NULL;
    PRINT 'Columna Valor actualizada a NVARCHAR(MAX)';
END
GO

-- 2. Procedimiento auxiliar para insertar o actualizar
CREATE OR ALTER PROCEDURE #InsertarConfigSiNoExiste
    @Clave VARCHAR(100),
    @Valor NVARCHAR(MAX),
    @Descripcion VARCHAR(500)
AS
BEGIN
    IF NOT EXISTS (SELECT 1 FROM [dbo].[ConfiguracionSistema] WHERE Clave = @Clave)
    BEGIN
        INSERT INTO [dbo].[ConfiguracionSistema] (Clave, Valor, Descripcion, FechaActualizacion)
        VALUES (@Clave, @Valor, @Descripcion, GETDATE());
        PRINT 'Insertada configuración: ' + @Clave;
    END
    ELSE
    BEGIN
        -- Actualizar solo la descripción si ya existe
        UPDATE [dbo].[ConfiguracionSistema]
        SET Descripcion = @Descripcion,
            FechaActualizacion = GETDATE()
        WHERE Clave = @Clave;
        PRINT 'Actualizada descripción para: ' + @Clave;
    END
END
GO

-- 3. Insertar variables de negocio
-- NOTA: Los valores aquí son los DEFAULT. Si el entorno ya tiene .env, el sistema usará .env hasta que se actualice la BD.

-- ===== EMAIL =====
EXEC #InsertarConfigSiNoExiste 'EMAIL_DESTINATARIOS', 'admin@example.com', 'Lista de correos separados por coma para alertas';

-- ===== LANZADOR =====
-- Ciclo principal
EXEC #InsertarConfigSiNoExiste 'LANZADOR_CICLO_INTERVALO_SEG', '15', 'Intervalo en segundos entre ciclos de lanzamiento';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_WORKERS_MAX', '10', 'Número máximo de workers para lanzamientos paralelos';

-- Sincronización
EXEC #InsertarConfigSiNoExiste 'LANZADOR_SYNC_HABILITAR', 'True', 'Habilita o deshabilita la sincronización automática con A360';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_SYNC_INTERVALO_SEG', '3600', 'Intervalo en segundos para sincronización completa con A360';

-- Conciliación
EXEC #InsertarConfigSiNoExiste 'LANZADOR_CONCILIACION_INTERVALO_SEG', '300', 'Intervalo en segundos para conciliación de estados';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_CONCILIACION_LOTE_TAMANO', '50', 'Tamaño del lote para conciliación de ejecuciones';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_CONCILIACION_UNKNOWN_TOLERANCIA_DIAS', '30', 'Días de tolerancia para estados Unknown antes de inferir finalización';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_CONCILIACION_INFERENCIA_MENSAJE', 'Finalizado (Inferido por ausencia en lista de activos)', 'Mensaje a guardar cuando se infiere finalización';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_CONCILIACION_INFERENCIA_MAX_INTENTOS', '5', 'Máximo de intentos de inferencia antes de marcar como fallido';

-- Deploy
EXEC #InsertarConfigSiNoExiste 'LANZADOR_DEPLOY_REINTENTOS_MAX', '2', 'Número máximo de reintentos para deploy de robot';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_DEPLOY_REINTENTO_DELAY_SEG', '5', 'Segundos de espera entre reintentos de deploy';

-- Robot
EXEC #InsertarConfigSiNoExiste 'LANZADOR_ROBOT_REPETICIONES', '3', 'Número de repeticiones por defecto para cada robot';

-- Pausa
EXEC #InsertarConfigSiNoExiste 'LANZADOR_PAUSA_INICIO_HHMM', '21:00', 'Hora de inicio de la pausa diaria de lanzamientos (HH:MM)';
EXEC #InsertarConfigSiNoExiste 'LANZADOR_PAUSA_FIN_HHMM', '21:15', 'Hora de fin de la pausa diaria de lanzamientos (HH:MM)';

-- Alertas
EXEC #InsertarConfigSiNoExiste 'LANZADOR_ALERTAS_ERROR_412_UMBRAL', '20', 'Umbral de errores 412 antes de enviar alerta';

-- ===== BALANCEADOR =====
-- Ciclo
EXEC #InsertarConfigSiNoExiste 'BALANCEADOR_CICLO_INTERVALO_SEG', '120', 'Intervalo en segundos del ciclo del balanceador';

-- Pool
EXEC #InsertarConfigSiNoExiste 'BALANCEADOR_POOL_ENFRIAMIENTO_SEG', '300', 'Tiempo de espera tras un cambio de pool antes de permitir nuevos cambios';
EXEC #InsertarConfigSiNoExiste 'BALANCEADOR_POOL_AISLAMIENTO_ESTRICTO', 'True', 'Si es True, respeta estrictamente las asignaciones de pool (No Overflow)';
EXEC #InsertarConfigSiNoExiste 'BALANCEADOR_PREEMPTION_HABILITAR', 'False', 'Si es True, permite quitar equipos a robots de baja prioridad (Preemption)';

-- Carga
EXEC #InsertarConfigSiNoExiste 'BALANCEADOR_CARGA_PROVEEDORES', 'clouders,rpa360', 'Proveedores de carga habilitados (separados por coma)';
EXEC #InsertarConfigSiNoExiste 'BALANCEADOR_TICKETS_DEFAULT_POR_EQUIPO', '15', 'Tickets por defecto asignados a cada equipo';

-- ===== INTERFAZ_WEB =====
-- Sesión
EXEC #InsertarConfigSiNoExiste 'INTERFAZ_WEB_SESION_TIMEOUT_MIN', '30', 'Tiempo de expiración de la sesión web en minutos';

-- Ejecución
EXEC #InsertarConfigSiNoExiste 'INTERFAZ_WEB_EJECUCION_DEMORA_UMBRAL_MIN', '25', 'Umbral en minutos para considerar una ejecución como demorada';
EXEC #InsertarConfigSiNoExiste 'INTERFAZ_WEB_EJECUCION_UMBRAL_FACTOR', '1.5', 'Factor multiplicador para umbral dinámico de demoras';
EXEC #InsertarConfigSiNoExiste 'INTERFAZ_WEB_EJECUCION_UMBRAL_PISO_MIN', '10', 'Piso mínimo en minutos para umbral dinámico';
EXEC #InsertarConfigSiNoExiste 'INTERFAZ_WEB_EJECUCION_FILTRO_CORTAS_MIN', '2', 'Minutos mínimos para filtrar ejecuciones muy cortas';

-- Limpieza
DROP PROCEDURE #InsertarConfigSiNoExiste;
GO
