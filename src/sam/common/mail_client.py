# SAM/src/common/mail_client.py
import datetime
import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Optional

from .config_manager import ConfigManager

# --- OBTENER EL LOGGER (Forma Estandarizada) ---
# Simplemente obtenemos el logger para este módulo. La configuración
# (handlers, level, etc.) ya fue establecida por el script de arranque.
logger = logging.getLogger(__name__)


class EmailAlertClient:
    def __init__(self, service_name: str = "SAM"):
        # ConfigManager se importa desde common.utils.config_manager
        config = ConfigManager.get_email_config()

        self.smtp_server = config["smtp_server"]
        self.smtp_port = config["smtp_port"]
        self.smtp_user = config.get("smtp_user", None)
        self.smtp_password = config.get("smtp_password", None)
        self.from_email = config["from_email"]
        self.recipients = config["recipients"]
        self.use_tls = config["use_tls"]
        self.service_name = service_name

        # Validar configuración esencial para email
        # Verificar que recipients no esté vacío y no contenga solo strings vacíos
        valid_recipients = [r for r in (self.recipients or []) if r and r.strip()]

        if not all([self.smtp_server, self.from_email, valid_recipients]):
            missing_parts = []
            if not self.smtp_server:
                missing_parts.append("smtp_server")
            if not self.from_email:
                missing_parts.append("from_email")
            if not valid_recipients:
                missing_parts.append("recipients (vacío o no configurado)")

            logger.error(
                f"Configuración de email incompleta: faltan {', '.join(missing_parts)}. "
                "Las alertas por email NO funcionarán. Configure las variables de entorno: "
                "EMAIL_SMTP_SERVER, EMAIL_FROM, EMAIL_RECIPIENTS"
            )
            # Actualizar recipients con la lista validada
            self.recipients = valid_recipients
            # Podrías levantar un error aquí si el email es crítico
            # raise ValueError("Configuración de email incompleta.")

        self.last_critical_sent: Dict[str, datetime.datetime] = {}

    def send_alert(self, subject: str, message: str, is_critical: bool = True):
        # Verificar si la configuración esencial está presente antes de intentar enviar
        if not all([self.smtp_server, self.from_email, self.recipients]):
            logger.error(
                f"No se puede enviar alerta (Asunto: {subject}) porque la configuración de email está incompleta."
            )
            return False

        try:
            now = datetime.datetime.now()

            if is_critical:
                last_sent = self.last_critical_sent.get(subject)
                # Esperar 30 minutos (1800 segundos) entre alertas críticas idénticas
                if last_sent and (now - last_sent).total_seconds() < 1800:
                    logger.warning(f"Alerta crítica omitida (enviada hace menos de 30 min): {subject}")
                    return False
                self.last_critical_sent[subject] = now

            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.recipients)  # Convertir lista a string para el header
            prefix = "[CRÍTICO]" if is_critical else "[ALERTA]"
            msg["Subject"] = f"{self.service_name} {prefix} {subject}"  # Añadir identificador del servicio

            # Escapar HTML en subject y message para prevenir inyección
            subject_escaped = html.escape(subject)
            message_escaped = html.escape(message)

            # Obtener timestamp formateado
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Usar preformateado para el cuerpo del mensaje si es texto plano, o asegurar que el HTML sea seguro.
            body_html = f"""
            <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="background-color: #f4f4f4; padding: 20px; border-radius: 5px;">
                    <h2 style="color: #d32f2f; margin-top: 0;">{subject_escaped}</h2>
                    <p><b>Servicio:</b> {html.escape(self.service_name)}</p>
                    <p><b>Fecha y Hora:</b> {timestamp}</p>
                    <hr style="border: 1px solid #ddd;">
                    <div style="background-color: #fff; padding: 15px; border-left: 4px solid #d32f2f; margin: 15px 0;">
                        <pre style="font-family: Consolas, 'Courier New', monospace; white-space: pre-wrap; margin: 0;">{message_escaped}</pre>
                    </div>
                    <hr style="border: 1px solid #ddd;">
                    <p style="color: #666; font-size: 0.9em; margin-bottom: 0;">Este es un mensaje generado automáticamente por el sistema SAM.</p>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(body_html, "html", "utf-8"))  # Especificar utf-8

            server: Optional[smtplib.SMTP] = None  # Para asegurar que server se define
            # Añadir timeout
            timeout = 10
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout)  # Añadir timeout
                server.starttls()
            else:
                if str(self.smtp_port) == "465":
                    server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=timeout)
                else:
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout)

            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
                logger.info("SMTP login realizado.")
            else:
                logger.info("SMTP sin autenticación (no se proporcionaron credenciales).")

            server.send_message(msg)
            server.quit()
            logger.info(f"Alerta enviada exitosamente: {subject}")
            return True

        except Exception as e:
            logger.error(f"Error al enviar alerta (Asunto: {subject}): {e}", exc_info=True)
            return False
