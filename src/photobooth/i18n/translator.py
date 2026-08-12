"""Flat JSON-based translations, exposed to QML as a live-updating singleton.

Simpler than a gettext toolchain: each `translations/<lang>.json` is just
`{"key": "translated string"}`; QML calls `Translator.tr("key")` and the
whole UI updates instantly on `setLanguage()` since every binding re-evaluates
when `languageChanged` fires.
"""

from __future__ import annotations

import json
import logging
from importlib import resources

from PySide6.QtCore import Property, QObject, Signal, Slot

logger = logging.getLogger(__name__)


class Translator(QObject):
    languageChanged = Signal()

    def __init__(self, language: str = "en") -> None:
        super().__init__()
        self._catalogs: dict[str, dict[str, str]] = {}
        self._language = "en"
        self._load_all()
        self.setLanguage(language)

    def _load_all(self) -> None:
        pkg = resources.files("photobooth.i18n.translations")
        for entry in pkg.iterdir():
            if entry.name.endswith(".json"):
                lang = entry.name.removesuffix(".json")
                try:
                    self._catalogs[lang] = json.loads(entry.read_text("utf-8"))
                except (json.JSONDecodeError, OSError):
                    logger.exception("Failed to load translation catalog %s", entry.name)

    @Property(list, constant=True)
    def availableLanguages(self) -> list[str]:
        return sorted(self._catalogs)

    def getLanguage(self) -> str:
        return self._language

    @Slot(str)
    def setLanguage(self, language: str) -> None:
        if language not in self._catalogs:
            logger.warning("Unknown language %r, keeping %r", language, self._language)
            return
        if language != self._language:
            self._language = language
            self.languageChanged.emit()

    language = Property(str, getLanguage, setLanguage, notify=languageChanged)

    @Slot(str, result=str)
    def tr(self, key: str) -> str:
        catalog = self._catalogs.get(self._language, {})
        fallback = self._catalogs.get("en", {})
        return catalog.get(key, fallback.get(key, key))
