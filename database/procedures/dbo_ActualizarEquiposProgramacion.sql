SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ActualizarEquiposProgramacion]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ActualizarEquiposProgramacion] AS'
END
GO
ALTER PROCEDURE [dbo].[ActualizarEquiposProgramacion]
    @ProgramacionId INT,
    @EquiposIds dbo.IdListType READONLY
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRANSACTION;

    BEGIN TRY
        -- 1. Obtener el RobotId asociado a esta programación
        DECLARE @RobotId INT;
        SELECT @RobotId = RobotId FROM dbo.Programaciones WHERE ProgramacionId = @ProgramacionId;

        -- 2. Eliminar asignaciones previas de esta programación
        -- (Limpiamos la tabla Asignaciones para este ID de programación)
        DELETE FROM dbo.Asignaciones
        WHERE ProgramacionId = @ProgramacionId;

        -- 3. Insertar las nuevas asignaciones
        INSERT INTO dbo.Asignaciones (RobotId, EquipoId, EsProgramado, Reservado, FechaAsignacion, ProgramacionId, AsignadoPor)
        SELECT
            @RobotId,
            ID,
            1, -- EsProgramado
            0, -- Reservado (asumimos 0 para programación estándar)
            GETDATE(),
            @ProgramacionId,
            'SAM_WEB'
        FROM @EquiposIds;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END

GO
