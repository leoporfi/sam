USE [SAM]
GO
/****** Object:  UserDefinedTableType [dbo].[EquipoListType] ******/
CREATE TYPE [dbo].[EquipoListType] AS TABLE(
	[EquipoId] [int] NOT NULL,
	[Equipo] [nvarchar](100) NOT NULL,
	[UserId] [int] NOT NULL,
	[UserName] [nvarchar](50) NULL,
	[Licencia] [nvarchar](50) NULL,
	[Activo_SAM] [bit] NOT NULL,
	PRIMARY KEY CLUSTERED 
(
	[EquipoId] ASC
)WITH (IGNORE_DUP_KEY = OFF)
)
GO
/****** Object:  UserDefinedTableType [dbo].[IdListType] ******/
CREATE TYPE [dbo].[IdListType] AS TABLE(
	[ID] [int] NOT NULL,
	PRIMARY KEY CLUSTERED 
(
	[ID] ASC
)WITH (IGNORE_DUP_KEY = OFF)
)
GO
/****** Object:  UserDefinedTableType [dbo].[RobotListType] ******/
CREATE TYPE [dbo].[RobotListType] AS TABLE(
	[RobotId] [int] NOT NULL,
	[Robot] [nvarchar](100) NOT NULL,
	[Descripcion] [nvarchar](4000) NULL,
	PRIMARY KEY CLUSTERED 
(
	[RobotId] ASC
)WITH (IGNORE_DUP_KEY = OFF)
)
GO
/****** Object:  Table [dbo].[Programaciones] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
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
 CONSTRAINT [PK__Programa__B9967C40CEE769DF] PRIMARY KEY CLUSTERED 
(
	[ProgramacionId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[HistoricoBalanceo] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
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
GO
/****** Object:  Table [dbo].[Robots] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
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
GO
/****** Object:  Table [dbo].[Ejecuciones] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
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
GO
/****** Object:  Table [dbo].[Pools] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Pools](
	[PoolId] [int] IDENTITY(1,1) NOT NULL,
	[Nombre] [nvarchar](100) NOT NULL,
	[Descripcion] [nvarchar](500) NULL,
	[Activo] [bit] NOT NULL,
	[FechaCreacion] [datetime2](0) NOT NULL,
	[FechaModificacion] [datetime2](0) NULL,
PRIMARY KEY CLUSTERED 
(
	[PoolId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[Nombre] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Asignaciones] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
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
GO
/****** Object:  View [dbo].[EquiposAsignados] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE VIEW [dbo].[EquiposAsignados] AS
SELECT 
    r.Robot,
    COUNT(DISTINCT a.EquipoId) AS Equipos  -- Cambiar COUNT(*) por COUNT(DISTINCT a.EquipoId)
FROM dbo.Robots r
LEFT JOIN dbo.Asignaciones a ON r.RobotId = a.RobotId
GROUP BY r.Robot;
GO
/****** Object:  View [dbo].[EstadoBalanceadorTiempoReal] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- =============================================
-- VISTA COMPLEMENTARIA: Estado en tiempo real
-- =============================================
CREATE   VIEW [dbo].[EstadoBalanceadorTiempoReal]
AS
SELECT
    R.RobotId,
    R.Robot,
    R.EsOnline,
    R.Activo,
    R.MinEquipos,
    R.MaxEquipos,
    R.PrioridadBalanceo,
    R.TicketsPorEquipoAdicional,
    ISNULL(EA.Equipos, 0) AS EquiposAsignados,
    CASE 
        WHEN R.EsOnline = 1 THEN 'Online'
        WHEN EXISTS(SELECT 1 FROM Programaciones P WHERE P.RobotId = R.RobotId AND P.Activo = 1) THEN 'Programado'
        WHEN R.Activo = 0 THEN 'Inactivo'
        ELSE 'Disponible'
    END AS EstadoActual,
    CASE
        WHEN ISNULL(EA.Equipos, 0) < R.MinEquipos THEN 'Necesita más equipos'
        WHEN R.MaxEquipos > 0 AND ISNULL(EA.Equipos, 0) > R.MaxEquipos THEN 'Exceso de equipos'
        ELSE 'Balanceado'
    END AS EstadoBalanceo,
    -- Indicador de carga basado en ejecuciones activas
    ISNULL(EjecActivas.EjecucionesActivas, 0) AS EjecucionesActivas,
    -- Última actividad del balanceador
    HB.UltimaActividad,
    HB.UltimaAccion,
    P.Nombre AS Pool
FROM Robots R
LEFT JOIN EquiposAsignados EA ON R.Robot = EA.Robot
LEFT JOIN (
    SELECT 
        RobotId,
        MAX(FechaBalanceo) AS UltimaActividad,
        FIRST_VALUE(AccionTomada) OVER (PARTITION BY RobotId ORDER BY FechaBalanceo DESC) AS UltimaAccion
    FROM HistoricoBalanceo
    WHERE FechaBalanceo >= DATEADD(DAY, -7, GETDATE())
    GROUP BY RobotId, AccionTomada, FechaBalanceo
) HB ON R.RobotId = HB.RobotId
LEFT JOIN (
    SELECT 
        RobotId,
        COUNT(*) AS EjecucionesActivas
    FROM Ejecuciones
    WHERE Estado IN ('DEPLOYED', 'RUNNING', 'QUEUED', 'PENDING_EXECUTION', 'UPDATE', 'RUN_PAUSED')
    GROUP BY RobotId
) EjecActivas ON R.RobotId = EjecActivas.RobotId
LEFT JOIN Pools P ON R.PoolId = P.PoolId
WHERE R.Activo = 1;

GO
/****** Object:  Table [dbo].[Equipos] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
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
GO
/****** Object:  View [dbo].[AsignacionesView] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE VIEW [dbo].[AsignacionesView]
AS
SELECT R.Robot, EQ.Equipo, A.RobotId, A.EquipoId, A.EsProgramado, A.Reservado
FROM     dbo.Asignaciones AS A INNER JOIN
                  dbo.Equipos AS EQ ON A.EquipoId = EQ.EquipoId INNER JOIN
                  dbo.Robots AS R ON A.RobotId = R.RobotId
GO
/****** Object:  View [dbo].[EjecucionesActivas] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO


CREATE VIEW [dbo].[EjecucionesActivas]
AS
SELECT TOP (100) PERCENT 
r.Robot, r.RobotId, CASE WHEN (r.EsOnline = 1) THEN 'ONLINE' ELSE 'PROGRAMADO' END AS Tipo, 
	eq.Equipo, eq.EquipoId, eq.UserId, eq.UserName, e.DeploymentId, e.Hora, e.FechaInicio, e.FechaFin, 
	e.Estado, e.FechaActualizacion, e.IntentosConciliadorFallidos, e.CallbackInfo, r.Descripcion
FROM     dbo.Ejecuciones AS E INNER JOIN
                  dbo.Equipos AS EQ ON E.EquipoId = EQ.EquipoId INNER JOIN
                  dbo.Robots AS R ON E.RobotId = R.RobotId
WHERE  (
    -- 1. Estados activos conocidos
    E.Estado IN ('PENDING_EXECUTION', 'DEPLOYED', 'RUNNING', 'UPDATE', 'RUN_PAUSED', 'QUEUED')
    OR
    -- 2. Estado UNKNOWN que aún se considera activo
    (E.Estado = 'UNKNOWN' AND E.FechaUltimoUNKNOWN > DATEADD(HOUR, -2, GETDATE()))
)
ORDER BY e.EjecucionId DESC
GO
/****** Object:  View [dbo].[AnalisisRendimientoCallbacks] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Vista: AnalisisRendimientoCallbacks
-- Descripción: Analiza el rendimiento del sistema de callbacks vs conciliador
--              basándose en los patrones de datos de la tabla Ejecuciones
-- Autor: Sistema SAM
-- Fecha: 2025-09-25
-- =============================================

CREATE VIEW [dbo].[AnalisisRendimientoCallbacks] AS
WITH EjecucionesAnalizadas AS (
    SELECT 
        EjecucionId,
        DeploymentId,
        RobotId,
        EquipoId,
        UserId,
        FechaInicio,
        FechaFin,
        Estado,
        FechaActualizacion,
        IntentosConciliadorFallidos,
        CallbackInfo,
        
        -- CLASIFICACIÓN DEL MECANISMO DE FINALIZACIÓN
        CASE 
            -- Callback exitoso: Estado final + CallbackInfo presente
            WHEN Estado IN ('COMPLETED', 'RUN_COMPLETED', 'RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED') 
                 AND CallbackInfo IS NOT NULL 
                 AND CallbackInfo != ''
            THEN 'CALLBACK_EXITOSO'
            
            -- Conciliador exitoso: Estado final + Sin CallbackInfo + Intentos fallidos > 0
            WHEN Estado IN ('COMPLETED', 'RUN_COMPLETED', 'RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED') 
                 AND (CallbackInfo IS NULL OR CallbackInfo = '')
                 AND IntentosConciliadorFallidos > 0
            THEN 'CONCILIADOR_EXITOSO'
            
            -- Estado UNKNOWN: Conciliador agotó intentos
            WHEN Estado = 'UNKNOWN'
            THEN 'CONCILIADOR_AGOTADO'
            
            -- Ejecución aún activa
            WHEN Estado IN ('DEPLOYED', 'RUNNING', 'QUEUED', 'PENDING_EXECUTION', 'UPDATE', 'RUN_PAUSED')
            THEN 'ACTIVA'
            
            -- Casos edge: Estado final sin CallbackInfo y sin intentos fallidos (posible conciliador inmediato)
            ELSE 'CONCILIADOR_INMEDIATO'
        END AS MecanismoFinalizacion,
        
        -- MÉTRICAS DE DURACIÓN
        CASE 
            WHEN FechaInicio IS NOT NULL AND FechaFin IS NOT NULL
            THEN DATEDIFF(MINUTE, FechaInicio, FechaFin)
            ELSE NULL
        END AS DuracionEjecucionMinutos,
        
        -- MÉTRICAS DE LATENCIA DEL SISTEMA
        CASE 
            WHEN FechaFin IS NOT NULL AND FechaActualizacion IS NOT NULL
            THEN DATEDIFF(MINUTE, FechaFin, FechaActualizacion)
            ELSE NULL
        END AS LatenciaActualizacionMinutos,
        
        -- INDICADORES DE PROBLEMAS
        CASE 
            WHEN FechaFin IS NOT NULL AND FechaActualizacion IS NOT NULL 
                 AND DATEDIFF(MINUTE, FechaFin, FechaActualizacion) > 15
            THEN 1 
            ELSE 0 
        END AS CallbackFallidoIndicador,
        
        CASE 
            WHEN IntentosConciliadorFallidos >= 3 
            THEN 1 
            ELSE 0 
        END AS ConciliadorProblemaIndicador,
        
        -- CLASIFICACIÓN DE RENDIMIENTO
        CASE 
            WHEN FechaFin IS NOT NULL AND FechaActualizacion IS NOT NULL
            THEN
                CASE 
                    WHEN DATEDIFF(MINUTE, FechaFin, FechaActualizacion) <= 2 THEN 'EXCELENTE'
                    WHEN DATEDIFF(MINUTE, FechaFin, FechaActualizacion) <= 5 THEN 'BUENO'
                    WHEN DATEDIFF(MINUTE, FechaFin, FechaActualizacion) <= 15 THEN 'REGULAR'
                    ELSE 'DEFICIENTE'
                END
            ELSE 'NO_APLICABLE'
        END AS ClasificacionRendimiento
        
    FROM Ejecuciones
    WHERE FechaInicio >= DATEADD(DAY, -30, GETDATE()) -- Últimos 30 días por defecto
)

SELECT 
    EjecucionId,
    DeploymentId,
    RobotId,
    EquipoId,
    UserId,
    FechaInicio,
    FechaFin,
    Estado,
    FechaActualizacion,
    IntentosConciliadorFallidos,
    CallbackInfo,
    MecanismoFinalizacion,
    DuracionEjecucionMinutos,
    LatenciaActualizacionMinutos,
    CallbackFallidoIndicador,
    ConciliadorProblemaIndicador,
    ClasificacionRendimiento,
    
    -- MÉTRICAS ADICIONALES CALCULADAS
    CASE 
        WHEN MecanismoFinalizacion = 'CALLBACK_EXITOSO' THEN 1 
        ELSE 0 
    END AS EsCallbackExitoso,
    
    CASE 
        WHEN MecanismoFinalizacion IN ('CONCILIADOR_EXITOSO', 'CONCILIADOR_INMEDIATO') THEN 1 
        ELSE 0 
    END AS EsConciliadorExitoso,
    
    CASE 
        WHEN MecanismoFinalizacion = 'CONCILIADOR_AGOTADO' THEN 1 
        ELSE 0 
    END AS EsConciliadorAgotado,
    
    -- INDICADORES DE SALUD DEL SISTEMA
    CASE 
        WHEN Estado IN ('COMPLETED', 'RUN_COMPLETED') THEN 1 
        ELSE 0 
    END AS EjecucionExitosa,
    
    CASE 
        WHEN Estado IN ('RUN_FAILED', 'DEPLOY_FAILED', 'RUN_ABORTED') THEN 1 
        ELSE 0 
    END AS EjecucionFallida

FROM EjecucionesAnalizadas;
GO
/****** Object:  View [dbo].[EjecucionesFinalizadas] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO


CREATE VIEW [dbo].[EjecucionesFinalizadas]
AS
SELECT TOP (100) PERCENT 
	r.Robot, r.RobotId, CASE WHEN (r.EsOnline = 1) THEN 'ONLINE' ELSE 'PROGRAMADO' END AS Tipo, 
	eq.Equipo, eq.EquipoId, eq.UserId, eq.UserName, e.DeploymentId, e.Hora, e.FechaInicio, e.FechaFin, 
	e.Estado, e.FechaActualizacion, e.IntentosConciliadorFallidos, e.CallbackInfo, r.Descripcion
FROM     dbo.Ejecuciones AS e INNER JOIN
                  dbo.Equipos AS eq ON e.EquipoId = eq.EquipoId INNER JOIN
                  dbo.Robots AS r ON e.RobotId = r.RobotId
WHERE
    -- 1. No es un estado activo conocido
    (e.Estado NOT IN (
        'DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 
        'RUNNING', 'UPDATE', 'RUN_PAUSED'
    ))
    AND
    -- 2. Y tampoco es un 'UNKNOWN' reciente
    (
        NOT (E.Estado = 'UNKNOWN' AND E.FechaUltimoUNKNOWN > DATEADD(HOUR, -2, GETDATE()))
    )
ORDER BY e.EjecucionId DESC
GO
/****** Object:  Table [dbo].[ConfiguracionSistema] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[ConfiguracionSistema](
	[Clave] [varchar](50) NOT NULL,
	[Valor] [varchar](255) NULL,
	[Descripcion] [varchar](500) NULL,
	[FechaActualizacion] [datetime] NULL,
PRIMARY KEY CLUSTERED 
(
	[Clave] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Ejecuciones_Historico] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
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
GO
/****** Object:  Table [dbo].[ErrorLog] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[ErrorLog](
	[ErrorLogId] [int] IDENTITY(1,1) NOT NULL,
	[FechaHora] [datetime2](0) NOT NULL,
	[Usuario] [nvarchar](100) NOT NULL,
	[SPNombre] [nvarchar](100) NOT NULL,
	[ErrorMensaje] [nvarchar](max) NOT NULL,
	[Parametros] [nvarchar](max) NULL,
 CONSTRAINT [PK_ErrorLog] PRIMARY KEY CLUSTERED 
(
	[ErrorLogId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[MapeoRobots] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
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
GO
ALTER TABLE [dbo].[Asignaciones] ADD  CONSTRAINT [DF_Asignaciones_EsProgramado]  DEFAULT ((0)) FOR [EsProgramado]
GO
ALTER TABLE [dbo].[Asignaciones] ADD  CONSTRAINT [DF_Asignaciones_Reservado]  DEFAULT ((0)) FOR [Reservado]
GO
ALTER TABLE [dbo].[Asignaciones] ADD  CONSTRAINT [DF_Asignaciones_FechaAsignacion]  DEFAULT (getdate()) FOR [FechaAsignacion]
GO
ALTER TABLE [dbo].[ConfiguracionSistema] ADD  DEFAULT (getdate()) FOR [FechaActualizacion]
GO
ALTER TABLE [dbo].[Ejecuciones] ADD  CONSTRAINT [DF_Ejecuciones_FechaInicio]  DEFAULT (getdate()) FOR [FechaInicio]
GO
ALTER TABLE [dbo].[Ejecuciones] ADD  CONSTRAINT [DF_Ejecuciones_IntentosConciliadorFallidos]  DEFAULT ((0)) FOR [IntentosConciliadorFallidos]
GO
ALTER TABLE [dbo].[Equipos] ADD  CONSTRAINT [DF_Equipos_Activo_SAM]  DEFAULT ((1)) FOR [Activo_SAM]
GO
ALTER TABLE [dbo].[Equipos] ADD  CONSTRAINT [DF_Equipos_PermiteBalanceoDinamico]  DEFAULT ((0)) FOR [PermiteBalanceoDinamico]
GO
ALTER TABLE [dbo].[ErrorLog] ADD  CONSTRAINT [DF_ErrorLog_FechaHora]  DEFAULT (getdate()) FOR [FechaHora]
GO
ALTER TABLE [dbo].[HistoricoBalanceo] ADD  DEFAULT (getdate()) FOR [FechaBalanceo]
GO
ALTER TABLE [dbo].[MapeoRobots] ADD  DEFAULT (getdate()) FOR [FechaCreacion]
GO
ALTER TABLE [dbo].[Pools] ADD  DEFAULT ((1)) FOR [Activo]
GO
ALTER TABLE [dbo].[Pools] ADD  DEFAULT (getdate()) FOR [FechaCreacion]
GO
ALTER TABLE [dbo].[Programaciones] ADD  CONSTRAINT [DF__Programac__Toler__208CD6FA]  DEFAULT ((60)) FOR [Tolerancia]
GO
ALTER TABLE [dbo].[Robots] ADD  CONSTRAINT [DF_Robots_Activo]  DEFAULT ((1)) FOR [Activo]
GO
ALTER TABLE [dbo].[Robots] ADD  CONSTRAINT [DF_Robots_EsOnline]  DEFAULT ((0)) FOR [EsOnline]
GO
ALTER TABLE [dbo].[Robots] ADD  CONSTRAINT [DF_Robots_MinEquipos]  DEFAULT ((1)) FOR [MinEquipos]
GO
ALTER TABLE [dbo].[Robots] ADD  CONSTRAINT [DF_Robots_MaxEquipos]  DEFAULT ((-1)) FOR [MaxEquipos]
GO
ALTER TABLE [dbo].[Robots] ADD  CONSTRAINT [DF_Robots_PrioridadBalanceo]  DEFAULT ((100)) FOR [PrioridadBalanceo]
GO
ALTER TABLE [dbo].[Robots] ADD  CONSTRAINT [DF_Robots_TicketsPorEquipoAdicional]  DEFAULT ((10)) FOR [TicketsPorEquipoAdicional]
GO
ALTER TABLE [dbo].[Equipos]  WITH CHECK ADD  CONSTRAINT [FK_Equipos_Pools] FOREIGN KEY([PoolId])
REFERENCES [dbo].[Pools] ([PoolId])
ON UPDATE CASCADE
ON DELETE SET NULL
GO
ALTER TABLE [dbo].[Equipos] CHECK CONSTRAINT [FK_Equipos_Pools]
GO
ALTER TABLE [dbo].[HistoricoBalanceo]  WITH CHECK ADD  CONSTRAINT [FK_HistoricoBalanceo_Robots] FOREIGN KEY([RobotId])
REFERENCES [dbo].[Robots] ([RobotId])
GO
ALTER TABLE [dbo].[HistoricoBalanceo] CHECK CONSTRAINT [FK_HistoricoBalanceo_Robots]
GO
ALTER TABLE [dbo].[MapeoRobots]  WITH CHECK ADD  CONSTRAINT [FK_MapeoRobots_Robots] FOREIGN KEY([RobotId])
REFERENCES [dbo].[Robots] ([RobotId])
GO
ALTER TABLE [dbo].[MapeoRobots] CHECK CONSTRAINT [FK_MapeoRobots_Robots]
GO
ALTER TABLE [dbo].[Robots]  WITH CHECK ADD  CONSTRAINT [FK_Robots_Pools] FOREIGN KEY([PoolId])
REFERENCES [dbo].[Pools] ([PoolId])
ON DELETE SET NULL
GO
ALTER TABLE [dbo].[Robots] CHECK CONSTRAINT [FK_Robots_Pools]
GO
ALTER TABLE [dbo].[Programaciones]  WITH CHECK ADD  CONSTRAINT [CK__Programac__TipoP__1F98B2C1] CHECK  (([TipoProgramacion]='Especifica' OR [TipoProgramacion]='Mensual' OR [TipoProgramacion]='Semanal' OR [TipoProgramacion]='Diaria'))
GO
ALTER TABLE [dbo].[Programaciones] CHECK CONSTRAINT [CK__Programac__TipoP__1F98B2C1]
GO
/****** Object:  StoredProcedure [dbo].[ActualizarEquiposProgramacion] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[ActualizarEquiposProgramacion]
    @ProgramacionId INT,
    @EquiposIds dbo.IdListType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRANSACTION;
    
    BEGIN TRY
        -- 1. Obtener el RobotId asociado a esta programación
        DECLARE @RobotId INT;
        SELECT @RobotId = RobotId FROM dbo.Programaciones WHERE ProgramacionId = @ProgramacionId;

        -- 2. Eliminar asignaciones previas de esta programación
        -- (Limpiamos la tabla Asignaciones para este ID de programación)
        DELETE FROM dbo.Asignaciones 
        WHERE ProgramacionId = @ProgramacionId;

        -- 3. Insertar las nuevas asignaciones
        INSERT INTO dbo.Asignaciones (RobotId, EquipoId, EsProgramado, Reservado, FechaAsignacion, ProgramacionId, AsignadoPor)
        SELECT 
            @RobotId,
            ID, 
            1, -- EsProgramado
            0, -- Reservado (asumimos 0 para programación estándar)
            GETDATE(), 
            @ProgramacionId,
            'SAM_WEB'
        FROM @EquiposIds;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
            
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[ActualizarEstadoEquipo] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE PROCEDURE [dbo].[ActualizarEstadoEquipo]
    @EquipoId INT,
    @Campo NVARCHAR(50),
    @Valor BIT
AS
BEGIN
    SET NOCOUNT ON;

    IF @Campo NOT IN ('Activo_SAM', 'PermiteBalanceoDinamico')
    BEGIN
        RAISERROR ('El campo especificado no es válido para esta operación.', 16, 1);
        RETURN;
    END

    -- 1. Verificar si el equipo existe
    IF NOT EXISTS (SELECT 1 FROM dbo.Equipos WHERE EquipoId = @EquipoId)
    BEGIN
        RAISERROR ('Equipo no encontrado.', 16, 1);
        RETURN;
    END

    -- 2. Verificar si el valor ya es el mismo
    DECLARE @SQL_CHECK NVARCHAR(MAX);
    SET @SQL_CHECK = 'IF EXISTS (SELECT 1 FROM dbo.Equipos WHERE EquipoId = @p_EquipoId AND ' + QUOTENAME(@Campo) + ' = @p_Valor) RAISERROR(''Sin cambios: el equipo ya tiene ese valor.'', 16, 2);';
    EXEC sp_executesql @SQL_CHECK, N'@p_Valor BIT, @p_EquipoId INT', @p_Valor = @Valor, @p_EquipoId = @EquipoId;

    -- 3. Actualizar
    DECLARE @SQL_UPDATE NVARCHAR(MAX);
    SET @SQL_UPDATE = 'UPDATE dbo.Equipos SET ' + QUOTENAME(@Campo) + ' = @p_Valor WHERE EquipoId = @p_EquipoId';
    EXEC sp_executesql @SQL_UPDATE, N'@p_Valor BIT, @p_EquipoId INT', @p_Valor = @Valor, @p_EquipoId = @EquipoId;
END
GO
/****** Object:  StoredProcedure [dbo].[ActualizarPool] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE PROCEDURE [dbo].[ActualizarPool]
    @PoolId INT,
    @Nombre NVARCHAR(100),
    @Descripcion NVARCHAR(500)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- 1. Validar que el PoolId exista. Si no, lanzar un error claro.
    IF NOT EXISTS (SELECT 1 FROM dbo.Pools WHERE PoolId = @PoolId)
    BEGIN
        RAISERROR ('No se encontró un pool con el ID %d.', 16, 1, @PoolId);
        RETURN;
    END

    -- 2. Validar que el nuevo nombre no esté en uso por OTRO pool.
    IF EXISTS (SELECT 1 FROM dbo.Pools WHERE Nombre = @Nombre AND PoolId <> @PoolId)
    BEGIN
        RAISERROR ('El nombre "%s" ya está en uso por otro pool.', 16, 1, @Nombre);
        RETURN;
    END

    -- 3. Simplemente ejecutar el UPDATE. No necesitamos TRY/CATCH aquí
    --    porque XACT_ABORT ya maneja los errores, y las validaciones previenen
    --    los casos más comunes.
    UPDATE dbo.Pools
    SET
        Nombre = @Nombre,
        Descripcion = @Descripcion,
        FechaModificacion = GETDATE()
    WHERE
        PoolId = @PoolId;
END
GO
/****** Object:  StoredProcedure [dbo].[ActualizarProgramacionCompleta] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[ActualizarProgramacionCompleta]
    @ProgramacionId INT,
    @RobotId INT,
    @TipoProgramacion NVARCHAR(20),
    @HoraInicio TIME,
    @DiaSemana NVARCHAR(20) = NULL,
    @DiaDelMes INT = NULL,
    @FechaEspecifica DATE = NULL,
    @Tolerancia INT = NULL,
    @Equipos NVARCHAR(MAX), -- Equipos como nombres separados por coma
    @UsuarioModifica NVARCHAR(50) = 'WebApp'
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @ErrorMessage NVARCHAR(4000);
    DECLARE @ErrorSeverity INT;
    DECLARE @ErrorState INT;
    DECLARE @Robot NVARCHAR(100);

    -- Tabla temporal para almacenar los IDs de equipos válidos
    CREATE TABLE #NuevosEquiposProgramados (EquipoId INT PRIMARY KEY);
    -- Tabla temporal para almacenar los equipos que se están desprogramando
    CREATE TABLE #EquiposDesprogramados (EquipoId INT PRIMARY KEY);

    BEGIN TRY
        SELECT @Robot = Robot FROM dbo.Robots WHERE RobotId = @RobotId;
        BEGIN TRANSACTION;

        -- 1. Actualizar datos de la programación
        UPDATE dbo.Programaciones
        SET TipoProgramacion = @TipoProgramacion,
            HoraInicio = @HoraInicio,
            DiasSemana = CASE WHEN @TipoProgramacion = 'Semanal' THEN @DiaSemana ELSE NULL END,
            DiaDelMes = CASE WHEN @TipoProgramacion = 'Mensual' THEN @DiaDelMes ELSE NULL END,
            FechaEspecifica = CASE WHEN @TipoProgramacion = 'Especifica' THEN @FechaEspecifica ELSE NULL END,
            Tolerancia = @Tolerancia,
            FechaModificacion = GETDATE()
        WHERE ProgramacionId = @ProgramacionId AND RobotId = @RobotId;

        IF @@ROWCOUNT = 0 BEGIN RAISERROR('Programación no encontrada.', 16, 1); RETURN; END

        -- 2. Poblar #NuevosEquiposProgramados
        INSERT INTO #NuevosEquiposProgramados (EquipoId)
        SELECT E.EquipoId
        FROM STRING_SPLIT(@Equipos, ',') AS S
        JOIN dbo.Equipos E ON LTRIM(RTRIM(S.value)) = E.Equipo
        WHERE E.Activo_SAM = 1;

        -- (Opcional) Mostrar advertencias
        SELECT 'Warning: Equipo "' + LTRIM(RTRIM(S.value)) + '" no encontrado o inactivo.' AS Advertencia
        FROM STRING_SPLIT(@Equipos, ',') S
        WHERE NOT EXISTS (SELECT 1 FROM dbo.Equipos E WHERE E.Equipo = LTRIM(RTRIM(S.value)) AND E.Activo_SAM = 1);

        -- 3. Desprogramar equipos
        -- Guardamos los equipos que estamos quitando de ESTA programación
        INSERT INTO #EquiposDesprogramados (EquipoId)
        SELECT EquipoId
        FROM dbo.Asignaciones
        WHERE ProgramacionId = @ProgramacionId
          AND EsProgramado = 1
          AND RobotId = @RobotId
          AND EquipoId NOT IN (SELECT EquipoId FROM #NuevosEquiposProgramados);
        
        -- Ahora sí, borramos la asignación
        DELETE FROM dbo.Asignaciones
        WHERE ProgramacionId = @ProgramacionId
          AND EsProgramado = 1
          AND RobotId = @RobotId
          AND EquipoId IN (SELECT EquipoId FROM #EquiposDesprogramados);
        
        -- 4. Programar los nuevos equipos (Sin cambios, la lógica MERGE es correcta)
        MERGE dbo.Asignaciones AS Target
        USING #NuevosEquiposProgramados AS Source
        ON (Target.EquipoId = Source.EquipoId 
            AND Target.RobotId = @RobotId 
            AND Target.ProgramacionId = @ProgramacionId)
        WHEN MATCHED THEN
            UPDATE SET
                EsProgramado = 1,
                Reservado = 0,
                AsignadoPor = @UsuarioModifica,
                FechaAsignacion = GETDATE()
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (RobotId, EquipoId, EsProgramado, ProgramacionId, Reservado, AsignadoPor, FechaAsignacion)
            VALUES (@RobotId, Source.EquipoId, 1, @ProgramacionId, 0, @UsuarioModifica, GETDATE());

        -- 5. Habilitar/Deshabilitar balanceo dinámico
        -- Desactivar balanceo para equipos recién programados
        UPDATE E
        SET PermiteBalanceoDinamico = 0
        FROM dbo.Equipos E
        JOIN #NuevosEquiposProgramados NEP ON E.EquipoId = NEP.EquipoId;
        
        -- Habilitar balanceo dinámico SÓLO para los equipos que acabamos de
        -- desprogramar Y que no tengan NINGUNA OTRA asignación (programada O reservada).
        UPDATE E
        SET E.PermiteBalanceoDinamico = 1
        FROM dbo.Equipos E
        JOIN #EquiposDesprogramados ED ON E.EquipoId = ED.EquipoId -- Solo afecta a los que quitamos
        WHERE NOT EXISTS (
              SELECT 1 FROM dbo.Asignaciones a2
              WHERE a2.EquipoId = E.EquipoId 
                AND (a2.EsProgramado = 1 OR a2.Reservado = 1) -- Comprueba AMBOS flags
          );

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;

        SET @ErrorMessage = ERROR_MESSAGE();
        SET @ErrorSeverity = ERROR_SEVERITY();
        SET @ErrorState = ERROR_STATE();
        DECLARE @Parametros NVARCHAR(MAX);
        SET @Parametros = 
            '@Robot = ' + ISNULL(@Robot, 'NULL') + 
            ', @Equipos = ' + ISNULL(@Equipos, 'NULL') + 
            ', @HoraInicio = ' + ISNULL(CONVERT(NVARCHAR(8), @HoraInicio, 108), 'NULL') + 
            ', @Tolerancia = ' + ISNULL(CAST(@Tolerancia AS NVARCHAR(10)), 'NULL');
        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'ActualizarProgramacionCompleta', @ErrorMessage, @Parametros);
        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH

    IF OBJECT_ID('tempdb..#NuevosEquiposProgramados') IS NOT NULL
        DROP TABLE #NuevosEquiposProgramados;
    IF OBJECT_ID('tempdb..#EquiposDesprogramados') IS NOT NULL
        DROP TABLE #EquiposDesprogramados;
END
GO
/****** Object:  StoredProcedure [dbo].[ActualizarProgramacionSimple] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[ActualizarProgramacionSimple]
    @ProgramacionId INT,
    @TipoProgramacion NVARCHAR(20),
    @HoraInicio TIME,
    @DiasSemana NVARCHAR(20) = NULL,
    @DiaDelMes INT = NULL,
    @FechaEspecifica DATE = NULL,
    @Tolerancia INT = NULL,
    @Activo BIT
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE dbo.Programaciones
    SET 
        TipoProgramacion = @TipoProgramacion,
        HoraInicio = @HoraInicio,
        DiasSemana = CASE WHEN @TipoProgramacion = 'Semanal' THEN @DiasSemana ELSE NULL END,
        DiaDelMes = CASE WHEN @TipoProgramacion = 'Mensual' THEN @DiaDelMes ELSE NULL END,
        FechaEspecifica = CASE WHEN @TipoProgramacion = 'Especifica' THEN @FechaEspecifica ELSE NULL END,
        Tolerancia = @Tolerancia,
        Activo = @Activo,
        FechaModificacion = GETDATE()
    WHERE
        ProgramacionId = @ProgramacionId;
END
GO
/****** Object:  StoredProcedure [dbo].[AnalisisDispersionRobot] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE   PROCEDURE [dbo].[AnalisisDispersionRobot]
    @pRobot VARCHAR(100),
    @pFecha DATE = NULL,
    @pTop   INT  = NULL,
    @pModo  CHAR(1) = 'I' -- I = Inicio→Inicio (dispersión), F = Fin→Inicio (tiempo muerto)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @RobotId INT;

    -- Resolver RobotId a partir del nombre
    SELECT @RobotId = RobotId
    FROM   dbo.Robots
    WHERE  Robot = @pRobot;

    IF @RobotId IS NULL
    BEGIN
        RAISERROR('El robot ''%s'' no existe en la tabla maestra.', 16, 1, @pRobot);
        RETURN;
    END;

    /* 1. CTE base de ejecuciones */
    ;WITH Ejecs AS
    (
        SELECT  EjecucionID,
                UserId,
                EquipoId,
                RobotId,
                Estado,
                FechaInicio,
                FechaFin, -- <<< Se necesita el fin para el modo 'F'
                ROW_NUMBER() OVER (ORDER BY FechaInicio DESC) AS RN
        FROM    dbo.Ejecuciones
        WHERE   RobotId = @RobotId
          AND   (Estado = 'RUN_COMPLETED' OR Estado = 'COMPLETED')
          AND   (@pFecha IS NULL OR CAST(FechaInicio AS DATE) = @pFecha)
    ),
    Filtradas AS
    (
        SELECT * FROM Ejecs WHERE @pTop IS NULL OR RN <= @pTop
    ),
    ConDelta AS
    (
        SELECT *,
               /* ------- Lógica para elegir el tipo de delta ------- */
               CASE @pModo
                   WHEN 'I' THEN -- Modo 'I': Inicio -> Inicio (dispersión entre arranques)
                        DATEDIFF(SECOND,
                                 LAG(FechaInicio) OVER (PARTITION BY UserId ORDER BY FechaInicio),
                                 FechaInicio)
                   WHEN 'F' THEN -- Modo 'F': Fin -> Inicio (tiempo muerto real)
                        DATEDIFF(SECOND,
                                 LAG(FechaFin) OVER (PARTITION BY UserId ORDER BY FechaInicio),
                                 FechaInicio)
               END AS DeltaSec
        FROM Filtradas
    )
    SELECT * INTO #ConDelta FROM ConDelta;

    /* 2. RESUMEN: agrupado por equipo + robot */
    SELECT  
            r.Robot,
            e.Equipo,
            COUNT(*)            AS Ejecuciones,
            MIN(cd.DeltaSec)    AS DeltaMin_Sec,
            MAX(cd.DeltaSec)    AS DeltaMax_Sec,
            AVG(cd.DeltaSec*1.0)   AS DeltaAvg_Sec,
            STDEV(cd.DeltaSec*1.0) AS DeltaDesv_Sec,
            @pModo              AS ModoCalculo
    INTO    #Resumen
    FROM    #ConDelta cd
    INNER JOIN dbo.Equipos e ON e.EquipoId = cd.EquipoId
    INNER JOIN dbo.Robots r ON r.RobotId = cd.RobotId
    WHERE   cd.DeltaSec IS NOT NULL
    GROUP BY r.Robot, e.Equipo;

	SELECT * FROM #Resumen ORDER BY Robot, Equipo;

    /* 3. DETALLE */
    SELECT  
            cd.EjecucionID,
            cd.UserId,
            cd.EquipoId,
            e.Equipo,
            cd.RobotId,
            r.Robot,
            cd.Estado,
            cd.FechaInicio,
            cd.FechaFin,
            cd.DeltaSec,
            cd.DeltaSec / 60.0 AS DeltaMin,
            @pModo AS ModoCalculo
    FROM    #ConDelta cd
    INNER JOIN dbo.Equipos e ON e.EquipoId = cd.EquipoId
    INNER JOIN dbo.Robots r ON r.RobotId = cd.RobotId
    WHERE   cd.DeltaSec IS NOT NULL
    ORDER BY e.Equipo, cd.FechaInicio;

    DROP TABLE #Resumen;
    DROP TABLE #ConDelta;
