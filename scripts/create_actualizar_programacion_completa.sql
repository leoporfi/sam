CREATE or ALTER PROCEDURE dbo.ActualizarProgramacionCompleta
    @ProgramacionId INT,
    @RobotId INT,
    @TipoProgramacion NVARCHAR(20),
    @HoraInicio TIME,
    @DiaSemana NVARCHAR(20) = NULL,
    @DiaDelMes INT = NULL,
    @FechaEspecifica DATE = NULL,
    @Tolerancia INT = NULL,
    @Equipos NVARCHAR(MAX), -- Equipos como nombres separados por coma
    @UsuarioModifica NVARCHAR(50) = 'WebApp'
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @ErrorMessage NVARCHAR(4000);
    DECLARE @ErrorSeverity INT;
    DECLARE @ErrorState INT;
    DECLARE @Robot NVARCHAR(100);

    -- Tabla temporal para almacenar los IDs de equipos válidos
    CREATE TABLE #NuevosEquiposProgramados (EquipoId INT PRIMARY KEY);

    BEGIN TRY
        -- Obtener el nombre del robot para logs
        SELECT @Robot = Robot FROM dbo.Robots WHERE RobotId = @RobotId;

        BEGIN TRANSACTION;

        -- 1. Actualizar datos de la programación
        UPDATE dbo.Programaciones
        SET TipoProgramacion = @TipoProgramacion,
            HoraInicio = @HoraInicio,
            DiasSemana = CASE WHEN @TipoProgramacion = 'Semanal' THEN @DiaSemana ELSE NULL END,
            DiaDelMes = CASE WHEN @TipoProgramacion = 'Mensual' THEN @DiaDelMes ELSE NULL END,
            FechaEspecifica = CASE WHEN @TipoProgramacion = 'Especifica' THEN @FechaEspecifica ELSE NULL END,
            Tolerancia = @Tolerancia,
            FechaModificacion = GETDATE()
        WHERE ProgramacionId = @ProgramacionId AND RobotId = @RobotId;

        IF @@ROWCOUNT = 0
        BEGIN
            RAISERROR('Programación no encontrada o no pertenece al RobotId especificado.', 16, 1);
            RETURN;
        END

        -- 2. Poblar #NuevosEquiposProgramados
        INSERT INTO #NuevosEquiposProgramados (EquipoId)
        SELECT E.EquipoId
        FROM STRING_SPLIT(@Equipos, ',') AS S
        JOIN dbo.Equipos E ON LTRIM(RTRIM(S.value)) = E.Equipo
        WHERE E.Activo_SAM = 1;

        -- Mostrar advertencias por equipos inválidos o inactivos
        SELECT 'Warning: Equipo "' + LTRIM(RTRIM(S.value)) + '" no encontrado o inactivo y no será programado.' AS Advertencia
        FROM STRING_SPLIT(@Equipos, ',') S
        WHERE NOT EXISTS (
            SELECT 1 FROM dbo.Equipos E
            WHERE E.Equipo = LTRIM(RTRIM(S.value)) AND E.Activo_SAM = 1
        );

        -- 3. Desprogramar equipos que ya no deben estar en esta programación
        UPDATE A
        SET EsProgramado = 0,
            ProgramacionId = NULL,
            AsignadoPor = @UsuarioModifica,
            FechaAsignacion = GETDATE()
        FROM dbo.Asignaciones A
        WHERE A.ProgramacionId = @ProgramacionId AND A.EsProgramado = 1
          AND NOT EXISTS (
              SELECT 1 FROM #NuevosEquiposProgramados NEP WHERE NEP.EquipoId = A.EquipoId
          )
          AND A.RobotId = @RobotId;

        -- Habilitar balanceo dinámico para los equipos que ya no están programados en ningún lado
        UPDATE E
        SET PermiteBalanceoDinamico = 1
        FROM dbo.Equipos E
        WHERE EXISTS (
            SELECT 1
            FROM dbo.Asignaciones A
            WHERE A.EquipoId = E.EquipoId
              AND A.RobotId = @RobotId
              AND A.ProgramacionId = @ProgramacionId
              AND A.EsProgramado = 0
        )
        AND NOT EXISTS (
            SELECT 1
            FROM dbo.Asignaciones A
            WHERE A.EquipoId = E.EquipoId
              AND A.EsProgramado = 1
              AND A.ProgramacionId IS NOT NULL
        );

        -- 4. Programar los nuevos equipos
        MERGE dbo.Asignaciones AS Target
        USING #NuevosEquiposProgramados AS Source
        ON Target.EquipoId = Source.EquipoId AND Target.RobotId = @RobotId
        WHEN MATCHED THEN
            UPDATE SET
                EsProgramado = 1,
                ProgramacionId = @ProgramacionId,
                Reservado = 0,
                AsignadoPor = @UsuarioModifica,
                FechaAsignacion = GETDATE()
        WHEN NOT MATCHED THEN
            INSERT (RobotId, EquipoId, EsProgramado, ProgramacionId, Reservado, AsignadoPor, FechaAsignacion)
            VALUES (@RobotId, Source.EquipoId, 1, @ProgramacionId, 0, @UsuarioModifica, GETDATE());

        -- Desactivar balanceo dinámico para equipos recién programados
        UPDATE E
        SET PermiteBalanceoDinamico = 0
        FROM dbo.Equipos E
        JOIN #NuevosEquiposProgramados NEP ON E.EquipoId = NEP.EquipoId;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SET @ErrorMessage = ERROR_MESSAGE();
        SET @ErrorSeverity = ERROR_SEVERITY();
        SET @ErrorState = ERROR_STATE();

        DECLARE @Parametros NVARCHAR(MAX);
        SET @Parametros = 
            '@Robot = ' + ISNULL(@Robot, 'NULL') + 
            ', @Equipos = ' + ISNULL(@Equipos, 'NULL') + 
            ', @HoraInicio = ' + ISNULL(CONVERT(NVARCHAR(8), @HoraInicio, 108), 'NULL') + 
            ', @Tolerancia = ' + ISNULL(CAST(@Tolerancia AS NVARCHAR(10)), 'NULL');

        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'ActualizarProgramacionCompleta', @ErrorMessage, @Parametros);

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH

    -- Limpieza de tabla temporal
    IF OBJECT_ID('tempdb..#NuevosEquiposProgramados') IS NOT NULL
        DROP TABLE #NuevosEquiposProgramados;
END
GO
