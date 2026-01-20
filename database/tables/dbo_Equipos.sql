SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Equipos]') AND type in (N'U'))
BEGIN
CREATE TABLE [dbo].[Equipos](
	[EquipoId] [int] NOT NULL,
	[Equipo] [nvarchar](100) NOT NULL,
	[UserId] [int] NOT NULL,
	[UserName] [nvarchar](50) NULL,
	[Licencia] [nvarchar](50) NULL,
	[Activo_SAM] [bit] NOT NULL,
	[EstadoBalanceador] [nvarchar](50) NULL,
	[PermiteBalanceoDinamico] [bit] NOT NULL,
	[PoolId] [int] NULL,
 CONSTRAINT [PK_Equipos] PRIMARY KEY CLUSTERED
(
	[EquipoId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
END
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE object_id = OBJECT_ID(N'[dbo].[FK_Equipos_Pools]') AND parent_object_id = OBJECT_ID(N'[dbo].[Equipos]'))
ALTER TABLE [dbo].[Equipos]  WITH CHECK ADD  CONSTRAINT [FK_Equipos_Pools] FOREIGN KEY([PoolId])
REFERENCES [dbo].[Pools] ([PoolId])
ON UPDATE CASCADE
ON DELETE SET NULL
IF  EXISTS (SELECT * FROM sys.foreign_keys WHERE object_id = OBJECT_ID(N'[dbo].[FK_Equipos_Pools]') AND parent_object_id = OBJECT_ID(N'[dbo].[Equipos]'))
ALTER TABLE [dbo].[Equipos] CHECK CONSTRAINT [FK_Equipos_Pools]
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Equipos', N'COLUMN',N'EstadoBalanceador'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'(Opcional, pero útil) Podría indicar "DisponibleEnPoolPivote", "AsignadoDinamicoA_RobotX", "EnMantenimientoManual", etc.' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Equipos', @level2type=N'COLUMN',@level2name=N'EstadoBalanceador'
GO
