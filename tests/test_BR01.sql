-- Inicia una transacción para revertir todos los cambios al final
BEGIN TRANSACTION;

-- Declaración de variables para los nombres de los robots de prueba
DECLARE @RobotApto NVARCHAR(100) = 'TEST_Robot_Programable';
DECLARE @RobotOnline NVARCHAR(100) = 'TEST_Robot_Online';
DECLARE @EquipoPrueba NVARCHAR(100) = 'TEST_Equipo_01';

-- 1. SETUP: Crear datos de prueba
PRINT '--- 1. Creando datos de prueba ---';
-- Insertar un robot apto para ser programado (EsOnline = 0)
IF NOT EXISTS (SELECT 1 FROM dbo.Robots WHERE Robot = @RobotApto)
    INSERT INTO dbo.Robots (RobotId, Robot, Descripcion, EsOnline) VALUES (99998, @RobotApto, 'Robot para prueba de programación', 0);
ELSE
    UPDATE dbo.Robots SET EsOnline = 0 WHERE Robot = @RobotApto;

-- Insertar un robot NO apto (EsOnline = 1)
IF NOT EXISTS (SELECT 1 FROM dbo.Robots WHERE Robot = @RobotOnline)
    INSERT INTO dbo.Robots (RobotId, Robot, Descripcion, EsOnline) VALUES (99999, @RobotOnline, 'Robot para prueba de validación', 1);
ELSE
    UPDATE dbo.Robots SET EsOnline = 1 WHERE Robot = @RobotOnline;

-- Insertar un equipo de prueba
IF NOT EXISTS (SELECT 1 FROM dbo.Equipos WHERE Equipo = @EquipoPrueba)
    INSERT INTO dbo.Equipos (EquipoId, Equipo, UserId, Activo_SAM, PermiteBalanceoDinamico) VALUES (99999, @EquipoPrueba, 1, 1, 1);

PRINT 'Datos de prueba creados.';
PRINT '';

-- 2. TEST 1: Caso de éxito (Intentar programar un robot con EsOnline = 0)
PRINT '--- 2. TEST 1: Intentando programar un robot apto (debería funcionar) ---';
BEGIN TRY
    EXEC dbo.CrearProgramacion
        @Robot = @RobotApto,
        @Equipos = @EquipoPrueba,
        @TipoProgramacion = 'Diaria',
        @HoraInicio = '10:00:00',
        @Tolerancia = 60;
    PRINT '=> RESULTADO: ÉXITO. La programación para ' + @RobotApto + ' se creó correctamente.';
END TRY
BEGIN CATCH
    PRINT '=> RESULTADO: ERROR INESPERADO. La programación para ' + @RobotApto + ' falló: ' + ERROR_MESSAGE();
END CATCH
PRINT '';

-- 3. TEST 2: Caso de fallo (Intentar programar un robot con EsOnline = 1)
PRINT '--- 3. TEST 2: Intentando programar un robot Online (debería fallar) ---';
BEGIN TRY
    EXEC dbo.CrearProgramacion
        @Robot = @RobotOnline,
        @Equipos = @EquipoPrueba,
        @TipoProgramacion = 'Diaria',
        @HoraInicio = '11:00:00',
        @Tolerancia = 60;
    PRINT '=> RESULTADO: ERROR. El SP no bloqueó la programación para ' + @RobotOnline;
END TRY
BEGIN CATCH
    IF ERROR_MESSAGE() LIKE '%No se puede crear una programación para un robot que está configurado como "Online"%'
        PRINT '=> RESULTADO: ÉXITO. El SP bloqueó correctamente la programación y devolvió el mensaje esperado.';
    ELSE
        PRINT '=> RESULTADO: ERROR. El SP falló, pero con un mensaje incorrecto: ' + ERROR_MESSAGE();
END CATCH
PRINT '';


-- 4. CLEANUP: Revertir la transacción para limpiar los datos de prueba
PRINT '--- 4. Limpiando datos de prueba ---';
ROLLBACK TRANSACTION;
PRINT 'Transacción revertida. La base de datos está en su estado original.';
