import json
import logging
import urllib.request
from typing import TYPE_CHECKING, Any

from strix.config import load_settings
from strix.telemetry._common import (
    SESSION_ID,
    base_props,
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

_POSTHOG_PUBLIC_API_KEY = "phc_7rO3XRuNT5sgSKAl6HDIrWdSGh1COzxw0vxVIAR6vVZ"
_POSTHOG_HOST = "https://us.i.posthog.com"


def _is_enabled() -> bool:
    return load_settings().telemetry.enabled


def _send(event: str, properties: dict[str, Any]) -> None:
    if not _is_enabled():
        logger.debug("posthog disabled; skipping event %s", event)
        return
    try:
        payload = {
            "api_key": _POSTHOG_PUBLIC_API_KEY,
            "event": event,
            "distinct_id": SESSION_ID,
            "properties": properties,
        }
        req = urllib.request.Request(  # noqa: S310
            f"{_POSTHOG_HOST}/capture/",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10):  # noqa: S310  # nosec B310
            pass
    except Exception:  # noqa: BLE001
        logger.debug("posthog send failed for event %s", event, exc_info=True)
    else:
        logger.debug("posthog event sent: %s", event)


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
            "severity": severity.lower(),
        },
    )


def end(report_state: "ReportState", exit_reason: str = "completed") -> None:
    vuln_counts = vulnerability_counts(report_state)
    _send(
        "scan_ended",
        {
            **base_props(),
            "exit_reason": exit_reason,
            "duration_seconds": round(scan_duration_seconds(report_state)),
            "vulnerabilities_total": len(report_state.vulnerability_reports),
            **{f"vulnerabilities_{k}": v for k, v in vuln_counts.items()},
            **llm_usage_props(report_state),
        },
    )


def error(error_type: str, error_msg: str | None = None) -> None:
    props = {**base_props(), "error_type": error_type}
    if error_msg:
        props["error_msg"] = error_msg
    _send("error", props)
