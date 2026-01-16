-- database/tables/dbo_Auditoria.sql
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Auditoria]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[Auditoria] (
        [AuditoriaId] INT IDENTITY(1,1) PRIMARY KEY,
        [Fecha] DATETIME DEFAULT GETDATE(),
        [Accion] NVARCHAR(50),      -- CREATE, UPDATE, DELETE, SYNC, UNLOCK, TOGGLE
        [Entidad] NVARCHAR(50),     -- Robot, Equipo, Pool, Programacion, Mapeo, Configuracion
        [EntidadId] NVARCHAR(100),  -- ID de la entidad afectada
        [Detalle] NVARCHAR(MAX),    -- Descripción del cambio o JSON con valores
        [Host] NVARCHAR(100),       -- IP o Hostname del cliente
        [Usuario] NVARCHAR(100)     -- 'WebApp'
    );
END
GO
