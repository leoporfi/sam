-- database/procedures/dbo_RegistrarAuditoria.sql
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[RegistrarAuditoria]') AND type in (N'P', N'PC'))
    DROP PROCEDURE [dbo].[RegistrarAuditoria];
GO

CREATE PROCEDURE [dbo].[RegistrarAuditoria]
    @Accion NVARCHAR(50),
    @Entidad NVARCHAR(50),
    @EntidadId NVARCHAR(100),
    @Detalle NVARCHAR(MAX),
    @Host NVARCHAR(100),
    @Usuario NVARCHAR(100) = 'WebApp'
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.Auditoria (Accion, Entidad, EntidadId, Detalle, Host, Usuario)
    VALUES (@Accion, @Entidad, @EntidadId, @Detalle, @Host, @Usuario);
END
GO
