SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Ejecuciones_Historico]') AND type in (N'U'))
BEGIN
CREATE TABLE [dbo].[Ejecuciones_Historico](
	[HistoricoId] [int] IDENTITY(1,1) NOT NULL,
	[EjecucionId] [int] NOT NULL,
	[DeploymentId] [nvarchar](100) NOT NULL,
	[RobotId] [int] NULL,
	[EquipoId] [int] NULL,
	[UserId] [int] NULL,
	[Hora] [time](0) NULL,
	[FechaInicio] [datetime2](0) NOT NULL,
	[FechaFin] [datetime2](0) NULL,
	[Estado] [nvarchar](20) NOT NULL,
	[FechaActualizacion] [datetime2](0) NULL,
	[IntentosConciliadorFallidos] [int] NOT NULL,
	[CallbackInfo] [nvarchar](max) NULL,
 CONSTRAINT [PK_Ejecuciones_Historico] PRIMARY KEY CLUSTERED
(
	[HistoricoId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
END
