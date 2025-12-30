-- =============================================
-- Script de Actualización: Stored Procedures para Robots Cíclicos
-- Fecha: 2025-01-XX
-- Descripción: Modifica los SPs existentes para soportar robots cíclicos con ventanas
-- =============================================

USE DEV  -- Ajustar según el nombre de tu base de datos
GO

PRINT 'Iniciando actualización de Stored Procedures...'
GO

-- =============================================
-- 1. MODIFICAR SP: CrearProgramacion
-- =============================================

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CrearProgramacion]') AND type in (N'P', N'PC'))
BEGIN
    EXEC('DROP PROCEDURE [dbo].[CrearProgramacion]')
END
GO

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

            -- Validar intervalo entre ejecuciones (solo si se proporciona - es opcional)
            IF @IntervaloEntreEjecuciones IS NOT NULL AND @IntervaloEntreEjecuciones < 1
                RAISERROR('IntervaloEntreEjecuciones debe ser mayor que 0 si se especifica.', 16, 1);
        END

        -- Poblar la tabla temporal de equipos
        INSERT INTO #EquiposAProgramar (EquipoId)
        SELECT E.EquipoId
        FROM STRING_SPLIT(@Equipos, ',') AS S
        JOIN dbo.Equipos E ON LTRIM(RTRIM(S.value)) = E.Equipo
        WHERE E.Activo_SAM = 1;

        -- VALIDAR SOLAPAMIENTOS para cada equipo
        DECLARE equipo_cursor CURSOR FOR
        SELECT EquipoId FROM #EquiposAProgramar;

        OPEN equipo_cursor;
        FETCH NEXT FROM equipo_cursor INTO @EquipoIdActual;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            -- Verificar solapamientos usando el SP de validación
            INSERT INTO #ConflictosDetectados (EquipoId, RobotNombre, ProgramacionId, TipoEjecucion)
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
                ', Tipo: ' + TipoEjecucion + CHAR(13) + CHAR(10)
            FROM #ConflictosDetectados;

            RAISERROR(@MensajeConflictos, 16, 1);
            RETURN;
        END

        BEGIN TRANSACTION;

        -- Insertar la nueva programación (con los nuevos campos)
        -- Nota: UsuarioCrea NO existe en la tabla Programaciones, solo se usa en Asignaciones
        -- Orden de columnas EXACTO según la estructura real de la tabla Programaciones:
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
GO

PRINT 'SP CrearProgramacion actualizado.';
GO

-- =============================================
-- 2. MODIFICAR SP: ObtenerRobotsEjecutables
-- =============================================

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ObtenerRobotsEjecutables]') AND type in (N'P', N'PC'))
BEGIN
    EXEC('DROP PROCEDURE [dbo].[ObtenerRobotsEjecutables]')
END
GO

