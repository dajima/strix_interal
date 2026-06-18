"""Unit tests for strix.report.dedupe (pure helper functions)."""

from __future__ import annotations

import pytest

from strix.report.dedupe import _parse_dedupe_response, _prepare_report_for_comparison


class TestPrepareReportForComparison:
    def test_extracts_relevant_fields(self) -> None:
        report = {
            "id": "vuln-0001",
            "title": "SQL Injection in /api/login",
            "description": "The login endpoint is vulnerable to SQL injection",
            "impact": "Full database access",
            "target": "https://example.com",
            "technical_analysis": "Input is concatenated directly",
            "poc_description": "Send ' OR 1=1 --",
            "endpoint": "/api/login",
            "method": "POST",
            "irrelevant_field": "should be excluded",
            "another_field": 42,
        }
        result = _prepare_report_for_comparison(report)
        assert result["id"] == "vuln-0001"
        assert result["title"] == "SQL Injection in /api/login"
        assert result["endpoint"] == "/api/login"
        assert "irrelevant_field" not in result
        assert "another_field" not in result

    def test_truncates_long_strings(self) -> None:
        report = {
            "id": "vuln-0002",
            "description": "x" * 10000,
        }
        result = _prepare_report_for_comparison(report)
        assert len(result["description"]) == 8000 + len("...[truncated]")
        assert result["description"].endswith("...[truncated]")

    def test_skips_empty_fields(self) -> None:
        report = {
            "id": "vuln-0003",
            "title": "Test",
            "description": "",
            "impact": None,
            "target": "",
        }
        result = _prepare_report_for_comparison(report)
        assert "id" in result
        assert "title" in result
        assert "description" not in result
        assert "impact" not in result
        assert "target" not in result

    def test_empty_report(self) -> None:
        result = _prepare_report_for_comparison({})
        assert result == {}


class TestParseDedupeResponse:
    def test_valid_json(self) -> None:
        content = '{"is_duplicate": true, "duplicate_id": "vuln-0001", "confidence": 0.95, "reason": "Same endpoint"}'
        result = _parse_dedupe_response(content)
        assert result["is_duplicate"] is True
        assert result["duplicate_id"] == "vuln-0001"
        assert result["confidence"] == 0.95
        assert result["reason"] == "Same endpoint"

    def test_json_in_code_fence(self) -> None:
        content = '```json\n{"is_duplicate": false, "duplicate_id": "", "confidence": 0.9, "reason": "Different endpoint"}\n```'
        result = _parse_dedupe_response(content)
        assert result["is_duplicate"] is False
        assert result["duplicate_id"] == ""
        assert result["confidence"] == 0.9

    def test_json_with_surrounding_text(self) -> None:
        content = 'Here is my analysis:\n{"is_duplicate": true, "duplicate_id": "vuln-0005", "confidence": 0.8, "reason": "Same vuln"}\nDone.'
        result = _parse_dedupe_response(content)
        assert result["is_duplicate"] is True
        assert result["duplicate_id"] == "vuln-0005"

    def test_no_json_raises(self) -> None:
        with pytest.raises(ValueError, match="No JSON object found"):
            _parse_dedupe_response("just plain text")

    def test_truncates_long_duplicate_id(self) -> None:
        long_id = "x" * 200
        content = f'{{"is_duplicate": true, "duplicate_id": "{long_id}", "confidence": 0.5, "reason": "test"}}'
        result = _parse_dedupe_response(content)
        assert len(result["duplicate_id"]) == 64

    def test_truncates_long_reason(self) -> None:
        long_reason = "y" * 1000
        content = f'{{"is_duplicate": false, "duplicate_id": "", "confidence": 0.5, "reason": "{long_reason}"}}'
        result = _parse_dedupe_response(content)
        assert len(result["reason"]) == 500

    def test_invalid_confidence_defaults_to_zero(self) -> None:
        content = (
            '{"is_duplicate": false, "duplicate_id": "", "confidence": "invalid", "reason": "test"}'
        )
        result = _parse_dedupe_response(content)
        assert result["confidence"] == 0.0

    def test_missing_fields_default(self) -> None:
        content = "{}"
        result = _parse_dedupe_response(content)
        assert result["is_duplicate"] is False
        assert result["duplicate_id"] == ""
        assert result["confidence"] == 0.0
        assert result["reason"] == ""
