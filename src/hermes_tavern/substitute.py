"""Replace SillyTavern placeholders in card text."""

from __future__ import annotations

import re

PLACEHOLDER_RE = re.compile(r"\{\{(char|user)\}\}|<(BOT|USER)>", re.IGNORECASE)


def substitute(text: str | None, char_name: str, user_noun: str) -> str:
    """Replace ``{{char}}`` / ``{{user}}`` and the legacy ``<BOT>`` / ``<USER>``.

    - Case-insensitive.
    - Non-recursive: placeholders inside the replacement value are left alone.
    - ``None`` returns ``""`` so templates can render empty sections cleanly.
    """
    if not text:
        return ""

    def repl(match: re.Match[str]) -> str:
        token = (match.group(1) or match.group(2)).lower()
        return char_name if token in ("char", "bot") else user_noun

    return PLACEHOLDER_RE.sub(repl, text)
