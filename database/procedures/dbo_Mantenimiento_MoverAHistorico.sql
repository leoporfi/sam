CREATE OR ALTER PROCEDURE [dbo].[Mantenimiento_MoverAHistorico]
    @BatchSizeParam INT = 1000,         -- Tamaño del lote para mover/eliminar
    @DiasRetencionMover INT = 1,        -- Mover ejecuciones con más de X días de antigüedad
    @DiasRetencionPurga INT = 15,       -- Purgar del histórico ejecuciones con más de X días de antigüedad
    @MaxIterationsParam INT = 20000     -- Límite de seguridad para evitar bucles infinitos (muy alto por defecto)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @usuario VARCHAR(255) = SUSER_SNAME();

    -- =================================================================================
    -- PARTE 1: MOVER REGISTROS DE 'Ejecuciones' A 'Ejecuciones_Historico'
    -- =================================================================================

    DECLARE @rowsAffected INT = @BatchSizeParam;
    DECLARE @totalRowsMoved INT = 0;
    DECLARE @iterationCount INT = 0;

    DECLARE @EstadosFinalizados TABLE (Estado NVARCHAR(20) PRIMARY KEY);
    INSERT INTO @EstadosFinalizados (Estado) VALUES
    ('DEPLOY_FAILED'), ('RUN_ABORTED'), ('COMPLETED'),
    ('RUN_COMPLETED'), ('RUN_FAILED'), ('UNKNOWN');

    PRINT 'Iniciando proceso de movimiento de ejecuciones a la tabla histórica.';
    PRINT 'Tamaño de lote: ' + CAST(@BatchSizeParam AS VARCHAR(10));

    -- Bucle para procesar por lotes, ahora con el límite de iteraciones como parámetro de seguridad
    WHILE @rowsAffected = @BatchSizeParam AND @iterationCount < @MaxIterationsParam
    BEGIN
        SET @iterationCount = @iterationCount + 1;

        BEGIN TRY
            -- Usamos una tabla temporal para el lote, más segura que verificar con OBJECT_ID y hacer DROP/CREATE
            IF OBJECT_ID('tempdb..#LoteActual') IS NOT NULL DROP TABLE #LoteActual;

            -- Paso 1: Seleccionar el lote a procesar
            SELECT TOP (@BatchSizeParam)
                EjecucionId,
				DeploymentId,
                RobotId,
                EquipoId,
                UserId,
                Hora,
                FechaInicio,
                FechaFin,
                FechaInicioReal,
                Estado,
                FechaActualizacion,
                IntentosConciliadorFallidos,
                CallbackInfo
            INTO #LoteActual
            FROM dbo.Ejecuciones
            WHERE
                Estado IN (SELECT Estado FROM @EstadosFinalizados)
                AND COALESCE(FechaFin, FechaInicio) < DATEADD(day, -@DiasRetencionMover, GETDATE())
            ORDER BY EjecucionId; -- Orden determinístico es crucial

            SET @rowsAffected = @@ROWCOUNT;

            IF @rowsAffected = 0 BREAK;

            -- Paso 2 y 3 en una sola transacción para garantizar consistencia
            BEGIN TRANSACTION T_Move;

            INSERT INTO dbo.Ejecuciones_Historico (
                EjecucionId,
				DeploymentId,
                RobotId,
                EquipoId,
                UserId,
                Hora,
                FechaInicio,
                FechaFin,
                FechaInicioReal,
                Estado,
                FechaActualizacion,
                IntentosConciliadorFallidos,
                CallbackInfo
            )
            SELECT
                EjecucionId,
				DeploymentId,
                RobotId,
                EquipoId,
                UserId,
                Hora,
                FechaInicio,
                FechaFin,
                FechaInicioReal,
                Estado,
                FechaActualizacion,
                IntentosConciliadorFallidos,
                CallbackInfo
            FROM #LoteActual;

            DELETE e
            FROM dbo.Ejecuciones e
            INNER JOIN #LoteActual l ON e.EjecucionID = l.EjecucionID;

            COMMIT TRANSACTION T_Move;

            SET @totalRowsMoved = @totalRowsMoved + @rowsAffected;

            IF @iterationCount % 10 = 0
                PRINT 'Procesados ' + CAST(@totalRowsMoved AS VARCHAR(10)) + ' registros en ' + CAST(@iterationCount AS VARCHAR(10)) + ' lotes.';

            IF @rowsAffected = @BatchSizeParam WAITFOR DELAY '00:00:02';

        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
			INSERT INTO dbo.ErrorLog (FechaHora ,Usuario, SPNombre, ErrorMensaje, Parametros)
            VALUES (
				GETDATE(),
				@usuario,
				'usp_MoverEjecucionesAHistorico_Mover',
				ERROR_MESSAGE() + ' (Iteración: ' + CAST(@iterationCount AS VARCHAR) + ')',
				'Lote: ' + CAST(@BatchSizeParam AS VARCHAR) + ', Registros movidos hasta ahora: ' + CAST(@totalRowsMoved AS VARCHAR)
			);

            IF ERROR_NUMBER() = 9002 -- Log lleno
            BEGIN
                PRINT 'Error de log lleno detectado. Abortando proceso.';
                BREAK;
            END
            ELSE
            BEGIN
                PRINT 'Error en iteración ' + CAST(@iterationCount AS VARCHAR) + ': ' + ERROR_MESSAGE();
                SET @rowsAffected = @BatchSizeParam;
            END
        END CATCH
    END

    PRINT 'Movimiento finalizado. Total de registros movidos: ' + CAST(@totalRowsMoved AS VARCHAR(10));
    IF @iterationCount >= @MaxIterationsParam
        PRINT 'ADVERTENCIA: El proceso se detuvo al alcanzar el límite máximo de iteraciones (' + CAST(@MaxIterationsParam AS VARCHAR) + '). Podrían quedar registros por mover.';

    -- =================================================================================
    -- PARTE 2: PURGAR REGISTROS ANTIGUOS DE 'Ejecuciones_Historico'
    -- =================================================================================

    DECLARE @purgeDate DATE = DATEADD(day, -@DiasRetencionPurga, GETDATE());
    DECLARE @totalRowsPurged INT = 0;
    DECLARE @purgeIterations INT = 0;

    PRINT 'Iniciando purga de registros históricos con más de ' + CAST(@DiasRetencionPurga AS VARCHAR) + ' días de antigüedad.';

    SET @rowsAffected = @BatchSizeParam;
    WHILE @rowsAffected = @BatchSizeParam AND @purgeIterations < @MaxIterationsParam
    BEGIN
        SET @purgeIterations = @purgeIterations + 1;

        BEGIN TRY
            BEGIN TRANSACTION T_Purge;

            DELETE TOP (@BatchSizeParam)
            FROM dbo.Ejecuciones_Historico
            WHERE FechaInicio < @purgeDate;

            SET @rowsAffected = @@ROWCOUNT;
            COMMIT TRANSACTION T_Purge;

            SET @totalRowsPurged = @totalRowsPurged + @rowsAffected;

            IF @purgeIterations % 10 = 0 AND @rowsAffected > 0
                PRINT 'Purgados ' + CAST(@totalRowsPurged AS VARCHAR(10)) + ' registros históricos.';

            IF @rowsAffected = @BatchSizeParam WAITFOR DELAY '00:00:01';

        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;

            INSERT INTO dbo.ErrorLog (FechaHora, Usuario, SPNombre, ErrorMensaje, Parametros)
            VALUES (
				GETDATE(),
				@usuario,
				'usp_MoverEjecucionesAHistorico_Purga',
                ERROR_MESSAGE() + ' (Iteración purga: ' + CAST(@purgeIterations AS VARCHAR) + ')',
                'Fecha límite: ' + CONVERT(VARCHAR, @purgeDate, 120)
			);

            IF ERROR_NUMBER() = 9002
            BEGIN
                PRINT 'Error de log lleno en purga. Abortando proceso.';
                BREAK;
            END
            ELSE
            BEGIN
                PRINT 'Error en purga, iteración ' + CAST(@purgeIterations AS VARCHAR) + ': ' + ERROR_MESSAGE();
                SET @rowsAffected = @BatchSizeParam;
            END
        END CATCH
    END

    PRINT 'Purga finalizada. Total de registros eliminados del histórico: ' + CAST(@totalRowsPurged AS VARCHAR(10));
     IF @purgeIterations >= @MaxIterationsParam
        PRINT 'ADVERTENCIA: La purga se detuvo al alcanzar el límite máximo de iteraciones (' + CAST(@MaxIterationsParam AS VARCHAR) + '). Podrían quedar registros por purgar.';

    -- Estadísticas finales
    PRINT '=== RESUMEN DE EJECUCIÓN ===';
    PRINT 'Registros movidos a histórico: ' + CAST(@totalRowsMoved AS VARCHAR(10));
    PRINT 'Registros purgados del histórico: ' + CAST(@totalRowsPurged AS VARCHAR(10));
    PRINT 'Proceso SAM completado exitosamente.';

END
