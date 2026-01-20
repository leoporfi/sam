SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[EliminarProgramacionCompleta]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[EliminarProgramacionCompleta] AS'
END

-- Usamos CREATE OR ALTER para que el script se pueda ejecutar múltiples veces sin error.
ALTER PROCEDURE [dbo].[EliminarProgramacionCompleta]
    @ProgramacionId INT,
    @RobotId INT,
    @UsuarioModifica NVARCHAR(50) = 'WebApp_Delete'
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @ErrorMessage NVARCHAR(4000);
    CREATE TABLE #EquiposAfectados (EquipoId INT PRIMARY KEY);

    BEGIN TRY
        BEGIN TRANSACTION;

        -- 1. Identificar los equipos que están asignados a ESTA programación específica
        INSERT INTO #EquiposAfectados (EquipoId)
        SELECT DISTINCT EquipoId
        FROM dbo.Asignaciones
        WHERE ProgramacionId = @ProgramacionId
          AND RobotId = @RobotId
          AND EsProgramado = 1;

        -- 2. Eliminar las asignaciones VINCULADAS A ESTA PROGRAMACIÓN
        DELETE FROM dbo.Asignaciones
        WHERE ProgramacionId = @ProgramacionId
          AND RobotId = @RobotId
          AND EquipoId IN (SELECT EquipoId FROM #EquiposAfectados)
          AND (Reservado = 0 OR Reservado IS NULL);

        -- 3. Eliminar la programación de la tabla principal.
        -- Ahora es seguro borrar el padre porque ya borramos sus hijos específicos.
        DELETE FROM dbo.Programaciones
        WHERE ProgramacionId = @ProgramacionId AND RobotId = @RobotId;

        -- 4. Actualizar estado de equipos
        -- Solo liberamos el equipo (PermiteBalanceoDinamico = 1) si YA NO TIENE ninguna asignación.
        -- Al haber corregido el paso 2, si existe otra programación, la fila en Asignaciones seguirá existiendo
        -- y el NOT EXISTS dará falso, protegiendo al equipo de ser liberado incorrectamente.
        UPDATE E
        SET E.PermiteBalanceoDinamico = 1
        FROM dbo.Equipos E
        JOIN #EquiposAfectados A ON E.EquipoId = A.EquipoId
        WHERE NOT EXISTS (
            SELECT 1 FROM dbo.Asignaciones a2
            WHERE a2.EquipoId = E.EquipoId
              AND (a2.EsProgramado = 1 OR a2.Reservado = 1)
        );

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SET @ErrorMessage = ERROR_MESSAGE();
        RAISERROR (@ErrorMessage, 16, 1);
    END CATCH

    IF OBJECT_ID('tempdb..#EquiposAfectados') IS NOT NULL
        DROP TABLE #EquiposAfectados;
END
GO
