SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ActualizarProgramacionCompleta]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ActualizarProgramacionCompleta] AS' 
END

ALTER PROCEDURE [dbo].[ActualizarProgramacionCompleta]
    @ProgramacionId INT,
    @RobotId INT,
    @TipoProgramacion NVARCHAR(20),
    @HoraInicio TIME,
    @DiaSemana NVARCHAR(20) = NULL,
    @DiaDelMes INT = NULL,
    @FechaEspecifica DATE = NULL,
    @Tolerancia INT = NULL,
    @Equipos NVARCHAR(MAX),
    @UsuarioModifica NVARCHAR(50) = 'WebApp',
    @DiaInicioMes INT = NULL,
    @DiaFinMes INT = NULL,
    @UltimosDiasMes INT = NULL,
    -- NUEVOS PARÁMETROS para robots cíclicos con ventanas
    @EsCiclico BIT = NULL,
    @HoraFin TIME = NULL,
    @FechaInicioVentana DATE = NULL,
    @FechaFinVentana DATE = NULL,
    @IntervaloEntreEjecuciones INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @ErrorMessage NVARCHAR(4000);
    DECLARE @ErrorSeverity INT;
    DECLARE @ErrorState INT;
    DECLARE @Robot NVARCHAR(100);
    DECLARE @EquipoIdActual INT;
    DECLARE @ConflictosCount INT = 0;

    CREATE TABLE #NuevosEquiposProgramados (EquipoId INT PRIMARY KEY);
    CREATE TABLE #EquiposDesprogramados (EquipoId INT PRIMARY KEY);
    CREATE TABLE #ConflictosDetectados (
        EquipoId INT,
        RobotNombre NVARCHAR(100),
        ProgramacionId INT,
        TipoEjecucion NVARCHAR(20)
    );

    BEGIN TRY
        SELECT @Robot = Robot FROM dbo.Robots WHERE RobotId = @RobotId;
        
        -- Validaciones para robots cíclicos
        IF @EsCiclico = 1
        BEGIN
            IF @HoraFin IS NOT NULL AND @HoraInicio >= @HoraFin
                RAISERROR('HoraFin debe ser mayor que HoraInicio para robots cíclicos.', 16, 1);
            
            IF @FechaInicioVentana IS NOT NULL AND @FechaFinVentana IS NOT NULL
                AND @FechaInicioVentana > @FechaFinVentana
                RAISERROR('FechaInicioVentana no puede ser mayor que FechaFinVentana.', 16, 1);
            
            IF @IntervaloEntreEjecuciones IS NOT NULL AND @IntervaloEntreEjecuciones < 1
                RAISERROR('IntervaloEntreEjecuciones debe ser mayor que 0.', 16, 1);
        END

        BEGIN TRANSACTION;

        -- 1. Actualizar datos de la programación
        UPDATE dbo.Programaciones
        SET TipoProgramacion = @TipoProgramacion,
            HoraInicio = @HoraInicio,
            HoraFin = @HoraFin,
            DiasSemana = CASE WHEN @TipoProgramacion = 'Semanal' THEN @DiaSemana ELSE NULL END,
            DiaDelMes = CASE WHEN @TipoProgramacion = 'Mensual' THEN @DiaDelMes ELSE NULL END,
            FechaEspecifica = CASE WHEN @TipoProgramacion = 'Especifica' THEN @FechaEspecifica ELSE NULL END,
            Tolerancia = @Tolerancia,
            DiaInicioMes = CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @DiaInicioMes ELSE NULL END,
            DiaFinMes = CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @DiaFinMes ELSE NULL END,
            UltimosDiasMes = CASE WHEN @TipoProgramacion = 'RangoMensual' THEN @UltimosDiasMes ELSE NULL END,
            EsCiclico = ISNULL(@EsCiclico, EsCiclico),  -- Solo actualizar si se proporciona
            FechaInicioVentana = @FechaInicioVentana,
            FechaFinVentana = @FechaFinVentana,
            IntervaloEntreEjecuciones = @IntervaloEntreEjecuciones,
            FechaModificacion = GETDATE()
        WHERE ProgramacionId = @ProgramacionId AND RobotId = @RobotId;

        IF @@ROWCOUNT = 0 BEGIN RAISERROR('Programación no encontrada.', 16, 1); RETURN; END

        -- 2. Poblar #NuevosEquiposProgramados
        INSERT INTO #NuevosEquiposProgramados (EquipoId)
        SELECT E.EquipoId
        FROM STRING_SPLIT(@Equipos, ',') AS S
        JOIN dbo.Equipos E ON LTRIM(RTRIM(S.value)) = E.Equipo
        WHERE E.Activo_SAM = 1;

        -- 3. VALIDAR SOLAPAMIENTOS para los nuevos equipos (excluyendo la programación actual)
        DECLARE equipo_cursor CURSOR FOR
        SELECT EquipoId FROM #NuevosEquiposProgramados;

        OPEN equipo_cursor;
        FETCH NEXT FROM equipo_cursor INTO @EquipoIdActual;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            INSERT INTO #ConflictosDetectados (EquipoId, RobotNombre, ProgramacionId, TipoEjecucion)
            EXEC dbo.ValidarSolapamientoVentanas
                @EquipoId = @EquipoIdActual,
                @HoraInicio = @HoraInicio,
                @HoraFin = @HoraFin,
                @FechaInicioVentana = @FechaInicioVentana,
                @FechaFinVentana = @FechaFinVentana,
                @DiasSemana = @DiaSemana,
                @TipoProgramacion = @TipoProgramacion,
                @DiaDelMes = @DiaDelMes,
                @DiaInicioMes = @DiaInicioMes,
                @DiaFinMes = @DiaFinMes,
                @UltimosDiasMes = @UltimosDiasMes,
                @ProgramacionId = @ProgramacionId;  -- Excluir la programación actual

            FETCH NEXT FROM equipo_cursor INTO @EquipoIdActual;
        END

        CLOSE equipo_cursor;
        DEALLOCATE equipo_cursor;

        -- Verificar si hay conflictos
        SELECT @ConflictosCount = COUNT(*) FROM #ConflictosDetectados;

        IF @ConflictosCount > 0
        BEGIN
            ROLLBACK TRANSACTION;
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

        -- 4. Desprogramar equipos
        INSERT INTO #EquiposDesprogramados (EquipoId)
        SELECT EquipoId
        FROM dbo.Asignaciones
        WHERE ProgramacionId = @ProgramacionId
          AND EsProgramado = 1
          AND RobotId = @RobotId
          AND EquipoId NOT IN (SELECT EquipoId FROM #NuevosEquiposProgramados);
        
        DELETE FROM dbo.Asignaciones
        WHERE ProgramacionId = @ProgramacionId
          AND EsProgramado = 1
          AND RobotId = @RobotId
          AND EquipoId IN (SELECT EquipoId FROM #EquiposDesprogramados);
        
        -- 5. Programar los nuevos equipos
        MERGE dbo.Asignaciones AS Target
        USING #NuevosEquiposProgramados AS Source
        ON (Target.EquipoId = Source.EquipoId 
            AND Target.RobotId = @RobotId 
            AND Target.ProgramacionId = @ProgramacionId)
        WHEN MATCHED THEN
            UPDATE SET
                EsProgramado = 1,
                Reservado = 0,
                AsignadoPor = @UsuarioModifica,
                FechaAsignacion = GETDATE()
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (RobotId, EquipoId, EsProgramado, ProgramacionId, Reservado, AsignadoPor, FechaAsignacion)
            VALUES (@RobotId, Source.EquipoId, 1, @ProgramacionId, 0, @UsuarioModifica, GETDATE());

        -- 6. Habilitar/Deshabilitar balanceo dinámico
        UPDATE E
        SET PermiteBalanceoDinamico = 0
        FROM dbo.Equipos E
        JOIN #NuevosEquiposProgramados NEP ON E.EquipoId = NEP.EquipoId;
        
        UPDATE E
        SET E.PermiteBalanceoDinamico = 1
        FROM dbo.Equipos E
        JOIN #EquiposDesprogramados ED ON E.EquipoId = ED.EquipoId
        WHERE NOT EXISTS (
              SELECT 1 FROM dbo.Asignaciones a2
              WHERE a2.EquipoId = E.EquipoId 
                AND (a2.EsProgramado = 1 OR a2.Reservado = 1)
          );

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;

        SET @ErrorMessage = ERROR_MESSAGE();
        SET @ErrorSeverity = ERROR_SEVERITY();
        SET @ErrorState = ERROR_STATE();
        DECLARE @Parametros NVARCHAR(MAX);
        SET @Parametros = 
            '@Robot = ' + ISNULL(@Robot, 'NULL') + 
            ', @Equipos = ' + ISNULL(@Equipos, 'NULL') + 
            ', @HoraInicio = ' + ISNULL(CONVERT(NVARCHAR(8), @HoraInicio, 108), 'NULL') + 
            ', @Tolerancia = ' + ISNULL(CAST(@Tolerancia AS NVARCHAR(10)), 'NULL') +
            ', @EsCiclico = ' + ISNULL(CAST(@EsCiclico AS NVARCHAR(1)), 'NULL');
        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'ActualizarProgramacionCompleta', @ErrorMessage, @Parametros);
        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH

    IF OBJECT_ID('tempdb..#NuevosEquiposProgramados') IS NOT NULL
        DROP TABLE #NuevosEquiposProgramados;
    IF OBJECT_ID('tempdb..#EquiposDesprogramados') IS NOT NULL
        DROP TABLE #EquiposDesprogramados;
    IF OBJECT_ID('tempdb..#ConflictosDetectados') IS NOT NULL
        DROP TABLE #ConflictosDetectados;
END

