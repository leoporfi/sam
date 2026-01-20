SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CargarProgramacionMensual]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[CargarProgramacionMensual] AS'
END
-- =============================================
-- Author:      <Author,,Name>
-- Create date: <Create Date,,>
-- Description: Carga una programación mensual para un robot y equipos específicos.
-- Modificado por: AI Agent
-- Fecha Modificación: <Current Date>
-- Descripción Modificación:
--   - @Equipos ahora acepta una lista de nombres de equipo separados por comas.
--   - Se utiliza SCOPE_IDENTITY() para obtener el ProgramacionId.
--   - Se procesan múltiples equipos, insertando o actualizando en dbo.Asignaciones.
--   - Se establece ProgramacionId y EsProgramado=1 en dbo.Asignaciones.
--   - Se manejan advertencias para equipos no encontrados.
--   - Se mantiene la lógica de transacción y actualización de Robot.EsOnline.
-- =============================================
ALTER PROCEDURE [dbo].[CargarProgramacionMensual]
    @Robot NVARCHAR(100),
    @Equipos NVARCHAR(MAX), -- Comma-separated team names
    @DiaDelMes INT,
    @HoraInicio TIME, -- Assuming HoraInicio is TIME for Mensual, adjust if different
    @Tolerancia INT
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
    DECLARE @HoraInicioStr NVARCHAR(MAX);

    -- Convert HoraInicio TIME to NVARCHAR(MAX) for Programaciones table if its type is NVARCHAR(MAX)
    SET @HoraInicioStr = CONVERT(NVARCHAR(8), @HoraInicio); -- HH:MM:SS format

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Obtener RobotId
        SELECT @RobotId = RobotId FROM dbo.Robots WHERE Robot = @Robot;

        IF @RobotId IS NULL
        BEGIN
            RAISERROR('El robot especificado no existe.', 16, 1);
            RETURN;
        END

        -- Insertar en Programaciones
        -- Note: Assuming Programaciones.HoraInicio is NVARCHAR(MAX). If it's TIME, use @HoraInicio directly.
        INSERT INTO dbo.Programaciones (RobotId, TipoProgramacion, DiaDelMes, HoraInicio, Tolerancia, Activo, FechaCreacion)
        VALUES (@RobotId, 'Mensual', @DiaDelMes, @HoraInicioStr, @Tolerancia, 1, GETDATE());

        -- Obtener el ProgramacionId recién insertado
        SET @NewProgramacionId = SCOPE_IDENTITY();

        IF @NewProgramacionId IS NULL
        BEGIN
            RAISERROR('No se pudo obtener el ID de la nueva programación.', 16, 1);
            RETURN;
        END

        -- Actualizar el estado del Robot
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
                        AsignadoPor = 'SP_Programacion_Mensual',
                        FechaAsignacion = GETDATE()
                    WHERE RobotId = @RobotId AND EquipoId = @CurrentEquipoId;
                END
                ELSE
                BEGIN
                    INSERT INTO dbo.Asignaciones (RobotId, EquipoId, EsProgramado, ProgramacionId, Reservado, AsignadoPor, FechaAsignacion)
                    VALUES (@RobotId, @CurrentEquipoId, 1, @NewProgramacionId, 0, 'SP_Programacion_Mensual', GETDATE());
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
        PRINT 'Programación mensual cargada y equipos asignados/actualizados exitosamente para el robot ' + @Robot;

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
                        ', @Tolerancia = ' + CAST(@Tolerancia AS NVARCHAR(10));

        -- Luego:
        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (
            SUSER_NAME(),
            'CargarProgramacionEspecifica',
            ERROR_MESSAGE(),
            @Parametros
        );


        -- Mostrar un mensaje de error
        PRINT 'Error: ' + ERROR_MESSAGE();

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END

GO
