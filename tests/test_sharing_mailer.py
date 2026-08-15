"""Unit tests for the email sharing backend, using a fake smtplib.SMTP/
SMTP_SSL rather than a live server -- the interesting behavior here is
entirely in *which* class gets used and *what* gets called on it (TLS
mode, auth, attachment), not in real SMTP wire behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from photobooth.config.settings import MailerConfig
from photobooth.sharing.mailer import send_email


class _FakeSMTP:
    """Records what was called on it; used for both the plain and
    implicit-TLS (SMTP_SSL) code paths -- `is_ssl` distinguishes them."""

    instances: list["_FakeSMTP"] = []
    is_ssl: bool = False

    def __init__(self, server: str, port: int, timeout: float | None = None) -> None:
        self.server = server
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_args: tuple[str, str] | None = None
        self.sent_message = None
        type(self).instances.append(self)

    def __enter__(self) -> "_FakeSMTP":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, user: str, password: str) -> None:
        self.login_args = (user, password)

    def send_message(self, msg) -> None:
        self.sent_message = msg


class _FakeSMTP_SSL(_FakeSMTP):
    is_ssl = True


@pytest.fixture(autouse=True)
def _reset_fakes():
    _FakeSMTP.instances = []
    _FakeSMTP_SSL.instances = []
    yield
    _FakeSMTP.instances = []
    _FakeSMTP_SSL.instances = []


@pytest.fixture
def image_path(tmp_path: Path) -> Path:
    path = tmp_path / "photo.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
    return path


def _config(**overrides) -> MailerConfig:
    defaults = dict(
        enable=True,
        sender="booth@example.com",
        recipient="guest@example.com",
        subject="Your photo",
        message="Enjoy!",
        server="smtp.example.com",
        port=587,
        use_auth=True,
        user="booth@example.com",
        password="hunter2",
        use_tls=True,
    )
    defaults.update(overrides)
    return MailerConfig(**defaults)


def test_starttls_port_uses_plain_smtp_and_calls_starttls(monkeypatch):
    monkeypatch.setattr("photobooth.sharing.mailer.smtplib.SMTP", _FakeSMTP)
    monkeypatch.setattr("photobooth.sharing.mailer.smtplib.SMTP_SSL", _FakeSMTP_SSL)

    send_email(_config(port=587), Path(__file__))  # any existing file works for the attachment

    assert len(_FakeSMTP.instances) == 1
    assert len(_FakeSMTP_SSL.instances) == 0
    assert _FakeSMTP.instances[0].started_tls is True


def test_implicit_tls_port_465_uses_smtp_ssl_and_skips_starttls(monkeypatch):
    monkeypatch.setattr("photobooth.sharing.mailer.smtplib.SMTP", _FakeSMTP)
    monkeypatch.setattr("photobooth.sharing.mailer.smtplib.SMTP_SSL", _FakeSMTP_SSL)

    send_email(_config(port=465), Path(__file__))

    assert len(_FakeSMTP_SSL.instances) == 1
    assert len(_FakeSMTP.instances) == 0
    # starttls() on an already-TLS connection would be a protocol error --
    # confirm it's never called for the implicit-TLS path.
    assert _FakeSMTP_SSL.instances[0].started_tls is False


def test_use_auth_false_skips_login(monkeypatch):
    monkeypatch.setattr("photobooth.sharing.mailer.smtplib.SMTP", _FakeSMTP)
    monkeypatch.setattr("photobooth.sharing.mailer.smtplib.SMTP_SSL", _FakeSMTP_SSL)

    send_email(_config(use_auth=False), Path(__file__))

    assert _FakeSMTP.instances[0].login_args is None


def test_use_auth_true_logs_in_with_configured_credentials(monkeypatch):
    monkeypatch.setattr("photobooth.sharing.mailer.smtplib.SMTP", _FakeSMTP)
    monkeypatch.setattr("photobooth.sharing.mailer.smtplib.SMTP_SSL", _FakeSMTP_SSL)

    send_email(_config(user="me@example.com", password="s3cret"), Path(__file__))

    assert _FakeSMTP.instances[0].login_args == ("me@example.com", "s3cret")


def test_sent_message_carries_the_configured_fields_and_attachment(monkeypatch, image_path: Path):
    monkeypatch.setattr("photobooth.sharing.mailer.smtplib.SMTP", _FakeSMTP)
    monkeypatch.setattr("photobooth.sharing.mailer.smtplib.SMTP_SSL", _FakeSMTP_SSL)

    send_email(_config(subject="Look at us!", recipient="them@example.com"), image_path)

    msg = _FakeSMTP.instances[0].sent_message
    assert msg["Subject"] == "Look at us!"
    assert msg["To"] == "them@example.com"
    attachments = list(msg.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == image_path.name
    assert attachments[0].get_content_type() == "image/jpeg"
