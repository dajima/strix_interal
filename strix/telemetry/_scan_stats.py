"""Shared helpers for computing scan-end telemetry properties."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from strix.report.state import ReportState


def vulnerability_counts(report_state: ReportState) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for v in report_state.vulnerability_reports:
        sev = v.get("severity", "info").lower()
        if sev in counts:
            counts[sev] += 1
    return counts


def scan_duration_seconds(report_state: ReportState) -> float:
    try:
        start = datetime.fromisoformat(report_state.start_time.replace("Z", "+00:00"))
        end_iso = report_state.end_time or datetime.now(start.tzinfo).isoformat()
        return (datetime.fromisoformat(end_iso.replace("Z", "+00:00")) - start).total_seconds()
    except (ValueError, TypeError, AttributeError):
        return 0.0


def llm_usage_props(report_state: ReportState) -> dict[str, int | float]:
    try:
        usage = report_state.get_total_llm_usage()
        if isinstance(usage, dict):
            return {
                "llm_requests": int(usage.get("requests") or 0),
                "llm_input_tokens": int(usage.get("input_tokens") or 0),
                "llm_output_tokens": int(usage.get("output_tokens") or 0),
                "llm_tokens": int(usage.get("total_tokens") or 0),
                "llm_cost": float(usage.get("cost") or 0.0),
            }
    except (TypeError, ValueError, AttributeError):
        pass
    return {}
