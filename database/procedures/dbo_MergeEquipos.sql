SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[MergeEquipos]') AND type in (N'P', N'PC'))
BEGIN
EXEC dbo.sp_executesql @statement = N'CREATE PROCEDURE [dbo].[MergeEquipos] AS' 
END
ALTER PROCEDURE [dbo].[MergeEquipos]
    @EquipoList dbo.EquipoListType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- 1. Tabla temporal para almacenar los equipos que cambiaron de ID
    --    AHORA INCLUYE LOS CAMPOS DE CONFIGURACIÓN DE SAM
    CREATE TABLE #IdUpdates (
        OldEquipoId INT PRIMARY KEY,
        NewEquipoId INT NOT NULL UNIQUE,
        Equipo NVARCHAR(100) NOT NULL,
        UserId INT,
        UserName NVARCHAR(50),
        Licencia NVARCHAR(50),
        Activo_SAM BIT,
        -- Campos de SAM que deben transferirse
        OldPoolId INT,
        OldPermiteBalanceoDinamico BIT,
        OldEstadoBalanceador NVARCHAR(50)
    );

    -- 2. Detectar los conflictos (mismo nombre, diferente ID)
    --    Y guardar la configuración antigua de SAM
    INSERT INTO #IdUpdates (
        OldEquipoId, NewEquipoId, Equipo, UserId, UserName, Licencia, Activo_SAM,
        OldPoolId, OldPermiteBalanceoDinamico, OldEstadoBalanceador
    )
    SELECT
        T.EquipoId AS OldEquipoId,
        S.EquipoId AS NewEquipoId,
        S.Equipo, S.UserId, S.UserName, S.Licencia, S.Activo_SAM,
        -- Guardamos la configuración de SAM del registro antiguo (Target)
        T.PoolId AS OldPoolId,
        T.PermiteBalanceoDinamico AS OldPermiteBalanceoDinamico,
        T.EstadoBalanceador AS OldEstadoBalanceador
    FROM @EquipoList AS S
    INNER JOIN dbo.Equipos AS T ON S.Equipo = T.Equipo -- Coincidencia por Hostname
    WHERE S.EquipoId <> T.EquipoId;                  -- Conflicto de ID

    BEGIN TRY
        BEGIN TRANSACTION;

        -- 3. ACTUALIZAR LOS HIJOS
        -- (Esta lógica re-dirige las FKs de Asignaciones/Ejecuciones al nuevo ID)
        UPDATE A SET A.EquipoId = U.NewEquipoId
        FROM dbo.Asignaciones AS A
        INNER JOIN #IdUpdates AS U ON A.EquipoId = U.OldEquipoId;

        UPDATE E SET E.EquipoId = U.NewEquipoId
        FROM dbo.Ejecuciones AS E
        INNER JOIN #IdUpdates AS U ON E.EquipoId = U.OldEquipoId;
        
        UPDATE EH SET EH.EquipoId = U.NewEquipoId
        FROM dbo.Ejecuciones_Historico AS EH
        INNER JOIN #IdUpdates AS U ON EH.EquipoId = U.OldEquipoId;

        -- 4. MANEJAR LA TABLA PADRE (Equipos)
        
        -- 4a. Eliminar los registros de Equipos ANTIGUOS.
        --     (Es seguro porque los hijos ya no apuntan a él)
        DELETE T
        FROM dbo.Equipos AS T
        INNER JOIN #IdUpdates AS U ON T.EquipoId = U.OldEquipoId;

        -- 4b. Insertar los registros de Equipos NUEVOS
        --     (USANDO LA CONFIGURACIÓN DE SAM GUARDADA)
        INSERT INTO dbo.Equipos (
            EquipoId, Equipo, UserId, UserName, Licencia, Activo_SAM,
            PoolId, PermiteBalanceoDinamico, EstadoBalanceador
        )
        SELECT 
            U.NewEquipoId, U.Equipo, U.UserId, U.UserName, U.Licencia, U.Activo_SAM,
            -- Aplicamos la configuración de SAM que guardamos
            U.OldPoolId,
            U.OldPermiteBalanceoDinamico,
            U.OldEstadoBalanceador
        FROM #IdUpdates AS U;

        -- 5. EJECUTAR EL MERGE NORMAL para el resto de equipos
        --    (Aquellos que no cambiaron su ID o son 100% nuevos)
        MERGE dbo.Equipos AS T
        USING (
            -- Excluimos los que ya manejamos en el paso 4b
            SELECT * FROM @EquipoList 
            WHERE Equipo NOT IN (SELECT Equipo FROM #IdUpdates)
        ) AS S
        ON (T.EquipoId = S.EquipoId) -- Coincidencia normal por ID

        -- 5a. Cuando el ID coincide (actualización normal de datos de A360)
        WHEN MATCHED AND (
                T.Equipo <> S.Equipo OR
                T.UserId <> S.UserId OR
                ISNULL(T.UserName, '') <> ISNULL(S.UserName, '') OR
                ISNULL(T.Licencia, '') <> ISNULL(S.Licencia, '') OR
                T.Activo_SAM <> S.Activo_SAM
            )
        THEN
            UPDATE SET
                T.Equipo = S.Equipo,
                T.UserId = S.UserId,
                T.UserName = S.UserName,
                T.Licencia = S.Licencia,
                T.Activo_SAM = S.Activo_SAM
                -- NOTA: No tocamos PoolId ni PermiteBalanceoDinamico aquí.

        -- 5b. Cuando es un equipo 100% nuevo (nunca visto)
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (EquipoId, Equipo, UserId, UserName, Licencia, Activo_SAM)
            VALUES (S.EquipoId, S.Equipo, S.UserId, S.UserName, S.Licencia, S.Activo_SAM)
            -- Se inserta con los valores por defecto de SAM (PoolId NULL, PermiteBalanceo 0)

        -- 5c. Opcional: Desactivar equipos que ya no vienen de A360
        --WHEN NOT MATCHED BY SOURCE AND T.Activo_SAM = 1 THEN
        --    UPDATE SET T.Activo_SAM = 0

        ;COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;

        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'dbo.MergeEquipos', @ErrorMessage, 'Input: @EquipoList (TVP)');

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
