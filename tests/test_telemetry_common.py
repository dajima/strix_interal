"""Unit tests for strix.telemetry._common."""

from __future__ import annotations

from pathlib import Path

from strix.telemetry._common import base_props, get_version, is_first_run


class TestGetVersion:
    def test_returns_string(self) -> None:
        result = get_version()
        assert isinstance(result, str)
        assert result != ""

    def test_known_version(self) -> None:
        result = get_version()
        # The installed package should return a valid version or "unknown"
        assert result in {"1.0.4", "unknown"}


class TestBaseProps:
    def test_returns_expected_keys(self) -> None:
        props = base_props()
        assert "os" in props
        assert "arch" in props
        assert "python" in props
        assert "strix_version" in props

    def test_os_is_lowercase(self) -> None:
        props = base_props()
        assert props["os"] == props["os"].lower()

    def test_python_version_format(self) -> None:
        props = base_props()
        major, minor = props["python"].split(".")
        assert int(major) >= 3
        assert int(minor) >= 0


class TestIsFirstRun:
    def test_creates_marker_file(self, tmp_path: Path, monkeypatch: object) -> None:
        import strix.telemetry._common as common

        common._FIRST_RUN_CACHED = None
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))  # type: ignore[arg-type]

        result = is_first_run()
        assert result is True
        assert (tmp_path / ".strix" / ".seen").exists()

        # Reset cache and check again - should now be False
        common._FIRST_RUN_CACHED = None
        result2 = is_first_run()
        assert result2 is False

    def test_cached_result(self) -> None:
        import strix.telemetry._common as common

        common._FIRST_RUN_CACHED = True
        assert is_first_run() is True

        common._FIRST_RUN_CACHED = False
        assert is_first_run() is False

        # Reset for other tests
        common._FIRST_RUN_CACHED = None
