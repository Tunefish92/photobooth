from __future__ import annotations

from pathlib import Path

import httpx

from photobooth.config.settings import WebdavConfig


def upload_file(config: WebdavConfig, image_path: Path) -> None:
    url = config.url.rstrip("/") + "/" + image_path.name
    auth = (config.user, config.password) if config.use_auth else None
    with httpx.Client(auth=auth, timeout=30) as client:
        response = client.put(url, content=image_path.read_bytes())
        response.raise_for_status()
