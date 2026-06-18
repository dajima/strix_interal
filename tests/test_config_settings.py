"""Unit tests for strix.config.settings."""

from __future__ import annotations

from strix.config.settings import (
    IntegrationSettings,
    LlmSettings,
    RuntimeSettings,
    Settings,
    TelemetrySettings,
)


class TestLlmSettings:
    def test_defaults(self, monkeypatch: object) -> None:
        for key in (
            "STRIX_LLM",
            "LLM_API_KEY",
            "OPENAI_API_KEY",
            "LLM_API_BASE",
            "OPENAI_API_BASE",
            "OPENAI_BASE_URL",
            "LITELLM_BASE_URL",
            "OLLAMA_API_BASE",
            "STRIX_REASONING_EFFORT",
            "LLM_TIMEOUT",
        ):
            monkeypatch.delenv(key, raising=False)  # type: ignore[attr-defined]

        s = LlmSettings()
        assert s.model is None
        assert s.api_key is None
        assert s.api_base is None
        assert s.reasoning_effort == "high"
        assert s.timeout == 300

    def test_from_env(self, monkeypatch: object) -> None:
        monkeypatch.setenv("STRIX_LLM", "openai/gpt-5.4")  # type: ignore[attr-defined]
        monkeypatch.setenv("LLM_API_KEY", "sk-test-key")  # type: ignore[attr-defined]
        monkeypatch.setenv("STRIX_REASONING_EFFORT", "medium")  # type: ignore[attr-defined]
        monkeypatch.setenv("LLM_TIMEOUT", "120")  # type: ignore[attr-defined]

        s = LlmSettings()
        assert s.model == "openai/gpt-5.4"
        assert s.api_key == "sk-test-key"
        assert s.reasoning_effort == "medium"
        assert s.timeout == 120

    def test_api_base_alias_choices(self, monkeypatch: object) -> None:
        for key in (
            "LLM_API_BASE",
            "OPENAI_API_BASE",
            "OPENAI_BASE_URL",
            "LITELLM_BASE_URL",
            "OLLAMA_API_BASE",
        ):
            monkeypatch.delenv(key, raising=False)  # type: ignore[attr-defined]

        monkeypatch.setenv("OLLAMA_API_BASE", "http://localhost:11434")  # type: ignore[attr-defined]
        s = LlmSettings()
        assert s.api_base == "http://localhost:11434"


class TestRuntimeSettings:
    def test_defaults(self, monkeypatch: object) -> None:
        monkeypatch.delenv("STRIX_IMAGE", raising=False)  # type: ignore[attr-defined]
        monkeypatch.delenv("STRIX_RUNTIME_BACKEND", raising=False)  # type: ignore[attr-defined]

        s = RuntimeSettings()
        assert s.image == "ghcr.io/usestrix/strix-sandbox:1.0.0"
        assert s.backend == "docker"


class TestTelemetrySettings:
    def test_default_enabled(self, monkeypatch: object) -> None:
        monkeypatch.delenv("STRIX_TELEMETRY", raising=False)  # type: ignore[attr-defined]
        s = TelemetrySettings()
        assert s.enabled is True

    def test_disable_via_env(self, monkeypatch: object) -> None:
        monkeypatch.setenv("STRIX_TELEMETRY", "false")  # type: ignore[attr-defined]
        s = TelemetrySettings()
        assert s.enabled is False


class TestIntegrationSettings:
    def test_defaults(self, monkeypatch: object) -> None:
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)  # type: ignore[attr-defined]
        s = IntegrationSettings()
        assert s.perplexity_api_key is None


class TestSettings:
    def test_composite_defaults(self, monkeypatch: object) -> None:
        env_keys = [
            "STRIX_LLM",
            "LLM_API_KEY",
            "OPENAI_API_KEY",
            "LLM_API_BASE",
            "OPENAI_API_BASE",
            "OPENAI_BASE_URL",
            "LITELLM_BASE_URL",
            "OLLAMA_API_BASE",
            "STRIX_REASONING_EFFORT",
            "LLM_TIMEOUT",
            "STRIX_IMAGE",
            "STRIX_RUNTIME_BACKEND",
            "STRIX_TELEMETRY",
            "PERPLEXITY_API_KEY",
        ]
        for key in env_keys:
            monkeypatch.delenv(key, raising=False)  # type: ignore[attr-defined]

        s = Settings()
        assert isinstance(s.llm, LlmSettings)
        assert isinstance(s.runtime, RuntimeSettings)
        assert isinstance(s.telemetry, TelemetrySettings)
        assert isinstance(s.integrations, IntegrationSettings)
