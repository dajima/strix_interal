from __future__ import annotations

import logging
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Any

from strix.config import load_settings
from strix.telemetry._common import (
    SESSION_ID,
    base_props,
    get_version,
    is_first_run,
)
from strix.telemetry._scan_stats import (
    llm_usage_props,
    scan_duration_seconds,
    vulnerability_counts,
)


if TYPE_CHECKING:
    from strix.report.state import ReportState


logger = logging.getLogger(__name__)

_SCARF_ENDPOINT = "https://strix.gateway.scarf.sh"


def _is_enabled() -> bool:
    return load_settings().telemetry.enabled


def _send(event: str, properties: dict[str, Any]) -> None:
    if not _is_enabled():
        logger.debug("scarf disabled; skipping event %s", event)
        return
    try:
        props = dict(properties)
        version = str(props.pop("strix_version", get_version()) or "unknown")
        path = f"/{urllib.parse.quote(event, safe='')}/{urllib.parse.quote(version, safe='')}"
        query = urllib.parse.urlencode(
            {k: ("" if v is None else str(v)) for k, v in props.items()},
        )
        url = f"{_SCARF_ENDPOINT}{path}"
        if query:
            url = f"{url}?{query}"
        req = urllib.request.Request(url, method="POST")  # noqa: S310
        with urllib.request.urlopen(req, timeout=10):  # noqa: S310  # nosec B310
            pass
    except Exception:  # noqa: BLE001
        logger.debug("scarf send failed for event %s", event, exc_info=True)
    else:
        logger.debug("scarf event sent: %s", event)


def start(
    model: str | None,
    scan_mode: str | None,
    is_whitebox: bool,
    interactive: bool,
    has_instructions: bool,
) -> None:
    _send(
        "scan_started",
        {
            **base_props(),
            "session": SESSION_ID,
            "model": model or "unknown",
            "scan_mode": scan_mode or "unknown",
            "scan_type": "whitebox" if is_whitebox else "blackbox",
            "interactive": interactive,
            "has_instructions": has_instructions,
            "first_run": is_first_run(),
        },
    )


def finding(severity: str) -> None:
    _send(
        "finding_reported",
        {
            **base_props(),
            "session": SESSION_ID,
            "severity": severity.lower(),
        },
    )


def end(report_state: ReportState, exit_reason: str = "completed") -> None:
    vuln_counts = vulnerability_counts(report_state)
    _send(
        "scan_ended",
        {
            **base_props(),
            "session": SESSION_ID,
            "exit_reason": exit_reason,
            "duration_seconds": round(scan_duration_seconds(report_state)),
            "vulnerabilities_total": len(report_state.vulnerability_reports),
            **{f"vulnerabilities_{k}": v for k, v in vuln_counts.items()},
            **llm_usage_props(report_state),
        },
    )


def error(error_type: str, error_msg: str | None = None) -> None:
    props: dict[str, Any] = {
        **base_props(),
        "session": SESSION_ID,
        "error_type": error_type,
    }
    if error_msg:
        props["error_msg"] = error_msg
    _send("error", props)
