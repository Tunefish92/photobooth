from __future__ import annotations

import smtplib
from email.message import EmailMessage
from mimetypes import guess_type
from pathlib import Path

from photobooth.config.settings import MailerConfig


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

    with smtplib.SMTP(config.server, config.port, timeout=20) as smtp:
        if config.use_tls:
            smtp.starttls()
        if config.use_auth:
            smtp.login(config.user, config.password)
        smtp.send_message(msg)
