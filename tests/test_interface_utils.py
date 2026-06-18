"""Unit tests for strix.interface.utils (pure utility functions)."""

from __future__ import annotations

from strix.interface.utils import (
    _derive_target_label_for_run_name,
    _extract_branch_name,
    _is_ci_environment,
    _is_pr_environment,
    _slugify_for_run_name,
    format_token_count,
    generate_run_name,
    get_cvss_color,
    get_severity_color,
)


class TestGetSeverityColor:
    def test_critical(self) -> None:
        assert get_severity_color("critical") == "#dc2626"

    def test_high(self) -> None:
        assert get_severity_color("high") == "#ea580c"

    def test_medium(self) -> None:
        assert get_severity_color("medium") == "#d97706"

    def test_low(self) -> None:
        assert get_severity_color("low") == "#65a30d"

    def test_info(self) -> None:
        assert get_severity_color("info") == "#0284c7"

    def test_unknown(self) -> None:
        assert get_severity_color("nonexistent") == "#6b7280"


class TestGetCvssColor:
    def test_critical(self) -> None:
        assert get_cvss_color(9.5) == "#dc2626"

    def test_high(self) -> None:
        assert get_cvss_color(7.5) == "#ea580c"

    def test_medium(self) -> None:
        assert get_cvss_color(5.0) == "#d97706"

    def test_low(self) -> None:
        assert get_cvss_color(2.0) == "#65a30d"

    def test_none(self) -> None:
        assert get_cvss_color(0.0) == "#6b7280"

    def test_boundary_9(self) -> None:
        assert get_cvss_color(9.0) == "#dc2626"

    def test_boundary_7(self) -> None:
        assert get_cvss_color(7.0) == "#ea580c"

    def test_boundary_4(self) -> None:
        assert get_cvss_color(4.0) == "#d97706"


class TestFormatTokenCount:
    def test_millions(self) -> None:
        assert format_token_count(1_500_000) == "1.5M"

    def test_thousands(self) -> None:
        assert format_token_count(2_500) == "2.5K"

    def test_hundreds(self) -> None:
        assert format_token_count(500) == "500"

    def test_zero(self) -> None:
        assert format_token_count(0) == "0"

    def test_none(self) -> None:
        assert format_token_count(None) == "0"

    def test_exact_million(self) -> None:
        assert format_token_count(1_000_000) == "1.0M"

    def test_exact_thousand(self) -> None:
        assert format_token_count(1_000) == "1.0K"


class TestSlugifyForRunName:
    def test_simple(self) -> None:
        assert _slugify_for_run_name("Hello World") == "hello-world"

    def test_special_chars(self) -> None:
        assert _slugify_for_run_name("test@app!#$%") == "test-app"

    def test_max_length(self) -> None:
        result = _slugify_for_run_name("a" * 100, max_length=10)
        assert len(result) <= 10

    def test_empty_returns_pentest(self) -> None:
        assert _slugify_for_run_name("") == "pentest"

    def test_only_special_chars(self) -> None:
        assert _slugify_for_run_name("!@#$%") == "pentest"

    def test_strips_leading_trailing_hyphens(self) -> None:
        assert _slugify_for_run_name("---hello---") == "hello"

    def test_truncation_strips_trailing_hyphen(self) -> None:
        result = _slugify_for_run_name("hello-world-test", max_length=6)
        assert not result.endswith("-")


class TestDeriveTargetLabelForRunName:
    def test_none_targets(self) -> None:
        assert _derive_target_label_for_run_name(None) == "pentest"

    def test_empty_targets(self) -> None:
        assert _derive_target_label_for_run_name([]) == "pentest"

    def test_web_application(self) -> None:
        targets = [
            {"type": "web_application", "details": {"target_url": "https://app.example.com/path"}}
        ]
        result = _derive_target_label_for_run_name(targets)
        assert result == "app.example.com"

    def test_repository(self) -> None:
        targets = [
            {"type": "repository", "details": {"target_repo": "https://github.com/org/my-repo.git"}}
        ]
        result = _derive_target_label_for_run_name(targets)
        assert result == "my-repo"

    def test_local_code(self) -> None:
        targets = [{"type": "local_code", "details": {"target_path": "/home/user/my-project"}}]
        result = _derive_target_label_for_run_name(targets)
        assert result == "my-project"

    def test_ip_address(self) -> None:
        targets = [{"type": "ip_address", "details": {"target_ip": "192.168.1.1"}}]
        result = _derive_target_label_for_run_name(targets)
        assert result == "192.168.1.1"

    def test_unknown_type_uses_original(self) -> None:
        targets = [{"type": "unknown_type", "details": {}, "original": "custom-target"}]
        result = _derive_target_label_for_run_name(targets)
        assert result == "custom-target"


class TestGenerateRunName:
    def test_has_random_suffix(self) -> None:
        name = generate_run_name()
        parts = name.rsplit("_", 1)
        assert len(parts) == 2
        assert len(parts[1]) == 4  # 2 bytes hex = 4 chars

    def test_with_targets(self) -> None:
        targets = [{"type": "web_application", "details": {"target_url": "https://example.com"}}]
        name = generate_run_name(targets)
        assert "example-com" in name

    def test_without_targets(self) -> None:
        name = generate_run_name(None)
        assert name.startswith("pentest_")


class TestIsCiEnvironment:
    def test_github_actions(self) -> None:
        assert _is_ci_environment({"GITHUB_ACTIONS": "true"}) is True

    def test_gitlab_ci(self) -> None:
        assert _is_ci_environment({"GITLAB_CI": "true"}) is True

    def test_not_ci(self) -> None:
        assert _is_ci_environment({}) is False

    def test_ci_generic(self) -> None:
        assert _is_ci_environment({"CI": "true"}) is True


class TestIsPrEnvironment:
    def test_github_pr(self) -> None:
        assert _is_pr_environment({"GITHUB_BASE_REF": "main"}) is True

    def test_gitlab_mr(self) -> None:
        assert _is_pr_environment({"CI_MERGE_REQUEST_TARGET_BRANCH_NAME": "main"}) is True

    def test_not_pr(self) -> None:
        assert _is_pr_environment({}) is False


class TestExtractBranchName:
    def test_full_ref(self) -> None:
        assert _extract_branch_name("refs/remotes/origin/main") == "main"

    def test_short_ref(self) -> None:
        assert _extract_branch_name("main") == "main"

    def test_none(self) -> None:
        assert _extract_branch_name(None) is None

    def test_empty(self) -> None:
        assert _extract_branch_name("") is None

    def test_whitespace_only(self) -> None:
        assert _extract_branch_name("   ") is None
