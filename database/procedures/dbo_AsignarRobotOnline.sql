SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[AsignarRobotOnline]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[AsignarRobotOnline] AS' 
END
ALTER PROCEDURE [dbo].[AsignarRobotOnline]
    @Robot NVARCHAR(100),
    @Equipos NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        BEGIN TRANSACTION;

		SET @Equipos = UPPER(TRIM(@Equipos))
        -- Validar la existencia del robot
        DECLARE @RobotId INT;
        SELECT @RobotId = RobotId FROM Robots WHERE Robot = @Robot;
        
        IF @RobotId IS NULL
        BEGIN
            RAISERROR('El robot especificado no existe.', 16, 1);
            RETURN;
        END

        -- Preparar la tabla temporal para los equipos
        DECLARE @EquiposTemp TABLE (Equipo NVARCHAR(255));
        INSERT INTO @EquiposTemp (Equipo)
        SELECT TRIM(value) FROM STRING_SPLIT(@Equipos, ',');

        -- Iterar sobre los equipos y asignarlos
        DECLARE @EquipoNombre NVARCHAR(255);
        DECLARE @EquipoId INT;
        
        DECLARE equipo_cursor CURSOR FOR 
        SELECT Equipo FROM @EquiposTemp;

        OPEN equipo_cursor;
        FETCH NEXT FROM equipo_cursor INTO @EquipoNombre;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            -- Validar la existencia del equipo
            SELECT @EquipoId = EquipoId FROM Equipos WHERE Equipo = @EquipoNombre;
            
            IF @EquipoId IS NULL
            BEGIN
                PRINT 'El equipo "' + @EquipoNombre + '" no existe. Se omitirá su asignación.';
            END
            ELSE
            BEGIN
                -- Verificar si el robot ya está asignado al equipo
                IF EXISTS (SELECT 1 FROM Asignaciones WHERE RobotId = @RobotId AND EquipoId = @EquipoId)
                BEGIN
                    PRINT 'El robot ya está asignado al equipo "' + @EquipoNombre + '". Se omitirá su asignación.';
                END
                ELSE
                BEGIN
                    -- Insertar la nueva asignación no programada
                    INSERT INTO Asignaciones (RobotId, EquipoId, EsProgramado)
                    VALUES (@RobotId, @EquipoId, 0); -- EsProgramado = 0 para robots no programados

                    PRINT 'Robot asignado exitosamente al equipo "' + @EquipoNombre + '".';
                END
            END

            FETCH NEXT FROM equipo_cursor INTO @EquipoNombre;
        END

        CLOSE equipo_cursor;
        DEALLOCATE equipo_cursor;

        COMMIT TRANSACTION;
        PRINT 'Asignaciones completadas exitosamente.';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        -- Registrar el error en la tabla ErrorLog
        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (
            SUSER_NAME(),
            'AsignarRobotOnline',
            ERROR_MESSAGE(),
            '@Robot = ' + @Robot + ', @Equipos = ' + @Equipos
        );

        -- Mostrar un mensaje de error
        PRINT 'Error: ' + ERROR_MESSAGE();
    END CATCH
END
