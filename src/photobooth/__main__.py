from __future__ import annotations

import logging
import sys

from photobooth import paths


def _setup_logging() -> None:
    log_path = paths.log_file()
    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        handlers=handlers,
    )


def main() -> int:
    _setup_logging()
    from photobooth.app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
