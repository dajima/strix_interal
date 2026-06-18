"""Atomic JSON file persistence — shared by notes and todos storage."""

from __future__ import annotations

import json
import logging
import tempfile
import threading
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class JsonStore:
    """Thread-safe JSON file backed by atomic write-via-rename."""

    def __init__(self, filename: str) -> None:
        self._filename = filename
        self._path: Path | None = None
        self._lock = threading.RLock()

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    def hydrate(self, state_dir: Path) -> dict[str, Any]:
        self._path = state_dir / self._filename
        with self._lock:
            if not self._path.exists():
                return {}
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                logger.exception(
                    "%s at %s is unreadable; starting empty",
                    self._filename,
                    self._path,
                )
                return {}
            if not isinstance(data, dict):
                return {}
            return data

    def persist(self, payload_obj: object) -> None:
        path = self._path
        if path is None:
            return
        try:
            payload = json.dumps(payload_obj, ensure_ascii=False, default=str)
            path.parent.mkdir(parents=True, exist_ok=True)
            with (
                self._lock,
                tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=str(path.parent),
                    prefix=f".{path.name}.",
                    suffix=".tmp",
                    delete=False,
                ) as tmp,
            ):
                tmp.write(payload)
                tmp_path = Path(tmp.name)
            tmp_path.replace(path)
        except Exception:
            logger.exception("%s persist to %s failed", self._filename, path)
