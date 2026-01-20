---
description: Ver los últimos logs de los servicios
---

Muestra las últimas 50 líneas de los logs de los servicios SAM.

1. **Lanzador**: `Get-Content C:\RPA\Logs\SAM\lanzador.log -Tail 50`
2. **Balanceador**: `Get-Content C:\RPA\Logs\SAM\balanceador.log -Tail 50`
3. **Callback**: `Get-Content C:\RPA\Logs\SAM\callback.log -Tail 50`
4. **Web**: `Get-Content C:\RPA\Logs\SAM\web.log -Tail 50`

// turbo
Get-Content C:\RPA\Logs\SAM\lanzador.log -Tail 50
