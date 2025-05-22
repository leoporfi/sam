# utils/mail_client.py
import datetime
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# from utils.config import setup_logging, ConfigManager
from lanzador.utils.config import setup_logging, ConfigManager

logger = setup_logging()


class EmailAlertClient:
    def __init__(self):
        config = ConfigManager.get_email_config()
        self.smtp_server = config["smtp_server"]
        self.smtp_port = config["smtp_port"]
        self.smtp_user = config.get("smtp_user", None)
        self.smtp_password = config.get("smtp_password", None)
        self.from_email = config["from_email"]
        self.recipients = config["recipients"]
        self.use_tls = config["use_tls"]
        self.last_critical_sent = {}  # clave: asunto, valor: datetime

    def send_alert(self, subject, message, is_critical=True):
        try:
            now = datetime.datetime.now()

            if is_critical:
                last_sent = self.last_critical_sent.get(subject)
                if last_sent and (now - last_sent).total_seconds() < 1800:
                    logger.warning(f"Alerta omitida (enviada hace menos de 30 min): {subject}")
                    return False
                self.last_critical_sent[subject] = now
                
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.recipients)
            prefix = "[CRÍTICO]" if is_critical else "[ALERTA]"
            msg["Subject"] = f"{prefix} {subject}"

            body = f"""
            <html>
            <body>
                <h2>{subject}</h2>
                <pre>{message}</pre>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, "html"))

            if self.use_tls: # Si es False (debido a la config anterior)
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls() # Esto NO se ejecutaría
            else:
                # Si no es STARTTLS, podría ser SMTP_SSL (usualmente puerto 465) o SMTP plano
                if str(self.smtp_port) == "465": # Comparar como string por si acaso
                    server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
                else: # Asumir SMTP plano para otros puertos si use_tls es False
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port) # ESTO SE EJECUTARÍA

            # Iniciar sesión si se requiere autenticación
            if self.smtp_user and self.smtp_password: # Si smtp_user o smtp_password son None o vacíos, esto es False
                server.login(self.smtp_user, self.smtp_password)
            else:
                # Este log debería aparecer si no se proveen credenciales y no se requiere autenticación
                logger.info("SMTP sin autenticación: credenciales no proporcionadas o incompletas.")

            server.send_message(msg)
            server.quit()

            logger.info(f"Alerta enviada: {subject}")
            return True

        except Exception as e:
            logger.error(f"Error al enviar alerta: {e}")
            return False
