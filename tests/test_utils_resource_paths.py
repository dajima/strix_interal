"""Unit tests for strix.utils.resource_paths."""

from __future__ import annotations

import sys
from pathlib import Path

from strix.utils.resource_paths import get_strix_resource_path


class TestGetStrixResourcePath:
    def test_returns_path(self) -> None:
        result = get_strix_resource_path("skills")
        assert isinstance(result, Path)
        assert result.name == "skills"

    def test_multiple_parts(self) -> None:
        result = get_strix_resource_path("tools", "notes", "templates")
        assert result.parts[-3:] == ("tools", "notes", "templates")

    def test_non_frozen_uses_source_tree(self) -> None:
        # In normal (non-frozen) execution, the base is the strix package dir
        result = get_strix_resource_path("config")
        assert "strix" in str(result)

    def test_frozen_base_used_when_set(self, tmp_path: Path) -> None:
        # Simulate PyInstaller frozen environment
        frozen_base = tmp_path / "frozen"
        strix_dir = frozen_base / "strix"
        strix_dir.mkdir(parents=True)
        (strix_dir / "skills").mkdir()

        sys._MEIPASS = str(frozen_base)  # type: ignore[attr-defined]
        try:
            result = get_strix_resource_path("skills")
            assert result == strix_dir / "skills"
        finally:
            del sys._MEIPASS  # type: ignore[attr-defined]

    def test_frozen_base_fallback_when_dir_missing(self, tmp_path: Path) -> None:
        # If _MEIPASS is set but strix dir doesn't exist, falls back to source tree
        sys._MEIPASS = str(tmp_path / "nonexistent")  # type: ignore[attr-defined]
        try:
            result = get_strix_resource_path("config")
            # Should fall through to the source-tree path
            assert "strix" in str(result)
        finally:
            del sys._MEIPASS  # type: ignore[attr-defined]
