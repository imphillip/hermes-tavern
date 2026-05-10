"""Managed-section append/strip helpers for the OpenClaw target.

OpenClaw's ``AGENTS.md`` is potentially shared with the user's
existing project setup — full replacement would destroy their work
config. SoulTavern marks its content with HTML-comment markers so it
can be updated and removed cleanly without touching anything outside
the section.

Marker shape (rendered as HTML comments so OpenClaw's Markdown loader
treats them as inert text):

    <!-- BEGIN soultavern:character -->
    <!-- managed by soultavern; safe to delete the markers + content
         between them, or run `soultavern delete --target openclaw` -->

    ...managed content...

    <!-- END soultavern:character -->

The two functions in this module are pure: no I/O, no globals, no
side effects. The library layer reads/writes files; this module just
transforms strings.
"""

from __future__ import annotations

import re

DEFAULT_MARKER = "soultavern:character"

_MANAGED_NOTE = (
    "<!-- managed by soultavern; safe to delete the markers + content "
    "between them, or run SoulTavern's delete.py against this workspace -->"
)


def _begin(marker: str) -> str:
    return f"<!-- BEGIN {marker} -->"


def _end(marker: str) -> str:
    return f"<!-- END {marker} -->"


def _block_pattern(marker: str) -> re.Pattern[str]:
    """Match the BEGIN..END block (greedy on inner content, anchored
    on the literal marker comments). Allows surrounding whitespace
    that the strip path then collapses."""
    return re.compile(
        rf"^[ \t]*{re.escape(_begin(marker))}.*?{re.escape(_end(marker))}[ \t]*\n?",
        re.DOTALL | re.MULTILINE,
    )


def apply_managed_section(
    existing: str,
    section: str,
    *,
    marker: str = DEFAULT_MARKER,
    position: str = "top",
) -> str:
    """Insert (or replace) the soultavern-managed section in ``existing``.

    Args:
        existing: current file content (may be empty if the file
            doesn't exist on disk yet).
        section: the inner content of the managed section (without
            BEGIN/END markers — this function adds them).
        marker: the inner marker string. Defaults to
            ``"soultavern:character"``.
        position: ``"top"`` (default) or ``"bottom"``. Controls where a
            *new* block goes when no markers are present in
            ``existing``. Ignored when an existing block is being
            replaced — in that case the block stays where it was.

    Returns:
        The full file contents with the managed section inserted /
        replaced. Trailing newline normalised to single ``\\n``.
    """
    block = _format_block(marker, section)
    pattern = _block_pattern(marker)

    if pattern.search(existing):
        # Replace in place; preserve content outside the markers.
        replaced = pattern.sub(block + "\n", existing, count=1)
        return _normalise(replaced)

    # No existing block — insert at the chosen position.
    if not existing.strip():
        # File is empty/whitespace-only — managed block is the whole content.
        return _normalise(block)

    if position == "top":
        return _normalise(block + "\n\n" + existing)
    if position == "bottom":
        return _normalise(existing.rstrip() + "\n\n" + block)
    raise ValueError(f"position must be 'top' or 'bottom', got {position!r}")


def strip_managed_section(
    existing: str,
    *,
    marker: str = DEFAULT_MARKER,
) -> str:
    """Remove the soultavern-managed section from ``existing``.

    Returns the file content with the BEGIN..END block (and one
    trailing blank line, if present) removed. If the result is empty
    or whitespace-only, returns the empty string — the caller should
    interpret that as "no file content remains; consider unlinking".
    """
    pattern = _block_pattern(marker)
    stripped = pattern.sub("", existing, count=1)
    # Collapse the gap left behind: any run of 3+ newlines becomes 2.
    stripped = re.sub(r"\n{3,}", "\n\n", stripped)
    if not stripped.strip():
        return ""
    return _normalise(stripped)


def has_managed_section(
    existing: str,
    *,
    marker: str = DEFAULT_MARKER,
) -> bool:
    """True iff a complete BEGIN..END block exists in ``existing``."""
    return _block_pattern(marker).search(existing) is not None


def _format_block(marker: str, section: str) -> str:
    """Render the BEGIN-note-content-END block with consistent
    spacing. Strips surrounding blank lines from ``section`` so the
    block is dense regardless of caller-provided whitespace."""
    body = section.strip("\n")
    return (
        f"{_begin(marker)}\n"
        f"{_MANAGED_NOTE}\n"
        f"\n"
        f"{body}\n"
        f"\n"
        f"{_end(marker)}"
    )


def _normalise(text: str) -> str:
    """Ensure the result ends with exactly one trailing newline and
    has no leading whitespace-only lines."""
    return text.lstrip("\n").rstrip() + "\n"
