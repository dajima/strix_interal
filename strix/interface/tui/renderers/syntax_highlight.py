"""Shared Pygments-based syntax highlighting for TUI renderers."""

from __future__ import annotations

from functools import cache
from typing import Any

from pygments.styles import get_style_by_name
from rich.text import Text


@cache
def get_style_colors() -> dict[Any, str]:
    style = get_style_by_name("native")
    return {token: f"#{style_def['color']}" for token, style_def in style if style_def["color"]}


def get_token_color(token_type: Any) -> str | None:
    colors = get_style_colors()
    while token_type:
        if token_type in colors:
            return colors[token_type]
        token_type = token_type.parent
    return None


def highlight_tokens(lexer: Any, code: str) -> Text:
    text = Text()
    for token_type, token_value in lexer.get_tokens(code):
        if not token_value:
            continue
        color = get_token_color(token_type)
        text.append(token_value, style=color)
    return text
