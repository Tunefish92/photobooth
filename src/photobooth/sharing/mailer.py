from __future__ import annotations

import smtplib
from email.message import EmailMessage
from mimetypes import guess_type
from pathlib import Path

from photobooth.config.settings import MailerConfig


_IMPLICIT_TLS_PORT = 465


def send_email(config: MailerConfig, image_path: Path) -> None:
    msg = EmailMessage()
    msg["Subject"] = config.subject
    msg["From"] = config.sender
    msg["To"] = config.recipient
    msg.set_content(config.message)

    mime_type, _ = guess_type(image_path.name)
    maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
    msg.add_attachment(
        image_path.read_bytes(), maintype=maintype, subtype=subtype, filename=image_path.name
    )

    # Port 465 is implicit TLS (the connection is TLS from the first byte);
    # plain SMTP + starttls() -- correct for the far more common port
    # 587/25 "STARTTLS" case -- would send a plaintext EHLO into a TLS
    # handshake and fail. Use SMTP_SSL for 465, matching what mail
    # providers actually expect on that port.
    smtp_cls = smtplib.SMTP_SSL if config.port == _IMPLICIT_TLS_PORT else smtplib.SMTP
    with smtp_cls(config.server, config.port, timeout=20) as smtp:
        if config.use_tls and config.port != _IMPLICIT_TLS_PORT:
            smtp.starttls()
        if config.use_auth:
            smtp.login(config.user, config.password)
        smtp.send_message(msg)
