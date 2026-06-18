"""Unit tests for strix.core.paths."""

from __future__ import annotations

from pathlib import Path

from strix.core.paths import (
    RUN_RECORD_FILENAME,
    RUNS_DIR_NAME,
    RUNTIME_STATE_DIR_NAME,
    run_dir_for,
    run_record_path,
    runtime_state_dir,
)


class TestRunDirFor:
    def test_default_cwd(self, tmp_path: Path, monkeypatch: object) -> None:
        import os

        monkeypatch.setattr(os, "getcwd", lambda: str(tmp_path))  # type: ignore[attr-defined]
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path))  # type: ignore[arg-type]
        result = run_dir_for("my-scan")
        assert result == tmp_path / RUNS_DIR_NAME / "my-scan"

    def test_explicit_cwd(self, tmp_path: Path) -> None:
        result = run_dir_for("scan-123", cwd=tmp_path)
        assert result == tmp_path / RUNS_DIR_NAME / "scan-123"

    def test_nested_run_name(self, tmp_path: Path) -> None:
        result = run_dir_for("deep/nested", cwd=tmp_path)
        assert result == tmp_path / RUNS_DIR_NAME / "deep" / "nested"


class TestRuntimeStateDir:
    def test_returns_state_subdir(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "strix_runs" / "scan-1"
        result = runtime_state_dir(run_dir)
        assert result == run_dir / RUNTIME_STATE_DIR_NAME


class TestRunRecordPath:
    def test_returns_run_json(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "strix_runs" / "scan-1"
        result = run_record_path(run_dir)
        assert result == run_dir / RUN_RECORD_FILENAME
        assert result.name == "run.json"
