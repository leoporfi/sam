-- =============================================
-- FIX COMPLETO: CrearProgramacion
-- =============================================
-- Este script actualiza SOLO el SP CrearProgramacion
-- con el INSERT corregido que incluye FechaModificacion
-- y la corrección de la tabla temporal intermedia

USE DEV  -- Ajustar según el nombre de tu base de datos
GO

SET NOCOUNT ON;

PRINT '============================================='
PRINT 'ACTUALIZANDO SP: CrearProgramacion'
PRINT '============================================='
PRINT ''

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CrearProgramacion]') AND type in (N'P', N'PC'))
BEGIN
    PRINT 'SP encontrado. Actualizando...'
    PRINT ''
END
ELSE
BEGIN
    PRINT 'SP no existe. Creando...'
    PRINT ''
END
GO

-- Eliminar el SP existente
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CrearProgramacion]') AND type in (N'P', N'PC'))
    DROP PROCEDURE [dbo].[CrearProgramacion]
GO

-- Crear el SP con el INSERT corregido
CREATE PROCEDURE [dbo].[CrearProgramacion]
    @Robot NVARCHAR(100),
    @Equipos NVARCHAR(MAX),
    @TipoProgramacion NVARCHAR(20), -- 'Diaria', 'Semanal', 'Mensual', 'Especifica', 'RangoMensual'
    @HoraInicio TIME,
    @Tolerancia INT,
    @DiasSemana NVARCHAR(20) = NULL,
    @DiaDelMes INT = NULL,
    @FechaEspecifica DATE = NULL,
    @DiaInicioMes INT = NULL,
    @DiaFinMes INT = NULL,
    @UltimosDiasMes INT = NULL,
    @UsuarioCrea NVARCHAR(50) = 'WebApp_Creation',
    -- NUEVOS PARÁMETROS para robots cíclicos con ventanas
    @EsCiclico BIT = 0,
    @HoraFin TIME = NULL,
    @FechaInicioVentana DATE = NULL,
    @FechaFinVentana DATE = NULL,
    @IntervaloEntreEjecuciones INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON; 

    DECLARE @RobotId INT;
    DECLARE @NewProgramacionId INT;
    DECLARE @ErrorMessage NVARCHAR(4000);
    DECLARE @ErrorSeverity INT;
    DECLARE @ErrorState INT;
    DECLARE @EquipoIdActual INT;
    DECLARE @ConflictosCount INT = 0;

    CREATE TABLE #EquiposAProgramar (EquipoId INT PRIMARY KEY);
    CREATE TABLE #ConflictosDetectados (
        EquipoId INT,
        RobotNombre NVARCHAR(100),
        ProgramacionId INT,
        TipoEjecucion NVARCHAR(20)
    );

    BEGIN TRY
        -- Validaciones existentes
        SELECT @RobotId = RobotId FROM dbo.Robots WHERE Robot = @Robot;
        IF @RobotId IS NULL BEGIN RAISERROR('Robot no encontrado.', 16, 1); RETURN; END

        -- NUEVAS VALIDACIONES para robots cíclicos
        IF @EsCiclico = 1
        BEGIN
            -- Validar que HoraFin sea mayor que HoraInicio (si ambos están definidos)
            IF @HoraFin IS NOT NULL AND @HoraInicio >= @HoraFin
                RAISERROR('HoraFin debe ser mayor que HoraInicio para robots cíclicos.', 16, 1);

            -- Validar rango de fechas
            IF @FechaInicioVentana IS NOT NULL AND @FechaFinVentana IS NOT NULL
                AND @FechaInicioVentana > @FechaFinVentana
                RAISERROR('FechaInicioVentana no puede ser mayor que FechaFinVentana.', 16, 1);
        END

        -- Validar solapamientos usando el nuevo SP
        INSERT INTO #EquiposAProgramar (EquipoId)
        SELECT E.EquipoId
        FROM STRING_SPLIT(@Equipos, ',') AS S
        JOIN dbo.Equipos E ON LTRIM(RTRIM(S.value)) = E.Equipo
        WHERE E.Activo_SAM = 1;

        DECLARE equipo_cursor CURSOR FOR
        SELECT EquipoId FROM #EquiposAProgramar;

        OPEN equipo_cursor;
        FETCH NEXT FROM equipo_cursor INTO @EquipoIdActual;

        -- Crear tabla temporal intermedia para recibir todos los resultados del SP
        CREATE TABLE #ResultadosValidacion (
            ProgramacionId INT,
            RobotNombre NVARCHAR(100),
            TipoProgramacion NVARCHAR(20),
            HoraInicio TIME,
            HoraFin TIME,
            FechaInicioVentana DATE,
            FechaFinVentana DATE,
            DiasSemana NVARCHAR(20),
            DiaDelMes INT,
            DiaInicioMes INT,
            DiaFinMes INT,
            UltimosDiasMes INT,
            TipoEjecucion NVARCHAR(20)
        );

        WHILE @@FETCH_STATUS = 0
        BEGIN
            -- Limpiar tabla temporal intermedia
            DELETE FROM #ResultadosValidacion;
            
            -- Insertar resultados del SP en la tabla temporal intermedia
            INSERT INTO #ResultadosValidacion
            EXEC dbo.ValidarSolapamientoVentanas
                @EquipoId = @EquipoIdActual,
                @HoraInicio = @HoraInicio,
                @HoraFin = @HoraFin,
                @FechaInicioVentana = @FechaInicioVentana,
                @FechaFinVentana = @FechaFinVentana,
                @DiasSemana = @DiasSemana,
                @TipoProgramacion = @TipoProgramacion,
                @DiaDelMes = @DiaDelMes,
                @DiaInicioMes = @DiaInicioMes,
                @DiaFinMes = @DiaFinMes,
                @UltimosDiasMes = @UltimosDiasMes,
                @ProgramacionId = NULL;  -- Nueva programación

            -- Insertar solo las columnas necesarias en #ConflictosDetectados
            INSERT INTO #ConflictosDetectados (EquipoId, RobotNombre, ProgramacionId, TipoEjecucion)
            SELECT 
                @EquipoIdActual AS EquipoId,
                RobotNombre,
                ProgramacionId,
                TipoEjecucion
            FROM #ResultadosValidacion;

            FETCH NEXT FROM equipo_cursor INTO @EquipoIdActual;
        END

        -- Limpiar tabla temporal intermedia
        DROP TABLE #ResultadosValidacion;

        CLOSE equipo_cursor;
        DEALLOCATE equipo_cursor;

        SELECT @ConflictosCount = COUNT(*) FROM #ConflictosDetectados;
        IF @ConflictosCount > 0
        BEGIN
            DECLARE @MensajeConflictos NVARCHAR(MAX) = 
                'Se detectaron ' + CAST(@ConflictosCount AS NVARCHAR(10)) + 
                ' solapamiento(s) de ventanas temporales:' + CHAR(13) + CHAR(10);
            
            SELECT @MensajeConflictos = @MensajeConflictos + 
                '  - EquipoId: ' + CAST(EquipoId AS NVARCHAR(10)) + 
                ', Robot: ' + RobotNombre + 
                ', ProgramaciónId: ' + CAST(ProgramacionId AS NVARCHAR(10)) + 
                ', Tipo: ' + TipoEjecucion + CHAR(13) + CHAR(10)
            FROM #ConflictosDetectados;
            
            RAISERROR(@MensajeConflictos, 16, 1);
            RETURN;
        END

        BEGIN TRANSACTION;

        -- Insertar la nueva programación (con los nuevos campos)
        -- Orden EXACTO según estructura de tabla (18 columnas sin ProgramacionId):
        -- 1. RobotId, 2. TipoProgramacion, 3. HoraInicio, 4. DiasSemana, 5. DiaDelMes,
        -- 6. FechaEspecifica, 7. Tolerancia, 8. Activo, 9. FechaCreacion, 10. FechaModificacion,
        -- 11. DiaInicioMes, 12. DiaFinMes, 13. UltimosDiasMes,
        -- 14. EsCiclico, 15. HoraFin, 16. FechaInicioVentana, 17. FechaFinVentana, 18. IntervaloEntreEjecuciones
        INSERT INTO dbo.Programaciones (
            RobotId, 
            TipoProgramacion, 
            HoraInicio, 
            DiasSemana, 
            DiaDelMes, 
            FechaEspecifica,
            Tolerancia, 
            Activo, 
            FechaCreacion,
            FechaModificacion,
            DiaInicioMes, 
            DiaFinMes, 
            UltimosDiasMes,
            EsCiclico, 
            HoraFin, 
            FechaInicioVentana, 
            FechaFinVentana, 
            IntervaloEntreEjecuciones
        )
        VALUES (
            @RobotId, 
            @TipoProgramacion, 
            @HoraInicio,
            CASE WHEN @TipoProgramacion = 'Semanal' THEN @DiasSemana ELSE NULL END,
            CASE WHEN @TipoProgramacion = 'Mensual' THEN @DiaDelMes ELSE NULL END,
            CASE WHEN @TipoProgramacion = 'Especifica' THEN @FechaEspecifica ELSE NULL END,
            @Tolerancia, 
            1, 
            GETDATE(),
            NULL,  -- FechaModificacion se establece en UPDATE, no en INSERT
            CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @DiaInicioMes ELSE NULL END,
            CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @DiaFinMes ELSE NULL END,
            CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @UltimosDiasMes ELSE NULL END,
            @EsCiclico, 
            @HoraFin, 
            @FechaInicioVentana, 
            @FechaFinVentana, 
            @IntervaloEntreEjecuciones
        );

        SET @NewProgramacionId = SCOPE_IDENTITY();
        IF @NewProgramacionId IS NULL BEGIN RAISERROR('Error fatal: No se pudo obtener el ID de la nueva programación.', 16, 1); RETURN; END

        -- Asignar los equipos
        -- Orden de columnas según estructura real de tabla Asignaciones:
        -- RobotId, EquipoId, EsProgramado, Reservado, FechaAsignacion, AsignadoPor, ProgramacionId
        INSERT INTO dbo.Asignaciones (
            RobotId, EquipoId, EsProgramado, Reservado, FechaAsignacion, AsignadoPor, ProgramacionId
        )
        SELECT @RobotId, Source.EquipoId, 1, 0, GETDATE(), @UsuarioCrea, @NewProgramacionId
        FROM #EquiposAProgramar AS Source;

        -- Actualizar el estado del Robot
        UPDATE dbo.Robots SET EsOnline = 0 WHERE RobotId = @RobotId;

        -- Desactivar el balanceo dinámico
        UPDATE E SET PermiteBalanceoDinamico = 0
        FROM dbo.Equipos E
        JOIN #EquiposAProgramar EP ON E.EquipoId = EP.EquipoId;

        COMMIT TRANSACTION;
        
        DECLARE @TipoEjecucionStr NVARCHAR(20) = CASE WHEN @EsCiclico = 1 THEN 'cíclica' ELSE 'única' END;
        PRINT 'Programación de tipo "' + @TipoProgramacion + '" (' + @TipoEjecucionStr + ') creada exitosamente.';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;

        SET @ErrorMessage = ERROR_MESSAGE();
        SET @ErrorSeverity = ERROR_SEVERITY();
        SET @ErrorState = ERROR_STATE();
        DECLARE @Parametros NVARCHAR(MAX) = FORMATMESSAGE(
            '@Robot=%s, @TipoProgramacion=%s, @EsCiclico=%s, @HoraInicio=%s, @HoraFin=%s',
            ISNULL(@Robot, 'NULL'), ISNULL(@TipoProgramacion, 'NULL'),
            ISNULL(CAST(@EsCiclico AS NVARCHAR(1)), 'NULL'),
            ISNULL(CONVERT(NVARCHAR(8), @HoraInicio, 108), 'NULL'),
            ISNULL(CONVERT(NVARCHAR(8), @HoraFin, 108), 'NULL')
        );
        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'CrearProgramacion', @ErrorMessage, @Parametros);
        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH

    IF OBJECT_ID('tempdb..#EquiposAProgramar') IS NOT NULL
        DROP TABLE #EquiposAProgramar;
    IF OBJECT_ID('tempdb..#ConflictosDetectados') IS NOT NULL
        DROP TABLE #ConflictosDetectados;
END
GO

PRINT 'SP CrearProgramacion actualizado correctamente.'
PRINT 'El INSERT ahora incluye FechaModificacion (18 columnas).'
GO