END;
GO
/****** Object:  StoredProcedure [dbo].[AnalisisTiemposEjecucionRobots] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- Crear o actualizar el Stored Procedure para análisis de tiempos de ejecución por robot
CREATE   PROCEDURE [dbo].[AnalisisTiemposEjecucionRobots]
    @ExcluirPorcentajeInferior DECIMAL(3,2) = 0.15,  -- 15% por defecto
    @ExcluirPorcentajeSuperior DECIMAL(3,2) = 0.85,  -- 85% por defecto
    @IncluirSoloCompletadas BIT = 1,                   -- 1 = Solo completadas, 0 = Todos los estados
	@MesesHaciaAtras INT = 1 
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Validar parámetros
    IF @ExcluirPorcentajeInferior >= @ExcluirPorcentajeSuperior
    BEGIN
        RAISERROR('El porcentaje inferior debe ser menor que el superior', 16, 1);
        RETURN;
    END;
    
    -- Análisis de tiempos de ejecución por robot excluyendo extremos
    WITH TiemposEjecucion AS (
        SELECT 
            e.RobotId,
            e.DeploymentId,
            e.FechaInicio,
            e.FechaFin,
            e.Estado,
            -- Calcular duración en minutos
            DATEDIFF(MINUTE, e.FechaInicio, e.FechaFin) AS DuracionMinutos,
            -- Calcular duración en segundos para mayor precisión
            DATEDIFF(SECOND, e.FechaInicio, e.FechaFin) AS DuracionSegundos
        FROM Ejecuciones e
        WHERE e.FechaInicio IS NOT NULL 
            AND e.FechaFin IS NOT NULL
			AND e.FechaInicio >= DATEADD(MONTH, -@MesesHaciaAtras, GETDATE())
            AND (@IncluirSoloCompletadas = 0 OR e.Estado IN ('COMPLETED', 'RUN_COMPLETED'))
            AND DATEDIFF(SECOND, e.FechaInicio, e.FechaFin) > 0  -- Duración positiva
    ),
    TiemposConRanking AS (
        SELECT 
            RobotId,
            DuracionMinutos,
            DuracionSegundos,
            -- Calcular posición y total de registros por robot
            ROW_NUMBER() OVER (PARTITION BY RobotId ORDER BY DuracionSegundos) AS Posicion,
            COUNT(*) OVER (PARTITION BY RobotId) AS TotalRegistros
        FROM TiemposEjecucion
    ),
    TiemposFiltrados AS (
        SELECT 
            RobotId,
            DuracionMinutos,
            DuracionSegundos,
            Posicion,
            TotalRegistros
        FROM TiemposConRanking
        WHERE Posicion > (TotalRegistros * @ExcluirPorcentajeInferior)
            AND Posicion <= (TotalRegistros * @ExcluirPorcentajeSuperior)
    )
    SELECT 
        tf.RobotId,
        r.Robot,  -- Nombre del robot desde la tabla Robots
        r.EsOnline,  -- Si el robot está online (bit)
        COUNT(*) AS EjecucionesAnalizadas,
        -- Mostrar también el total original para comparación
        MAX(tf.TotalRegistros) AS TotalEjecucionesOriginales,
        -- Porcentaje de ejecuciones incluidas en el análisis
        CAST((COUNT(*) * 100.0 / MAX(tf.TotalRegistros)) AS DECIMAL(5,2)) AS PorcentajeIncluido,
        -- Tiempo promedio POR EJECUCIÓN (sin extremos)
        AVG(CAST(tf.DuracionMinutos AS FLOAT)) AS TiempoPromedioPorEjecucionMinutos,
        -- Tiempo total acumulado de todas las ejecuciones analizadas
        SUM(CAST(tf.DuracionMinutos AS FLOAT)) AS TiempoTotalAcumuladoMinutos,
        -- Tiempo promedio en segundos
        AVG(CAST(tf.DuracionSegundos AS FLOAT)) AS TiempoPromedioPorEjecucionSegundos,
        -- Tiempo máximo y mínimo (después del filtro)
        MAX(tf.DuracionMinutos) AS TiempoMaximoPorEjecucionMinutos,
        MIN(tf.DuracionMinutos) AS TiempoMinimoPorEjecucionMinutos,
        -- Formatear tiempo promedio como HH:MM:SS
        CONVERT(VARCHAR(8), DATEADD(SECOND, AVG(CAST(tf.DuracionSegundos AS FLOAT)), 0), 108) AS TiempoPromedioPorEjecucionFormateado,
        -- Formatear tiempo total acumulado (máximo 24 horas, sino mostrará días)
        CASE 
            WHEN SUM(CAST(tf.DuracionSegundos AS FLOAT)) < 86400 THEN 
                CONVERT(VARCHAR(8), DATEADD(SECOND, SUM(CAST(tf.DuracionSegundos AS FLOAT)), 0), 108)
            ELSE 
                CONCAT(
                    CAST(SUM(CAST(tf.DuracionSegundos AS FLOAT)) / 86400 AS INT), 'd ',
                    CONVERT(VARCHAR(8), DATEADD(SECOND, CAST(SUM(CAST(tf.DuracionSegundos AS FLOAT)) AS BIGINT) % 86400, 0), 108)
                )
        END AS TiempoTotalAcumuladoFormateado,
        -- Mostrar el rango de percentiles incluidos
        CONCAT('P', CAST(@ExcluirPorcentajeInferior * 100 AS INT), ' - P', CAST(@ExcluirPorcentajeSuperior * 100 AS INT)) AS RangoPercentiles,
        -- Información adicional de performance
        STDEV(CAST(tf.DuracionSegundos AS FLOAT)) AS DesviacionEstandarSegundos,
        -- Fecha del análisis
        GETDATE() AS FechaAnalisis
    FROM TiemposFiltrados tf 
    INNER JOIN Robots r ON r.RobotId = tf.RobotId
    GROUP BY tf.RobotId, r.Robot, r.EsOnline
    ORDER BY TiempoPromedioPorEjecucionSegundos DESC;
END;
GO
/****** Object:  StoredProcedure [dbo].[AsignarRecursosAPool] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO


-- 2. STORED PROCEDURE PARA ASIGNAR RECURSOS (VERSIÓN CORREGIDA)
CREATE PROCEDURE [dbo].[AsignarRecursosAPool]
    @PoolId INT,
    @RobotIds dbo.IdListType READONLY,
    @EquipoIds dbo.IdListType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF NOT EXISTS (SELECT 1 FROM dbo.Pools WHERE PoolId = @PoolId)
    BEGIN
        RAISERROR ('No se encontró un pool con el ID %d.', 16, 1, @PoolId);
        RETURN;
    END

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Desasignar recursos que actualmente pertenecen a este pool
        UPDATE dbo.Robots SET PoolId = NULL WHERE PoolId = @PoolId;
        UPDATE dbo.Equipos SET PoolId = NULL WHERE PoolId = @PoolId;

        -- Asignar los nuevos recursos
        UPDATE R SET R.PoolId = @PoolId FROM dbo.Robots R INNER JOIN @RobotIds TVP ON R.RobotId = TVP.ID;
        UPDATE E SET E.PoolId = @PoolId FROM dbo.Equipos E INNER JOIN @EquipoIds TVP ON E.EquipoId = TVP.ID;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;

        -- Log del error
        DECLARE @ErrorMessage_ASG NVARCHAR(4000) = ERROR_MESSAGE();
        -- No podemos serializar fácilmente los TVP, así que lo indicamos en el log.
        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'dbo.AsignarRecursosAPool', @ErrorMessage_ASG, CONCAT('@PoolId=', @PoolId, ', @RobotIds/EquipoIds: (TVP)'));

        -- Re-lanzar el error
        THROW;
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[AsignarRobotOnline] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE PROCEDURE [dbo].[AsignarRobotOnline]
    @Robot NVARCHAR(100),
    @Equipos NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        BEGIN TRANSACTION;

		SET @Equipos = UPPER(TRIM(@Equipos))
        -- Validar la existencia del robot
        DECLARE @RobotId INT;
        SELECT @RobotId = RobotId FROM Robots WHERE Robot = @Robot;
        
        IF @RobotId IS NULL
        BEGIN
            RAISERROR('El robot especificado no existe.', 16, 1);
            RETURN;
        END

        -- Preparar la tabla temporal para los equipos
        DECLARE @EquiposTemp TABLE (Equipo NVARCHAR(255));
        INSERT INTO @EquiposTemp (Equipo)
        SELECT TRIM(value) FROM STRING_SPLIT(@Equipos, ',');

        -- Iterar sobre los equipos y asignarlos
        DECLARE @EquipoNombre NVARCHAR(255);
        DECLARE @EquipoId INT;
        
        DECLARE equipo_cursor CURSOR FOR 
        SELECT Equipo FROM @EquiposTemp;

        OPEN equipo_cursor;
        FETCH NEXT FROM equipo_cursor INTO @EquipoNombre;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            -- Validar la existencia del equipo
            SELECT @EquipoId = EquipoId FROM Equipos WHERE Equipo = @EquipoNombre;
            
            IF @EquipoId IS NULL
            BEGIN
                PRINT 'El equipo "' + @EquipoNombre + '" no existe. Se omitirá su asignación.';
            END
            ELSE
            BEGIN
                -- Verificar si el robot ya está asignado al equipo
                IF EXISTS (SELECT 1 FROM Asignaciones WHERE RobotId = @RobotId AND EquipoId = @EquipoId)
                BEGIN
                    PRINT 'El robot ya está asignado al equipo "' + @EquipoNombre + '". Se omitirá su asignación.';
                END
                ELSE
                BEGIN
                    -- Insertar la nueva asignación no programada
                    INSERT INTO Asignaciones (RobotId, EquipoId, EsProgramado)
                    VALUES (@RobotId, @EquipoId, 0); -- EsProgramado = 0 para robots no programados

                    PRINT 'Robot asignado exitosamente al equipo "' + @EquipoNombre + '".';
                END
            END

            FETCH NEXT FROM equipo_cursor INTO @EquipoNombre;
        END

        CLOSE equipo_cursor;
        DEALLOCATE equipo_cursor;

        COMMIT TRANSACTION;
        PRINT 'Asignaciones completadas exitosamente.';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        -- Registrar el error en la tabla ErrorLog
        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (
            SUSER_NAME(),
            'AsignarRobotOnline',
            ERROR_MESSAGE(),
            '@Robot = ' + @Robot + ', @Equipos = ' + @Equipos
        );

        -- Mostrar un mensaje de error
        PRINT 'Error: ' + ERROR_MESSAGE();
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[CargarProgramacionDiaria] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:      <Author,,Name>
-- Create date: <Create Date,,>
-- Description: Carga una programación diaria para un robot y equipos específicos.
-- Fecha Modificación: <Current Date>
-- Descripción Modificación:
--   - @Equipos ahora acepta una lista de nombres de equipo separados por comas.
--   - Se utiliza SCOPE_IDENTITY() para obtener el ProgramacionId.
--   - Se procesan múltiples equipos, insertando o actualizando en dbo.Asignaciones.
--   - Se establece ProgramacionId y EsProgramado=1 en dbo.Asignaciones.
--   - Se manejan advertencias para equipos no encontrados.
--   - Se mantiene la lógica de transacción y actualización de Robot.EsOnline.
-- =============================================
CREATE PROCEDURE [dbo].[CargarProgramacionDiaria]
    @Robot NVARCHAR(100),
    @Equipos NVARCHAR(MAX), -- Comma-separated team names
    @HoraInicio NVARCHAR(MAX),
    @Tolerancia INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @RobotId INT;
    DECLARE @NewProgramacionId INT;
    DECLARE @CurrentEquipoId INT;
    DECLARE @CurrentEquipoNombre NVARCHAR(100);
    DECLARE @ErrorMessage NVARCHAR(4000);
    DECLARE @ErrorSeverity INT;
    DECLARE @ErrorState INT;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Obtener RobotId
        SELECT @RobotId = RobotId FROM dbo.Robots WHERE Robot = @Robot;

        IF @RobotId IS NULL
        BEGIN
            RAISERROR('El robot especificado no existe.', 16, 1);
            RETURN; -- Salir si el robot no existe
        END

        -- Insertar en Programaciones
        INSERT INTO dbo.Programaciones (RobotId, TipoProgramacion, HoraInicio, Tolerancia, Activo, FechaCreacion)
        VALUES (@RobotId, 'Diaria', @HoraInicio, @Tolerancia, 1, GETDATE());

        -- Obtener el ProgramacionId recién insertado
        SET @NewProgramacionId = SCOPE_IDENTITY();

        IF @NewProgramacionId IS NULL
        BEGIN
            RAISERROR('No se pudo obtener el ID de la nueva programación.', 16, 1);
            RETURN; -- Salir si no se pudo crear la programación
        END

        -- Actualizar el estado del Robot
        UPDATE dbo.Robots
        SET EsOnline = 0
        WHERE RobotId = @RobotId;

        -- Procesar cada equipo en la lista @Equipos
        DECLARE team_cursor CURSOR FOR
        SELECT LTRIM(RTRIM(value))
        FROM STRING_SPLIT(@Equipos, ',');

        OPEN team_cursor;
        FETCH NEXT FROM team_cursor INTO @CurrentEquipoNombre;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @CurrentEquipoId = NULL; -- Reset for each team

            -- Obtener EquipoId para el equipo actual
            SELECT @CurrentEquipoId = EquipoId FROM dbo.Equipos WHERE Equipo = @CurrentEquipoNombre;

            IF @CurrentEquipoId IS NOT NULL
            BEGIN
                -- Verificar si la asignación ya existe
                IF EXISTS (SELECT 1 FROM dbo.Asignaciones WHERE RobotId = @RobotId AND EquipoId = @CurrentEquipoId)
                BEGIN
                    UPDATE dbo.Asignaciones
                    SET EsProgramado = 1,
                        ProgramacionId = @NewProgramacionId,
                        Reservado = 0, -- Programación anula reserva manual
                        AsignadoPor = 'SP_Programacion_Diaria',
                        FechaAsignacion = GETDATE() -- Actualizar fecha de asignación/modificación
                    WHERE RobotId = @RobotId AND EquipoId = @CurrentEquipoId;
                END
                ELSE
                BEGIN
                    INSERT INTO dbo.Asignaciones (RobotId, EquipoId, EsProgramado, ProgramacionId, Reservado, AsignadoPor, FechaAsignacion)
                    VALUES (@RobotId, @CurrentEquipoId, 1, @NewProgramacionId, 0, 'SP_Programacion_Diaria', GETDATE());
                END

                -- Actualizar el equipo para que no permita balanceo dinámico
                UPDATE dbo.Equipos
                SET PermiteBalanceoDinamico = 0
                WHERE EquipoId = @CurrentEquipoId;
            END
            ELSE
            BEGIN
                -- Equipo no encontrado, imprimir advertencia
                PRINT 'Warning: Equipo ' + @CurrentEquipoNombre + ' no encontrado y no será asignado.';
            END

            FETCH NEXT FROM team_cursor INTO @CurrentEquipoNombre;
        END

        CLOSE team_cursor;
        DEALLOCATE team_cursor;

        COMMIT TRANSACTION;
        PRINT 'Programación diaria cargada y equipos asignados/actualizados exitosamente para el robot ' + @Robot;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SELECT
            @ErrorMessage = ERROR_MESSAGE(),
            @ErrorSeverity = ERROR_SEVERITY(),
            @ErrorState = ERROR_STATE();

        -- Registrar el error en la tabla ErrorLog
        DECLARE @Parametros NVARCHAR(MAX);
        SET @Parametros = '@Robot = ' + @Robot + 
                        ', @Equipos = ' + @Equipos + 
                        ', @HoraInicio = ' + CONVERT(NVARCHAR(8), @HoraInicio, 108) + 
                        ', @Tolerancia = ' + CAST(@Tolerancia AS NVARCHAR(10));

        -- Luego:
        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (
            SUSER_NAME(),
            'CargarProgramacionEspecifica',
            ERROR_MESSAGE(),
            @Parametros
        );

        -- Mostrar un mensaje de error
        PRINT 'Error: ' + ERROR_MESSAGE();

        -- Relanzar el error para que el cliente lo reciba
        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[CargarProgramacionEspecifica] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:      <Author,,Name>
-- Create date: <Create Date,,>
-- Description: Carga una programación específica para un robot y equipos determinados.
-- Modificado por: AI Agent
-- Fecha Modificación: <Current Date>
-- Descripción Modificación:
--   - @Equipos ahora acepta una lista de nombres de equipo separados por comas.
--   - Se utiliza SCOPE_IDENTITY() para obtener el ProgramacionId.
--   - Se procesan múltiples equipos, insertando o actualizando en dbo.Asignaciones.
--   - Se establece ProgramacionId y EsProgramado=1 en dbo.Asignaciones.
--   - Se manejan advertencias para equipos no encontrados.
--   - Se mantiene la lógica de transacción y actualización de Robot.EsOnline.
-- =============================================
CREATE PROCEDURE [dbo].[CargarProgramacionEspecifica]
    @Robot NVARCHAR(100),
    @Equipos NVARCHAR(MAX), -- Comma-separated team names
    @FechaEspecifica NVARCHAR(MAX),
    @HoraInicio NVARCHAR(MAX),
    @Tolerancia INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @RobotId INT;
    DECLARE @NewProgramacionId INT;
    DECLARE @CurrentEquipoId INT;
    DECLARE @CurrentEquipoNombre NVARCHAR(100);
    DECLARE @ErrorMessage NVARCHAR(4000);
    DECLARE @ErrorSeverity INT;
    DECLARE @ErrorState INT;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Obtener RobotId
        SELECT @RobotId = RobotId FROM dbo.Robots WHERE Robot = @Robot;

        IF @RobotId IS NULL
        BEGIN
            RAISERROR('El robot especificado no existe.', 16, 1);
            RETURN; 
        END

        -- Insertar en Programaciones
        INSERT INTO dbo.Programaciones (RobotId, TipoProgramacion, FechaEspecifica, HoraInicio, Tolerancia, Activo, FechaCreacion)
        VALUES (@RobotId, 'Especifica', @FechaEspecifica, @HoraInicio, @Tolerancia, 1, GETDATE());

        -- Obtener el ProgramacionId recién insertado
        SET @NewProgramacionId = SCOPE_IDENTITY();

        IF @NewProgramacionId IS NULL
        BEGIN
            RAISERROR('No se pudo obtener el ID de la nueva programación.', 16, 1);
            RETURN;
        END

        -- Actualizar el estado del Robot
        UPDATE dbo.Robots
        SET EsOnline = 0
        WHERE RobotId = @RobotId;

        -- Procesar cada equipo en la lista @Equipos
        DECLARE team_cursor CURSOR FOR
        SELECT LTRIM(RTRIM(value))
        FROM STRING_SPLIT(@Equipos, ',');

        OPEN team_cursor;
        FETCH NEXT FROM team_cursor INTO @CurrentEquipoNombre;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @CurrentEquipoId = NULL; 

            -- Obtener EquipoId para el equipo actual
            SELECT @CurrentEquipoId = EquipoId FROM dbo.Equipos WHERE Equipo = @CurrentEquipoNombre;

            IF @CurrentEquipoId IS NOT NULL
            BEGIN
                -- Verificar si la asignación ya existe
                IF EXISTS (SELECT 1 FROM dbo.Asignaciones WHERE RobotId = @RobotId AND EquipoId = @CurrentEquipoId)
                BEGIN
                    UPDATE dbo.Asignaciones
                    SET EsProgramado = 1,
                        ProgramacionId = @NewProgramacionId,
                        Reservado = 0, 
                        AsignadoPor = 'SP_Programacion_Especifica',
                        FechaAsignacion = GETDATE() 
                    WHERE RobotId = @RobotId AND EquipoId = @CurrentEquipoId;
                END
                ELSE
                BEGIN
                    INSERT INTO dbo.Asignaciones (RobotId, EquipoId, EsProgramado, ProgramacionId, Reservado, AsignadoPor, FechaAsignacion)
                    VALUES (@RobotId, @CurrentEquipoId, 1, @NewProgramacionId, 0, 'SP_Programacion_Especifica', GETDATE());
                END

                -- Actualizar el equipo para que no permita balanceo dinámico
                UPDATE dbo.Equipos
                SET PermiteBalanceoDinamico = 0
                WHERE EquipoId = @CurrentEquipoId;
            END
            ELSE
            BEGIN
                PRINT 'Warning: Equipo ' + @CurrentEquipoNombre + ' no encontrado y no será asignado.';
            END

            FETCH NEXT FROM team_cursor INTO @CurrentEquipoNombre;
        END

        CLOSE team_cursor;
        DEALLOCATE team_cursor;

        COMMIT TRANSACTION;
        PRINT 'Programación específica cargada y equipos asignados/actualizados exitosamente para el robot ' + @Robot;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SELECT
            @ErrorMessage = ERROR_MESSAGE(),
            @ErrorSeverity = ERROR_SEVERITY(),
            @ErrorState = ERROR_STATE();

        -- Registrar el error en la tabla ErrorLog
        DECLARE @Parametros NVARCHAR(MAX);
        SET @Parametros = '@Robot = ' + @Robot + 
                        ', @Equipos = ' + @Equipos + 
                        ', @HoraInicio = ' + CONVERT(NVARCHAR(8), @HoraInicio, 108) + 
                        ', @Tolerancia = ' + CAST(@Tolerancia AS NVARCHAR(10));

        -- Luego:
        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (
            SUSER_NAME(),
            'CargarProgramacionEspecifica',
            ERROR_MESSAGE(),
            @Parametros
        );

        -- Mostrar un mensaje de error
        PRINT 'Error: ' + ERROR_MESSAGE();

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[CargarProgramacionMensual] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:      <Author,,Name>
-- Create date: <Create Date,,>
-- Description: Carga una programación mensual para un robot y equipos específicos.
-- Modificado por: AI Agent
-- Fecha Modificación: <Current Date>
-- Descripción Modificación:
--   - @Equipos ahora acepta una lista de nombres de equipo separados por comas.
--   - Se utiliza SCOPE_IDENTITY() para obtener el ProgramacionId.
--   - Se procesan múltiples equipos, insertando o actualizando en dbo.Asignaciones.
--   - Se establece ProgramacionId y EsProgramado=1 en dbo.Asignaciones.
--   - Se manejan advertencias para equipos no encontrados.
--   - Se mantiene la lógica de transacción y actualización de Robot.EsOnline.
-- =============================================
CREATE PROCEDURE [dbo].[CargarProgramacionMensual]
    @Robot NVARCHAR(100),
    @Equipos NVARCHAR(MAX), -- Comma-separated team names
    @DiaDelMes INT,
    @HoraInicio TIME, -- Assuming HoraInicio is TIME for Mensual, adjust if different
    @Tolerancia INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @RobotId INT;
    DECLARE @NewProgramacionId INT;
    DECLARE @CurrentEquipoId INT;
    DECLARE @CurrentEquipoNombre NVARCHAR(100);
    DECLARE @ErrorMessage NVARCHAR(4000);
    DECLARE @ErrorSeverity INT;
    DECLARE @ErrorState INT;
    DECLARE @HoraInicioStr NVARCHAR(MAX);

    -- Convert HoraInicio TIME to NVARCHAR(MAX) for Programaciones table if its type is NVARCHAR(MAX)
    SET @HoraInicioStr = CONVERT(NVARCHAR(8), @HoraInicio); -- HH:MM:SS format

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Obtener RobotId
        SELECT @RobotId = RobotId FROM dbo.Robots WHERE Robot = @Robot;

        IF @RobotId IS NULL
        BEGIN
            RAISERROR('El robot especificado no existe.', 16, 1);
            RETURN; 
        END

        -- Insertar en Programaciones
        -- Note: Assuming Programaciones.HoraInicio is NVARCHAR(MAX). If it's TIME, use @HoraInicio directly.
        INSERT INTO dbo.Programaciones (RobotId, TipoProgramacion, DiaDelMes, HoraInicio, Tolerancia, Activo, FechaCreacion)
        VALUES (@RobotId, 'Mensual', @DiaDelMes, @HoraInicioStr, @Tolerancia, 1, GETDATE());

        -- Obtener el ProgramacionId recién insertado
        SET @NewProgramacionId = SCOPE_IDENTITY();

        IF @NewProgramacionId IS NULL
        BEGIN
            RAISERROR('No se pudo obtener el ID de la nueva programación.', 16, 1);
            RETURN;
        END

        -- Actualizar el estado del Robot
        UPDATE dbo.Robots
        SET EsOnline = 0
        WHERE RobotId = @RobotId;

        -- Procesar cada equipo en la lista @Equipos
        DECLARE team_cursor CURSOR FOR
        SELECT LTRIM(RTRIM(value))
        FROM STRING_SPLIT(@Equipos, ',');

        OPEN team_cursor;
        FETCH NEXT FROM team_cursor INTO @CurrentEquipoNombre;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @CurrentEquipoId = NULL; 

            -- Obtener EquipoId para el equipo actual
            SELECT @CurrentEquipoId = EquipoId FROM dbo.Equipos WHERE Equipo = @CurrentEquipoNombre;

            IF @CurrentEquipoId IS NOT NULL
            BEGIN
                -- Verificar si la asignación ya existe
                IF EXISTS (SELECT 1 FROM dbo.Asignaciones WHERE RobotId = @RobotId AND EquipoId = @CurrentEquipoId)
                BEGIN
                    UPDATE dbo.Asignaciones
                    SET EsProgramado = 1,
                        ProgramacionId = @NewProgramacionId,
                        Reservado = 0, 
                        AsignadoPor = 'SP_Programacion_Mensual',
                        FechaAsignacion = GETDATE() 
                    WHERE RobotId = @RobotId AND EquipoId = @CurrentEquipoId;
                END
                ELSE
                BEGIN
                    INSERT INTO dbo.Asignaciones (RobotId, EquipoId, EsProgramado, ProgramacionId, Reservado, AsignadoPor, FechaAsignacion)
                    VALUES (@RobotId, @CurrentEquipoId, 1, @NewProgramacionId, 0, 'SP_Programacion_Mensual', GETDATE());
                END

                -- Actualizar el equipo para que no permita balanceo dinámico
                UPDATE dbo.Equipos
                SET PermiteBalanceoDinamico = 0
                WHERE EquipoId = @CurrentEquipoId;
            END
            ELSE
            BEGIN
                PRINT 'Warning: Equipo ' + @CurrentEquipoNombre + ' no encontrado y no será asignado.';
            END

            FETCH NEXT FROM team_cursor INTO @CurrentEquipoNombre;
        END

        CLOSE team_cursor;
        DEALLOCATE team_cursor;

        COMMIT TRANSACTION;
        PRINT 'Programación mensual cargada y equipos asignados/actualizados exitosamente para el robot ' + @Robot;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SELECT
            @ErrorMessage = ERROR_MESSAGE(),
            @ErrorSeverity = ERROR_SEVERITY(),
            @ErrorState = ERROR_STATE();

        -- Registrar el error en la tabla ErrorLog
        DECLARE @Parametros NVARCHAR(MAX);
        SET @Parametros = '@Robot = ' + @Robot + 
                        ', @Equipos = ' + @Equipos + 
                        ', @HoraInicio = ' + CONVERT(NVARCHAR(8), @HoraInicio, 108) + 
                        ', @Tolerancia = ' + CAST(@Tolerancia AS NVARCHAR(10));

        -- Luego:
        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (
            SUSER_NAME(),
            'CargarProgramacionEspecifica',
            ERROR_MESSAGE(),
            @Parametros
        );


        -- Mostrar un mensaje de error
        PRINT 'Error: ' + ERROR_MESSAGE();

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[CargarProgramacionSemanal] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:      <Author,,Name>
-- Create date: <Create Date,,>
-- Description: Carga una programación semanal para un robot y equipos específicos.
-- Modificado por: AI Agent
-- Fecha Modificación: <Current Date>
-- Descripción Modificación:
--   - @Equipos ahora acepta una lista de nombres de equipo separados por comas.
--   - Se utiliza SCOPE_IDENTITY() para obtener el ProgramacionId.
--   - Se procesan múltiples equipos, insertando o actualizando en dbo.Asignaciones.
--   - Se establece ProgramacionId y EsProgramado=1 en dbo.Asignaciones.
--   - Se manejan advertencias para equipos no encontrados.
--   - Se mantiene la lógica de transacción y actualización de Robot.EsOnline.
-- =============================================
CREATE PROCEDURE [dbo].[CargarProgramacionSemanal]
    @Robot NVARCHAR(100),
    @Equipos NVARCHAR(MAX), -- Comma-separated team names
    @DiasSemana NVARCHAR(100),
    @HoraInicio NVARCHAR(MAX),
    @Tolerancia INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @RobotId INT;
    DECLARE @NewProgramacionId INT;
    DECLARE @CurrentEquipoId INT;
    DECLARE @CurrentEquipoNombre NVARCHAR(100);
    DECLARE @ErrorMessage NVARCHAR(4000);
    DECLARE @ErrorSeverity INT;
    DECLARE @ErrorState INT;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Obtener RobotId
        SELECT @RobotId = RobotId FROM dbo.Robots WHERE Robot = @Robot;

        IF @RobotId IS NULL
        BEGIN
            RAISERROR('El robot especificado no existe.', 16, 1);
            RETURN; 
        END

        -- Insertar en Programaciones
        INSERT INTO dbo.Programaciones (RobotId, TipoProgramacion, DiasSemana, HoraInicio, Tolerancia, Activo, FechaCreacion)
        VALUES (@RobotId, 'Semanal', @DiasSemana, @HoraInicio, @Tolerancia, 1, GETDATE());

        -- Obtener el ProgramacionId recién insertado
        SET @NewProgramacionId = SCOPE_IDENTITY();

        IF @NewProgramacionId IS NULL
        BEGIN
            RAISERROR('No se pudo obtener el ID de la nueva programación.', 16, 1);
            RETURN;
        END

        -- Actualizar el estado del Robot
        UPDATE dbo.Robots
        SET EsOnline = 0
        WHERE RobotId = @RobotId;

        -- Procesar cada equipo en la lista @Equipos
        DECLARE team_cursor CURSOR FOR
        SELECT LTRIM(RTRIM(value))
        FROM STRING_SPLIT(@Equipos, ',');

        OPEN team_cursor;
        FETCH NEXT FROM team_cursor INTO @CurrentEquipoNombre;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @CurrentEquipoId = NULL; 

            -- Obtener EquipoId para el equipo actual
            SELECT @CurrentEquipoId = EquipoId FROM dbo.Equipos WHERE Equipo = @CurrentEquipoNombre;

            IF @CurrentEquipoId IS NOT NULL
            BEGIN
                -- Verificar si la asignación ya existe
                IF EXISTS (SELECT 1 FROM dbo.Asignaciones WHERE RobotId = @RobotId AND EquipoId = @CurrentEquipoId)
                BEGIN
                    UPDATE dbo.Asignaciones
                    SET EsProgramado = 1,
                        ProgramacionId = @NewProgramacionId,
                        Reservado = 0, 
                        AsignadoPor = 'SP_Programacion_Semanal',
                        FechaAsignacion = GETDATE() 
                    WHERE RobotId = @RobotId AND EquipoId = @CurrentEquipoId;
                END
                ELSE
                BEGIN
                    INSERT INTO dbo.Asignaciones (RobotId, EquipoId, EsProgramado, ProgramacionId, Reservado, AsignadoPor, FechaAsignacion)
                    VALUES (@RobotId, @CurrentEquipoId, 1, @NewProgramacionId, 0, 'SP_Programacion_Semanal', GETDATE());
                END

                -- Actualizar el equipo para que no permita balanceo dinámico
                UPDATE dbo.Equipos
                SET PermiteBalanceoDinamico = 0
                WHERE EquipoId = @CurrentEquipoId;
            END
            ELSE
            BEGIN
                PRINT 'Warning: Equipo ' + @CurrentEquipoNombre + ' no encontrado y no será asignado.';
            END

            FETCH NEXT FROM team_cursor INTO @CurrentEquipoNombre;
        END

        CLOSE team_cursor;
        DEALLOCATE team_cursor;

        COMMIT TRANSACTION;
        PRINT 'Programación semanal cargada y equipos asignados/actualizados exitosamente para el robot ' + @Robot;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SELECT
            @ErrorMessage = ERROR_MESSAGE(),
            @ErrorSeverity = ERROR_SEVERITY(),
            @ErrorState = ERROR_STATE();

        -- Registrar el error en la tabla ErrorLog
        DECLARE @Parametros NVARCHAR(MAX);
        SET @Parametros = '@Robot = ' + @Robot + 
                        ', @Equipos = ' + @Equipos + 
                        ', @HoraInicio = ' + CONVERT(NVARCHAR(8), @HoraInicio, 108) + 
                        ', @Tolerancia = ' + CAST(@Tolerancia AS NVARCHAR(10));

        -- Luego:
        INSERT INTO ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (
            SUSER_NAME(),
            'CargarProgramacionEspecifica',
            ERROR_MESSAGE(),
            @Parametros
        );

        -- Mostrar un mensaje de error
        PRINT 'Error: ' + ERROR_MESSAGE();

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[CrearPool] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:      LP
-- Create date: 2025-08-01
-- Description: Inserta un nuevo pool en la tabla dbo.Pools
--              y devuelve el registro recién creado.
-- =============================================
CREATE PROCEDURE [dbo].[CrearPool]
    @Nombre NVARCHAR(100),
    @Descripcion NVARCHAR(500)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Verificar que no exista un pool con el mismo nombre
    IF EXISTS (SELECT 1 FROM dbo.Pools WHERE Nombre = @Nombre)
    BEGIN
        RAISERROR ('Ya existe un pool con el nombre "%s".', 16, 1, @Nombre);
        RETURN;
    END

    BEGIN TRY
        INSERT INTO dbo.Pools (Nombre, Descripcion)
        -- La cláusula OUTPUT devuelve los datos de la fila insertada
        OUTPUT INSERTED.PoolId, INSERTED.Nombre, INSERTED.Descripcion, INSERTED.Activo
        VALUES (@Nombre, @Descripcion);
    END TRY
    BEGIN CATCH
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        RAISERROR (@ErrorMessage, 16, 1);
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[CrearProgramacion] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[CrearProgramacion]
    @Robot NVARCHAR(100),
    @Equipos NVARCHAR(MAX), -- Nombres de equipos separados por comas
    @TipoProgramacion NVARCHAR(20), -- 'Diaria', 'Semanal', 'Mensual', 'Especifica'
    @HoraInicio TIME,
    @Tolerancia INT,
    @DiasSemana NVARCHAR(20) = NULL,
    @DiaDelMes INT = NULL,
    @FechaEspecifica DATE = NULL,
    @UsuarioCrea NVARCHAR(50) = 'WebApp_Creation'
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON; 

    DECLARE @RobotId INT;
    DECLARE @NewProgramacionId INT;
    DECLARE @ErrorMessage NVARCHAR(4000);
    DECLARE @ErrorSeverity INT;
    DECLARE @ErrorState INT;

    CREATE TABLE #EquiposAProgramar (EquipoId INT PRIMARY KEY);

    BEGIN TRY
        -- (Las validaciones 1, 1.1 y 2 no cambian) ...
        SELECT @RobotId = RobotId FROM dbo.Robots WHERE Robot = @Robot;
        IF @RobotId IS NULL BEGIN RAISERROR('El robot especificado no existe.', 16, 1); RETURN; END
        IF EXISTS (SELECT 1 FROM dbo.Robots WHERE RobotId = @RobotId AND EsOnline = 1) BEGIN RAISERROR('No se puede crear una programación para un robot "Online".', 16, 1); RETURN; END
        IF @TipoProgramacion = 'Semanal' AND ISNULL(@DiasSemana, '') = '' RAISERROR('Para una programación Semanal, se debe especificar @DiasSemana.', 16, 1);
        IF @TipoProgramacion = 'Mensual' AND @DiaDelMes IS NULL RAISERROR('Para una programación Mensual, se debe especificar @DiaDelMes.', 16, 1);
        IF @TipoProgramacion = 'Especifica' AND @FechaEspecifica IS NULL RAISERROR('Para una programación Específica, se debe especificar @FechaEspecifica.', 16, 1);

        BEGIN TRANSACTION;

        -- 3. Insertar la nueva programación (Sin cambios)
        INSERT INTO dbo.Programaciones (
            RobotId, TipoProgramacion, HoraInicio, Tolerancia, Activo, 
            FechaCreacion, DiasSemana, DiaDelMes, FechaEspecifica
        )
        VALUES (
            @RobotId, @TipoProgramacion, @HoraInicio, @Tolerancia, 1, 
            GETDATE(),
            CASE WHEN @TipoProgramacion = 'Semanal' THEN @DiasSemana ELSE NULL END,
            CASE WHEN @TipoProgramacion = 'Mensual' THEN @DiaDelMes ELSE NULL END,
            CASE WHEN @TipoProgramacion = 'Especifica' THEN @FechaEspecifica ELSE NULL END
        );

        SET @NewProgramacionId = SCOPE_IDENTITY();
        IF @NewProgramacionId IS NULL BEGIN RAISERROR('Error fatal: No se pudo obtener el ID de la nueva programación.', 16, 1); RETURN; END

        -- 4. Poblar la tabla temporal (Sin cambios)
        INSERT INTO #EquiposAProgramar (EquipoId)
        SELECT E.EquipoId
        FROM STRING_SPLIT(@Equipos, ',') AS S
        JOIN dbo.Equipos E ON LTRIM(RTRIM(S.value)) = E.Equipo
        WHERE E.Activo_SAM = 1;

        -- (Opcional) Mostrar advertencias (Sin cambios)
        SELECT 'Warning: Equipo "' + LTRIM(RTRIM(S.value)) + '" no encontrado o inactivo.' AS Advertencia
        FROM STRING_SPLIT(@Equipos, ',') S
        WHERE NOT EXISTS (SELECT 1 FROM dbo.Equipos E WHERE E.Equipo = LTRIM(RTRIM(S.value)) AND E.Activo_SAM = 1);

        -- 5. Asignar los equipos (ESTA ES LA MODIFICACIÓN)
        -- Eliminamos el MERGE y lo reemplazamos por un INSERT directo.
        -- Esto creará una nueva fila por cada equipo, usando la nueva ProgramacionId,
        -- sin tocar las asignaciones existentes.
        INSERT INTO dbo.Asignaciones (
            RobotId, 
            EquipoId, 
            EsProgramado, 
            ProgramacionId, 
            Reservado, 
            AsignadoPor, 
            FechaAsignacion
        )
        SELECT 
            @RobotId, 
            Source.EquipoId, 
            1, -- EsProgramado
            @NewProgramacionId, -- El ID de la nueva programación
            0, -- Reservado
            @UsuarioCrea, 
            GETDATE()
        FROM #EquiposAProgramar AS Source;

        -- 6. Actualizar el estado del Robot (Sin cambios)
        UPDATE dbo.Robots SET EsOnline = 0 WHERE RobotId = @RobotId;

        -- 7. Desactivar el balanceo dinámico (Sin cambios)
        UPDATE E SET PermiteBalanceoDinamico = 0
        FROM dbo.Equipos E JOIN #EquiposAProgramar NEP ON E.EquipoId = NEP.EquipoId;

        COMMIT TRANSACTION;
        
        PRINT 'Programación de tipo "' + @TipoProgramacion + '" creada exitosamente.';

        IF OBJECT_ID('tempdb..#EquiposAProgramar') IS NOT NULL
            DROP TABLE #EquiposAProgramar;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF OBJECT_ID('tempdb..#EquiposAProgramar') IS NOT NULL DROP TABLE #EquiposAProgramar;

        -- (El bloque CATCH no necesita cambios)
        SET @ErrorMessage = ERROR_MESSAGE();
        SET @ErrorSeverity = ERROR_SEVERITY();
        SET @ErrorState = ERROR_STATE();
        DECLARE @Parametros NVARCHAR(MAX) = FORMATMESSAGE(
            '@Robot=%s, @Equipos=%s, @TipoProgramacion=%s, @HoraInicio=%s, @Tolerancia=%d, @DiasSemana=%s, @DiaDelMes=%d, @FechaEspecifica=%s',
            ISNULL(@Robot, 'NULL'), ISNULL(@Equipos, 'NULL'), ISNULL(@TipoProgramacion, 'NULL'),
            ISNULL(CONVERT(NVARCHAR(8), @HoraInicio, 108), 'NULL'), ISNULL(@Tolerancia, 'NULL'),
            ISNULL(@DiasSemana, 'NULL'), ISNULL(CAST(@DiaDelMes AS NVARCHAR(10)), 'NULL'),
            ISNULL(CONVERT(NVARCHAR(10), @FechaEspecifica, 120), 'NULL')
        );
        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'CrearProgramacion', @ErrorMessage, @Parametros);
        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[EliminarPool] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- Reemplaza los SPs de la respuesta anterior con estos:

-- 1. STORED PROCEDURE PARA ELIMINAR UN POOL (VERSIÓN CORREGIDA)
CREATE PROCEDURE [dbo].[EliminarPool]
    @PoolId INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF NOT EXISTS (SELECT 1 FROM dbo.Pools WHERE PoolId = @PoolId)
    BEGIN
        RAISERROR ('No se encontró un pool con el ID %d para eliminar.', 16, 1, @PoolId);
        RETURN;
    END

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE dbo.Equipos SET PoolId = NULL WHERE PoolId = @PoolId;
        UPDATE dbo.Robots SET PoolId = NULL WHERE PoolId = @PoolId;
        DELETE FROM dbo.Pools WHERE PoolId = @PoolId;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;

        -- Log del error
        DECLARE @ErrorMessage_DEL NVARCHAR(4000) = ERROR_MESSAGE();
        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'dbo.EliminarPool', @ErrorMessage_DEL, CONCAT('@PoolId=', @PoolId));

        -- Re-lanzar el error
        THROW;
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[EliminarProgramacionCompleta] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- Usamos CREATE OR ALTER para que el script se pueda ejecutar múltiples veces sin error.
CREATE   PROCEDURE [dbo].[EliminarProgramacionCompleta]
    @ProgramacionId INT,
    @RobotId INT,
    @UsuarioModifica NVARCHAR(50) = 'WebApp_Delete'
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @ErrorMessage NVARCHAR(4000);
    CREATE TABLE #EquiposAfectados (EquipoId INT PRIMARY KEY);

    BEGIN TRY
        BEGIN TRANSACTION;

        -- 1. Identificar los equipos que están asignados a ESTA programación
        INSERT INTO #EquiposAfectados (EquipoId)
        SELECT DISTINCT EquipoId
        FROM dbo.Asignaciones
        WHERE ProgramacionId = @ProgramacionId AND RobotId = @RobotId AND EsProgramado = 1;

        -- 2. Eliminar la programación de la tabla principal.
        -- Esto debe hacerse ANTES de modificar las asignaciones para evitar conflictos de FK.
        DELETE FROM dbo.Programaciones
        WHERE ProgramacionId = @ProgramacionId AND RobotId = @RobotId;

        -- 3. Ahora, manejamos las asignaciones.
        -- Borramos la fila de asignación para los equipos afectados, pero SOLO
        -- si no están también marcados como 'Reservado'.
        DELETE FROM dbo.Asignaciones
        WHERE RobotId = @RobotId
          AND EquipoId IN (SELECT EquipoId FROM #EquiposAfectados)
          AND (Reservado = 0 OR Reservado IS NULL); -- No tocar asignaciones reservadas manualmente

        -- 4. Finalmente, para los equipos que liberamos, nos aseguramos
        -- de que puedan volver al pool de balanceo dinámico.
        UPDATE E
        SET E.PermiteBalanceoDinamico = 1
        FROM dbo.Equipos E
        JOIN #EquiposAfectados A ON E.EquipoId = A.EquipoId
        WHERE NOT EXISTS (
            SELECT 1 FROM dbo.Asignaciones a2
            WHERE a2.EquipoId = E.EquipoId AND (a2.EsProgramado = 1 OR a2.Reservado = 1)
        );

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SET @ErrorMessage = ERROR_MESSAGE();
        RAISERROR (@ErrorMessage, 16, 1);
    END CATCH

    IF OBJECT_ID('tempdb..#EquiposAfectados') IS NOT NULL
        DROP TABLE #EquiposAfectados;
END

GO
/****** Object:  StoredProcedure [dbo].[ListarEquipos] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
/*
MODIFICACIÓN:
    - Se reemplazó el JOIN directo a Asignaciones/Robots con un OUTER APPLY.
    - Esto soluciona un bug que duplicaba Equipos si tenían múltiples asignaciones.
    - Se añade la columna 'EsProgramado' al SELECT, que reporta el estado
      de la asignación con mayor prioridad (Programado > Reservado > Dinámico).
*/
CREATE PROCEDURE [dbo].[ListarEquipos]
    @Nombre NVARCHAR(100) = NULL,
    @ActivoSAM BIT = NULL,
    @PermiteBalanceo BIT = NULL,
    @Page INT = 1,
    @Size INT = 20,
    @SortBy NVARCHAR(100) = 'Equipo',
    @SortDir NVARCHAR(4) = 'ASC'