CREATE PROCEDURE [dbo].[ObtenerRobotsEjecutables]
AS
BEGIN
    SET NOCOUNT ON;
    SET LANGUAGE Spanish;

    DECLARE @FechaActual DATETIME = GETDATE();
    DECLARE @HoraActual TIME(0) = CAST(@FechaActual AS TIME(0));
    DECLARE @DiaDelMesActual INT = DAY(@FechaActual);
    DECLARE @UltimoDiaDelMes INT = DAY(EOMONTH(@FechaActual));
    DECLARE @DiaSemanaActual NVARCHAR(2) = UPPER(LEFT(DATENAME(WEEKDAY, @FechaActual), 2) COLLATE Latin1_General_CI_AI);
    DECLARE @FechaActualDate DATE = CAST(@FechaActual AS DATE);

    -- Tabla temporal para almacenar los resultados
    CREATE TABLE #ResultadosRobots (
        RobotId INT,
        EquipoId INT,
        UserId INT,
        Hora TIME(0),
        EsProgramado BIT,
        PrioridadBalanceo INT  -- Para ordenar por prioridad en caso de conflictos
    );

    -- =============================================
    -- PARTE 1: Robots Programados (Tradicionales - Una vez)
    -- =============================================
    INSERT INTO #ResultadosRobots (RobotId, EquipoId, UserId, Hora, EsProgramado, PrioridadBalanceo)
    SELECT
        R.RobotId,
        A.EquipoId,
        E.UserId,
        P.HoraInicio,
        1 AS EsProgramado,
        R.PrioridadBalanceo
    FROM Robots R
    INNER JOIN Asignaciones A ON R.RobotId = A.RobotId
    INNER JOIN Equipos E ON A.EquipoId = E.EquipoId
    INNER JOIN Programaciones P ON A.ProgramacionId = P.ProgramacionId
    CROSS APPLY (
        SELECT
            DATEADD(MINUTE, P.Tolerancia, P.HoraInicio) AS HoraFin,
            CASE
                WHEN @HoraActual < P.HoraInicio AND P.HoraInicio > '12:00'
                THEN CAST(DATEADD(DAY, -1, @FechaActual) AS DATE)
                ELSE @FechaActualDate
            END AS FechaTeoricaProgramacion
    ) Calc
    WHERE
        A.EsProgramado = 1
        AND R.Activo = 1
        AND P.Activo = 1
        AND (P.EsCiclico = 0 OR P.EsCiclico IS NULL)  -- Solo programaciones tradicionales (una vez)
        -- Validar ventana de fechas (si está definida)
        AND (
            (P.FechaInicioVentana IS NULL AND P.FechaFinVentana IS NULL)
            OR
            (@FechaActualDate >= ISNULL(P.FechaInicioVentana, @FechaActualDate)
             AND @FechaActualDate <= ISNULL(P.FechaFinVentana, @FechaActualDate))
        )
        -- Validar rango horario (si está definido)
        AND (
            (P.HoraFin IS NULL)
            OR
            (@HoraActual >= P.HoraInicio AND @HoraActual <= P.HoraFin)
            OR
            (P.HoraFin < P.HoraInicio AND (@HoraActual >= P.HoraInicio OR @HoraActual <= P.HoraFin))  -- Cruce medianoche
        )
        -- Lógica de Tiempos (Ventana de Tolerancia)
        AND (
            (
                (Calc.HoraFin >= P.HoraInicio AND @HoraActual BETWEEN P.HoraInicio AND Calc.HoraFin)
                OR
                (Calc.HoraFin < P.HoraInicio AND (@HoraActual >= P.HoraInicio OR @HoraActual <= Calc.HoraFin))
            )
            AND
            (
                (P.TipoProgramacion = 'Diaria')
                OR (P.TipoProgramacion = 'Semanal' AND UPPER(P.DiasSemana COLLATE Latin1_General_CI_AI) LIKE '%' + @DiaSemanaActual + '%')
                OR (P.TipoProgramacion = 'Mensual' AND P.DiaDelMes = @DiaDelMesActual)
                OR (P.TipoProgramacion = 'Especifica' AND P.FechaEspecifica = @FechaActualDate)
                OR (P.TipoProgramacion = 'RangoMensual'
                    AND ((P.DiaInicioMes IS NOT NULL AND P.DiaFinMes IS NOT NULL AND @DiaDelMesActual BETWEEN P.DiaInicioMes AND P.DiaFinMes)
                         OR (P.UltimosDiasMes IS NOT NULL AND @DiaDelMesActual > (@UltimoDiaDelMes - P.UltimosDiasMes))))
            )
        )
        -- Validación de duplicados
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones Ejec
            WHERE Ejec.RobotId = R.RobotId
              AND Ejec.EquipoId = A.EquipoId
              AND Ejec.Hora = P.HoraInicio
              AND CAST(Ejec.FechaInicio AS DATE) = Calc.FechaTeoricaProgramacion
        )
        -- No ejecutar si el equipo ya está ocupado
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones Ejec
            WHERE Ejec.EquipoId = A.EquipoId
              AND (Ejec.Estado IN ('DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 'RUNNING', 'UPDATE', 'RUN_PAUSED')
                   OR (Ejec.Estado = 'UNKNOWN' AND Ejec.FechaUltimoUNKNOWN > DATEADD(HOUR, -2, GETDATE())))
        )
        -- No duplicar equipos en la misma vuelta del SP
        AND NOT EXISTS (
            SELECT 1 FROM #ResultadosRobots RR WHERE RR.EquipoId = A.EquipoId
        );

    -- =============================================
    -- PARTE 2: Robots Cíclicos con Ventanas
    -- =============================================
    INSERT INTO #ResultadosRobots (RobotId, EquipoId, UserId, Hora, EsProgramado, PrioridadBalanceo)
    SELECT
        R.RobotId,
        A.EquipoId,
        E.UserId,
        CASE WHEN P.IntervaloEntreEjecuciones IS NOT NULL THEN NULL ELSE P.HoraInicio END AS Hora,
        1 AS EsProgramado,
        R.PrioridadBalanceo
    FROM Robots R
    INNER JOIN Asignaciones A ON R.RobotId = A.RobotId
    INNER JOIN Equipos E ON A.EquipoId = E.EquipoId
    INNER JOIN Programaciones P ON A.ProgramacionId = P.ProgramacionId
    WHERE
        A.EsProgramado = 1
        AND R.Activo = 1
        AND P.Activo = 1
        AND P.EsCiclico = 1  -- Solo robots cíclicos
        -- Validar ventana de fechas
        AND (
            (P.FechaInicioVentana IS NULL AND P.FechaFinVentana IS NULL)
            OR
            (@FechaActualDate >= ISNULL(P.FechaInicioVentana, @FechaActualDate)
             AND @FechaActualDate <= ISNULL(P.FechaFinVentana, @FechaActualDate))
        )
        -- Validar rango horario
        AND (
            (P.HoraFin IS NULL)
            OR
            (@HoraActual >= P.HoraInicio AND @HoraActual <= P.HoraFin)
            OR
            (P.HoraFin < P.HoraInicio AND (@HoraActual >= P.HoraInicio OR @HoraActual <= P.HoraFin))
        )
        -- Validar tipo de programación (días de la semana, día del mes, etc.)
        AND (
            (P.TipoProgramacion = 'Diaria')
            OR (P.TipoProgramacion = 'Semanal' AND UPPER(P.DiasSemana COLLATE Latin1_General_CI_AI) LIKE '%' + @DiaSemanaActual + '%')
            OR (P.TipoProgramacion = 'Mensual' AND P.DiaDelMes = @DiaDelMesActual)
            OR (P.TipoProgramacion = 'RangoMensual'
                AND ((P.DiaInicioMes IS NOT NULL AND P.DiaFinMes IS NOT NULL AND @DiaDelMesActual BETWEEN P.DiaInicioMes AND P.DiaFinMes)
                     OR (P.UltimosDiasMes IS NOT NULL AND @DiaDelMesActual > (@UltimoDiaDelMes - P.UltimosDiasMes))))
        )
        -- Validar intervalo entre ejecuciones (si está definido)
        AND (
            P.IntervaloEntreEjecuciones IS NULL
            OR
            NOT EXISTS (
                SELECT 1
                FROM Ejecuciones Ejec
                WHERE Ejec.RobotId = R.RobotId
                  AND Ejec.EquipoId = A.EquipoId
                  AND Ejec.Estado IN ('COMPLETED', 'RUN_COMPLETED', 'RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED')
                  AND Ejec.FechaFin IS NOT NULL
                  AND DATEDIFF(MINUTE, Ejec.FechaFin, @FechaActual) < P.IntervaloEntreEjecuciones
            )
        )
        -- No ejecutar si el equipo ya está ocupado
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones Ejec
            WHERE Ejec.EquipoId = A.EquipoId
              AND (Ejec.Estado IN ('DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 'RUNNING', 'UPDATE', 'RUN_PAUSED')
                   OR (Ejec.Estado = 'UNKNOWN' AND Ejec.FechaUltimoUNKNOWN > DATEADD(HOUR, -2, GETDATE())))
        )
        -- No duplicar equipos en la misma vuelta del SP
        AND NOT EXISTS (
            SELECT 1 FROM #ResultadosRobots RR WHERE RR.EquipoId = A.EquipoId
        );

    -- =============================================
    -- PARTE 3: Robots Online (SIN CAMBIOS)
    -- =============================================
    INSERT INTO #ResultadosRobots (RobotId, EquipoId, UserId, Hora, EsProgramado, PrioridadBalanceo)
    SELECT
        R.RobotId,
        A.EquipoId,
        E.UserId,
        NULL AS Hora,
        0 AS EsProgramado,
        R.PrioridadBalanceo
    FROM Robots R
    INNER JOIN Asignaciones A ON R.RobotId = A.RobotId
    INNER JOIN Equipos E ON A.EquipoId = E.EquipoId
    WHERE
        R.EsOnline = 1
        AND R.Activo = 1
        AND A.EsProgramado = 0
        AND NOT EXISTS (SELECT 1 FROM #ResultadosRobots RR WHERE RR.EquipoId = A.EquipoId)
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones Ejec
            WHERE Ejec.EquipoId = A.EquipoId
              AND (Ejec.Estado IN ('DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 'RUNNING', 'UPDATE', 'RUN_PAUSED')
                   OR (Ejec.Estado = 'UNKNOWN' AND Ejec.FechaUltimoUNKNOWN > DATEADD(HOUR, -2, GETDATE())))
        );

    -- =============================================
    -- RESULTADO FINAL: Ordenar por prioridad y tipo
    -- =============================================
    -- Si hay múltiples robots para el mismo equipo, se prioriza:
    -- 1. EsProgramado (programados primero)
    -- 2. PrioridadBalanceo (menor = mayor prioridad)
    -- 3. Hora (más temprano primero)

    -- RESULTADO FINAL: Ordenar y seleccionar el mejor por equipo
    -- El ROW_NUMBER ya ordenó correctamente dentro de cada equipo
    -- Hacemos JOIN con la tabla temporal para tener acceso a EsProgramado y PrioridadBalanceo en el ORDER BY
    SELECT
        R.RobotId,
        R.EquipoId,
        R.UserId,
        R.Hora
    FROM (
        SELECT
            RobotId,
            EquipoId,
            UserId,
            Hora,
            EsProgramado,
            PrioridadBalanceo,
            ROW_NUMBER() OVER (
                PARTITION BY EquipoId
                ORDER BY EsProgramado DESC, PrioridadBalanceo ASC, Hora ASC
            ) AS RN
        FROM #ResultadosRobots
    ) AS Ordenados
    INNER JOIN #ResultadosRobots R
        ON Ordenados.RobotId = R.RobotId
        AND Ordenados.EquipoId = R.EquipoId
    WHERE Ordenados.RN = 1  -- Solo el de mayor prioridad por equipo
    ORDER BY R.EsProgramado DESC, R.PrioridadBalanceo ASC, R.Hora;

    DROP TABLE #ResultadosRobots;
END
GO

PRINT 'SP ObtenerRobotsEjecutables actualizado.';
GO

-- =============================================
-- 3. MODIFICAR SP: ActualizarProgramacionCompleta
-- =============================================

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ActualizarProgramacionCompleta]') AND type in (N'P', N'PC'))
BEGIN
    EXEC('DROP PROCEDURE [dbo].[ActualizarProgramacionCompleta]')
