SET ANSI_NULLS ON
SET QUOTED_IDENTIFIER ON
IF NOT EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID(N'[dbo].[EjecucionesFinalizadas]'))
EXEC dbo.sp_executesql @statement = N'

CREATE VIEW [dbo].[EjecucionesFinalizadas]
AS
SELECT TOP (100) PERCENT 
	r.Robot, r.RobotId, CASE WHEN (r.EsOnline = 1) THEN ''ONLINE'' ELSE ''PROGRAMADO'' END AS Tipo, 
	eq.Equipo, eq.EquipoId, eq.UserId, eq.UserName, e.DeploymentId, e.Hora, e.FechaInicio, e.FechaFin, 
	e.Estado, e.FechaActualizacion, e.IntentosConciliadorFallidos, e.CallbackInfo, r.Descripcion
FROM     dbo.Ejecuciones AS e INNER JOIN
                  dbo.Equipos AS eq ON e.EquipoId = eq.EquipoId INNER JOIN
                  dbo.Robots AS r ON e.RobotId = r.RobotId
WHERE
    -- 1. No es un estado activo conocido
    (e.Estado NOT IN (
        ''DEPLOYED'', ''QUEUED'', ''PENDING_EXECUTION'', 
        ''RUNNING'', ''UPDATE'', ''RUN_PAUSED''
    ))
    AND
    -- 2. Y tampoco es un ''UNKNOWN'' reciente
    (
        NOT (E.Estado = ''UNKNOWN'' AND E.FechaUltimoUNKNOWN > DATEADD(HOUR, -2, GETDATE()))
    )
ORDER BY e.EjecucionId DESC
' 
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_DiagramPane1' , N'SCHEMA',N'dbo', N'VIEW',N'EjecucionesFinalizadas', NULL,NULL))
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
IF NOT EXISTS (SELECT * FROM sys.fn_listextendedproperty(N'MS_DiagramPaneCount' , N'SCHEMA',N'dbo', N'VIEW',N'EjecucionesFinalizadas', NULL,NULL))
	EXEC sys.sp_addextendedproperty @name=N'MS_DiagramPaneCount', @value=1 , @level0type=N'SCHEMA',@level0name=N'dbo', @level1type=N'VIEW',@level1name=N'EjecucionesFinalizadas'
