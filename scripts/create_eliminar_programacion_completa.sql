CREATE PROCEDURE dbo.EliminarProgramacionCompleta
    @ProgramacionId INT,
    @RobotId INT,
    @UsuarioModifica NVARCHAR(50) = 'WebApp_Delete'
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @ErrorMessage NVARCHAR(4000);
    DECLARE @ErrorSeverity INT;
    DECLARE @ErrorState INT;

    CREATE TABLE #EquiposDelCronogramaEliminado (EquipoId INT PRIMARY KEY);

    BEGIN TRY
        BEGIN TRANSACTION;

        -- 1. Verificación de existencia
        IF NOT EXISTS (
            SELECT 1
            FROM dbo.Programaciones
            WHERE ProgramacionId = @ProgramacionId AND RobotId = @RobotId
        )
        BEGIN
            RAISERROR('Programación no encontrada para el RobotId especificado o ya ha sido eliminada.', 16, 1);
            RETURN;
        END

        -- 2. Equipos afectados
        INSERT INTO #EquiposDelCronogramaEliminado (EquipoId)
        SELECT DISTINCT EquipoId
        FROM dbo.Asignaciones
        WHERE ProgramacionId = @ProgramacionId
          AND EsProgramado = 1
          AND RobotId = @RobotId;

        -- 3. Desasignar equipos de esta programación
        UPDATE dbo.Asignaciones
        SET EsProgramado = 0,
            ProgramacionId = NULL,
            AsignadoPor = @UsuarioModifica,
            FechaAsignacion = GETDATE()
        WHERE ProgramacionId = @ProgramacionId AND RobotId = @RobotId;

        -- 4. Eliminar la programación
        DELETE FROM dbo.Programaciones
        WHERE ProgramacionId = @ProgramacionId AND RobotId = @RobotId;

        -- 5. Restaurar PermiteBalanceoDinamico si el equipo ya no está en ninguna otra programación
        UPDATE E
        SET PermiteBalanceoDinamico = 1
        FROM dbo.Equipos E
        WHERE EXISTS (
            SELECT 1 FROM #EquiposDelCronogramaEliminado ED
            WHERE E.EquipoId = ED.EquipoId
        )
        AND NOT EXISTS (
            SELECT 1 FROM dbo.Asignaciones A
            WHERE A.EquipoId = E.EquipoId AND A.EsProgramado = 1 AND A.ProgramacionId IS NOT NULL
        );

        COMMIT TRANSACTION;

        PRINT 'Programación ID ' + CAST(@ProgramacionId AS VARCHAR(10)) + ' eliminada exitosamente.';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SET @ErrorMessage = ERROR_MESSAGE();
        SET @ErrorSeverity = ERROR_SEVERITY();
        SET @ErrorState = ERROR_STATE();

        DECLARE @Parametros NVARCHAR(MAX);
        SET @Parametros = 
            '@ProgramacionId = ' + CAST(@ProgramacionId AS NVARCHAR) +
            ', @RobotId = ' + CAST(@RobotId AS NVARCHAR);

        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (
            SUSER_NAME(),
            'EliminarProgramacionCompleta',
            @ErrorMessage,
            @Parametros
        );

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH

    -- Limpieza de tabla temporal
    IF OBJECT_ID('tempdb..#EquiposDelCronogramaEliminado') IS NOT NULL
        DROP TABLE #EquiposDelCronogramaEliminado;
END
GO
