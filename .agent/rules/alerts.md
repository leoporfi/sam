---
description: Reglas para el manejo de alertas y notificaciones en SAM
---

# Sistema de Alertas SAM

El proyecto cuenta con un sistema de alertas centralizado que **DEBE** ser utilizado para reportar errores críticos o eventos importantes.

## 🚨 Reglas de Uso

1.  **NO uses `print()` ni solo `logging.error()`** para errores que requieran intervención humana inmediata.
2.  **Usa `EmailAlertClient`** para enviar notificaciones.
3.  **Usa `AlertContext`** para estructurar la alerta (Nivel, Alcance, Tipo).

## 📚 Referencia

Para ver ejemplos de código y configuración detallada, consulta:
👉 [docs/ai/08_alertas.md](../../docs/ai/08_alertas.md)

## 💡 Snippet Rápido

```python
from sam.common.alert_types import AlertContext, AlertLevel, AlertScope, AlertType
from sam.common.mail_client import EmailAlertClient

notificador = EmailAlertClient(service_name="MiServicio")
context = AlertContext(
    alert_level=AlertLevel.CRITICAL,
    alert_scope=AlertScope.SYSTEM,
    alert_type=AlertType.PERMANENT,
    subject="Error Crítico",
    summary="Descripción breve",
    technical_details={"error": str(e)},
    actions=["Reiniciar servicio"]
)
notificador.send_alert_v2(context)
```
