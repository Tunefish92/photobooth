"""Unit tests for the WebDAV sharing backend, using httpx's MockTransport
(built into httpx, no live server or extra dependency needed) to inspect
exactly what request gets sent.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from photobooth.config.settings import WebdavConfig
from photobooth.sharing.webdav import upload_file

_REAL_CLIENT = httpx.Client


@pytest.fixture
def image_path(tmp_path: Path) -> Path:
    path = tmp_path / "result.jpg"
    path.write_bytes(b"the-photo-bytes")
    return path


def _config(**overrides) -> WebdavConfig:
    defaults = dict(
        enable=True,
        url="https://cloud.example.com/remote.php/webdav/Photobooth/",
        use_auth=True,
        user="booth",
        password="hunter2",
    )
    defaults.update(overrides)
    return WebdavConfig(**defaults)


def _install_mock_transport(monkeypatch, handler):
    """Patches photobooth.sharing.webdav.httpx.Client to route through a
    MockTransport. `webdav.py` does `import httpx`, so that module
    attribute *is* the real httpx module -- patching Client on it patches
    httpx.Client globally, so the replacement below closes over the real
    class captured at import time rather than looking it up as `httpx.
    Client` again (which would now resolve to itself and recurse).
    """
    monkeypatch.setattr(
        "photobooth.sharing.webdav.httpx.Client",
        lambda **kw: _REAL_CLIENT(transport=httpx.MockTransport(handler), **kw),
    )


def test_upload_puts_to_url_plus_filename(monkeypatch, image_path: Path):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201)

    _install_mock_transport(monkeypatch, handler)

    upload_file(_config(), image_path)

    assert len(requests) == 1
    assert requests[0].method == "PUT"
    assert str(requests[0].url) == "https://cloud.example.com/remote.php/webdav/Photobooth/result.jpg"
    assert requests[0].content == b"the-photo-bytes"


def test_upload_url_without_trailing_slash_still_joins_correctly(monkeypatch, image_path: Path):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201)

    _install_mock_transport(monkeypatch, handler)

    upload_file(_config(url="https://cloud.example.com/dav"), image_path)

    assert str(requests[0].url) == "https://cloud.example.com/dav/result.jpg"


def test_upload_sends_basic_auth_when_use_auth_true(monkeypatch, image_path: Path):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201)

    _install_mock_transport(monkeypatch, handler)

    upload_file(_config(user="booth", password="hunter2"), image_path)

    assert "authorization" in requests[0].headers


def test_upload_sends_no_auth_header_when_use_auth_false(monkeypatch, image_path: Path):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201)

    _install_mock_transport(monkeypatch, handler)

    upload_file(_config(use_auth=False), image_path)

    assert "authorization" not in requests[0].headers


def test_upload_raises_on_server_error(monkeypatch, image_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(507)  # Insufficient Storage

    _install_mock_transport(monkeypatch, handler)

    with pytest.raises(httpx.HTTPStatusError):
        upload_file(_config(), image_path)
