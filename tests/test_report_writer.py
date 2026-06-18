"""Unit tests for strix.report.writer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from strix.report.writer import (
    _atomic_write_text,
    read_run_record,
    render_vulnerability_md,
    write_executive_report,
    write_run_record,
    write_vulnerabilities,
)


class TestAtomicWriteText:
    def test_creates_file(self, tmp_path: Path) -> None:
        target = tmp_path / "output.txt"
        _atomic_write_text(target, "hello world")
        assert target.read_text(encoding="utf-8") == "hello world"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        target = tmp_path / "sub" / "dir" / "file.txt"
        _atomic_write_text(target, "nested content")
        assert target.read_text(encoding="utf-8") == "nested content"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "overwrite.txt"
        target.write_text("old", encoding="utf-8")
        _atomic_write_text(target, "new")
        assert target.read_text(encoding="utf-8") == "new"


class TestReadRunRecord:
    def test_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        result = read_run_record(tmp_path / "no-such-dir")
        assert result == {}

    def test_valid_json(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "scan-1"
        run_dir.mkdir()
        (run_dir / "run.json").write_text(
            json.dumps({"status": "running", "targets": []}),
            encoding="utf-8",
        )
        result = read_run_record(run_dir)
        assert result["status"] == "running"

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "scan-2"
        run_dir.mkdir()
        (run_dir / "run.json").write_text("not json", encoding="utf-8")
        with pytest.raises(RuntimeError, match="unreadable"):
            read_run_record(run_dir)

    def test_non_object_raises(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "scan-3"
        run_dir.mkdir()
        (run_dir / "run.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with pytest.raises(RuntimeError, match="not an object"):
            read_run_record(run_dir)


class TestWriteRunRecord:
    def test_creates_run_json(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "scan-1"
        run_dir.mkdir()
        write_run_record(run_dir, {"status": "completed", "findings": 3})
        result = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        assert result["status"] == "completed"
        assert result["findings"] == 3


class TestWriteExecutiveReport:
    def test_creates_report_file(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "scan-1"
        run_dir.mkdir()
        write_executive_report(run_dir, "No critical issues found.")
        path = run_dir / "penetration_test_report.md"
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "# Security Penetration Test Report" in content
        assert "No critical issues found." in content
        assert "Generated:" in content


class TestWriteVulnerabilities:
    def test_writes_new_reports(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "scan-1"
        run_dir.mkdir()

        reports = [
            {
                "id": "vuln-0001",
                "title": "SQL Injection",
                "severity": "critical",
                "timestamp": "2025-01-01T00:00:00Z",
            },
            {
                "id": "vuln-0002",
                "title": "XSS",
                "severity": "high",
                "timestamp": "2025-01-01T00:01:00Z",
            },
        ]
        saved: set[str] = set()
        count = write_vulnerabilities(run_dir, reports, saved)

        assert count == 2
        assert (run_dir / "vulnerabilities" / "vuln-0001.md").exists()
        assert (run_dir / "vulnerabilities" / "vuln-0002.md").exists()
        assert (run_dir / "vulnerabilities.csv").exists()
        assert (run_dir / "vulnerabilities.json").exists()
        assert "vuln-0001" in saved
        assert "vuln-0002" in saved

    def test_skips_already_saved(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "scan-2"
        run_dir.mkdir()

        reports = [
            {
                "id": "vuln-0001",
                "title": "SQL Injection",
                "severity": "critical",
                "timestamp": "2025-01-01T00:00:00Z",
            },
        ]
        saved: set[str] = {"vuln-0001"}
        count = write_vulnerabilities(run_dir, reports, saved)
        assert count == 0

    def test_csv_ordering(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "scan-3"
        run_dir.mkdir()

        reports = [
            {
                "id": "vuln-low",
                "title": "Info leak",
                "severity": "low",
                "timestamp": "2025-01-01T00:00:00Z",
            },
            {
                "id": "vuln-crit",
                "title": "RCE",
                "severity": "critical",
                "timestamp": "2025-01-01T00:01:00Z",
            },
        ]
        saved: set[str] = set()
        write_vulnerabilities(run_dir, reports, saved)

        csv_content = (run_dir / "vulnerabilities.csv").read_text(encoding="utf-8")
        lines = csv_content.strip().split("\n")
        # Header + 2 rows, critical should come first
        assert len(lines) == 3
        assert "vuln-crit" in lines[1]
        assert "vuln-low" in lines[2]


class TestRenderVulnerabilityMd:
    def test_basic_report(self) -> None:
        report = {
            "id": "vuln-0001",
            "title": "SQL Injection",
            "severity": "critical",
            "timestamp": "2025-01-01T00:00:00Z",
            "description": "SQL injection via user input",
            "target": "https://example.com",
            "endpoint": "/api/login",
            "method": "POST",
        }
        result = render_vulnerability_md(report)
        assert "# SQL Injection" in result
        assert "**Severity:** CRITICAL" in result
        assert "**Target:** https://example.com" in result
        assert "**Endpoint:** /api/login" in result
        assert "## Description" in result

    def test_with_poc(self) -> None:
        report = {
            "id": "vuln-0002",
            "title": "XSS",
            "severity": "high",
            "timestamp": "2025-01-01T00:00:00Z",
            "poc_description": "Inject script tag",
            "poc_script_code": "<script>alert(1)</script>",
        }
        result = render_vulnerability_md(report)
        assert "## Proof of Concept" in result
        assert "Inject script tag" in result
        assert "<script>alert(1)</script>" in result

    def test_with_code_locations(self) -> None:
        report = {
            "id": "vuln-0003",
            "title": "Hardcoded Secret",
            "severity": "medium",
            "timestamp": "2025-01-01T00:00:00Z",
            "code_locations": [
                {
                    "file": "src/config.py",
                    "start_line": 10,
                    "end_line": 12,
                    "label": "API key stored in plaintext",
                    "snippet": 'API_KEY = "sk-secret123"',
                }
            ],
        }
        result = render_vulnerability_md(report)
        assert "## Code Analysis" in result
        assert "`src/config.py`" in result
        assert "(lines 10-12)" in result
        assert "API key stored in plaintext" in result

    def test_with_remediation(self) -> None:
        report = {
            "id": "vuln-0004",
            "title": "Open Redirect",
            "severity": "low",
            "timestamp": "2025-01-01T00:00:00Z",
            "remediation_steps": "Validate redirect URLs against allowlist",
        }
        result = render_vulnerability_md(report)
        assert "## Remediation" in result
        assert "Validate redirect URLs" in result

    def test_minimal_report(self) -> None:
        report = {"id": "vuln-0005"}
        result = render_vulnerability_md(report)
        assert "# Untitled Vulnerability" in result
        assert "**Severity:** UNKNOWN" in result
