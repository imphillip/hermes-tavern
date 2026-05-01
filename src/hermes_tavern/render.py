"""Render a parsed character card to ``SOUL.md`` and ``HERMES.md``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jinja2 import ChainableUndefined, Environment, PackageLoader, select_autoescape

from .sanitize import sanitize
from .substitute import substitute

SOUL_BUDGET = 19_000
HERMES_BUDGET = 19_000

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


def _quote_block(text: str) -> str:
    """Prefix every line of ``text`` with ``> `` to form a markdown blockquote."""
    if not text:
        return ""
    return "\n".join(("> " + line) if line else ">" for line in text.splitlines())


def _env(char_name: str, user_noun: str) -> Environment:
    env = Environment(
        loader=PackageLoader("hermes_tavern", "templates"),
        autoescape=select_autoescape(disabled_extensions=("j2",), default=False),
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
        undefined=ChainableUndefined,
    )

    def _s(text: object) -> str:
        return sanitize(substitute(text if isinstance(text, str) else "", char_name, user_noun))

    env.filters["s"] = _s
    env.filters["quote"] = _quote_block
    return env


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


def _book_entries(book: dict[str, Any]) -> list[dict[str, Any]]:
    raw = book.get("entries") or []
    if isinstance(raw, dict):
        raw = list(raw.values())
    entries = [_normalize_book_entry(e) for e in raw if isinstance(e, dict)]
    entries = [e for e in entries if e["enabled"]]
    entries.sort(key=lambda e: (e["insertion_order"] is None, e["insertion_order"] or 0))
    return entries


def render(
    data: dict[str, Any],
    *,
    user_noun: str = "the visitor",
    include_hermes_md: bool = True,
    trust_system_prompt: bool = False,
    enforce_budget: bool = True,
) -> RenderResult:
    """Render the parsed card.

    If ``enforce_budget`` is True (default), raise ``BudgetExceededError``
    when SOUL exceeds 19k. apply_card sets this False so the rendered text
    can flow into the distillation pipeline; the budget decision happens
    one layer up.

    ``trust_system_prompt`` controls how ``system_prompt`` and
    ``post_history_instructions`` are placed: when False (default) they are
    rendered inside an explicitly-marked "untrusted author note" blockquote;
    when True they take their high-trust positions (top of file / final
    section) as the V2 spec intends. Default False because card authors are
    third parties and these two fields are the most attractive prompt-injection
    surface.
    """
    name = (data.get("name") or "Unnamed").strip()
    env = _env(name, user_noun)

    metadata = {k: data.get(k) for k in _METADATA_KEYS if data.get(k)}
    soul = env.get_template("SOUL.md.j2").render(
        data=data,
        metadata=metadata or None,
        user_noun=user_noun,
        trust_system_prompt=trust_system_prompt,
    )
    soul = _collapse_blank_lines(soul)
    if enforce_budget and len(soul) > SOUL_BUDGET:
        raise BudgetExceededError("SOUL.md", len(soul), SOUL_BUDGET)

    hermes_text: str | None = None
    truncated = 0
    book = data.get("character_book") if include_hermes_md else None
    if isinstance(book, dict):
        entries = _book_entries(book)
        hermes_text, truncated = _render_hermes(env, book, entries, name)
    return RenderResult(soul=soul, hermes=hermes_text, truncated_entries=truncated)


def _render_hermes(
    env: Environment,
    book: dict[str, Any],
    entries: list[dict[str, Any]],
    char_name: str,
) -> tuple[str, int]:
    template = env.get_template("HERMES.md.j2")
    text = _collapse_blank_lines(
        template.render(book=book, entries=entries, char_name=char_name)
    )
    truncated = 0
    while len(text) > HERMES_BUDGET and entries:
        entries = entries[:-1]
        truncated += 1
        text = _collapse_blank_lines(
            template.render(book=book, entries=entries, char_name=char_name)
        )
    return text, truncated


def _collapse_blank_lines(text: str) -> str:
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
