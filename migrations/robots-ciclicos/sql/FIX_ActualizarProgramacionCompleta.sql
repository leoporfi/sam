-- =============================================
-- FIX: ActualizarProgramacionCompleta
-- =============================================
-- Corrige el mismo problema que CrearProgramacion:
-- INSERT INTO #ConflictosDetectados (4 cols) EXEC sp (13 cols)
-- Solución: usar tabla temporal intermedia

SET NOCOUNT ON;

PRINT '============================================='
PRINT 'ACTUALIZANDO SP: ActualizarProgramacionCompleta'
PRINT '============================================='
PRINT ''

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ActualizarProgramacionCompleta]') AND type in (N'P', N'PC'))
BEGIN
    PRINT '[ERROR] SP ActualizarProgramacionCompleta NO EXISTE'
    RETURN
END

PRINT 'SP encontrado. Actualizando...'
PRINT ''

-- Obtener el texto actual del SP
DECLARE @SPText NVARCHAR(MAX)
SELECT @SPText = OBJECT_DEFINITION(OBJECT_ID('dbo.ActualizarProgramacionCompleta'))

-- Buscar la sección problemática
DECLARE @CursorStart INT = CHARINDEX('DECLARE equipo_cursor CURSOR FOR', @SPText)
DECLARE @WhileStart INT = CHARINDEX('WHILE @@FETCH_STATUS = 0', @SPText, @CursorStart)
DECLARE @WhileEnd INT = CHARINDEX('CLOSE equipo_cursor;', @SPText, @WhileStart)

IF @CursorStart = 0 OR @WhileStart = 0 OR @WhileEnd = 0
BEGIN
    PRINT '[ERROR] No se encontró la sección del cursor en el SP'
    RETURN
END

-- Extraer la parte antes del cursor
DECLARE @ParteAntes NVARCHAR(MAX) = SUBSTRING(@SPText, 1, @WhileStart - 1)

-- Extraer la parte después del cursor
DECLARE @ParteDespues NVARCHAR(MAX) = SUBSTRING(@SPText, @WhileEnd, LEN(@SPText) - @WhileEnd + 1)

-- Construir la nueva sección del cursor con tabla temporal intermedia
DECLARE @NuevaSeccionCursor NVARCHAR(MAX) = '
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
'

-- Construir el nuevo SP completo
DECLARE @NuevoSPText NVARCHAR(MAX) = @ParteAntes + @NuevaSeccionCursor + @ParteDespues

-- Buscar y agregar DROP TABLE al final del CATCH si no existe
IF CHARINDEX('DROP TABLE #ResultadosValidacion', @NuevoSPText) = 0
BEGIN
    -- Buscar el final del SP (antes del END final)
    DECLARE @UltimoEnd INT = LEN(@NuevoSPText) - CHARINDEX('END', REVERSE(@NuevoSPText)) + 1

    -- Insertar DROP TABLE antes del último END
    SET @NuevoSPText = STUFF(@NuevoSPText, @UltimoEnd, 0, CHAR(13) + CHAR(10) + '        IF OBJECT_ID(''tempdb..#ResultadosValidacion'') IS NOT NULL' + CHAR(13) + CHAR(10) + '            DROP TABLE #ResultadosValidacion;' + CHAR(13) + CHAR(10))
END

-- Ejecutar el nuevo SP
EXEC sp_executesql @NuevoSPText

PRINT 'SP ActualizarProgramacionCompleta actualizado correctamente.'
PRINT 'El INSERT ahora usa tabla temporal intermedia para ValidarSolapamientoVentanas.'
PRINT ''
