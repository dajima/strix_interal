"""Unit tests for strix.core.inputs."""

from __future__ import annotations

from strix.core.inputs import (
    build_root_task,
    build_scope_context,
    child_initial_input,
)


class TestBuildRootTask:
    def test_empty_config(self) -> None:
        result = build_root_task({})
        assert isinstance(result, str)

    def test_repository_target(self) -> None:
        config = {
            "targets": [
                {
                    "type": "repository",
                    "details": {
                        "target_repo": "https://github.com/org/app",
                        "workspace_subdir": "app",
                        "cloned_repo_path": "/workspace/app",
                    },
                }
            ]
        }
        result = build_root_task(config)
        assert "https://github.com/org/app" in result
        assert "/workspace/app" in result
        assert "Repositories:" in result

    def test_local_code_target(self) -> None:
        config = {
            "targets": [
                {
                    "type": "local_code",
                    "details": {"target_path": "/home/user/project", "workspace_subdir": "project"},
                }
            ]
        }
        result = build_root_task(config)
        assert "/home/user/project" in result
        assert "Local Codebases:" in result

    def test_web_application_target(self) -> None:
        config = {
            "targets": [
                {
                    "type": "web_application",
                    "details": {"target_url": "https://example.com"},
                }
            ]
        }
        result = build_root_task(config)
        assert "https://example.com" in result
        assert "URLs:" in result

    def test_ip_address_target(self) -> None:
        config = {"targets": [{"type": "ip_address", "details": {"target_ip": "192.168.1.1"}}]}
        result = build_root_task(config)
        assert "192.168.1.1" in result
        assert "IP Addresses:" in result

    def test_user_instructions_appended(self) -> None:
        config = {
            "targets": [],
            "user_instructions": "Focus on auth bypass",
        }
        result = build_root_task(config)
        assert "Special instructions: Focus on auth bypass" in result

    def test_diff_scope_active(self) -> None:
        config = {
            "targets": [],
            "diff_scope": {
                "active": True,
                "repos": [
                    {
                        "workspace_subdir": "my-app",
                        "analyzable_files_count": 5,
                        "deleted_files_count": 2,
                    }
                ],
            },
        }
        result = build_root_task(config)
        assert "Scope Constraints:" in result
        assert "diff-scope mode is active" in result
        assert "5 changed file(s)" in result
        assert "2 deleted file(s)" in result


class TestBuildScopeContext:
    def test_empty_targets(self) -> None:
        result = build_scope_context({"targets": []})
        assert result["authorized_targets"] == []
        assert result["scope_source"] == "system_scan_config"

    def test_web_application_authorized(self) -> None:
        config = {
            "targets": [
                {
                    "type": "web_application",
                    "details": {"target_url": "https://example.com"},
                }
            ]
        }
        result = build_scope_context(config)
        targets = result["authorized_targets"]
        assert len(targets) == 1
        assert targets[0]["type"] == "web_application"
        assert targets[0]["value"] == "https://example.com"

    def test_repository_with_workspace(self) -> None:
        config = {
            "targets": [
                {
                    "type": "repository",
                    "details": {
                        "target_repo": "https://github.com/org/repo",
                        "workspace_subdir": "repo",
                    },
                }
            ]
        }
        result = build_scope_context(config)
        targets = result["authorized_targets"]
        assert targets[0]["workspace_path"] == "/workspace/repo"

    def test_multiple_targets(self) -> None:
        config = {
            "targets": [
                {"type": "web_application", "details": {"target_url": "https://a.com"}},
                {"type": "ip_address", "details": {"target_ip": "10.0.0.1"}},
            ]
        }
        result = build_scope_context(config)
        assert len(result["authorized_targets"]) == 2


class TestChildInitialInput:
    def test_basic_without_history(self) -> None:
        result = child_initial_input(
            name="scanner-1",
            child_id="child-001",
            parent_id="parent-001",
            task="Find XSS vulnerabilities",
            parent_history=[],
        )
        assert len(result) == 2
        assert "scanner-1" in result[0]["content"]
        assert "child-001" in result[0]["content"]
        assert "parent-001" in result[0]["content"]
        assert result[1]["content"] == "Find XSS vulnerabilities"

    def test_with_parent_history(self) -> None:
        history = [{"role": "assistant", "content": "Starting scan..."}]
        result = child_initial_input(
            name="scanner-2",
            child_id="child-002",
            parent_id="parent-002",
            task="Check IDOR",
            parent_history=history,
        )
        assert len(result) == 3
        assert "Inherited context" in result[0]["content"]
        assert "Starting scan..." in result[0]["content"]
        assert "scanner-2" in result[1]["content"]
        assert result[2]["content"] == "Check IDOR"
