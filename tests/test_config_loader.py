"""Unit tests for strix.config.loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from strix.config.loader import (
    _aliases_for,
    _read_json_overrides,
    apply_config_override,
    load_settings,
    persist_current,
)
from strix.config.settings import Settings


@pytest.fixture(autouse=True)
def _reset_loader_cache() -> None:
    """Reset module-level cache between tests."""
    from strix.config import loader

    loader._cached = None
    loader._override = None


class TestAliasesFor:
    def test_field_with_alias(self) -> None:
        from strix.config.settings import LlmSettings

        model_field = LlmSettings.model_fields["model"]
        aliases = _aliases_for(model_field)
        assert "STRIX_LLM" in aliases

    def test_field_with_alias_choices(self) -> None:
        from strix.config.settings import LlmSettings

        api_key_field = LlmSettings.model_fields["api_key"]
        aliases = _aliases_for(api_key_field)
        assert "LLM_API_KEY" in aliases
        assert "OPENAI_API_KEY" in aliases


class TestReadJsonOverrides:
    def test_nonexistent_file(self, tmp_path: Path) -> None:
        result = _read_json_overrides(tmp_path / "nope.json")
        assert result == {}

    def test_invalid_json(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json at all", encoding="utf-8")
        result = _read_json_overrides(bad_file)
        assert result == {}

    def test_missing_env_block(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(json.dumps({"other": "data"}), encoding="utf-8")
        result = _read_json_overrides(cfg_file)
        assert result == {}

    def test_env_block_parsed(self, tmp_path: Path, monkeypatch: object) -> None:
        monkeypatch.delenv("STRIX_LLM", raising=False)  # type: ignore[attr-defined]
        monkeypatch.delenv("LLM_API_KEY", raising=False)  # type: ignore[attr-defined]
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)  # type: ignore[attr-defined]

        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(
            json.dumps({"env": {"STRIX_LLM": "anthropic/claude-4"}}),
            encoding="utf-8",
        )
        result = _read_json_overrides(cfg_file)
        assert "llm" in result
        assert result["llm"]["model"] == "anthropic/claude-4"

    def test_env_wins_over_json(self, tmp_path: Path, monkeypatch: object) -> None:
        monkeypatch.setenv("STRIX_LLM", "openai/gpt-5.4")  # type: ignore[attr-defined]

        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(
            json.dumps({"env": {"STRIX_LLM": "anthropic/claude-4"}}),
            encoding="utf-8",
        )
        result = _read_json_overrides(cfg_file)
        # "model" should NOT be in the result since env wins
        assert result.get("llm", {}).get("model") is None


class TestApplyConfigOverride:
    def test_invalidates_cache(self, tmp_path: Path) -> None:
        from strix.config import loader

        loader._cached = Settings()  # type: ignore[assignment]
        assert loader._cached is not None

        apply_config_override(tmp_path / "new-cfg.json")
        assert loader._cached is None
        assert loader._override == tmp_path / "new-cfg.json"


class TestLoadSettings:
    def test_memoized(self, monkeypatch: object) -> None:
        monkeypatch.delenv("STRIX_LLM", raising=False)  # type: ignore[attr-defined]
        s1 = load_settings()
        s2 = load_settings()
        assert s1 is s2

    def test_uses_override_path(self, tmp_path: Path, monkeypatch: object) -> None:
        monkeypatch.delenv("STRIX_LLM", raising=False)  # type: ignore[attr-defined]
        monkeypatch.delenv("LLM_API_KEY", raising=False)  # type: ignore[attr-defined]
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)  # type: ignore[attr-defined]

        cfg_file = tmp_path / "test-cfg.json"
        cfg_file.write_text(
            json.dumps({"env": {"STRIX_LLM": "test/model"}}),
            encoding="utf-8",
        )
        apply_config_override(cfg_file)
        s = load_settings()
        assert s.llm.model == "test/model"


class TestPersistCurrent:
    def test_writes_config_file(self, tmp_path: Path, monkeypatch: object) -> None:
        monkeypatch.setenv("STRIX_LLM", "openai/gpt-5.4")  # type: ignore[attr-defined]
        monkeypatch.setenv("LLM_API_KEY", "sk-test")  # type: ignore[attr-defined]

        cfg_file = tmp_path / "persist-test.json"
        apply_config_override(cfg_file)

        persist_current()

        assert cfg_file.exists()
        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        assert "env" in data
        assert data["env"]["STRIX_LLM"] == "openai/gpt-5.4"
        assert data["env"]["LLM_API_KEY"] == "sk-test"
