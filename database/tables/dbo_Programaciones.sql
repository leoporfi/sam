SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Programaciones]') AND type in (N'U'))
BEGIN
CREATE TABLE [dbo].[Programaciones](
	[ProgramacionId] [int] IDENTITY(1,1) NOT NULL,
	[RobotId] [int] NULL,
	[TipoProgramacion] [nvarchar](20) NULL,
	[HoraInicio] [time](0) NOT NULL,
	[DiasSemana] [nvarchar](20) NULL,
	[DiaDelMes] [int] NULL,
	[FechaEspecifica] [date] NULL,
	[Tolerancia] [int] NULL,
	[Activo] [bit] NULL,
	[FechaCreacion] [datetime2](0) NULL,
	[FechaModificacion] [datetime2](0) NULL,
	[DiaInicioMes] [int] NULL,
	[DiaFinMes] [int] NULL,
	[UltimosDiasMes] [int] NULL,
	[EsCiclico] [bit] NULL,
	[HoraFin] [time](0) NULL,
	[FechaInicioVentana] [date] NULL,
	[FechaFinVentana] [date] NULL,
	[IntervaloEntreEjecuciones] [int] NULL,
 CONSTRAINT [PK__Programa__B9967C40CEE769DF] PRIMARY KEY CLUSTERED
(
	[ProgramacionId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
END
SET ANSI_PADDING ON

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Programaciones]') AND name = N'IX_Programaciones_Activo_EsCiclico_Tipo')
CREATE NONCLUSTERED INDEX [IX_Programaciones_Activo_EsCiclico_Tipo] ON [dbo].[Programaciones]
(
	[Activo] ASC,
	[EsCiclico] ASC,
	[TipoProgramacion] ASC
)
INCLUDE([RobotId],[HoraInicio],[HoraFin],[Tolerancia],[DiasSemana],[DiaDelMes],[FechaEspecifica],[DiaInicioMes],[DiaFinMes],[UltimosDiasMes],[FechaInicioVentana],[FechaFinVentana],[IntervaloEntreEjecuciones]) WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[Programaciones]') AND name = N'IX_Programaciones_RobotId')
CREATE NONCLUSTERED INDEX [IX_Programaciones_RobotId] ON [dbo].[Programaciones]
(
	[RobotId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE object_id = OBJECT_ID(N'[dbo].[CK__Programac__TipoP__1F98B2C1]') AND parent_object_id = OBJECT_ID(N'[dbo].[Programaciones]'))
ALTER TABLE [dbo].[Programaciones]  WITH CHECK ADD  CONSTRAINT [CK__Programac__TipoP__1F98B2C1] CHECK  (([TipoProgramacion]='RangoMensual' OR [TipoProgramacion]='Especifica' OR [TipoProgramacion]='Mensual' OR [TipoProgramacion]='Semanal' OR [TipoProgramacion]='Diaria'))
IF  EXISTS (SELECT * FROM sys.check_constraints WHERE object_id = OBJECT_ID(N'[dbo].[CK__Programac__TipoP__1F98B2C1]') AND parent_object_id = OBJECT_ID(N'[dbo].[Programaciones]'))
ALTER TABLE [dbo].[Programaciones] CHECK CONSTRAINT [CK__Programac__TipoP__1F98B2C1]
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Programaciones', N'COLUMN',N'TipoProgramacion'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'1-Diaria, 2-Semanal, 3-Mensual, 4-Especifica' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Programaciones', @level2type=N'COLUMN',@level2name=N'TipoProgramacion'
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Programaciones', N'COLUMN',N'DiaInicioMes'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Día de inicio del rango mensual (1-31). Usar con DiaFinMes para definir un rango. Ej: 1 para "del 1 al 15"' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Programaciones', @level2type=N'COLUMN',@level2name=N'DiaInicioMes'
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Programaciones', N'COLUMN',N'DiaFinMes'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Día de fin del rango mensual (1-31). Usar con DiaInicioMes. Ej: 15 para "del 1 al 15"' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Programaciones', @level2type=N'COLUMN',@level2name=N'DiaFinMes'
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Programaciones', N'COLUMN',N'UltimosDiasMes'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Cantidad de días desde el FINAL del mes. Ej: 5 para "los últimos 5 días de cada mes"' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Programaciones', @level2type=N'COLUMN',@level2name=N'UltimosDiasMes'
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Programaciones', N'COLUMN',N'EsCiclico'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Indica si el robot se ejecuta cíclicamente (1) o solo una vez (0/NULL). Si es 1, el robot se ejecutará repetidamente dentro de la ventana temporal definida.' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Programaciones', @level2type=N'COLUMN',@level2name=N'EsCiclico'
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Programaciones', N'COLUMN',N'HoraFin'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Hora de fin del rango horario permitido para ejecución. Si es NULL y EsCiclico=1, se permite ejecución durante todo el día.' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Programaciones', @level2type=N'COLUMN',@level2name=N'HoraFin'
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Programaciones', N'COLUMN',N'FechaInicioVentana'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Fecha desde la cual la ventana temporal es válida. Si es NULL, la ventana es válida desde la fecha de creación.' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Programaciones', @level2type=N'COLUMN',@level2name=N'FechaInicioVentana'
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Programaciones', N'COLUMN',N'FechaFinVentana'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Fecha hasta la cual la ventana temporal es válida. Si es NULL, la ventana es válida indefinidamente.' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Programaciones', @level2type=N'COLUMN',@level2name=N'FechaFinVentana'
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_Description' , N'SCHEMA',N'dbo', N'TABLE',N'Programaciones', N'COLUMN',N'IntervaloEntreEjecuciones'))
	EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Minutos de espera entre ejecuciones cíclicas. Si es NULL y EsCiclico=1, se ejecuta tan pronto como el equipo esté disponible.' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Programaciones', @level2type=N'COLUMN',@level2name=N'IntervaloEntreEjecuciones'
GO
