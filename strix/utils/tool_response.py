"""Shared helper for serialising tool responses to JSON strings."""

from __future__ import annotations

import json
from typing import Any


def tool_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)
