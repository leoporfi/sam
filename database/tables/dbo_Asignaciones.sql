SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Asignaciones]') AND type in (N'U'))
BEGIN
CREATE TABLE [dbo].[Asignaciones](
	[RobotId] [int] NULL,
	[EquipoId] [int] NULL,
	[EsProgramado] [bit] NULL,
	[Reservado] [bit] NULL,
	[FechaAsignacion] [datetime2](0) NULL,
	[AsignadoPor] [nvarchar](50) NULL,
	[ProgramacionId] [int] NULL,
 CONSTRAINT [UQ_RobotEquipoProgramacion] UNIQUE NONCLUSTERED
(
	[RobotId] ASC,
	[EquipoId] ASC,
	[ProgramacionId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
END
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Asignaciones]') AND name = N'IX_Asignaciones_EsProgramado_RobotId_EquipoId')
CREATE NONCLUSTERED INDEX [IX_Asignaciones_EsProgramado_RobotId_EquipoId] ON [dbo].[Asignaciones]
(
	[EsProgramado] ASC,
	[RobotId] ASC,
	[EquipoId] ASC
)
INCLUDE([ProgramacionId]) WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Asignaciones]') AND name = N'IX_Asignaciones_ProgramacionId')
CREATE NONCLUSTERED INDEX [IX_Asignaciones_ProgramacionId] ON [dbo].[Asignaciones]
(
	[ProgramacionId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Asignaciones]') AND name = N'IX_AsignacionesRobotEquipo_EquipoId')
CREATE NONCLUSTERED INDEX [IX_AsignacionesRobotEquipo_EquipoId] ON [dbo].[Asignaciones]
(
	[EquipoId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Asignaciones]') AND name = N'IX_AsignacionesRobotEquipo_RobotId')
CREATE NONCLUSTERED INDEX [IX_AsignacionesRobotEquipo_RobotId] ON [dbo].[Asignaciones]
(
	[RobotId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]