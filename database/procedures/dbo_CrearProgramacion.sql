SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CrearProgramacion]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[CrearProgramacion] AS'
END
GO

ALTER PROCEDURE [dbo].[CrearProgramacion]
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

    -- Variables para cálculo de HoraFin (fuera del loop)
    DECLARE @FechaBase DATETIME;
    DECLARE @InicioFull DATETIME;
    DECLARE @FinFull DATETIME;
    DECLARE @HoraFinCalculada TIME;

    CREATE TABLE #EquiposAProgramar (EquipoId INT PRIMARY KEY);
    CREATE TABLE #ConflictosDetectados (
        EquipoId INT,
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

    BEGIN TRY
        -- Validaciones existentes
        SELECT @RobotId = RobotId FROM dbo.Robots WHERE Robot = @Robot;
        IF @RobotId IS NULL BEGIN RAISERROR('El robot especificado no existe.', 16, 1); RETURN; END

        IF @TipoProgramacion = 'Semanal' AND ISNULL(@DiasSemana, '') = ''
            RAISERROR('Para una programación Semanal, se debe especificar @DiasSemana.', 16, 1);
        IF @TipoProgramacion = 'Mensual' AND @DiaDelMes IS NULL
            RAISERROR('Para una programación Mensual, se debe especificar @DiaDelMes.', 16, 1);
        IF @TipoProgramacion = 'Especifica' AND @FechaEspecifica IS NULL
            RAISERROR('Para una programación Específica, se debe especificar @FechaEspecifica.', 16, 1);

        -- Validaciones para RangoMensual
        IF @TipoProgramacion = 'RangoMensual'
        BEGIN
            IF @DiaInicioMes IS NULL AND @DiaFinMes IS NULL AND @UltimosDiasMes IS NULL
                RAISERROR('Para RangoMensual, debe especificar un rango (DiaInicioMes+DiaFinMes) o UltimosDiasMes.', 16, 1);

            IF @DiaInicioMes IS NOT NULL AND @DiaFinMes IS NOT NULL AND @UltimosDiasMes IS NOT NULL
                RAISERROR('No puede especificar simultáneamente un rango Y UltimosDiasMes.', 16, 1);

            IF (@DiaInicioMes IS NOT NULL AND @DiaFinMes IS NULL) OR (@DiaInicioMes IS NULL AND @DiaFinMes IS NOT NULL)
                RAISERROR('Debe especificar ambos: DiaInicioMes y DiaFinMes.', 16, 1);

            IF @DiaInicioMes IS NOT NULL AND @DiaFinMes IS NOT NULL AND @DiaInicioMes > @DiaFinMes
                RAISERROR('DiaInicioMes no puede ser mayor que DiaFinMes.', 16, 1);
        END

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

            -- Validar intervalo entre ejecuciones
            IF @IntervaloEntreEjecuciones IS NOT NULL AND @IntervaloEntreEjecuciones < 1
                RAISERROR('IntervaloEntreEjecuciones debe ser mayor que 0.', 16, 1);
        END

        -- Poblar la tabla temporal de equipos
        INSERT INTO #EquiposAProgramar (EquipoId)
        SELECT E.EquipoId
        FROM STRING_SPLIT(@Equipos, ',') AS S
        JOIN dbo.Equipos E ON LTRIM(RTRIM(S.value)) = E.Equipo
        WHERE E.Activo_SAM = 1;

        -------------------------------------------------------------------------
        -- CÁLCULO DE @HoraFin UNA SOLA VEZ (ANTES DEL CURSOR)
        -------------------------------------------------------------------------
        -- Preservar el valor original de @HoraFin
        SET @HoraFinCalculada = @HoraFin;

        -- Si no se especificó HoraFin, calcularla usando la Tolerancia
        IF @HoraFinCalculada IS NULL AND @Tolerancia IS NOT NULL AND @Tolerancia > 0
        BEGIN
            -- Calculamos la fecha-hora completa temporalmente
            SET @FechaBase = CAST(GETDATE() AS DATE); -- Solo referencia
            SET @InicioFull = DATEADD(MINUTE, DATEDIFF(MINUTE, 0, @HoraInicio), @FechaBase);
            SET @FinFull = DATEADD(MINUTE, @Tolerancia, @InicioFull);

            -- Si al sumar minutos cambiamos de día, topeamos a medianoche
            IF CAST(@FinFull AS DATE) > CAST(@InicioFull AS DATE)
            BEGIN
                SET @HoraFinCalculada = '23:59:59';
            END
            ELSE
            BEGIN
                -- Si sigue en el mismo día, tomamos la hora calculada
                SET @HoraFinCalculada = CAST(@FinFull AS TIME);
            END
        END
        -------------------------------------------------------------------------

        -- VALIDAR SOLAPAMIENTOS para cada equipo
        DECLARE equipo_cursor CURSOR FOR
        SELECT EquipoId FROM #EquiposAProgramar;

        OPEN equipo_cursor;
        FETCH NEXT FROM equipo_cursor INTO @EquipoIdActual;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            -- Verificar solapamientos usando el SP de validación
            INSERT INTO #ConflictosDetectados
            EXEC dbo.ValidarSolapamientoVentanas
                @EquipoId = @EquipoIdActual,
                @HoraInicio = @HoraInicio,
                @HoraFin = @HoraFinCalculada,
                @FechaInicioVentana = @FechaInicioVentana,
                @FechaFinVentana = @FechaFinVentana,
                @DiasSemana = @DiasSemana,
                @TipoProgramacion = @TipoProgramacion,
                @DiaDelMes = @DiaDelMes,
                @DiaInicioMes = @DiaInicioMes,
                @DiaFinMes = @DiaFinMes,
                @UltimosDiasMes = @UltimosDiasMes,
                @FechaEspecifica = @FechaEspecifica,
                @ProgramacionId = NULL;

            FETCH NEXT FROM equipo_cursor INTO @EquipoIdActual;
        END

        CLOSE equipo_cursor;
        DEALLOCATE equipo_cursor;

        -- Verificar si hay conflictos
        SELECT @ConflictosCount = COUNT(*) FROM #ConflictosDetectados;

        IF @ConflictosCount > 0
        BEGIN
            -- Construir mensaje de error detallado
            DECLARE @MensajeConflictos NVARCHAR(MAX) =
                'Se detectaron ' + CAST(@ConflictosCount AS NVARCHAR(10)) +
                ' solapamiento(s) de ventanas temporales:' + CHAR(13) + CHAR(10);

            SELECT @MensajeConflictos = @MensajeConflictos +
                '  - EquipoId: ' + CAST(EquipoId AS NVARCHAR(10)) +
                ', Robot: ' + RobotNombre +
                ', ProgramaciónId: ' + CAST(ProgramacionId AS NVARCHAR(10)) +
                ', Tipo: ' + TipoEjecucion +
                ', Horario: ' + CONVERT(NVARCHAR(8), HoraInicio, 108) + ' - ' + CONVERT(NVARCHAR(8), HoraFin, 108) +
                CASE WHEN DiasSemana IS NOT NULL THEN ', Días: ' + DiasSemana ELSE '' END +
                CHAR(13) + CHAR(10)
            FROM #ConflictosDetectados;

            RAISERROR(@MensajeConflictos, 16, 1);
            RETURN;
        END

        BEGIN TRANSACTION;

        -- Insertar la nueva programación (con los nuevos campos)
        INSERT INTO dbo.Programaciones (
            RobotId, TipoProgramacion, HoraInicio, HoraFin, Tolerancia, Activo,
            FechaCreacion, DiasSemana, DiaDelMes, FechaEspecifica,
            DiaInicioMes, DiaFinMes, UltimosDiasMes,
            EsCiclico, FechaInicioVentana, FechaFinVentana, IntervaloEntreEjecuciones
        )
        VALUES (
            @RobotId, @TipoProgramacion, @HoraInicio, @HoraFin, @Tolerancia, 1,
            GETDATE(),
            CASE WHEN @TipoProgramacion = 'Semanal' THEN @DiasSemana ELSE NULL END,
            CASE WHEN @TipoProgramacion = 'Mensual' THEN @DiaDelMes ELSE NULL END,
            CASE WHEN @TipoProgramacion = 'Especifica' THEN @FechaEspecifica ELSE NULL END,
            CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @DiaInicioMes ELSE NULL END,
            CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @DiaFinMes ELSE NULL END,
            CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @UltimosDiasMes ELSE NULL END,
            @EsCiclico, @FechaInicioVentana, @FechaFinVentana, @IntervaloEntreEjecuciones
        );

        SET @NewProgramacionId = SCOPE_IDENTITY();
        IF @NewProgramacionId IS NULL BEGIN RAISERROR('Error fatal: No se pudo obtener el ID de la nueva programación.', 16, 1); RETURN; END

        -- Asignar los equipos
        INSERT INTO dbo.Asignaciones (
            RobotId, EquipoId, EsProgramado, ProgramacionId, Reservado, AsignadoPor, FechaAsignacion
        )
        SELECT @RobotId, Source.EquipoId, 1, @NewProgramacionId, 0, @UsuarioCrea, GETDATE()
        FROM #EquiposAProgramar AS Source;

        -- Actualizar el estado del Robot
        UPDATE dbo.Robots SET EsOnline = 0 WHERE RobotId = @RobotId;

        -- Desactivar el balanceo dinámico
        UPDATE E SET PermiteBalanceoDinamico = 0
        FROM dbo.Equipos E JOIN #EquiposAProgramar NEP ON E.EquipoId = NEP.EquipoId;

        COMMIT TRANSACTION;

        DECLARE @TipoEjecucionStr NVARCHAR(20) = CASE WHEN @EsCiclico = 1 THEN 'cíclica' ELSE 'única' END;
        PRINT 'Programación de tipo "' + @TipoProgramacion + '" (' + @TipoEjecucionStr + ') creada exitosamente.';

        IF OBJECT_ID('tempdb..#EquiposAProgramar') IS NOT NULL
            DROP TABLE #EquiposAProgramar;
        IF OBJECT_ID('tempdb..#ConflictosDetectados') IS NOT NULL
            DROP TABLE #ConflictosDetectados;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF OBJECT_ID('tempdb..#EquiposAProgramar') IS NOT NULL DROP TABLE #EquiposAProgramar;
        IF OBJECT_ID('tempdb..#ConflictosDetectados') IS NOT NULL DROP TABLE #ConflictosDetectados;

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

        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'CrearProgramacion', @ErrorMessage, @Parametros);

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
