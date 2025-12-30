SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Ejecuciones]') AND type in (N'U'))
BEGIN
CREATE TABLE [dbo].[Ejecuciones](
	[EjecucionId] [int] IDENTITY(1,1) NOT NULL,
	[DeploymentId] [nvarchar](50) NOT NULL,
	[RobotId] [int] NULL,
	[EquipoId] [int] NULL,
	[UserId] [int] NULL,
	[Hora] [time](0) NULL,
	[FechaInicio] [datetime2](0) NOT NULL,
	[FechaFin] [datetime2](0) NULL,
	[Estado] [nvarchar](20) NOT NULL,
	[FechaActualizacion] [datetime2](0) NULL,
	[CallbackInfo] [nvarchar](500) NULL,
	[IntentosConciliadorFallidos] [int] NOT NULL,
	[FechaUltimoUNKNOWN] [datetime] NULL,
 CONSTRAINT [pk_EjecucionId] PRIMARY KEY CLUSTERED
(
	[EjecucionId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
END
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Ejecuciones]') AND name = N'IX_Ejecuciones_EquipoId')
CREATE NONCLUSTERED INDEX [IX_Ejecuciones_EquipoId] ON [dbo].[Ejecuciones]
(
	[EquipoId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
SET ANSI_PADDING ON

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Ejecuciones]') AND name = N'IX_Ejecuciones_EquipoId_Estado')
CREATE NONCLUSTERED INDEX [IX_Ejecuciones_EquipoId_Estado] ON [dbo].[Ejecuciones]
(
	[EquipoId] ASC,
	[Estado] ASC
)
INCLUDE([RobotId],[FechaUltimoUNKNOWN],[FechaFin],[Hora],[FechaInicio]) WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
SET ANSI_PADDING ON

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Ejecuciones]') AND name = N'IX_Ejecuciones_Estado')
CREATE NONCLUSTERED INDEX [IX_Ejecuciones_Estado] ON [dbo].[Ejecuciones]
(
	[Estado] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
SET ANSI_PADDING ON

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Ejecuciones]') AND name = N'IX_Ejecuciones_Estado_FechaFin')
CREATE NONCLUSTERED INDEX [IX_Ejecuciones_Estado_FechaFin] ON [dbo].[Ejecuciones]
(
	[Estado] ASC,
	[FechaFin] ASC
)
INCLUDE([RobotId],[EquipoId]) WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Ejecuciones]') AND name = N'IX_Ejecuciones_RobotEquipoHoraFecha')
CREATE NONCLUSTERED INDEX [IX_Ejecuciones_RobotEquipoHoraFecha] ON [dbo].[Ejecuciones]
(
	[RobotId] ASC,
	[EquipoId] ASC,
	[Hora] ASC,
	[FechaInicio] ASC
)
INCLUDE([Estado],[FechaFin]) WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Ejecuciones]') AND name = N'IX_Ejecuciones_RobotId')
CREATE NONCLUSTERED INDEX [IX_Ejecuciones_RobotId] ON [dbo].[Ejecuciones]
(
	[RobotId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
SET ANSI_PADDING ON

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Ejecuciones]') AND name = N'UQ_Ejecuciones_DeploymentId')
CREATE UNIQUE NONCLUSTERED INDEX [UQ_Ejecuciones_DeploymentId] ON [dbo].[Ejecuciones]
(
	[DeploymentId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
