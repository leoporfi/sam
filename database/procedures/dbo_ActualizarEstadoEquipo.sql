SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ActualizarEstadoEquipo]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[ActualizarEstadoEquipo] AS'
END
ALTER PROCEDURE [dbo].[ActualizarEstadoEquipo]
    @EquipoId INT,
    @Campo NVARCHAR(50),
    @Valor BIT
AS
BEGIN
    SET NOCOUNT ON;

    IF @Campo NOT IN ('Activo_SAM', 'PermiteBalanceoDinamico')
    BEGIN
        RAISERROR ('El campo especificado no es válido para esta operación.', 16, 1);
        RETURN;
    END

    -- 1. Verificar si el equipo existe
    IF NOT EXISTS (SELECT 1 FROM dbo.Equipos WHERE EquipoId = @EquipoId)
    BEGIN
        RAISERROR ('Equipo no encontrado.', 16, 1);
        RETURN;
    END

    -- 2. Verificar si el valor ya es el mismo
    DECLARE @SQL_CHECK NVARCHAR(MAX);
    SET @SQL_CHECK = 'IF EXISTS (SELECT 1 FROM dbo.Equipos WHERE EquipoId = @p_EquipoId AND ' + QUOTENAME(@Campo) + ' = @p_Valor) RAISERROR(''Sin cambios: el equipo ya tiene ese valor.'', 16, 2);';
    EXEC sp_executesql @SQL_CHECK, N'@p_Valor BIT, @p_EquipoId INT', @p_Valor = @Valor, @p_EquipoId = @EquipoId;

    -- 3. Actualizar
    DECLARE @SQL_UPDATE NVARCHAR(MAX);
    SET @SQL_UPDATE = 'UPDATE dbo.Equipos SET ' + QUOTENAME(@Campo) + ' = @p_Valor WHERE EquipoId = @p_EquipoId';
    EXEC sp_executesql @SQL_UPDATE, N'@p_Valor BIT, @p_EquipoId INT', @p_Valor = @Valor, @p_EquipoId = @EquipoId;
END
