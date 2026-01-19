---
description: Verificar el estado de los servicios SAM en Windows
---

Muestra si los servicios de SAM están ejecutándose.

// turbo
Get-Service SAM_* | Select-Object Name, DisplayName, Status
