"""Parse-time hygiene: strip invisible / control characters from card text.

These transformations run before placeholder substitution and before
red-flag scanning. They are intentionally conservative — visible text is
left alone, only categories of characters that have no legitimate purpose
in a roleplay card are removed.
"""

from __future__ import annotations

import re
import unicodedata

# Unicode categories that should never appear in card text:
# - Cc: control characters (we keep \t and \n explicitly below)
# - Cf: format characters (zero-width spaces, joiners, RTL/LTR overrides, ...)
_STRIPPED_CATEGORIES = {"Cc", "Cf"}
_KEPT_CONTROL = {"\t", "\n"}

# A few specific code points worth calling out, all in Cf:
#   U+200B-U+200D zero-width space / non-joiner / joiner
#   U+200E,U+200F LTR / RTL marks
#   U+202A-U+202E embedding / override (RLO is U+202E — used in spoofing)
#   U+2060        word joiner
#   U+2066-U+2069 directional isolates
#   U+FEFF        zero-width no-break space (BOM)

_LONG_TOKEN_RE = re.compile(r"\S{200,}")


def sanitize(text: str | None) -> str:
    """Return ``text`` with invisible control / format characters stripped."""
    if not text:
        return ""
    out: list[str] = []
    for ch in text:
        if ch in _KEPT_CONTROL:
            out.append(ch)
            continue
        if unicodedata.category(ch) in _STRIPPED_CATEGORIES:
            continue
        out.append(ch)
    return "".join(out)


def find_long_unbroken_tokens(text: str | None, threshold: int = 200) -> list[str]:
    """Return runs of ``threshold``+ non-whitespace characters.

    Long unbroken tokens in human-readable persona text usually indicate an
    encoded payload (base64, hex, packed JSON). Reported as warnings, not
    stripped — a card author might legitimately include a long URL.
    """
    if not text:
        return []
    return [m.group(0) for m in re.finditer(rf"\S{{{threshold},}}", text)]
