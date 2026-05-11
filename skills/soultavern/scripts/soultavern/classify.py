"""V2-aligned content categories: definitions, dataclass, and the
disk-loading helper used by ``finalize`` after the agent has written
per-category content.

This module is intentionally LLM-call-free. The actual semantic
categorization is done by the agent (with whatever LLM tools it has,
guided by ``soultavern/SKILL.md``); this module only owns:

- the canonical V2 category names + display titles + summaries
- the ``Classification`` dataclass that ``render`` and ``extended``
  consume
- ``_detect_subheaders`` — pure-regex preprocessor used by ``staging``
  to give the agent a structurally-flagged ``source.md``
- ``load_classification_from_extended`` — used by ``finalize`` to read
  the agent's per-category files back into a ``Classification`` for
  template rendering

Earlier versions (≤ v0.4.0) shelled out to ``hermes -q`` here. That
coupled the project to a specific Hermes CLI shape and broke when the
hermes subcommand layout changed; v0.4.5 moved the LLM call into the
agent's own context, where it belongs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# The eight V2-aligned categories. Order is the on-screen order for the
# index in HERMES.md and the iteration order in extended/.
CATEGORIES: tuple[str, ...] = (
    "identity",
    "appearance",
    "personality",
    "backstory",
    "scenario",
    "kinks",
    "roleplay_guides",
    "examples",
)

# Categories included in the always-on curated SOUL.md (the rest stay in
# extended/ and are reached via the HERMES.md index).
SOUL_PICKS: tuple[str, ...] = ("identity", "personality", "roleplay_guides")

CATEGORY_TITLES: dict[str, str] = {
    "identity": "Identity",
    "appearance": "Appearance",
    "personality": "Personality",
    "backstory": "Backstory",
    "scenario": "Scenario",
    "kinks": "Kinks & Preferences",
    "roleplay_guides": "Roleplay Guidelines",
    "examples": "Example Dialogues",
}

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "identity": "name, age, ethnicity, height, basic biographical facts",
    "appearance": "physical description, body, voice, distinctive features",
    "personality": "traits, archetype, mannerisms, speech style, quirks",
    "backstory": "past events, history, relationships, formative context",
    "scenario": "the situation the conversation opens in",
    "kinks": "sexual preferences, fetishes, taboos (if present in source)",
    "roleplay_guides": "explicit instructions about how to portray the character",
    "examples": "sample dialogue or interaction patterns",
}


@dataclass
class Classification:
    """Per-category content for one card.

    ``categories`` always contains all eight keys; values are empty
    strings for categories with no source content (or where the agent
    declined to populate them — both are observable signals via
    ``non_empty()``).
    """

    categories: dict[str, str] = field(default_factory=dict)

    def non_empty(self) -> dict[str, str]:
        return {k: v for k, v in self.categories.items() if v.strip()}


def _detect_subheaders(text: str, *, min_count: int = 3) -> list[tuple[str, str]] | None:
    """Detect ``Header: value`` subheaders in ``text``.

    Common pattern in description-stuffed cards (e.g. Veranna):
    ``Full Name: ...``, ``Age: ...``, ``Appearance: ...``. Returns
    ``[(header, body), ...]`` if at least ``min_count`` subheaders are
    found at column 0; otherwise None.

    A subheader is:
    - At column 0 (no leading whitespace)
    - 1-5 title-cased words ending with a colon
    - Followed by at least one space and non-whitespace content on the
      same line

    Used as a deterministic preprocessor when staging ``source.md`` for
    the agent — pre-flagging structure means the agent gets cleaner
    input and produces cleaner classification.
    """
    pattern = re.compile(
        r"^([A-Z][A-Za-z'\-]{0,30}(?:\s+[A-Za-z'\-/&]{1,30}){0,4}):[ \t]+(.+)$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    if len(matches) < min_count:
        return None
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        header = m.group(1).strip()
        first_line = m.group(2)
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = (first_line + text[body_start:body_end]).rstrip()
        out.append((header, body))
    return out


def _strip_h1(text: str) -> str:
    """Remove the leading ``# Title`` line (if present) and the blank
    line after it. Used when reading agent-written category files: the
    H1 is for human readability on disk; the body is what we care about
    when re-rendering SOUL.md / HERMES.md."""
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def load_classification_from_extended(extended_dir: Path) -> Classification:
    """Read agent-written ``extended/<category>.md`` files into a
    ``Classification`` for ``finalize`` to render from.

    Missing or empty files become empty strings (the LLM-tolerance
    signal: visible by absence in ``Classification.non_empty()``).
    """
    categories: dict[str, str] = {}
    for cat in CATEGORIES:
        path = extended_dir / f"{cat}.md"
        if path.is_file():
            categories[cat] = _strip_h1(path.read_text("utf-8"))
        else:
            categories[cat] = ""
    return Classification(categories=categories)
