SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[HistoricoBalanceo]') AND type in (N'U'))
BEGIN
CREATE TABLE [dbo].[HistoricoBalanceo](
	[HistoricoId] [int] IDENTITY(1,1) NOT NULL,
	[FechaBalanceo] [datetime2](0) NOT NULL,
	[RobotId] [int] NOT NULL,
	[TicketsPendientes] [int] NOT NULL,
	[EquiposAsignadosAntes] [int] NOT NULL,
	[EquiposAsignadosDespues] [int] NOT NULL,
	[AccionTomada] [nvarchar](50) NOT NULL,
	[Justificacion] [nvarchar](255) NULL,
	[PoolId] [int] NULL,
 CONSTRAINT [PK_HistoricoBalanceo] PRIMARY KEY CLUSTERED 
(
	[HistoricoId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
END
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE object_id = OBJECT_ID(N'[dbo].[FK_HistoricoBalanceo_Robots]') AND parent_object_id = OBJECT_ID(N'[dbo].[HistoricoBalanceo]'))
ALTER TABLE [dbo].[HistoricoBalanceo]  WITH CHECK ADD  CONSTRAINT [FK_HistoricoBalanceo_Robots] FOREIGN KEY([RobotId])
REFERENCES [dbo].[Robots] ([RobotId])
IF  EXISTS (SELECT * FROM sys.foreign_keys WHERE object_id = OBJECT_ID(N'[dbo].[FK_HistoricoBalanceo_Robots]') AND parent_object_id = OBJECT_ID(N'[dbo].[HistoricoBalanceo]'))
ALTER TABLE [dbo].[HistoricoBalanceo] CHECK CONSTRAINT [FK_HistoricoBalanceo_Robots]
