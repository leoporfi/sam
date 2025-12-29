SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
SET ANSI_PADDING ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[MapeoRobots]') AND type in (N'U'))
BEGIN
CREATE TABLE [dbo].[MapeoRobots](
	[MapeoId] [int] IDENTITY(1,1) NOT NULL,
	[Proveedor] [varchar](50) NOT NULL,
	[NombreExterno] [varchar](255) NOT NULL,
	[RobotId] [int] NOT NULL,
	[Descripcion] [varchar](500) NULL,
	[FechaCreacion] [datetime] NULL,
PRIMARY KEY CLUSTERED 
(
	[MapeoId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Proveedor_NombreExterno] UNIQUE NONCLUSTERED 
(
	[Proveedor] ASC,
	[NombreExterno] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
END
SET ANSI_PADDING OFF
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE object_id = OBJECT_ID(N'[dbo].[FK_MapeoRobots_Robots]') AND parent_object_id = OBJECT_ID(N'[dbo].[MapeoRobots]'))
ALTER TABLE [dbo].[MapeoRobots]  WITH CHECK ADD  CONSTRAINT [FK_MapeoRobots_Robots] FOREIGN KEY([RobotId])
REFERENCES [dbo].[Robots] ([RobotId])
IF  EXISTS (SELECT * FROM sys.foreign_keys WHERE object_id = OBJECT_ID(N'[dbo].[FK_MapeoRobots_Robots]') AND parent_object_id = OBJECT_ID(N'[dbo].[MapeoRobots]'))
ALTER TABLE [dbo].[MapeoRobots] CHECK CONSTRAINT [FK_MapeoRobots_Robots]
