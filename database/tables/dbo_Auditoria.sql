SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Auditoria]') AND type in (N'U'))
BEGIN
CREATE TABLE [dbo].[Auditoria](
	[AuditoriaId] [int] IDENTITY(1,1) NOT NULL,
	[Fecha] [datetime] NULL,
	[Accion] [nvarchar](50) NULL,
	[Entidad] [nvarchar](50) NULL,
	[EntidadId] [nvarchar](100) NULL,
	[Detalle] [nvarchar](max) NULL,
	[Host] [nvarchar](100) NULL,
	[Usuario] [nvarchar](100) NULL,
PRIMARY KEY CLUSTERED
(
	[AuditoriaId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
END
GO
