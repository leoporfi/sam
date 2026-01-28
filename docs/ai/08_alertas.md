# 🚨 Sistema de Alertas SAM

Este documento describe el sistema de alertas centralizado de SAM, diseñado para notificar proactivamente sobre errores críticos, problemas de infraestructura y eventos operativos importantes.

## 🏛️ Arquitectura

El sistema se basa en un cliente de correo unificado (`EmailAlertClient`) y un modelo de datos estructurado (`AlertContext`) que permite clasificar y formatear las alertas de manera consistente.

### Componentes Principales

1.  **`src/sam/common/alert_types.py`**: Define los tipos de datos y enumeraciones.
    *   **`AlertLevel`**: Severidad (`CRITICAL`, `HIGH`, `MEDIUM`).
    *   **`AlertScope`**: Alcance (`SYSTEM`, `ROBOT`, `DEVICE`).
    *   **`AlertType`**: Naturaleza (`PERMANENT`, `TRANSIENT`, `THRESHOLD`, `RECOVERY`).
    *   **`AlertContext`**: Dataclass que encapsula toda la información de la alerta.

2.  **`src/sam/common/mail_client.py`**: Cliente SMTP.
    *   **`EmailAlertClient`**: Clase principal.
    *   **`send_alert_v2(context)`**: Método recomendado para enviar alertas estructuradas con HTML rico.
    *   **`send_alert(subject, message)`**: Método legacy (evitar en nuevo código).
    *   **Throttling**: Evita spam de alertas idénticas (mismo subject) enviadas en menos de 30 minutos.

3.  **`src/sam/common/config_manager.py`**: Gestión de configuración.
    *   Carga variables de entorno para SMTP (`EMAIL_SMTP_SERVER`, `EMAIL_RECIPIENTS`, etc.).

## ⚙️ Configuración

Las siguientes variables de entorno en `.env` controlan el envío de correos:

| Variable | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `EMAIL_SMTP_SERVER` | Servidor SMTP | `smtp.office365.com` |
| `EMAIL_SMTP_PORT` | Puerto SMTP | `587` |
| `EMAIL_FROM` | Remitente | `rpa-alerts@empresa.com` |
| `EMAIL_RECIPIENTS` | Destinatarios (separados por coma) | `admin@empresa.com,devops@empresa.com` |
| `EMAIL_USER` | Usuario SMTP (si requiere auth) | `rpa-alerts@empresa.com` |
| `EMAIL_PASSWORD` | Contraseña SMTP | `******` |
| `EMAIL_USE_TLS` | Usar TLS | `True` |

## 🚀 Uso en Código

Para implementar una nueva alerta, sigue este patrón:

```python
from sam.common.alert_types import AlertContext, AlertLevel, AlertScope, AlertType
from sam.common.mail_client import EmailAlertClient

# 1. Instanciar cliente (idealmente inyectado o singleton por servicio)
notificador = EmailAlertClient(service_name="MiServicio")

# 2. Crear contexto
context = AlertContext(
    alert_level=AlertLevel.HIGH,
    alert_scope=AlertScope.SYSTEM,
    alert_type=AlertType.PERMANENT,
    subject="Título Descriptivo del Problema",
    summary="Resumen ejecutivo de una o dos líneas explicando qué pasó y el impacto.",
    technical_details={
        "Error Code": "500",
        "Function": "process_data",
        "Exception": str(e),
        "Trace ID": "12345"
    },
    actions=[
        "1. Verificar logs del servidor.",
        "2. Reiniciar el servicio si persiste."
    ]
)

# 3. Enviar
notificador.send_alert_v2(context)
```

## 🔍 Casos de Uso Actuales

*   **Lanzador**:
    *   **Errores Críticos en Ciclos**: Si un ciclo (Lanzamiento, Sincronización, Conciliación) falla con una excepción no controlada.
    *   **Error 412 (No compatible targets)**: Si un robot falla con "No compatible targets found", se **INACTIVA** el robot en la base de datos para evitar intentos en todos los equipos asignados.
    *   **Error 412 (Device Disconnected)**: Si un robot falla persistentemente (umbral configurable) porque el equipo está desconectado.
    *   **Fallo de Autenticación AA**: Si la API Key es rechazada por el Control Room.
    *   **Recuperación de Autenticación**: Cuando se restablece la conexión con el Control Room.
*   **Balanceador**:
    *   **Errores Críticos en Main**: Excepciones fatales que detienen el servicio.

## 📝 Buenas Prácticas

1.  **No usar `print` ni `logging.error` solamente**: Para errores críticos que requieren intervención humana, SIEMPRE usar el sistema de alertas.
2.  **Ser descriptivo**: El `summary` debe ser entendible por un humano no técnico (o manager). Los `technical_details` son para el desarrollador.
3.  **Acciones Claras**: Sugerir pasos concretos en `actions` reduce el tiempo de resolución (MTTR).
4.  **No abusar**: Usar `AlertLevel.MEDIUM` para advertencias que no requieren despertar a alguien a las 3 AM.