AS
BEGIN
    SET NOCOUNT ON;

    -- Usamos OUTER APPLY para obtener la asignación de MAYOR prioridad
    -- Esto evita duplicados de equipos.
    DECLARE @SelectFromClause NVARCHAR(MAX) = 
        'FROM dbo.Equipos e
         LEFT JOIN dbo.Pools p ON e.PoolId = p.PoolId
         OUTER APPLY (
            -- Obtenemos la asignación de MAYOR prioridad para este equipo
            -- Prioridad: Programado (1) > Reservado (1) > Dinámico (0)
            SELECT TOP 1
                r.Robot,
                a.EsProgramado
            FROM dbo.Asignaciones a
            JOIN dbo.Robots r ON a.RobotId = r.RobotId
            WHERE a.EquipoId = e.EquipoId
            ORDER BY
                a.EsProgramado DESC, -- 1. Prioridad a Programado
                a.Reservado DESC,    -- 2. Prioridad a Reservado
                a.FechaAsignacion DESC -- 3. Luego al más reciente
         ) AS AsignacionInfo';
    
    DECLARE @WhereClause NVARCHAR(MAX) = 'WHERE 1=1';
    DECLARE @Params NVARCHAR(MAX) = '@p_Nombre NVARCHAR(100), @p_ActivoSAM BIT, @p_PermiteBalanceo BIT';

    IF @Nombre IS NOT NULL AND @Nombre != ''
        SET @WhereClause += ' AND e.Equipo LIKE ''%'' + @p_Nombre + ''%''';
    IF @ActivoSAM IS NOT NULL
        SET @WhereClause += ' AND e.Activo_SAM = @p_ActivoSAM';
    IF @PermiteBalanceo IS NOT NULL
        SET @WhereClause += ' AND e.PermiteBalanceoDinamico = @p_PermiteBalanceo';

    -- Conteo total (Ahora es un COUNT simple sobre el FROM/WHERE)
    DECLARE @CountQuery NVARCHAR(MAX) = 'SELECT COUNT(e.EquipoId) as total_count ' + @SelectFromClause + ' ' + @WhereClause;
    EXEC sp_executesql @CountQuery, @Params, @p_Nombre = @Nombre, @p_ActivoSAM = @ActivoSAM, @p_PermiteBalanceo = @PermiteBalanceo;

    -- Paginación y ordenamiento
    -- Añadimos 'EsProgramado' a las columnas ordenables
    DECLARE @SortableColumns TABLE (ColName NVARCHAR(100) PRIMARY KEY);
    INSERT INTO @SortableColumns VALUES ('Equipo'), ('Licencia'), ('Activo_SAM'), ('PermiteBalanceoDinamico'), ('RobotAsignado'), ('Pool'), ('EsProgramado');
    
    IF NOT EXISTS (SELECT 1 FROM @SortableColumns WHERE ColName = @SortBy)
        SET @SortBy = 'Equipo';

    -- Mapeo de SortBy a las columnas reales (incluyendo la del OUTER APPLY)
    DECLARE @SortColumnReal NVARCHAR(100) = 
        CASE @SortBy
            WHEN 'RobotAsignado' THEN 'AsignacionInfo.Robot'
            WHEN 'EsProgramado' THEN 'AsignacionInfo.EsProgramado'
            WHEN 'Pool' THEN 'p.Nombre'
            ELSE 'e.' + QUOTENAME(@SortBy)
        END;
    
    DECLARE @OrderByClause NVARCHAR(100) = @SortColumnReal + ' ' + @SortDir;
    DECLARE @Offset INT = (@Page - 1) * @Size;

    DECLARE @MainQuery NVARCHAR(MAX) = 
        'SELECT 
            e.EquipoId, e.Equipo, e.UserName, e.Licencia, e.Activo_SAM, e.PermiteBalanceoDinamico,
            ISNULL(AsignacionInfo.Robot, ''N/A'') as RobotAsignado,
            ISNULL(AsignacionInfo.EsProgramado, 0) as EsProgramado, -- <-- NUEVA COLUMNA
            ISNULL(p.Nombre, ''N/A'') as Pool
         ' + @SelectFromClause + ' ' + @WhereClause + 
        ' ORDER BY ' + @OrderByClause +
        ' OFFSET ' + CAST(@Offset AS NVARCHAR(10)) + ' ROWS FETCH NEXT ' + CAST(@Size AS NVARCHAR(10)) + ' ROWS ONLY';

    EXEC sp_executesql @MainQuery, @Params, @p_Nombre = @Nombre, @p_ActivoSAM = @ActivoSAM, @p_PermiteBalanceo = @PermiteBalanceo;
