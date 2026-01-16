CREATE PROCEDURE [dbo].[CargarProgramacionRangoMensual]
    @Robot NVARCHAR(100),
    @Equipos NVARCHAR(MAX), -- Lista de equipos separados por comas
    @HoraInicio TIME,
    @Tolerancia INT,
    @DiaInicioMes INT = NULL,        -- Para rangos tipo "del 1 al 15"
    @DiaFinMes INT = NULL,            -- Para rangos tipo "del 1 al 15"
    @UltimosDiasMes INT = NULL        -- Para rangos tipo "últimos 5 días"
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @RobotId INT;
    DECLARE @NewProgramacionId INT;
    DECLARE @CurrentEquipoId INT;
    DECLARE @CurrentEquipoNombre NVARCHAR(100);
    DECLARE @ErrorMessage NVARCHAR(4000);
    DECLARE @ErrorSeverity INT;
    DECLARE @ErrorState INT;
    BEGIN TRY
        -- Validaciones de parámetros
        IF @DiaInicioMes IS NULL AND @DiaFinMes IS NULL AND @UltimosDiasMes IS NULL
        BEGIN
            RAISERROR('Debe especificar o bien un rango (DiaInicioMes + DiaFinMes) o bien UltimosDiasMes.', 16, 1);
            RETURN;
        END
        IF @DiaInicioMes IS NOT NULL AND @DiaFinMes IS NOT NULL AND @UltimosDiasMes IS NOT NULL
        BEGIN
            RAISERROR('No puede especificar simultáneamente un rango (DiaInicioMes/DiaFinMes) Y UltimosDiasMes.', 16, 1);
            RETURN;
        END
        IF @DiaInicioMes IS NOT NULL AND @DiaFinMes IS NULL
        BEGIN
            RAISERROR('Si especifica DiaInicioMes, debe especificar también DiaFinMes.', 16, 1);
            RETURN;
        END
        IF @DiaInicioMes IS NULL AND @DiaFinMes IS NOT NULL
        BEGIN
            RAISERROR('Si especifica DiaFinMes, debe especificar también DiaInicioMes.', 16, 1);
            RETURN;
        END
        IF @DiaInicioMes IS NOT NULL AND (@DiaInicioMes < 1 OR @DiaInicioMes > 31)
        BEGIN
            RAISERROR('DiaInicioMes debe estar entre 1 y 31.', 16, 1);
            RETURN;
        END
        IF @DiaFinMes IS NOT NULL AND (@DiaFinMes < 1 OR @DiaFinMes > 31)
        BEGIN
            RAISERROR('DiaFinMes debe estar entre 1 y 31.', 16, 1);
            RETURN;
        END
        IF @DiaInicioMes IS NOT NULL AND @DiaFinMes IS NOT NULL AND @DiaInicioMes > @DiaFinMes
        BEGIN
            RAISERROR('DiaInicioMes no puede ser mayor que DiaFinMes.', 16, 1);
            RETURN;
        END
        IF @UltimosDiasMes IS NOT NULL AND (@UltimosDiasMes < 1 OR @UltimosDiasMes > 31)
        BEGIN
            RAISERROR('UltimosDiasMes debe estar entre 1 y 31.', 16, 1);
            RETURN;
        END
        BEGIN TRANSACTION;
        -- Obtener RobotId
        SELECT @RobotId = RobotId FROM dbo.Robots WHERE Robot = @Robot;
        IF @RobotId IS NULL
        BEGIN
            RAISERROR('El robot especificado no existe.', 16, 1);
            RETURN;
        END
        -- Insertar en Programaciones con el nuevo tipo 'RangoMensual'
        INSERT INTO dbo.Programaciones (
            RobotId,
            TipoProgramacion,
            HoraInicio,
            Tolerancia,
            Activo,
            FechaCreacion,
            DiaInicioMes,
            DiaFinMes,
            UltimosDiasMes
        )
        VALUES (
            @RobotId,
            'RangoMensual',
            @HoraInicio,
            @Tolerancia,
            1,
            GETDATE(),
            @DiaInicioMes,
            @DiaFinMes,
            @UltimosDiasMes
        );
        -- Obtener el ProgramacionId recién insertado
        SET @NewProgramacionId = SCOPE_IDENTITY();
        IF @NewProgramacionId IS NULL
        BEGIN
            RAISERROR('No se pudo obtener el ID de la nueva programación.', 16, 1);
            RETURN;
        END
        -- Actualizar el estado del Robot a no online (programado)
        UPDATE dbo.Robots
        SET EsOnline = 0
        WHERE RobotId = @RobotId;
        -- Procesar cada equipo en la lista @Equipos
        DECLARE team_cursor CURSOR FOR
        SELECT LTRIM(RTRIM(value))
        FROM STRING_SPLIT(@Equipos, ',');
        OPEN team_cursor;
        FETCH NEXT FROM team_cursor INTO @CurrentEquipoNombre;
        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @CurrentEquipoId = NULL;
            -- Obtener EquipoId para el equipo actual
            SELECT @CurrentEquipoId = EquipoId FROM dbo.Equipos WHERE Equipo = @CurrentEquipoNombre;
            IF @CurrentEquipoId IS NOT NULL
            BEGIN
                -- Verificar si la asignación ya existe
                IF EXISTS (SELECT 1 FROM dbo.Asignaciones WHERE RobotId = @RobotId AND EquipoId = @CurrentEquipoId)
                BEGIN
                    UPDATE dbo.Asignaciones
                    SET EsProgramado = 1,
                        ProgramacionId = @NewProgramacionId,
                        Reservado = 0,
                        AsignadoPor = 'SP_Programacion_RangoMensual',
                        FechaAsignacion = GETDATE()
                    WHERE RobotId = @RobotId AND EquipoId = @CurrentEquipoId;
                END
                ELSE
                BEGIN
                    INSERT INTO dbo.Asignaciones (RobotId, EquipoId, EsProgramado, ProgramacionId, Reservado, AsignadoPor, FechaAsignacion)
                    VALUES (@RobotId, @CurrentEquipoId, 1, @NewProgramacionId, 0, 'SP_Programacion_RangoMensual', GETDATE());
                END
                -- Actualizar el equipo para que no permita balanceo dinámico
                UPDATE dbo.Equipos
                SET PermiteBalanceoDinamico = 0
                WHERE EquipoId = @CurrentEquipoId;
            END
            ELSE
            BEGIN
                PRINT 'Warning: Equipo ' + @CurrentEquipoNombre + ' no encontrado y no será asignado.';
            END
            FETCH NEXT FROM team_cursor INTO @CurrentEquipoNombre;
        END
        CLOSE team_cursor;
        DEALLOCATE team_cursor;
        COMMIT TRANSACTION;
        -- Mensaje de éxito con detalles
        DECLARE @MensajeDetalle NVARCHAR(500);
        IF @UltimosDiasMes IS NOT NULL
            SET @MensajeDetalle = 'los últimos ' + CAST(@UltimosDiasMes AS NVARCHAR(10)) + ' días de cada mes';
        ELSE
            SET @MensajeDetalle = 'del día ' + CAST(@DiaInicioMes AS NVARCHAR(10)) + ' al ' + CAST(@DiaFinMes AS NVARCHAR(10)) + ' de cada mes';
        PRINT 'Programación de rango mensual cargada exitosamente para el robot ' + @Robot + ' - Ejecutará ' + @MensajeDetalle;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
        SELECT
            @ErrorMessage = ERROR_MESSAGE(),
            @ErrorSeverity = ERROR_SEVERITY(),
            @ErrorState = ERROR_STATE();
        -- Registrar el error en la tabla ErrorLog
        DECLARE @Parametros NVARCHAR(MAX);
        SET @Parametros = '@Robot = ' + @Robot +
                        ', @Equipos = ' + @Equipos +
                        ', @HoraInicio = ' + CONVERT(NVARCHAR(8), @HoraInicio, 108) +
                        ', @Tolerancia = ' + CAST(@Tolerancia AS NVARCHAR(10)) +
                        ', @DiaInicioMes = ' + ISNULL(CAST(@DiaInicioMes AS NVARCHAR(10)), 'NULL') +
                        ', @DiaFinMes = ' + ISNULL(CAST(@DiaFinMes AS NVARCHAR(10)), 'NULL') +
                        ', @UltimosDiasMes = ' + ISNULL(CAST(@UltimosDiasMes AS NVARCHAR(10)), 'NULL');
        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (
            SUSER_NAME(),
            'CargarProgramacionRangoMensual',
            @ErrorMessage,
            @Parametros
        );
        PRINT 'Error: ' + @ErrorMessage;
        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END