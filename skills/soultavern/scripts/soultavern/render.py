"""Render a parsed character card to ``SOUL.md`` and companion files.

v2.0: pure stdlib — no jinja2. Each target's render functions live
beside its ``Target`` instance in ``targets/<runtime>.py``; this module
holds shared helpers, the orchestration entry points, and the budget /
oversized-card logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .targets import DEFAULT_TARGET, Target
from .text import (
    collapse_blank_lines,
    make_s,
    quote_block,
    render_alternate_greetings,
    render_first_mes_block,
    render_metadata_comment,
)

# Backwards-compatible aliases — internal code paths now consult a Target
# object, but tests and external callers may still import these directly.
SOUL_BUDGET = DEFAULT_TARGET.soul_budget
HERMES_BUDGET = DEFAULT_TARGET.companion_budget

# Re-export helpers for any external callers that historically imported
# them from this module.
__all__ = [
    "BudgetExceededError",
    "HERMES_BUDGET",
    "RenderResult",
    "SOUL_BUDGET",
    "collapse_blank_lines",
    "make_s",
    "quote_block",
    "render",
    "render_alternate_greetings",
    "render_curated_soul",
    "render_extra_file",
    "render_first_mes_block",
    "render_managed_companion",
    "render_metadata_comment",
]

_METADATA_KEYS = ("creator", "creator_version", "creator_notes", "tags", "extensions")


class BudgetExceededError(Exception):
    def __init__(self, kind: str, size: int, limit: int) -> None:
        super().__init__(f"{kind} would be {size} chars; limit is {limit}.")
        self.kind = kind
        self.size = size
        self.limit = limit


@dataclass
class RenderResult:
    soul: str
    hermes: str | None
    truncated_entries: int = 0


# ---------------------------------------------------------------------------
# Public orchestration entry points
# ---------------------------------------------------------------------------


def _book_entries(book: dict[str, Any]) -> list[dict[str, Any]]:
    raw = book.get("entries") or []
    if isinstance(raw, dict):
        raw = list(raw.values())
    entries = [_normalize_book_entry(e) for e in raw if isinstance(e, dict)]
    entries = [e for e in entries if e["enabled"]]
    entries.sort(key=lambda e: (e["insertion_order"] is None, e["insertion_order"] or 0))
    return entries


def _normalize_book_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "comment": entry.get("comment") or "",
        "keys": entry.get("keys") or entry.get("key") or [],
        "content": entry.get("content") or "",
        "constant": entry.get("constant"),
        "priority": entry.get("priority"),
        "insertion_order": entry.get("insertion_order"),
        "enabled": entry.get("enabled", True),
        "extensions": entry.get("extensions"),
    }


def render(
    data: dict[str, Any],
    *,
    user_noun: str = "the visitor",
    include_hermes_md: bool = True,
    trust_system_prompt: bool = False,
    enforce_budget: bool = True,
    target: Target = DEFAULT_TARGET,
) -> RenderResult:
    """Render the parsed card.

    If ``enforce_budget`` is True (default), raise ``BudgetExceededError``
    when SOUL exceeds the target's soul_budget. apply_card sets this
    False so the rendered text can flow into the oversized-card pipeline;
    the budget decision happens one layer up.

    ``trust_system_prompt`` controls how ``system_prompt`` and
    ``post_history_instructions`` are placed: when False (default) they are
    rendered inside an explicitly-marked "untrusted author note" blockquote;
    when True they take their high-trust positions (top of file / final
    section) as the V2 spec intends. Default False because card authors are
    third parties and these two fields are the most attractive prompt-injection
    surface.
    """
    name = (data.get("name") or "Unnamed").strip()
    metadata = {k: data.get(k) for k in _METADATA_KEYS if data.get(k)}

    soul = target.soul_renderer(
        data=data,
        metadata=metadata or None,
        user_noun=user_noun,
        trust_system_prompt=trust_system_prompt,
    )
    soul = collapse_blank_lines(soul)
    if enforce_budget and len(soul) > target.soul_budget:
        raise BudgetExceededError(target.soul_filename, len(soul), target.soul_budget)

    hermes_text: str | None = None
    truncated = 0
    # Managed-section targets (OpenClaw) render their companion file via
    # render_managed_companion — its inputs differ (extended_files, not
    # book/entries), and the file is written via apply_managed_section
    # rather than full overwrite. Skip companion rendering here for those
    # targets.
    if target.companion_write_mode == "replace":
        book = data.get("character_book") if include_hermes_md else None
        if isinstance(book, dict):
            entries = _book_entries(book)
            hermes_text, truncated = _render_replace_companion(book, entries, name, target=target)
    return RenderResult(soul=soul, hermes=hermes_text, truncated_entries=truncated)


def render_managed_companion(
    char_name: str,
    user_noun: str,
    extended_files: list,
    *,
    target: Target,
) -> str:
    """Render the inner content of a managed-section companion file
    (e.g. OpenClaw's AGENTS.md). Returns just the inside content; the
    caller wraps it with markers via ``apply_managed_section``.

    Only applicable when ``target.companion_write_mode ==
    "managed-section"``.
    """
    if target.companion_write_mode != "managed-section":
        raise ValueError(
            f"render_managed_companion only applies to managed-section "
            f"targets; got {target.name!r} with mode "
            f"{target.companion_write_mode!r}",
        )
    text = target.companion_renderer(
        char_name=char_name,
        user_noun=user_noun,
        extended_files=extended_files,
    )
    return collapse_blank_lines(text)


def render_extra_file(
    extra_file,
    data: dict[str, Any],
    *,
    char_name: str,
    user_noun: str,
    avatar_path: str = "",
) -> str:
    """Render one of the target's extra files (e.g. OpenClaw's
    IDENTITY.md). Returns the full file content."""
    text = extra_file.renderer(
        data=data,
        char_name=char_name,
        user_noun=user_noun,
        avatar_path=avatar_path,
    )
    return collapse_blank_lines(text)


def render_curated_soul(
    char_name: str,
    classification: "Classification",
    *,
    user_noun: str = "the visitor",
    enforce_budget: bool = True,
    target: Target = DEFAULT_TARGET,
) -> str:
    """Render the curated SOUL.md from a Classification result.

    Used in the oversized-card flow: the always-on persona file is built
    from a small subset of categories (identity + personality +
    roleplay_guides). Other categories live in extended/ and are reached
    via the companion-file index.

    Raises ``BudgetExceededError`` (when ``enforce_budget``) if the
    rendered curated SOUL exceeds the target's soul_budget — caller can
    fall back to a follow-up compression call in that case.
    """
    from .classify import SOUL_PICKS  # local import to avoid module-cycle at top
    picks = {cat: classification.categories.get(cat, "") for cat in SOUL_PICKS}
    soul = target.curated_soul_renderer(
        data={"name": char_name},
        user_noun=user_noun,
        picks=picks,
    )
    soul = collapse_blank_lines(soul)
    if enforce_budget and len(soul) > target.soul_budget:
        raise BudgetExceededError(
            f"curated {target.soul_filename}", len(soul), target.soul_budget,
        )
    return soul


# Forward declaration so the Classification type hint above resolves
# without forcing an import-time cycle (extended imports from classify;
# render imports from neither at module top).
if False:  # pragma: no cover
    from .classify import Classification  # noqa: F401


def _render_replace_companion(
    book: dict[str, Any],
    entries: list[dict[str, Any]],
    char_name: str,
    *,
    target: Target,
) -> tuple[str, int]:
    """Render the companion file with iterative truncation if oversize."""
    text = collapse_blank_lines(
        target.companion_renderer(book=book, entries=entries, char_name=char_name)
    )
    truncated = 0
    while len(text) > target.companion_budget and entries:
        entries = entries[:-1]
        truncated += 1
        text = collapse_blank_lines(
            target.companion_renderer(book=book, entries=entries, char_name=char_name)
        )
    return text, truncated
