SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Robots]') AND type in (N'U'))
BEGIN
CREATE TABLE [dbo].[Robots](
	[RobotId] [int] NOT NULL,
	[Robot] [nvarchar](100) NOT NULL,
	[Descripcion] [nvarchar](4000) NULL,
	[Parametros] [nvarchar](max) NULL,
	[Activo] [bit] NULL,
	[EsOnline] [bit] NULL,
	[MinEquipos] [int] NOT NULL,
	[MaxEquipos] [int] NOT NULL,
	[PrioridadBalanceo] [int] NOT NULL,
	[TicketsPorEquipoAdicional] [int] NULL,
	[PoolId] [int] NULL,
 CONSTRAINT [PK__Robots__FBB332411B3A6772] PRIMARY KEY CLUSTERED
(
	[RobotId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
END
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Robots]') AND name = N'IX_Robots_Activo_EsOnline')
CREATE NONCLUSTERED INDEX [IX_Robots_Activo_EsOnline] ON [dbo].[Robots]
(
	[Activo] ASC,
	[EsOnline] ASC
)
INCLUDE([RobotId],[PrioridadBalanceo]) WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE object_id = OBJECT_ID(N'[dbo].[FK_Robots_Pools]') AND parent_object_id = OBJECT_ID(N'[dbo].[Robots]'))
ALTER TABLE [dbo].[Robots]  WITH CHECK ADD  CONSTRAINT [FK_Robots_Pools] FOREIGN KEY([PoolId])
REFERENCES [dbo].[Pools] ([PoolId])
ON DELETE SET NULL
IF  EXISTS (SELECT * FROM sys.foreign_keys WHERE object_id = OBJECT_ID(N'[dbo].[FK_Robots_Pools]') AND parent_object_id = OBJECT_ID(N'[dbo].[Robots]'))
ALTER TABLE [dbo].[Robots] CHECK CONSTRAINT [FK_Robots_Pools]
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Robots', N'COLUMN',N'MinEquipos'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Número mínimo de equipos que el balanceador intentará mantener asignado si hay tickets.' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Robots', @level2type=N'COLUMN',@level2name=N'MinEquipos'
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Robots', N'COLUMN',N'MaxEquipos'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Límite de equipos que el balanceador puede asignar dinámicamente a este robot. (default -1 o un número alto)' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Robots', @level2type=N'COLUMN',@level2name=N'MaxEquipos'
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Robots', N'COLUMN',N'PrioridadBalanceo'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Para decidir qué robot obtiene recursos si son escasos. Menor número = mayor prioridad.' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Robots', @level2type=N'COLUMN',@level2name=N'PrioridadBalanceo'