END
GO

CREATE PROCEDURE [dbo].[ActualizarProgramacionCompleta]
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
        -- Crear tabla temporal intermedia para recibir todos los resultados del SP
        IF OBJECT_ID('tempdb..#ResultadosValidacion') IS NOT NULL
            DROP TABLE #ResultadosValidacion;

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

        DECLARE equipo_cursor CURSOR FOR
        SELECT EquipoId FROM #NuevosEquiposProgramados;

        OPEN equipo_cursor;
        FETCH NEXT FROM equipo_cursor INTO @EquipoIdActual;

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
                @DiasSemana = @DiaSemana,
                @TipoProgramacion = @TipoProgramacion,
                @DiaDelMes = @DiaDelMes,
                @DiaInicioMes = @DiaInicioMes,
                @DiaFinMes = @DiaFinMes,
                @UltimosDiasMes = @UltimosDiasMes,
                @ProgramacionId = @ProgramacionId;  -- Excluir la programación actual

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

        CLOSE equipo_cursor;
        DEALLOCATE equipo_cursor;

        -- Limpiar tabla temporal intermedia
        DROP TABLE #ResultadosValidacion;

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
            INSERT (RobotId, EquipoId, EsProgramado, Reservado, FechaAsignacion, AsignadoPor, ProgramacionId)
            VALUES (@RobotId, Source.EquipoId, 1, 0, GETDATE(), @UsuarioModifica, @ProgramacionId);

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
    IF OBJECT_ID('tempdb..#ResultadosValidacion') IS NOT NULL
        DROP TABLE #ResultadosValidacion;
END
GO

PRINT 'SP ActualizarProgramacionCompleta actualizado.';
GO
