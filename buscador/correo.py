"""Envío de correos por SMTP (Hostinger) desde tu propia cuenta."""
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid


def enviar(destino: str, asunto: str, texto: str, cfg) -> None:
    if not cfg.smtp_configurado:
        raise RuntimeError("Configura SMTP_USUARIO y SMTP_CONTRASENA en el archivo .env")
    msg = EmailMessage()
    msg["From"] = formataddr((cfg.firma_nombre or cfg.firma_empresa, cfg.smtp_usuario))
    msg["To"] = destino
    msg["Subject"] = asunto
    msg["Message-ID"] = make_msgid(domain=cfg.smtp_usuario.split("@")[-1])
    msg["List-Unsubscribe"] = f"<mailto:{cfg.smtp_usuario}?subject=Baja>"
    if cfg.smtp_copia_a_mi:
        msg["Bcc"] = cfg.smtp_usuario
    msg.set_content(texto)
    ctx = ssl.create_default_context()
    if cfg.smtp_port == 465:
        with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, context=ctx, timeout=30) as s:
            s.login(cfg.smtp_usuario, cfg.smtp_contrasena)
            s.send_message(msg)
    else:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(cfg.smtp_usuario, cfg.smtp_contrasena)
            s.send_message(msg)
