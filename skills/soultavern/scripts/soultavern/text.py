"""Shared text helpers used by per-target render functions.

Lives in its own module (not ``render.py``) because the per-target
renderers under ``targets/*.py`` need these helpers, and ``render.py``
imports the targets — so co-locating helpers with ``render`` would
create a circular import.
"""

from __future__ import annotations

from typing import Any, Callable

from .sanitize import sanitize
from .substitute import substitute


def make_s(char_name: str, user_noun: str) -> Callable[[Any], str]:
    """Return the ``s`` function — substitute placeholders + sanitize.

    Replaces what was the Jinja ``| s`` filter. Per-target renderers
    construct one of these once and apply it to each card field they emit.
    """

    def _s(text: Any) -> str:
        if not isinstance(text, str):
            text = "" if text is None else str(text)
        return sanitize(substitute(text, char_name, user_noun))

    return _s


def quote_block(text: str) -> str:
    """Prefix every line of ``text`` with ``> `` to form a markdown blockquote."""
    if not text:
        return ""
    return "\n".join(("> " + line) if line else ">" for line in text.splitlines())


def collapse_blank_lines(text: str) -> str:
    """Collapse runs of 3+ newlines to 2, keep trailing single newline."""
    out_lines: list[str] = []
    blank = 0
    for line in text.splitlines():
        if line.strip() == "":
            blank += 1
            if blank <= 1:
                out_lines.append("")
        else:
            blank = 0
            out_lines.append(line)
    while out_lines and out_lines[0] == "":
        out_lines.pop(0)
    while out_lines and out_lines[-1] == "":
        out_lines.pop()
    return "\n".join(out_lines) + "\n"


def render_metadata_comment(metadata: dict[str, Any] | None, header_line: str) -> str:
    """Emit the HTML-comment metadata block at the top of a SOUL.md.

    ``header_line`` is the first line inside ``<!-- ... -->`` (it
    differs between hermes / openclaw to call out which target wrote
    the file).
    """
    if not metadata:
        return ""
    lines: list[str] = ["<!--", header_line]
    if metadata.get("creator"):
        lines.append(f"creator: {metadata['creator']}")
    if metadata.get("creator_version"):
        lines.append(f"creator_version: {metadata['creator_version']}")
    if metadata.get("tags"):
        lines.append(f"tags: {', '.join(metadata['tags'])}")
    if metadata.get("creator_notes"):
        notes = str(metadata["creator_notes"]).replace("\n", "\n  ")
        lines.append("creator_notes: |")
        lines.append(f"  {notes}")
    if metadata.get("extensions"):
        lines.append("extensions: (preserved, not parsed)")
    lines.append("-->")
    return "\n".join(lines)


def render_first_mes_block(text: str, s: Callable[[Any], str]) -> str:
    """Render the ``first_mes`` block — each line prefixed with ``> ``."""
    rendered = s(text)
    return "\n".join(f"> {line}" for line in rendered.splitlines())


def render_alternate_greetings(greetings: list[Any], s: Callable[[Any], str]) -> str:
    """Render the alternate-greetings list — markdown bullets, each
    line of each greeting becomes its own blockquote line."""
    blocks: list[str] = []
    for greeting in greetings:
        lines = s(greeting).splitlines()
        if not lines:
            continue
        body = [f"- > {lines[0]}"]
        for line in lines[1:]:
            body.append(f"  > {line}")
        blocks.append("\n".join(body))
    return "\n\n".join(blocks)
