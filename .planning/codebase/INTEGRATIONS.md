# Integrations & External Dependencies

**Last mapped:** 2026-06-16
**Commit:** 11e5d1c

## External APIs & Services

### LLM Providers (via LiteLLM)

Strix supports any LLM provider available through LiteLLM. Provider selection uses the provider/model prefix convention:

| Prefix | Routing | Config |
|---|---|---|
| openai/ | OpenAI Responses or Chat Completions API | LLM_API_KEY, OPENAI_BASE_URL |
| nthropic/ | Anthropic Messages API | ANTHROPIC_API_KEY (auto-detected) |
| deepseek/ | DeepSeek API | DEEPSEEK_API_KEY (auto-detected) |
| ollama/ | Ollama → litellm ollama_chat/ | OLLAMA_API_BASE |
| (bare name) | OpenAI by default | Same as openai/ |
| any other x/ | LiteLLM fallback | Provider-specific env keys auto-detected |

Key setting: STRIX_LLM env var (required). LLM_API_KEY + LLM_API_BASE are optional (not needed for local models, Vertex AI, AWS bedrock, etc.).

API key mirroring (_mirror_api_key_to_provider_env): When LLM_API_KEY is set, Strix uses litellm.validate_environment to discover the actual provider API key env var names and sets them from the generic key — one key works across providers.

### Perplexity AI

- **Purpose:** Real-time web research during scans
- **Config:** PERPLEXITY_API_KEY env var (optional)
- **Tool:** web_search (strix/tools/web_search/tool.py)

### Docker Engine API

- **Purpose:** Sandboxed execution environment for AI agents
- **Connection:** docker.from_env() — uses local Docker daemon
- **Image:** ghcr.io/usestrix/strix-sandbox:1.0.0
- **Client:** Custom StrixDockerSandboxClient in strix/runtime/docker_client.py
- **Privileges:** Injects NET_ADMIN + NET_RAW capabilities, configures host.docker.internal host-gateway
- **Caido bootstrap:** strix/runtime/caido_bootstrap.py — container-init scripts

### Caido Proxy

- **Purpose:** Traffic interception proxy for HTTP request/response analysis
- **SDK:** caido-sdk-client >=0.2.0
- **Tools:** list_requests, iew_request, epeat_request, list_sitemap, iew_sitemap_entry, scope_rules (strix/tools/proxy/)
- **Container bootstrap:** Configures Caido inside the sandbox container at startup

### Telemetry

- **PostHog** (strix/telemetry/posthog.py) — product analytics
- **Scarf** (strix/telemetry/scarf.py) — usage tracking
- **Config:** STRIX_TELEMETRY env var (default: enabled)
- **Events tracked:** scan start/end, model used, scan mode, whitebox flag, errors

## GitHub Container Registry

- **ghcr.io/usestrix/strix-sandbox:1.0.0** — default sandbox image
- Configurable via STRIX_IMAGE env var
- Pulled on first run, cached locally

## CI/CD

- **Build + Release workflow:** .github/workflows/build-release.yml
- **PyPI:** Published as strix-agent (version in pyproject.toml)
- **PyInstaller:** strix.spec for standalone binary distribution

## Network Dependencies (Runtime)

| Dependency | Direction | Protocol |
|---|---|---|
| LLM API endpoint | Outbound | HTTPS |
| Perplexity API | Outbound | HTTPS |
| Target application | Outbound | HTTP(S) |
| Docker daemon | Local | Unix socket / TCP |
| Caido proxy | Container-internal | HTTP |
| GitHub Container Registry | Outbound | HTTPS (image pull) |

## Config Surface

All integration config flows through strix/config/settings.py (pydantic-settings BaseSettings), with env var aliases:

| **LLM** | STRIX_LLM, LLM_API_KEY, LLM_API_BASE, STRIX_REASONING_EFFORT, LLM_TIMEOUT |
| **Runtime** | STRIX_IMAGE, STRIX_RUNTIME_BACKEND |
| **Telemetry** | STRIX_TELEMETRY |
| **Integrations** | PERPLEXITY_API_KEY |