END
GO
/****** Object:  StoredProcedure [dbo].[ListarPools] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:      LP
-- Create date: 2025-08-01
-- Description: Obtiene una lista de todos los pools de recursos
--              junto con la cantidad de robots y equipos
--              asignados a cada uno. Incluye manejo de errores.
-- =============================================
CREATE PROCEDURE [dbo].[ListarPools]
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON; -- Asegura que la sesión se cierre si hay un error grave

    BEGIN TRY
        -- Lógica principal de la consulta
        SELECT
            p.PoolId,
            p.Nombre,
            p.Descripcion,
            p.Activo,
            (SELECT COUNT(*) FROM dbo.Robots r WHERE r.PoolId = p.PoolId) AS CantidadRobots,
            (SELECT COUNT(*) FROM dbo.Equipos e WHERE e.PoolId = p.PoolId) AS CantidadEquipos
        FROM
            dbo.Pools p
        ORDER BY
            p.Nombre ASC;

    END TRY
    BEGIN CATCH
        -- Manejo de errores estándar del proyecto
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        -- Insertar el error en la tabla de log
        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'dbo.ListarPools', @ErrorMessage, NULL);

        -- Relanzar el error para que la aplicación cliente lo reciba
        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[ListarProgramaciones] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[ListarProgramaciones]
AS
BEGIN
	SET NOCOUNT ON;

	SELECT
        P.ProgramacionId,
        P.RobotId,
        R.Robot AS RobotNombre,
        P.TipoProgramacion,
        P.HoraInicio,
        P.DiasSemana,
        P.DiaDelMes,
        P.FechaEspecifica,
        P.Tolerancia,
        P.Activo,
        P.FechaCreacion,
        P.FechaModificacion,
        STRING_AGG(E.Equipo, ', ') WITHIN GROUP (ORDER BY E.Equipo) AS EquiposProgramados
    FROM
        Programaciones P
    INNER JOIN
        Robots R ON P.RobotId = R.RobotId
    LEFT JOIN
        Asignaciones A ON P.ProgramacionId = A.ProgramacionId
    LEFT JOIN
        Equipos E ON A.EquipoId = E.EquipoId
    GROUP BY
        P.ProgramacionId,
        P.RobotId,
        R.Robot,
        P.TipoProgramacion,
        P.HoraInicio,
        P.DiasSemana,
        P.DiaDelMes,
        P.FechaEspecifica,
        P.Tolerancia,
        P.Activo,
        P.FechaCreacion,
        P.FechaModificacion
    ORDER BY
        P.ProgramacionId;
END
GO
/****** Object:  StoredProcedure [dbo].[ListarProgramacionesPaginadas] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[ListarProgramacionesPaginadas]
    @RobotId INT = NULL,
    @Tipo NVARCHAR(50) = NULL,
    @Activo BIT = NULL,
    @Search NVARCHAR(100) = NULL,
    @PageSize INT = 100,
    @Offset INT = 0
AS
BEGIN
    SET NOCOUNT ON;

    WITH ProgramasFiltradosCTE AS (
        SELECT 
            p.ProgramacionId,
            p.RobotId,
            r.Robot AS RobotNombre,
            p.TipoProgramacion,
            CONVERT(VARCHAR(5), p.HoraInicio, 108) AS HoraInicio,
            p.DiasSemana,
            p.DiaDelMes,
            CONVERT(VARCHAR(10), p.FechaEspecifica, 23) AS FechaEspecifica,
            p.Tolerancia,
            p.Activo,
            
            -- --- CAMBIO AQUÍ ---
            -- Usamos STRING_AGG para listar nombres, pero filtrando por p.ProgramacionId
            (
                SELECT STRING_AGG(eq.Equipo, ', ') WITHIN GROUP (ORDER BY eq.Equipo)
                FROM dbo.Asignaciones a
                INNER JOIN dbo.Equipos eq ON a.EquipoId = eq.EquipoId
                WHERE a.ProgramacionId = p.ProgramacionId  -- <--- FILTRO CORRECTO
                  AND eq.Activo_SAM = 1                    -- <--- Solo activos
            ) AS EquiposProgramados,
            -- -------------------

            COUNT(*) OVER() AS TotalRows
        FROM dbo.Programaciones p
        JOIN dbo.Robots r ON p.RobotId = r.RobotId
        WHERE 
            (@RobotId IS NULL OR p.RobotId = @RobotId)
            AND (@Tipo IS NULL OR p.TipoProgramacion = @Tipo)
            AND (@Activo IS NULL OR p.Activo = @Activo)
            AND (
                @Search IS NULL OR 
                r.Robot LIKE '%' + @Search + '%' OR 
                p.TipoProgramacion LIKE '%' + @Search + '%'
            )
    )
    
    SELECT *
    FROM ProgramasFiltradosCTE
    ORDER BY RobotNombre, HoraInicio
    OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;
END
GO
/****** Object:  StoredProcedure [dbo].[ListarProgramacionesPorRobot] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:      <Author>
-- Create date: <Create Date>
-- Description: Obtiene las programaciones para un robot específico,
--              incluyendo una lista de los equipos asignados.
-- =============================================
CREATE   PROCEDURE [dbo].[ListarProgramacionesPorRobot]
    @RobotId INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        P.ProgramacionId,
        P.RobotId,
        R.Robot AS RobotNombre,
        P.TipoProgramacion,
        P.HoraInicio,
        P.DiasSemana,
        P.DiaDelMes,
        P.FechaEspecifica,
        P.Tolerancia,
        P.Activo,
        P.FechaCreacion,
        P.FechaModificacion,
        STRING_AGG(E.Equipo, ', ') WITHIN GROUP (ORDER BY E.Equipo) AS EquiposProgramados
    FROM
        dbo.Programaciones P
    INNER JOIN
        dbo.Robots R ON P.RobotId = R.RobotId
    LEFT JOIN
        dbo.Asignaciones A ON P.ProgramacionId = A.ProgramacionId AND A.EsProgramado = 1
    LEFT JOIN
        dbo.Equipos E ON A.EquipoId = E.EquipoId
    WHERE
        P.RobotId = @RobotId
    GROUP BY
        P.ProgramacionId,
        P.RobotId,
        R.Robot,
        P.TipoProgramacion,
        P.HoraInicio,
        P.DiasSemana,
        P.DiaDelMes,
        P.FechaEspecifica,
        P.Tolerancia,
        P.Activo,
        P.FechaCreacion,
        P.FechaModificacion
    ORDER BY
        P.ProgramacionId;
END
GO
/****** Object:  StoredProcedure [dbo].[MergeEquipos] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE PROCEDURE [dbo].[MergeEquipos]
    @EquipoList dbo.EquipoListType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- 1. Tabla temporal para almacenar los equipos que cambiaron de ID
    --    AHORA INCLUYE LOS CAMPOS DE CONFIGURACIÓN DE SAM
    CREATE TABLE #IdUpdates (
        OldEquipoId INT PRIMARY KEY,
        NewEquipoId INT NOT NULL UNIQUE,
        Equipo NVARCHAR(100) NOT NULL,
        UserId INT,
        UserName NVARCHAR(50),
        Licencia NVARCHAR(50),
        Activo_SAM BIT,
        -- Campos de SAM que deben transferirse
        OldPoolId INT,
        OldPermiteBalanceoDinamico BIT,
        OldEstadoBalanceador NVARCHAR(50)
    );

    -- 2. Detectar los conflictos (mismo nombre, diferente ID)
    --    Y guardar la configuración antigua de SAM
    INSERT INTO #IdUpdates (
        OldEquipoId, NewEquipoId, Equipo, UserId, UserName, Licencia, Activo_SAM,
        OldPoolId, OldPermiteBalanceoDinamico, OldEstadoBalanceador
    )
    SELECT
        T.EquipoId AS OldEquipoId,
        S.EquipoId AS NewEquipoId,
        S.Equipo, S.UserId, S.UserName, S.Licencia, S.Activo_SAM,
        -- Guardamos la configuración de SAM del registro antiguo (Target)
        T.PoolId AS OldPoolId,
        T.PermiteBalanceoDinamico AS OldPermiteBalanceoDinamico,
        T.EstadoBalanceador AS OldEstadoBalanceador
    FROM @EquipoList AS S
    INNER JOIN dbo.Equipos AS T ON S.Equipo = T.Equipo -- Coincidencia por Hostname
    WHERE S.EquipoId <> T.EquipoId;                  -- Conflicto de ID

    BEGIN TRY
        BEGIN TRANSACTION;

        -- 3. ACTUALIZAR LOS HIJOS
        -- (Esta lógica re-dirige las FKs de Asignaciones/Ejecuciones al nuevo ID)
        UPDATE A SET A.EquipoId = U.NewEquipoId
        FROM dbo.Asignaciones AS A
        INNER JOIN #IdUpdates AS U ON A.EquipoId = U.OldEquipoId;

        UPDATE E SET E.EquipoId = U.NewEquipoId
        FROM dbo.Ejecuciones AS E
        INNER JOIN #IdUpdates AS U ON E.EquipoId = U.OldEquipoId;
        
        UPDATE EH SET EH.EquipoId = U.NewEquipoId
        FROM dbo.Ejecuciones_Historico AS EH
        INNER JOIN #IdUpdates AS U ON EH.EquipoId = U.OldEquipoId;

        -- 4. MANEJAR LA TABLA PADRE (Equipos)
        
        -- 4a. Eliminar los registros de Equipos ANTIGUOS.
        --     (Es seguro porque los hijos ya no apuntan a él)
        DELETE T
        FROM dbo.Equipos AS T
        INNER JOIN #IdUpdates AS U ON T.EquipoId = U.OldEquipoId;

        -- 4b. Insertar los registros de Equipos NUEVOS
        --     (USANDO LA CONFIGURACIÓN DE SAM GUARDADA)
        INSERT INTO dbo.Equipos (
            EquipoId, Equipo, UserId, UserName, Licencia, Activo_SAM,
            PoolId, PermiteBalanceoDinamico, EstadoBalanceador
        )
        SELECT 
            U.NewEquipoId, U.Equipo, U.UserId, U.UserName, U.Licencia, U.Activo_SAM,
            -- Aplicamos la configuración de SAM que guardamos
            U.OldPoolId,
            U.OldPermiteBalanceoDinamico,
            U.OldEstadoBalanceador
        FROM #IdUpdates AS U;

        -- 5. EJECUTAR EL MERGE NORMAL para el resto de equipos
        --    (Aquellos que no cambiaron su ID o son 100% nuevos)
        MERGE dbo.Equipos AS T
        USING (
            -- Excluimos los que ya manejamos en el paso 4b
            SELECT * FROM @EquipoList 
            WHERE Equipo NOT IN (SELECT Equipo FROM #IdUpdates)
        ) AS S
        ON (T.EquipoId = S.EquipoId) -- Coincidencia normal por ID

        -- 5a. Cuando el ID coincide (actualización normal de datos de A360)
        WHEN MATCHED AND (
                T.Equipo <> S.Equipo OR
                T.UserId <> S.UserId OR
                ISNULL(T.UserName, '') <> ISNULL(S.UserName, '') OR
                ISNULL(T.Licencia, '') <> ISNULL(S.Licencia, '') OR
                T.Activo_SAM <> S.Activo_SAM
            )
        THEN
            UPDATE SET
                T.Equipo = S.Equipo,
                T.UserId = S.UserId,
                T.UserName = S.UserName,
                T.Licencia = S.Licencia,
                T.Activo_SAM = S.Activo_SAM
                -- NOTA: No tocamos PoolId ni PermiteBalanceoDinamico aquí.

        -- 5b. Cuando es un equipo 100% nuevo (nunca visto)
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (EquipoId, Equipo, UserId, UserName, Licencia, Activo_SAM)
            VALUES (S.EquipoId, S.Equipo, S.UserId, S.UserName, S.Licencia, S.Activo_SAM)
            -- Se inserta con los valores por defecto de SAM (PoolId NULL, PermiteBalanceo 0)

        -- 5c. Opcional: Desactivar equipos que ya no vienen de A360
        --WHEN NOT MATCHED BY SOURCE AND T.Activo_SAM = 1 THEN
        --    UPDATE SET T.Activo_SAM = 0

        ;COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;

        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'dbo.MergeEquipos', @ErrorMessage, 'Input: @EquipoList (TVP)');

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[MergeRobots] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:      LP
-- Create date: 2025-08-01
-- Description: Sincroniza (actualiza o inserta) la tabla dbo.Robots
--              usando una lista de robots proporcionada como un TVP.
--              Sigue el estándar de manejo de errores y transacciones.
-- =============================================
CREATE PROCEDURE [dbo].[MergeRobots]
    @RobotList dbo.RobotListType READONLY
AS
BEGIN
    -- --- Adiciones para robustez y estándar ---
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- --- Lógica principal del MERGE ---
        MERGE dbo.Robots AS TARGET
        USING @RobotList AS SOURCE
        ON (TARGET.RobotId = SOURCE.RobotId)

        -- CUANDO EL ROBOT YA EXISTE Y ALGO CAMBIÓ
        WHEN MATCHED AND (TARGET.Robot <> SOURCE.Robot OR ISNULL(TARGET.Descripcion, '') <> ISNULL(SOURCE.Descripcion, '')) THEN
            UPDATE SET
                TARGET.Robot = SOURCE.Robot,
                TARGET.Descripcion = SOURCE.Descripcion

        -- CUANDO EL ROBOT ES NUEVO
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (RobotId, Robot, Descripcion)
            VALUES (SOURCE.RobotId, SOURCE.Robot, SOURCE.Descripcion);
            -- Las demás columnas se llenan con los valores DEFAULT de la tabla.

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        -- --- Manejo de errores estándar ---
        -- Si hay una transacción activa, se revierte.
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        -- Declaración de variables para el mensaje de error
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();

        -- Insertar el error en la tabla de log
        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'dbo.MergeRobots', @ErrorMessage, 'Input: @RobotList (Table-Valued Parameter)');

        -- Relanzar el error para que la aplicación cliente lo reciba
        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[ObtenerDashboardBalanceador] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:      Sistema SAM
-- Create date: 2025-08-22
-- Description: Genera datos para el dashboard de análisis del balanceador
--              Proporciona métricas de rendimiento y actividad del sistema
-- Modified:    2025-10-16 - Corrección de duplicación de robots
-- =============================================
CREATE PROCEDURE [dbo].[ObtenerDashboardBalanceador]
    @FechaInicio DATETIME2(0) = NULL,
    @FechaFin DATETIME2(0) = NULL,
    @PoolId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Establecer fechas por defecto si no se proporcionan
    IF @FechaInicio IS NULL
        SET @FechaInicio = DATEADD(DAY, -30, GETDATE()); 
    
    IF @FechaFin IS NULL
        SET @FechaFin = GETDATE();

    BEGIN TRY
        -- =============================================
        -- RESULT SET 1: MÉTRICAS GENERALES (CORREGIDO)
        -- =============================================
        SELECT
            'METRICAS_GENERALES' AS TipoResultado,
            COUNT(*) AS TotalAcciones,
            
            -- Clasificación con prioridad: DESASIGNAR primero, luego ASIGNAR
            -- Esto evita que "DESASIGNAR" se cuente como "ASIGNAR"
            SUM(CASE 
                WHEN AccionTomada LIKE 'DESASIGNAR%' OR AccionTomada LIKE '%QUITAR%' THEN 0
                WHEN AccionTomada LIKE 'ASIGNAR%' OR AccionTomada LIKE '%AGREGAR%' THEN 1 
                ELSE 0 
            END) AS TotalAsignaciones,
            
            SUM(CASE 
                WHEN AccionTomada LIKE 'DESASIGNAR%' OR AccionTomada LIKE '%QUITAR%' THEN 1 
                ELSE 0 
            END) AS TotalDesasignaciones,
            
            -- Nueva métrica: acciones no clasificadas
            SUM(CASE 
                WHEN AccionTomada NOT LIKE 'ASIGNAR%'
                 AND AccionTomada NOT LIKE 'DESASIGNAR%' 
                 AND AccionTomada NOT LIKE '%AGREGAR%'
                 AND AccionTomada NOT LIKE '%QUITAR%' 
                THEN 1 
                ELSE 0 
            END) AS AccionesOtras,
            
            -- Métricas basadas en el delta real de equipos
            SUM(CASE WHEN (EquiposAsignadosDespues - EquiposAsignadosAntes) > 0 THEN 1 ELSE 0 END) AS AsignacionesReales,
            SUM(CASE WHEN (EquiposAsignadosDespues - EquiposAsignadosAntes) < 0 THEN 1 ELSE 0 END) AS DesasignacionesReales,
            SUM(CASE WHEN (EquiposAsignadosDespues - EquiposAsignadosAntes) = 0 THEN 1 ELSE 0 END) AS AccionesSinCambio,
            
            AVG(CAST(EquiposAsignadosDespues - EquiposAsignadosAntes AS FLOAT)) AS PromedioMovimientoNeto,
            COUNT(DISTINCT RobotId) AS RobotsAfectados,
            AVG(CAST(TicketsPendientes AS FLOAT)) AS PromedioTicketsPendientes
        FROM HistoricoBalanceo
        WHERE FechaBalanceo BETWEEN @FechaInicio AND @FechaFin
            AND (@PoolId IS NULL OR PoolId = @PoolId);

        -- =============================================
        -- RESULT SET 2: TRAZABILIDAD PARA EL GRÁFICO
        -- =============================================
        SELECT
            'TRAZABILIDAD' AS TipoResultado,
            FORMAT(H.FechaBalanceo, 'yyyy-MM-dd HH:mm:ss') AS Timestamp,
            H.RobotId,
            R.Robot AS RobotNombre,
            H.AccionTomada AS Accion,
            H.EquiposAsignadosAntes,
            H.EquiposAsignadosDespues,
            (H.EquiposAsignadosDespues - H.EquiposAsignadosAntes) AS MovimientoNeto,
            H.TicketsPendientes,
            H.Justificacion
        FROM HistoricoBalanceo H
        INNER JOIN Robots R ON H.RobotId = R.RobotId  -- INNER JOIN para evitar nulls
        WHERE H.FechaBalanceo BETWEEN @FechaInicio AND @FechaFin
            AND (@PoolId IS NULL OR H.PoolId = @PoolId)
        ORDER BY H.FechaBalanceo ASC;

        -- =============================================
        -- RESULT SET 3: RESUMEN DIARIO
        -- =============================================
        SELECT
            'RESUMEN_DIARIO' AS TipoResultado,
            CAST(FechaBalanceo AS DATE) AS Fecha,
            COUNT(*) AS TotalAcciones,
            SUM(CASE WHEN AccionTomada LIKE 'DESASIGNAR%' OR AccionTomada LIKE '%QUITAR%' THEN 0
                     WHEN AccionTomada LIKE 'ASIGNAR%' OR AccionTomada LIKE '%AGREGAR%' THEN 1 
                     ELSE 0 END) AS Asignaciones,
            SUM(CASE WHEN AccionTomada LIKE 'DESASIGNAR%' OR AccionTomada LIKE '%QUITAR%' THEN 1 
                     ELSE 0 END) AS Desasignaciones,
            AVG(CAST(TicketsPendientes AS FLOAT)) AS PromedioTickets,
            COUNT(DISTINCT RobotId) AS RobotsActivos
        FROM HistoricoBalanceo
        WHERE FechaBalanceo BETWEEN @FechaInicio AND @FechaFin
            AND (@PoolId IS NULL OR PoolId = @PoolId)
        GROUP BY CAST(FechaBalanceo AS DATE)
        ORDER BY Fecha ASC;

        -- =============================================
        -- RESULT SET 4: ANÁLISIS POR ROBOT (CORREGIDO)
        -- =============================================
        SELECT
            'ANALISIS_ROBOTS' AS TipoResultado,
            R.RobotId,
            R.Robot AS RobotNombre,
            ISNULL(Stats.TotalAcciones, 0) AS TotalAcciones,
            ISNULL(Stats.Asignaciones, 0) AS Asignaciones,
            ISNULL(Stats.Desasignaciones, 0) AS Desasignaciones,
            ISNULL(Stats.PromedioEquiposAntes, 0) AS PromedioEquiposAntes,
            ISNULL(Stats.PromedioEquiposDespues, 0) AS PromedioEquiposDespues,
            ISNULL(Stats.PromedioTickets, 0) AS PromedioTickets,
            Stats.UltimaAccion,
            ISNULL(Stats.CambiosEquipos, 0) AS CambiosEquipos
        FROM Robots R
        LEFT JOIN (
            SELECT 
                H.RobotId,
                COUNT(*) AS TotalAcciones,
                SUM(CASE WHEN H.AccionTomada LIKE 'DESASIGNAR%' OR H.AccionTomada LIKE '%QUITAR%' THEN 0
                         WHEN H.AccionTomada LIKE 'ASIGNAR%' OR H.AccionTomada LIKE '%AGREGAR%' THEN 1 
                         ELSE 0 END) AS Asignaciones,
                SUM(CASE WHEN H.AccionTomada LIKE 'DESASIGNAR%' OR H.AccionTomada LIKE '%QUITAR%' THEN 1 
                         ELSE 0 END) AS Desasignaciones,
                AVG(CAST(H.EquiposAsignadosAntes AS FLOAT)) AS PromedioEquiposAntes,
                AVG(CAST(H.EquiposAsignadosDespues AS FLOAT)) AS PromedioEquiposDespues,
                AVG(CAST(H.TicketsPendientes AS FLOAT)) AS PromedioTickets,
                MAX(H.FechaBalanceo) AS UltimaAccion,
                SUM(CASE WHEN ABS(H.EquiposAsignadosDespues - H.EquiposAsignadosAntes) > 0 THEN 1 ELSE 0 END) AS CambiosEquipos
            FROM HistoricoBalanceo H
            WHERE H.FechaBalanceo BETWEEN @FechaInicio AND @FechaFin
                AND (@PoolId IS NULL OR H.PoolId = @PoolId)
            GROUP BY H.RobotId
        ) Stats ON R.RobotId = Stats.RobotId
        WHERE R.Activo = 1  -- Solo robots activos
            AND (@PoolId IS NULL OR R.PoolId = @PoolId)
            AND Stats.TotalAcciones IS NOT NULL  -- Solo incluir robots con actividad
        ORDER BY Stats.TotalAcciones DESC;

        -- =============================================
        -- RESULT SET 5: ESTADO ACTUAL DEL SISTEMA (CORREGIDO)
        -- =============================================
        SELECT
            'ESTADO_ACTUAL' AS TipoResultado,
            (SELECT COUNT(*) FROM Robots WHERE Activo = 1 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS RobotsActivos,
            (SELECT COUNT(*) FROM Robots WHERE EsOnline = 1 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS RobotsOnline,
            (SELECT COUNT(*) FROM Equipos WHERE Activo_SAM = 1 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS EquiposActivos,
            (SELECT COUNT(*) FROM Equipos WHERE PermiteBalanceoDinamico = 1 AND (@PoolId IS NULL OR PoolId = @PoolId)) AS EquiposBalanceables,
            (SELECT COUNT(*) FROM Asignaciones A 
             INNER JOIN Robots R ON A.RobotId = R.RobotId 
             WHERE A.EsProgramado = 1 AND (@PoolId IS NULL OR R.PoolId = @PoolId)) AS AsignacionesProgramadas,
            (SELECT COUNT(*) FROM Asignaciones A 
             INNER JOIN Robots R ON A.RobotId = R.RobotId 
             WHERE A.Reservado = 1 AND (@PoolId IS NULL OR R.PoolId = @PoolId)) AS AsignacionesReservadas,
            (SELECT COUNT(*) FROM Ejecuciones E 
             INNER JOIN Robots R ON E.RobotId = R.RobotId 
             WHERE E.Estado IN ('DEPLOYED', 'RUNNING', 'QUEUED', 'PENDING_EXECUTION') 
             AND (@PoolId IS NULL OR R.PoolId = @PoolId)) AS EjecucionesActivas;

        -- =============================================
        -- RESULT SET 6: DETECCIÓN DE THRASHING
        -- =============================================
        WITH ThrashingAnalysis AS (
            SELECT 
                RobotId,
                FechaBalanceo,
                AccionTomada,
                EquiposAsignadosAntes,
                EquiposAsignadosDespues,
                LAG(AccionTomada) OVER (PARTITION BY RobotId ORDER BY FechaBalanceo) AS AccionAnterior,
                LAG(FechaBalanceo) OVER (PARTITION BY RobotId ORDER BY FechaBalanceo) AS FechaAnterior,
                DATEDIFF(MINUTE, LAG(FechaBalanceo) OVER (PARTITION BY RobotId ORDER BY FechaBalanceo), FechaBalanceo) AS MinutosDesdeUltimaAccion
            FROM HistoricoBalanceo
            WHERE FechaBalanceo BETWEEN @FechaInicio AND @FechaFin
                AND (@PoolId IS NULL OR PoolId = @PoolId)
        )
        SELECT
            'THRASHING_EVENTS' AS TipoResultado,
            COUNT(*) AS EventosThrashing,
            COUNT(DISTINCT RobotId) AS RobotsAfectados,
            AVG(CAST(MinutosDesdeUltimaAccion AS FLOAT)) AS PromedioMinutosEntreAcciones
        FROM ThrashingAnalysis
        WHERE MinutosDesdeUltimaAccion <= 5 
            AND ((AccionTomada LIKE '%ASIGNAR%' AND AccionAnterior LIKE '%DESASIGNAR%')
                 OR (AccionTomada LIKE '%DESASIGNAR%' AND AccionAnterior LIKE '%ASIGNAR%'));

    END TRY
    BEGIN CATCH
        -- Manejo de errores
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @Parametros NVARCHAR(MAX) = FORMATMESSAGE(
            '@FechaInicio=%s, @FechaFin=%s, @PoolId=%s',
            ISNULL(CONVERT(NVARCHAR(20), @FechaInicio, 120), 'NULL'),
            ISNULL(CONVERT(NVARCHAR(20), @FechaFin, 120), 'NULL'),
            ISNULL(CAST(@PoolId AS NVARCHAR(10)), 'NULL')
        );

        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'ObtenerDashboardBalanceador', @ErrorMessage, @Parametros);

        THROW;
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[ObtenerDashboardCallbacks] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Stored Procedure: ObtenerDashboardCallbacks
-- Descripción: Genera métricas agregadas sobre el rendimiento del sistema
--              de callbacks vs conciliador basándose en la vista AnalisisRendimientoCallbacks
-- Autor: Sistema SAM
-- Fecha: 2025-09-25
-- =============================================

CREATE PROCEDURE [dbo].[ObtenerDashboardCallbacks]
    @FechaInicio DATETIME2(0) = NULL,
    @FechaFin DATETIME2(0) = NULL,
    @RobotId INT = NULL,
    @IncluirDetalleHorario BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Establecer fechas por defecto si no se proporcionan
    IF @FechaInicio IS NULL
        SET @FechaInicio = DATEADD(DAY, -7, GETDATE()); -- Últimos 7 días por defecto
    
    IF @FechaFin IS NULL
        SET @FechaFin = GETDATE();

    BEGIN TRY
        -- =============================================
        -- RESULT SET 1: MÉTRICAS GENERALES DEL SISTEMA
        -- =============================================
        SELECT
            'METRICAS_GENERALES' AS TipoResultado,
            
            -- Totales por mecanismo de finalización
            COUNT(*) AS TotalEjecuciones,
            SUM(EsCallbackExitoso) AS CallbacksExitosos,
            SUM(EsConciliadorExitoso) AS ConciliadorExitosos,
            SUM(EsConciliadorAgotado) AS ConciliadorAgotados,
            COUNT(CASE WHEN MecanismoFinalizacion = 'ACTIVA' THEN 1 END) AS EjecucionesActivas,
            
            -- Porcentajes de efectividad
            CAST(SUM(EsCallbackExitoso) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeCallbackExitoso,
            CAST(SUM(EsConciliadorExitoso) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeConciliadorExitoso,
            CAST(SUM(EsConciliadorAgotado) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeConciliadorAgotado,
            
            -- Métricas de rendimiento
            AVG(CAST(LatenciaActualizacionMinutos AS FLOAT)) AS LatenciaPromedioMinutos,
            MAX(LatenciaActualizacionMinutos) AS LatenciaMaximaMinutos,
            MIN(LatenciaActualizacionMinutos) AS LatenciaMinimaMinutos,
            
            -- Indicadores de problemas
            SUM(CallbackFallidoIndicador) AS CallbacksFallidos,
            SUM(ConciliadorProblemaIndicador) AS ProblemasConciliador,
            CAST(SUM(CallbackFallidoIndicador) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeCallbacksFallidos,
            
            -- Métricas de duración de ejecuciones
            AVG(CAST(DuracionEjecucionMinutos AS FLOAT)) AS DuracionPromedioMinutos,
            MAX(DuracionEjecucionMinutos) AS DuracionMaximaMinutos,
            
            -- Salud del sistema
            SUM(EjecucionExitosa) AS EjecucionesExitosas,
            SUM(EjecucionFallida) AS EjecucionesFallidas,
            CAST(SUM(EjecucionExitosa) * 100.0 / NULLIF(SUM(EjecucionExitosa) + SUM(EjecucionFallida), 0) AS DECIMAL(5,2)) AS PorcentajeExito
            
        FROM dbo.AnalisisRendimientoCallbacks
        WHERE FechaInicio BETWEEN @FechaInicio AND @FechaFin
            AND (@RobotId IS NULL OR RobotId = @RobotId);

        -- =============================================
        -- RESULT SET 2: DISTRIBUCIÓN POR CLASIFICACIÓN DE RENDIMIENTO
        -- =============================================
        SELECT
            'RENDIMIENTO_DISTRIBUCION' AS TipoResultado,
            ClasificacionRendimiento,
            COUNT(*) AS Cantidad,
            CAST(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS DECIMAL(5,2)) AS Porcentaje,
            AVG(CAST(LatenciaActualizacionMinutos AS FLOAT)) AS LatenciaPromedioMinutos
        FROM dbo.AnalisisRendimientoCallbacks
        WHERE FechaInicio BETWEEN @FechaInicio AND @FechaFin
            AND (@RobotId IS NULL OR RobotId = @RobotId)
            AND ClasificacionRendimiento != 'NO_APLICABLE'
        GROUP BY ClasificacionRendimiento
        ORDER BY 
            CASE ClasificacionRendimiento
                WHEN 'EXCELENTE' THEN 1
                WHEN 'BUENO' THEN 2
                WHEN 'REGULAR' THEN 3
                WHEN 'DEFICIENTE' THEN 4
            END;

        -- =============================================
        -- RESULT SET 3: ANÁLISIS POR ROBOT
        -- =============================================
        SELECT
            'ANALISIS_POR_ROBOT' AS TipoResultado,
            R.RobotId,
            R.Robot AS RobotNombre,
            COUNT(*) AS TotalEjecuciones,
            SUM(A.EsCallbackExitoso) AS CallbacksExitosos,
            SUM(A.EsConciliadorExitoso) AS ConciliadorExitosos,
            SUM(A.EsConciliadorAgotado) AS ConciliadorAgotados,
            CAST(SUM(A.EsCallbackExitoso) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeCallbackExito,
            AVG(CAST(A.LatenciaActualizacionMinutos AS FLOAT)) AS LatenciaPromedioMinutos,
            AVG(CAST(A.DuracionEjecucionMinutos AS FLOAT)) AS DuracionPromedioMinutos,
            SUM(A.CallbackFallidoIndicador) AS CallbacksFallidos,
            SUM(A.EjecucionExitosa) AS EjecucionesExitosas,
            CAST(SUM(A.EjecucionExitosa) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeExito
        FROM dbo.AnalisisRendimientoCallbacks A
        INNER JOIN dbo.Robots R ON A.RobotId = R.RobotId
        WHERE A.FechaInicio BETWEEN @FechaInicio AND @FechaFin
            AND (@RobotId IS NULL OR A.RobotId = @RobotId)
        GROUP BY R.RobotId, R.Robot
        HAVING COUNT(*) >= 5 -- Solo robots con al menos 5 ejecuciones
        ORDER BY COUNT(*) DESC;

        -- =============================================
        -- RESULT SET 4: TENDENCIA DIARIA
        -- =============================================
        SELECT
            'TENDENCIA_DIARIA' AS TipoResultado,
            CAST(FechaInicio AS DATE) AS Fecha,
            COUNT(*) AS TotalEjecuciones,
            SUM(EsCallbackExitoso) AS CallbacksExitosos,
            SUM(EsConciliadorExitoso) AS ConciliadorExitosos,
            SUM(EsConciliadorAgotado) AS ConciliadorAgotados,
            AVG(CAST(LatenciaActualizacionMinutos AS FLOAT)) AS LatenciaPromedioMinutos,
            AVG(CAST(DuracionEjecucionMinutos AS FLOAT)) AS DuracionPromedioMinutos,
            SUM(CallbackFallidoIndicador) AS CallbacksFallidos,
            CAST(SUM(EsCallbackExitoso) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeCallbackExito
        FROM dbo.AnalisisRendimientoCallbacks
        WHERE FechaInicio BETWEEN @FechaInicio AND @FechaFin
            AND (@RobotId IS NULL OR RobotId = @RobotId)
        GROUP BY CAST(FechaInicio AS DATE)
        ORDER BY Fecha ASC;

        -- =============================================
        -- RESULT SET 5: ANÁLISIS HORARIO (si se solicita)
        -- =============================================
        IF @IncluirDetalleHorario = 1
        BEGIN
            SELECT
                'PATRON_HORARIO' AS TipoResultado,
                DATEPART(HOUR, FechaInicio) AS Hora,
                COUNT(*) AS TotalEjecuciones,
                SUM(EsCallbackExitoso) AS CallbacksExitosos,
                SUM(EsConciliadorExitoso) AS ConciliadorExitosos,
                AVG(CAST(LatenciaActualizacionMinutos AS FLOAT)) AS LatenciaPromedioMinutos,
                SUM(CallbackFallidoIndicador) AS CallbacksFallidos,
                CAST(SUM(EsCallbackExitoso) * 100.0 / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS PorcentajeCallbackExito
            FROM dbo.AnalisisRendimientoCallbacks
            WHERE FechaInicio BETWEEN @FechaInicio AND @FechaFin
                AND (@RobotId IS NULL OR RobotId = @RobotId)
            GROUP BY DATEPART(HOUR, FechaInicio)
            ORDER BY Hora;
        END

        -- =============================================
        -- RESULT SET 6: CASOS PROBLEMÁTICOS RECIENTES
        -- =============================================
        SELECT TOP 20
            'CASOS_PROBLEMATICOS' AS TipoResultado,
            EjecucionId,
            DeploymentId,
            R.Robot AS RobotNombre,
            E.Equipo AS EquipoNombre,
            FechaInicio,
            FechaFin,
            Estado,
            MecanismoFinalizacion,
            LatenciaActualizacionMinutos,
            IntentosConciliadorFallidos,
            ClasificacionRendimiento,
            CASE 
                WHEN CallbackFallidoIndicador = 1 AND ConciliadorProblemaIndicador = 1 
                THEN 'CALLBACK_Y_CONCILIADOR_PROBLEMA'
                WHEN CallbackFallidoIndicador = 1 
                THEN 'CALLBACK_FALLIDO'
                WHEN ConciliadorProblemaIndicador = 1 
                THEN 'CONCILIADOR_PROBLEMA'
                WHEN MecanismoFinalizacion = 'CONCILIADOR_AGOTADO'
                THEN 'CONCILIADOR_AGOTADO'
                ELSE 'OTRO'
            END AS TipoProblema
        FROM dbo.AnalisisRendimientoCallbacks A
        LEFT JOIN dbo.Robots R ON A.RobotId = R.RobotId
        LEFT JOIN dbo.Equipos E ON A.EquipoId = E.EquipoId
        WHERE A.FechaInicio BETWEEN @FechaInicio AND @FechaFin
            AND (@RobotId IS NULL OR A.RobotId = @RobotId)
            AND (A.CallbackFallidoIndicador = 1 
                 OR A.ConciliadorProblemaIndicador = 1 
                 OR A.MecanismoFinalizacion = 'CONCILIADOR_AGOTADO'
                 OR A.ClasificacionRendimiento = 'DEFICIENTE')
        ORDER BY A.FechaInicio DESC;

    END TRY
    BEGIN CATCH
        -- Manejo de errores
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @Parametros NVARCHAR(MAX) = FORMATMESSAGE(
            '@FechaInicio=%s, @FechaFin=%s, @RobotId=%s, @IncluirDetalleHorario=%s',
            ISNULL(CONVERT(NVARCHAR(20), @FechaInicio, 120), 'NULL'),
            ISNULL(CONVERT(NVARCHAR(20), @FechaFin, 120), 'NULL'),
            ISNULL(CAST(@RobotId AS NVARCHAR(10)), 'NULL'),
            ISNULL(CAST(@IncluirDetalleHorario AS NVARCHAR(1)), 'NULL')
        );

        INSERT INTO dbo.ErrorLog (Usuario, SPNombre, ErrorMensaje, Parametros)
        VALUES (SUSER_NAME(), 'ObtenerDashboardCallbacks', @ErrorMessage, @Parametros);

        THROW;
    END CATCH
END
GO
/****** Object:  StoredProcedure [dbo].[ObtenerEquiposDisponiblesParaRobot] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- Modificamos el Stored Procedure existente
CREATE PROCEDURE [dbo].[ObtenerEquiposDisponiblesParaRobot]
    @RobotId INT  -- Mantenemos el parámetro aunque ya no se use en la lógica,
                  -- para no tener que modificar el código de Python.
AS
BEGIN
    SET NOCOUNT ON;

    -- REGLAS DE NEGOCIO ACTUALIZADAS:
    -- Un equipo está disponible para una NUEVA PROGRAMACIÓN si:
    -- 1. Está Activo_SAM = 1
    -- 2. Tiene la licencia correcta ('ATTENDEDRUNTIME' o 'RUNTIME')
    -- 3. NO está 'Reservado = 1'
    -- 4. NO está asignado dinámicamente (EsProgramado = 0 AND Reservado = 0)
    --
    -- NOTA: Se elimina la restricción que impedía asignarlo si ya
    -- estaba programado (EsProgramado = 1) para este mismo robot.

    WITH EquiposNoDisponibles AS (
        -- Equipos reservados manualmente o asignados dinámicamente por CUALQUIER robot
        SELECT DISTINCT EquipoId
        FROM dbo.Asignaciones
        WHERE 
            Reservado = 1 
            OR (EsProgramado = 0 AND Reservado = 0)
    )
    SELECT 
        E.EquipoId, 
        E.Equipo
    FROM dbo.Equipos E
    WHERE 
        E.Activo_SAM = 1
        AND E.Licencia IN ('ATTENDEDRUNTIME', 'RUNTIME')
        AND E.EquipoId NOT IN (SELECT EquipoId FROM EquiposNoDisponibles)
    ORDER BY 
        E.Equipo;
END
GO
/****** Object:  StoredProcedure [dbo].[ObtenerRecursosParaPool] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO


-- Corrección definitiva para el Stored Procedure ObtenerRecursosParaPool
-- Selecciona la columna de ID correcta para cada tipo de recurso y la renombra a 'ID'.

CREATE PROCEDURE [dbo].[ObtenerRecursosParaPool]
    @PoolId INT
AS
BEGIN
    SET NOCOUNT ON;

    -- Primer result set: Recursos ASIGNADOS
    -- Se selecciona RobotId o EquipoId según corresponda y se aliasa como 'ID'
    SELECT RobotId AS ID, Robot AS Nombre, 'Robot' as Tipo FROM dbo.Robots WHERE PoolId = @PoolId
    UNION ALL
    SELECT EquipoId AS ID, Equipo AS Nombre, 'Equipo' as Tipo FROM dbo.Equipos WHERE PoolId = @PoolId;

    -- Segundo result set: Recursos DISPONIBLES
    -- Se hace lo mismo para los recursos sin pool
    SELECT RobotId AS ID, Robot AS Nombre, 'Robot' as Tipo FROM dbo.Robots WHERE PoolId IS NULL AND Activo = 1
    UNION ALL
    SELECT EquipoId AS ID, Equipo AS Nombre, 'Equipo' as Tipo FROM dbo.Equipos WHERE PoolId IS NULL AND Activo_SAM = 1;

END
GO
/****** Object:  StoredProcedure [dbo].[ObtenerRobotsDetalle] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[ObtenerRobotsDetalle]
    @Robot NVARCHAR(100) = NULL,
    @PoolId INT = NULL,
    @ActivoSAM NVARCHAR(5) = 'todos', -- 'true', 'false', 'todos'
    @EsOnline NVARCHAR(5) = 'todos'  -- 'true', 'false', 'todos'
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Manejo de NULL para el string de búsqueda
    DECLARE @SearchRobot NVARCHAR(102) = CASE WHEN @Robot IS NULL THEN '%' ELSE '%' + @Robot + '%' END;
    
    -- Manejo de filtros booleanos
    DECLARE @FilterActivoSAM BIT = CASE @ActivoSAM WHEN 'true' THEN 1 WHEN 'false' THEN 0 ELSE NULL END;
    DECLARE @FilterEsOnline BIT = CASE @EsOnline WHEN 'true' THEN 1 WHEN 'false' THEN 0 ELSE NULL END;

    SELECT
        R.RobotId,
        R.Robot,
        R.Descripcion,
        R.EsOnline,
        R.Activo AS ActivoSAM,
        
        -- Campos reales de dbo.Robots
        ISNULL(PL.Nombre, 'Sin Asignar') AS Pool,
        ISNULL(R.PoolId, 0) AS PoolId,
        R.PrioridadBalanceo AS Prioridad,
        
        -- Corrección del bug de conteo usando subconsultas
        ISNULL(ProgCounts.CantidadProgramaciones, 0) AS CantidadProgramaciones,
        ISNULL(EquipoCounts.CantidadEquiposAsignados, 0) AS CantidadEquiposAsignados
        
    FROM
        dbo.Robots AS R
    LEFT JOIN
        -- Unir con la tabla real dbo.Pools y usar el campo real 'Nombre'
        dbo.Pools AS PL ON R.PoolId = PL.PoolId
        
    -- Subconsulta aislada para contar programaciones
    OUTER APPLY (
        SELECT COUNT(DISTINCT A_prog.ProgramacionId) AS CantidadProgramaciones
        FROM dbo.Asignaciones AS A_prog
        INNER JOIN dbo.Programaciones AS P ON A_prog.ProgramacionId = P.ProgramacionId
        WHERE A_prog.RobotId = R.RobotId AND P.Activo = 1
    ) AS ProgCounts

    -- Subconsulta aislada para contar equipos
    OUTER APPLY (
        SELECT COUNT(DISTINCT A_eq.EquipoId) AS CantidadEquiposAsignados
        FROM dbo.Asignaciones AS A_eq
        WHERE A_eq.RobotId = R.RobotId
    ) AS EquipoCounts

    WHERE
        -- Filtros (quitamos los campos que no existen como Activo_A360)
        (R.Robot LIKE @SearchRobot OR R.Descripcion LIKE @SearchRobot)
        AND (@PoolId IS NULL OR R.PoolId = @PoolId) -- Filtrar por el PoolId del Robot
        AND (@FilterActivoSAM IS NULL OR R.Activo = @FilterActivoSAM)
        AND (@FilterEsOnline IS NULL OR R.EsOnline = @FilterEsOnline)
    ORDER BY
        R.Robot;
END
GO
/****** Object:  StoredProcedure [dbo].[ObtenerRobotsEjecutables] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE PROCEDURE [dbo].[ObtenerRobotsEjecutables]
AS
BEGIN
    SET NOCOUNT ON;
    -- Configurar el idioma español
    SET LANGUAGE Spanish;

    DECLARE @FechaActual DATETIME = GETDATE();
    DECLARE @HoraActual TIME(0) = CAST(@FechaActual AS TIME(0));
    

    -- 1. Obtener el día actual (ej. 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do')
    DECLARE @DiaSemanaActual NVARCHAR(2) = LEFT(DATENAME(WEEKDAY, @FechaActual), 2);
    
    -- 2. Estandarizar el día actual a MAYÚSCULAS y SIN ACENTOS
    -- Convertimos 'Sá' (Sábado) a 'SA'
    SET @DiaSemanaActual = UPPER(@DiaSemanaActual COLLATE Latin1_General_CI_AI);
    -- NOTA: COLLATE Latin1_General_CI_AI maneja tanto mayúsculas como acentos.
    -- 'Sá' se convierte en 'SA'
    


    -- Tabla temporal para almacenar los resultados
    CREATE TABLE #ResultadosRobots (
        RobotId INT,
        EquipoId INT,
        UserId INT,
        Hora TIME(0),
        EsProgramado BIT
    );

    -- Insertar robots programados elegibles
    INSERT INTO #ResultadosRobots (RobotId, EquipoId, UserId, Hora, EsProgramado)
    SELECT 
        R.RobotId,
        A.EquipoId,
        E.UserId,
        P.HoraInicio,
        1 AS EsProgramado
    FROM Robots R
    INNER JOIN Asignaciones A ON R.RobotId = A.RobotId
    INNER JOIN Equipos E ON A.EquipoId = E.EquipoId
    -- Unir Asignaciones con la Programacion específica que le corresponde
    INNER JOIN Programaciones P ON A.ProgramacionId = P.ProgramacionId -- <<<< CAMBIO CLAVE
    WHERE 
        A.EsProgramado = 1
        AND R.Activo = 1
        AND P.Activo = 1 -- Asegurarse de que la programación esté activa
        -- 1. Lógica de Tiempos (Ventana de Tolerancia)
        AND (
            (P.TipoProgramacion = 'Diaria' AND @HoraActual BETWEEN P.HoraInicio AND DATEADD(MINUTE, P.Tolerancia, P.HoraInicio))
            OR (
                P.TipoProgramacion = 'Semanal' 
                AND (UPPER(P.DiasSemana COLLATE Latin1_General_CI_AI) LIKE '%' + @DiaSemanaActual + '%')
                AND @HoraActual BETWEEN P.HoraInicio AND DATEADD(MINUTE, P.Tolerancia, P.HoraInicio)
            )
            OR (P.TipoProgramacion = 'Mensual' AND P.DiaDelMes = DAY(@FechaActual) AND @HoraActual BETWEEN P.HoraInicio AND DATEADD(MINUTE, P.Tolerancia, P.HoraInicio))
            OR (P.TipoProgramacion = 'Especifica' AND P.FechaEspecifica = CAST(@FechaActual AS DATE) AND @HoraActual BETWEEN P.HoraInicio AND DATEADD(MINUTE, P.Tolerancia, P.HoraInicio))
        )
        -- 2. No ejecutar si ya se ejecutó hoy para esa hora específica
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones E
            WHERE E.RobotId = R.RobotId
              AND E.EquipoId = A.EquipoId
              AND CAST(E.FechaInicio AS DATE) = CAST(@FechaActual AS DATE)
              AND E.Hora = P.HoraInicio
        )
        -- 3. No ejecutar si el equipo ya está ocupado
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones E
            WHERE E.EquipoId = A.EquipoId 
			  AND (
                 -- 1. Sigue siendo un estado activo conocido
                 E.Estado IN ('DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 'RUNNING', 'UPDATE', 'RUN_PAUSED')
                 OR
                 -- 2. O es UNKNOWN, pero es RECIENTE (aún no lo consideramos final)
                 (E.Estado = 'UNKNOWN' AND E.FechaUltimoUNKNOWN > DATEADD(HOUR, -2, GETDATE()))
            )
        )
        -- 4. (Solución anterior ahora innecesaria, pero se deja por seguridad)
        AND NOT EXISTS ( 
            SELECT 1
            FROM #ResultadosRobots RR
            WHERE RR.EquipoId = A.EquipoId
        );


    -- Insertar robots online elegibles para equipos sin robots programados o en ejecución
    INSERT INTO #ResultadosRobots (RobotId, EquipoId, UserId, Hora, EsProgramado)
    SELECT 
        R.RobotId,
        A.EquipoId,
        E.UserId,
        NULL AS Hora,
        0 AS EsProgramado
    FROM Robots R
    INNER JOIN Asignaciones A ON R.RobotId = A.RobotId
    INNER JOIN Equipos E ON A.EquipoId = E.EquipoId
    WHERE 
        R.EsOnline = 1
        AND R.Activo = 1
        AND A.EsProgramado = 0
        AND NOT EXISTS ( -- no repetir equipo ya asignado
            SELECT 1
            FROM #ResultadosRobots RR
            WHERE RR.EquipoId = A.EquipoId
        )
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones E
            WHERE 1=1
                AND E.EquipoId = A.EquipoId 
				AND (
                 -- 1. Sigue siendo un estado activo conocido
                 E.Estado IN ('DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 'RUNNING', 'UPDATE', 'RUN_PAUSED')
                 OR
                 -- 2. O es UNKNOWN, pero es RECIENTE (aún no lo consideramos final)
                 (E.Estado = 'UNKNOWN' AND E.FechaUltimoUNKNOWN > DATEADD(HOUR, -2, GETDATE()))
            )
        );

    -- Devolver los resultados
    SELECT RobotId, EquipoId, UserId, Hora
    FROM #ResultadosRobots
    ORDER BY EsProgramado DESC, Hora;

    -- Limpiar la tabla temporal
    DROP TABLE #ResultadosRobots;
END
GO
/****** Object:  StoredProcedure [dbo].[ObtenerRobotsEjecutables_old] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE PROCEDURE [dbo].[ObtenerRobotsEjecutables_old]
AS
BEGIN
    SET NOCOUNT ON;
    -- Configurar el idioma español
    SET LANGUAGE Spanish;

    DECLARE @FechaActual DATETIME = GETDATE();
    DECLARE @HoraActual TIME(0) = CAST(@FechaActual AS TIME(0));
    

    -- 1. Obtener el día actual (ej. 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do')
    DECLARE @DiaSemanaActual NVARCHAR(2) = LEFT(DATENAME(WEEKDAY, @FechaActual), 2);
    
    -- 2. Estandarizar el día actual a MAYÚSCULAS y SIN ACENTOS
    -- Convertimos 'Sá' (Sábado) a 'SA'
    SET @DiaSemanaActual = UPPER(@DiaSemanaActual COLLATE Latin1_General_CI_AI);
    -- NOTA: COLLATE Latin1_General_CI_AI maneja tanto mayúsculas como acentos.
    -- 'Sá' se convierte en 'SA'
    


    -- Tabla temporal para almacenar los resultados
    CREATE TABLE #ResultadosRobots (
        RobotId INT,
        EquipoId INT,
        UserId INT,
        Hora TIME(0),
        EsProgramado BIT
    )

    -- Insertar robots programados elegibles
    INSERT INTO #ResultadosRobots (RobotId, EquipoId, UserId, Hora, EsProgramado)
    SELECT 
        R.RobotId,
        A.EquipoId,
        E.UserId,
        P.HoraInicio,
        1 AS EsProgramado
    FROM Robots R
    INNER JOIN Asignaciones A ON R.RobotId = A.RobotId
    INNER JOIN Equipos E ON A.EquipoId = E.EquipoId
    INNER JOIN Programaciones P ON R.RobotId = P.RobotId
    WHERE 
        A.EsProgramado = 1
        AND R.Activo = 1
        AND (
            (P.TipoProgramacion = 'Diaria' AND @HoraActual BETWEEN P.HoraInicio AND DATEADD(MINUTE, P.Tolerancia, P.HoraInicio))
            
            -- 3. Comparar usando UPPER() y la misma intercalación (COLLATE)
            OR (
                P.TipoProgramacion = 'Semanal' 
                AND (
                    -- Compara 'LU,MA,MI...' con 'MI'
                    UPPER(P.DiasSemana COLLATE Latin1_General_CI_AI) LIKE '%' + @DiaSemanaActual + '%'
                )
                AND @HoraActual BETWEEN P.HoraInicio AND DATEADD(MINUTE, P.Tolerancia, P.HoraInicio)
            )
            
            OR (P.TipoProgramacion = 'Mensual' AND P.DiaDelMes = DAY(@FechaActual) AND @HoraActual BETWEEN P.HoraInicio AND DATEADD(MINUTE, P.Tolerancia, P.HoraInicio))
            OR (P.TipoProgramacion = 'Especifica' AND P.FechaEspecifica = CAST(@FechaActual AS DATE) AND @HoraActual BETWEEN P.HoraInicio AND DATEADD(MINUTE, P.Tolerancia, P.HoraInicio))
        )
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones E
            WHERE 1=1
				AND E.RobotId = R.RobotId
                AND E.EquipoId = A.EquipoId
                AND CAST(E.FechaInicio AS DATE) = CAST(@FechaActual AS DATE)
                AND E.Hora = P.HoraInicio
        )
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones E
            WHERE 1=1
				AND E.EquipoId = A.EquipoId 
				AND E.Estado in ('DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 'RUNNING', 'UPDATE','RUN_PAUSED')
        )
		AND NOT EXISTS ( -- no repetir equipo ya asignado
            SELECT 1
            FROM #ResultadosRobots RR
            WHERE RR.EquipoId = A.EquipoId
        )

    -- Insertar robots online elegibles para equipos sin robots programados o en ejecución
    INSERT INTO #ResultadosRobots (RobotId, EquipoId, UserId, Hora, EsProgramado)
    SELECT 
        R.RobotId,
        A.EquipoId,
        E.UserId,
        NULL AS Hora,
        0 AS EsProgramado
    FROM Robots R
    INNER JOIN Asignaciones A ON R.RobotId = A.RobotId
    INNER JOIN Equipos E ON A.EquipoId = E.EquipoId
    WHERE 
        R.EsOnline = 1
        AND R.Activo = 1
        AND A.EsProgramado = 0
        AND NOT EXISTS ( -- no repetir equipo ya asignado
            SELECT 1
            FROM #ResultadosRobots RR
            WHERE RR.EquipoId = A.EquipoId
        )
        AND NOT EXISTS (
            SELECT 1
            FROM Ejecuciones E
            WHERE 1=1
				AND E.EquipoId = A.EquipoId 
				AND E.Estado in ('DEPLOYED', 'QUEUED', 'PENDING_EXECUTION', 'RUNNING', 'UPDATE','RUN_PAUSED')
        )

    -- Devolver los resultados
    SELECT RobotId, EquipoId, UserId, Hora
    FROM #ResultadosRobots
    ORDER BY EsProgramado DESC, Hora

    -- Limpiar la tabla temporal
    DROP TABLE #ResultadosRobots
END
GO
/****** Object:  StoredProcedure [dbo].[usp_MoverEjecucionesAHistorico] ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE   PROCEDURE [dbo].[usp_MoverEjecucionesAHistorico]
    -- PARÁMETROS PARA MAYOR FLEXIBILIDAD
    @BatchSizeParam INT = 500,          -- Tamaño de los lotes para mover y purgar
    @DiasRetencionMover INT = 1,        -- Mover ejecuciones con más de X días de antigüedad
    @DiasRetencionPurga INT = 15,       -- Purgar del histórico ejecuciones con más de X días de antigüedad
    @MaxIterationsParam INT = 20000     -- Límite de seguridad para evitar bucles infinitos (muy alto por defecto)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @usuario VARCHAR(255) = SUSER_SNAME();
    
    -- =================================================================================
    -- PARTE 1: MOVER REGISTROS DE 'Ejecuciones' A 'Ejecuciones_Historico'
    -- =================================================================================
    
    DECLARE @rowsAffected INT = @BatchSizeParam;
    DECLARE @totalRowsMoved INT = 0;
    DECLARE @iterationCount INT = 0;
    
    DECLARE @EstadosFinalizados TABLE (Estado NVARCHAR(20) PRIMARY KEY);
    INSERT INTO @EstadosFinalizados (Estado) VALUES 
    ('DEPLOY_FAILED'), ('RUN_ABORTED'), ('COMPLETED'), 
    ('RUN_COMPLETED'), ('RUN_FAILED'), ('UNKNOWN');

    PRINT 'Iniciando proceso de movimiento de ejecuciones a la tabla histórica.';
    PRINT 'Tamaño de lote: ' + CAST(@BatchSizeParam AS VARCHAR(10));

    -- Bucle para procesar por lotes, ahora con el límite de iteraciones como parámetro de seguridad
    WHILE @rowsAffected = @BatchSizeParam AND @iterationCount < @MaxIterationsParam
    BEGIN
        SET @iterationCount = @iterationCount + 1;
        
        BEGIN TRY
            -- Usamos una tabla temporal para el lote, más segura que verificar con OBJECT_ID y hacer DROP/CREATE
            IF OBJECT_ID('tempdb..#LoteActual') IS NOT NULL DROP TABLE #LoteActual;
            
            -- Paso 1: Seleccionar el lote a procesar
            SELECT TOP (@BatchSizeParam)
                EjecucionId,
				DeploymentId,
                RobotId,
                EquipoId,
                UserId,
                Hora,
                FechaInicio,
                FechaFin,
                Estado,
                FechaActualizacion,
                IntentosConciliadorFallidos,
                CallbackInfo
            INTO #LoteActual
            FROM dbo.Ejecuciones
            WHERE 
                Estado IN (SELECT Estado FROM @EstadosFinalizados)
                AND COALESCE(FechaFin, FechaInicio) < DATEADD(day, -@DiasRetencionMover, GETDATE())
            ORDER BY EjecucionId; -- Orden determinístico es crucial

            SET @rowsAffected = @@ROWCOUNT;
            
            IF @rowsAffected = 0 BREAK;

            -- Paso 2 y 3 en una sola transacción para garantizar consistencia
            BEGIN TRANSACTION T_Move;
            
            INSERT INTO dbo.Ejecuciones_Historico (
                EjecucionId,
				DeploymentId,
                RobotId,
                EquipoId,
                UserId,
                Hora,
                FechaInicio,
                FechaFin,
                Estado,
                FechaActualizacion,
                IntentosConciliadorFallidos,
                CallbackInfo
            )
            SELECT 
                EjecucionId,
				DeploymentId,
                RobotId,
                EquipoId,
                UserId,
                Hora,
                FechaInicio,
                FechaFin,
                Estado,
                FechaActualizacion,
                IntentosConciliadorFallidos,
                CallbackInfo
            FROM #LoteActual;
            
            DELETE e
            FROM dbo.Ejecuciones e
            INNER JOIN #LoteActual l ON e.EjecucionID = l.EjecucionID;
            
            COMMIT TRANSACTION T_Move;

            SET @totalRowsMoved = @totalRowsMoved + @rowsAffected;
            
            IF @iterationCount % 10 = 0
                PRINT 'Procesados ' + CAST(@totalRowsMoved AS VARCHAR(10)) + ' registros en ' + CAST(@iterationCount AS VARCHAR(10)) + ' lotes.';

            IF @rowsAffected = @BatchSizeParam WAITFOR DELAY '00:00:02';

        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
			INSERT INTO dbo.ErrorLog (FechaHora ,Usuario, SPNombre, ErrorMensaje, Parametros)
            VALUES (
				GETDATE(), 
				@usuario,
				'usp_MoverEjecucionesAHistorico_Mover',
				ERROR_MESSAGE() + ' (Iteración: ' + CAST(@iterationCount AS VARCHAR) + ')', 
				'Lote: ' + CAST(@BatchSizeParam AS VARCHAR) + ', Registros movidos hasta ahora: ' + CAST(@totalRowsMoved AS VARCHAR)
			);
            
            IF ERROR_NUMBER() = 9002 -- Log lleno
            BEGIN
                PRINT 'Error de log lleno detectado. Abortando proceso.';
                BREAK;
            END
            ELSE
            BEGIN
                PRINT 'Error en iteración ' + CAST(@iterationCount AS VARCHAR) + ': ' + ERROR_MESSAGE();
                SET @rowsAffected = @BatchSizeParam;
            END
        END CATCH
    END

    PRINT 'Movimiento finalizado. Total de registros movidos: ' + CAST(@totalRowsMoved AS VARCHAR(10));
    IF @iterationCount >= @MaxIterationsParam
        PRINT 'ADVERTENCIA: El proceso se detuvo al alcanzar el límite máximo de iteraciones (' + CAST(@MaxIterationsParam AS VARCHAR) + '). Podrían quedar registros por mover.';

    -- =================================================================================
    -- PARTE 2: PURGAR REGISTROS ANTIGUOS DE 'Ejecuciones_Historico'
    -- =================================================================================
    
    DECLARE @purgeDate DATE = DATEADD(day, -@DiasRetencionPurga, GETDATE());
    DECLARE @totalRowsPurged INT = 0;
    DECLARE @purgeIterations INT = 0;

    PRINT 'Iniciando purga de registros históricos con más de ' + CAST(@DiasRetencionPurga AS VARCHAR) + ' días de antigüedad.';

    SET @rowsAffected = @BatchSizeParam;
    WHILE @rowsAffected = @BatchSizeParam AND @purgeIterations < @MaxIterationsParam
    BEGIN
        SET @purgeIterations = @purgeIterations + 1;
        
        BEGIN TRY
            BEGIN TRANSACTION T_Purge;

            DELETE TOP (@BatchSizeParam)
            FROM dbo.Ejecuciones_Historico
            WHERE FechaInicio < @purgeDate;

            SET @rowsAffected = @@ROWCOUNT;
            COMMIT TRANSACTION T_Purge;
            
            SET @totalRowsPurged = @totalRowsPurged + @rowsAffected;
            
            IF @purgeIterations % 10 = 0 AND @rowsAffected > 0
                PRINT 'Purgados ' + CAST(@totalRowsPurged AS VARCHAR(10)) + ' registros históricos.';

            IF @rowsAffected = @BatchSizeParam WAITFOR DELAY '00:00:01';

        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
           
            INSERT INTO dbo.ErrorLog (FechaHora, Usuario, SPNombre, ErrorMensaje, Parametros)
            VALUES (
				GETDATE(), 
				@usuario, 
				'usp_MoverEjecucionesAHistorico_Purga', 
                ERROR_MESSAGE() + ' (Iteración purga: ' + CAST(@purgeIterations AS VARCHAR) + ')', 
                'Fecha límite: ' + CONVERT(VARCHAR, @purgeDate, 120)
			);
            
            IF ERROR_NUMBER() = 9002
            BEGIN
                PRINT 'Error de log lleno en purga. Abortando proceso.';
                BREAK;
            END
            ELSE
            BEGIN
                PRINT 'Error en purga, iteración ' + CAST(@purgeIterations AS VARCHAR) + ': ' + ERROR_MESSAGE();
                SET @rowsAffected = @BatchSizeParam;
            END
        END CATCH
    END
    
    PRINT 'Purga finalizada. Total de registros eliminados del histórico: ' + CAST(@totalRowsPurged AS VARCHAR(10));
     IF @purgeIterations >= @MaxIterationsParam
        PRINT 'ADVERTENCIA: La purga se detuvo al alcanzar el límite máximo de iteraciones (' + CAST(@MaxIterationsParam AS VARCHAR) + '). Podrían quedar registros por purgar.';
    
    -- Estadísticas finales
    PRINT '=== RESUMEN DE EJECUCIÓN ===';
    PRINT 'Registros movidos a histórico: ' + CAST(@totalRowsMoved AS VARCHAR(10));
    PRINT 'Registros purgados del histórico: ' + CAST(@totalRowsPurged AS VARCHAR(10));
    PRINT 'Proceso SAM completado exitosamente.';
    
END
GO
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'(Opcional, pero útil) Podría indicar "DisponibleEnPoolPivote", "AsignadoDinamicoA_RobotX", "EnMantenimientoManual", etc.' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Equipos', @level2type=N'COLUMN',@level2name=N'EstadoBalanceador'
GO
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'1-Diaria, 2-Semanal, 3-Mensual, 4-Especifica' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Programaciones', @level2type=N'COLUMN',@level2name=N'TipoProgramacion'
GO
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Número mínimo de equipos que el balanceador intentará mantener asignado si hay tickets.' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Robots', @level2type=N'COLUMN',@level2name=N'MinEquipos'
GO
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Límite de equipos que el balanceador puede asignar dinámicamente a este robot. (default -1 o un número alto)' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Robots', @level2type=N'COLUMN',@level2name=N'MaxEquipos'
GO
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Para decidir qué robot obtiene recursos si son escasos. Menor número = mayor prioridad.' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'TABLE',@level1name=N'Robots', @level2type=N'COLUMN',@level2name=N'PrioridadBalanceo'
GO
EXEC sys.sp_addextendedproperty @name=N'MS_DiagramPane1', @value=N'[0E232FF0-B466-11cf-A24F-00AA00A3EFFF, 1.00]
Begin DesignProperties = 
   Begin PaneConfigurations = 
      Begin PaneConfiguration = 0
         NumPanes = 4
         Configuration = "(H (1[40] 4[20] 2[20] 3) )"
      End
      Begin PaneConfiguration = 1
         NumPanes = 3
         Configuration = "(H (1 [50] 4 [25] 3))"
      End
      Begin PaneConfiguration = 2
         NumPanes = 3
         Configuration = "(H (1 [50] 2 [25] 3))"
      End
      Begin PaneConfiguration = 3
         NumPanes = 3
         Configuration = "(H (4 [30] 2 [40] 3))"
      End
      Begin PaneConfiguration = 4
         NumPanes = 2
         Configuration = "(H (1 [56] 3))"
      End
      Begin PaneConfiguration = 5
         NumPanes = 2
         Configuration = "(H (2 [66] 3))"
      End
      Begin PaneConfiguration = 6
         NumPanes = 2
         Configuration = "(H (4 [50] 3))"
      End
      Begin PaneConfiguration = 7
         NumPanes = 1
         Configuration = "(V (3))"
      End
      Begin PaneConfiguration = 8
         NumPanes = 3
         Configuration = "(H (1[56] 4[18] 2) )"
      End
      Begin PaneConfiguration = 9
         NumPanes = 2
         Configuration = "(H (1 [75] 4))"
      End
      Begin PaneConfiguration = 10
         NumPanes = 2
         Configuration = "(H (1[66] 2) )"
      End
      Begin PaneConfiguration = 11
         NumPanes = 2
         Configuration = "(H (4 [60] 2))"
      End
      Begin PaneConfiguration = 12
         NumPanes = 1
         Configuration = "(H (1) )"
      End
      Begin PaneConfiguration = 13
         NumPanes = 1
         Configuration = "(V (4))"
      End
      Begin PaneConfiguration = 14
         NumPanes = 1
         Configuration = "(V (2))"
      End
      ActivePaneConfig = 0
   End
   Begin DiagramPane = 
      Begin Origin = 
         Top = 0
         Left = 0
      End
      Begin Tables = 
         Begin Table = "A"
            Begin Extent = 
               Top = 7
               Left = 48
               Bottom = 170
               Right = 242
            End
            DisplayFlags = 280
            TopColumn = 0
         End
         Begin Table = "EQ"
            Begin Extent = 
               Top = 111
               Left = 303
               Bottom = 274
               Right = 497
            End
            DisplayFlags = 280
            TopColumn = 0
         End
         Begin Table = "R"
            Begin Extent = 
               Top = 7
               Left = 532
               Bottom = 170
               Right = 726
            End
            DisplayFlags = 280
            TopColumn = 0
         End
      End
   End
   Begin SQLPane = 
   End
   Begin DataPane = 
      Begin ParameterDefaults = ""
      End
      Begin ColumnWidths = 9
         Width = 284
         Width = 1200
         Width = 1200
         Width = 1200
         Width = 1200
         Width = 1200
         Width = 1200
         Width = 1200
         Width = 1200
      End
   End
   Begin CriteriaPane = 
      Begin ColumnWidths = 11
         Column = 1440
         Alias = 900
         Table = 1176
         Output = 720
         Append = 1400
         NewValue = 1170
         SortType = 1356
         SortOrder = 1416
         GroupBy = 1350
         Filter = 1356
         Or = 1350
         Or = 1350
         Or = 1350
      End
   End
End
' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'VIEW',@level1name=N'AsignacionesView'
GO
EXEC sys.sp_addextendedproperty @name=N'MS_DiagramPaneCount', @value=1 , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'VIEW',@level1name=N'AsignacionesView'
GO
EXEC sys.sp_addextendedproperty @name=N'MS_DiagramPane1', @value=N'[0E232FF0-B466-11cf-A24F-00AA00A3EFFF, 1.00]
Begin DesignProperties = 
   Begin PaneConfigurations = 
      Begin PaneConfiguration = 0
         NumPanes = 4
         Configuration = "(H (1[40] 4[20] 2[20] 3) )"
      End
      Begin PaneConfiguration = 1
         NumPanes = 3
         Configuration = "(H (1 [50] 4 [25] 3))"
      End
      Begin PaneConfiguration = 2
         NumPanes = 3
         Configuration = "(H (1 [50] 2 [25] 3))"
      End
      Begin PaneConfiguration = 3
         NumPanes = 3
         Configuration = "(H (4 [30] 2 [40] 3))"
      End
      Begin PaneConfiguration = 4
         NumPanes = 2
         Configuration = "(H (1 [56] 3))"
      End
      Begin PaneConfiguration = 5
         NumPanes = 2
         Configuration = "(H (2 [66] 3))"
      End
      Begin PaneConfiguration = 6
         NumPanes = 2
         Configuration = "(H (4 [50] 3))"
      End
      Begin PaneConfiguration = 7
         NumPanes = 1
         Configuration = "(V (3))"
      End
      Begin PaneConfiguration = 8
         NumPanes = 3
         Configuration = "(H (1[56] 4[18] 2) )"
      End
      Begin PaneConfiguration = 9
         NumPanes = 2
         Configuration = "(H (1 [75] 4))"
      End
      Begin PaneConfiguration = 10
         NumPanes = 2
         Configuration = "(H (1[66] 2) )"
      End
      Begin PaneConfiguration = 11
         NumPanes = 2
         Configuration = "(H (4 [60] 2))"
      End
      Begin PaneConfiguration = 12
         NumPanes = 1
         Configuration = "(H (1) )"
      End
      Begin PaneConfiguration = 13
         NumPanes = 1
         Configuration = "(V (4))"
      End
      Begin PaneConfiguration = 14
         NumPanes = 1
         Configuration = "(V (2))"
      End
      ActivePaneConfig = 0
   End
   Begin DiagramPane = 
      Begin Origin = 
         Top = 0
         Left = 0
      End
      Begin Tables = 
         Begin Table = "E"
            Begin Extent = 
               Top = 7
               Left = 48
               Bottom = 288
               Right = 242
            End
            DisplayFlags = 280
            TopColumn = 0
         End
         Begin Table = "EQ"
            Begin Extent = 
               Top = 7
               Left = 290
               Bottom = 170
               Right = 484
            End
            DisplayFlags = 280
            TopColumn = 0
         End
         Begin Table = "R"
            Begin Extent = 
               Top = 7
               Left = 532
               Bottom = 170
               Right = 726
            End
            DisplayFlags = 280
            TopColumn = 0
         End
      End
   End
   Begin SQLPane = 
   End
   Begin DataPane = 
      Begin ParameterDefaults = ""
      End
      Begin ColumnWidths = 12
         Width = 284
         Width = 1200
         Width = 1200
         Width = 1200
         Width = 1200
         Width = 1200
         Width = 1200
         Width = 1200
         Width = 2496
         Width = 1200
         Width = 1944
         Width = 1200
      End
   End
   Begin CriteriaPane = 
      Begin ColumnWidths = 11
         Column = 1440
         Alias = 900
         Table = 1170
         Output = 720
         Append = 1400
         NewValue = 1170
         SortType = 1350
         SortOrder = 1410
         GroupBy = 1350
         Filter = 1350
         Or = 1350
         Or = 1350
         Or = 1350
      End
   End
End
' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'VIEW',@level1name=N'EjecucionesActivas'
GO
EXEC sys.sp_addextendedproperty @name=N'MS_DiagramPaneCount', @value=1 , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'VIEW',@level1name=N'EjecucionesActivas'
GO
EXEC sys.sp_addextendedproperty @name=N'MS_DiagramPane1', @value=N'[0E232FF0-B466-11cf-A24F-00AA00A3EFFF, 1.00]
Begin DesignProperties = 
   Begin PaneConfigurations = 
      Begin PaneConfiguration = 0
         NumPanes = 4
         Configuration = "(H (1[41] 4[14] 2[15] 3) )"
      End
      Begin PaneConfiguration = 1
         NumPanes = 3
         Configuration = "(H (1 [50] 4 [25] 3))"
      End
      Begin PaneConfiguration = 2
         NumPanes = 3
         Configuration = "(H (1 [50] 2 [25] 3))"
      End
      Begin PaneConfiguration = 3
         NumPanes = 3
         Configuration = "(H (4 [30] 2 [40] 3))"
      End
      Begin PaneConfiguration = 4
         NumPanes = 2
         Configuration = "(H (1 [56] 3))"
      End
      Begin PaneConfiguration = 5
         NumPanes = 2
         Configuration = "(H (2 [66] 3))"
      End
      Begin PaneConfiguration = 6
         NumPanes = 2
         Configuration = "(H (4 [50] 3))"
      End
      Begin PaneConfiguration = 7
         NumPanes = 1
         Configuration = "(V (3))"
      End
      Begin PaneConfiguration = 8
         NumPanes = 3
         Configuration = "(H (1[56] 4[18] 2) )"
      End
      Begin PaneConfiguration = 9
         NumPanes = 2
         Configuration = "(H (1 [75] 4))"
      End
      Begin PaneConfiguration = 10
         NumPanes = 2
         Configuration = "(H (1[66] 2) )"
      End
      Begin PaneConfiguration = 11
         NumPanes = 2
         Configuration = "(H (4 [60] 2))"
      End
      Begin PaneConfiguration = 12
         NumPanes = 1
         Configuration = "(H (1) )"
      End
      Begin PaneConfiguration = 13
         NumPanes = 1
         Configuration = "(V (4))"
      End
      Begin PaneConfiguration = 14
         NumPanes = 1
         Configuration = "(V (2))"
      End
      ActivePaneConfig = 0
   End
   Begin DiagramPane = 
      Begin Origin = 
         Top = 0
         Left = 0
      End
      Begin Tables = 
         Begin Table = "e"
            Begin Extent = 
               Top = 4
               Left = 507
               Bottom = 167
               Right = 782
            End
            DisplayFlags = 280
            TopColumn = 8
         End
         Begin Table = "eq"
            Begin Extent = 
               Top = 120
               Left = 841
               Bottom = 283
               Right = 1112
            End
            DisplayFlags = 280
            TopColumn = 3
         End
         Begin Table = "r"
            Begin Extent = 
               Top = 117
               Left = 177
               Bottom = 280
               Right = 449
            End
            DisplayFlags = 280
            TopColumn = 3
         End
      End
   End
   Begin SQLPane = 
   End
   Begin DataPane = 
      Begin ParameterDefaults = ""
      End
   End
   Begin CriteriaPane = 
      Begin ColumnWidths = 11
         Column = 1440
         Alias = 900
         Table = 1176
         Output = 720
         Append = 1400
         NewValue = 1170
         SortType = 1356
         SortOrder = 1416
         GroupBy = 1350
         Filter = 1356
         Or = 1350
         Or = 1350
         Or = 1350
      End
   End
End
' , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'VIEW',@level1name=N'EjecucionesFinalizadas'
GO
EXEC sys.sp_addextendedproperty @name=N'MS_DiagramPaneCount', @value=1 , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'VIEW',@level1name=N'EjecucionesFinalizadas'
GO
