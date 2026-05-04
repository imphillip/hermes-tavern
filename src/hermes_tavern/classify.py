"""V2 semantic classification: redistribute character content into V2-aligned
categories.

When a card is large enough to trigger distillation, HermesTavern asks the
configured LLM to re-categorize the source material into eight fixed
buckets that map to how a long-context model uses persona reference. The
result drives both:

- the per-category ``extended/<category>.md`` files (full original
  content, kept on disk for runtime retrieval)
- the curated SOUL.md (a small subset of categories — identity,
  personality, roleplay_guides — included always-on)

Two design constraints, both per the project's "actor / script /
director" model:

1. **Faithful to source.** The classification prompt forbids
   paraphrasing; the LLM is asked to redistribute the original wording,
   not rewrite it.
2. **Tolerance probe.** If the LLM refuses or sanitizes the content
   during classification, that signal is observable here (empty / short
   categories) — and the project accepts the LLM's choice rather than
   trying to bypass it. Out-of-the-box it doubles as an early signal
   that the configured model isn't a good fit for this card.

Module owns: prompt construction, the subprocess call, and response
parsing. Filesystem layout and SOUL.md curation live in ``extended.py``
and ``library.py`` respectively.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Any

from .distill import (
    DEFAULT_DISTILL_CMD,
    DEFAULT_TIMEOUT_SECONDS,
    DistillationError,
)

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
    """Result of a classification call.

    ``categories`` always contains all 8 keys; values are empty strings
    for categories with no relevant source content (or where the LLM
    declined / produced nothing for that bucket — which is itself an
    observable signal of model fit).
    """

    categories: dict[str, str] = field(default_factory=dict)
    raw_response: str = ""

    def non_empty(self) -> dict[str, str]:
        return {k: v for k, v in self.categories.items() if v.strip()}


def classify(
    data: dict[str, Any],
    *,
    char_name: str,
    command: str = DEFAULT_DISTILL_CMD,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    runner: object | None = None,
) -> Classification:
    """Call the configured LLM to redistribute card content into
    categories. ``runner`` is an injection seam for tests; pass a callable
    ``(argv) -> CompletedProcess`` to bypass the real subprocess."""
    prompt = build_classification_prompt(data, char_name=char_name)
    argv = shlex.split(command)
    if not argv:
        raise DistillationError("classification command cannot be empty")

    if runner is None:
        try:
            proc = subprocess.run(
                argv + [prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise DistillationError(
                f"classification command {argv[0]!r} not found on PATH; "
                f"install hermes-agent or pass --no-distill"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise DistillationError(
                f"classification command timed out after {timeout}s"
            ) from exc
    else:
        proc = runner(argv + [prompt])  # type: ignore[operator]

    if proc.returncode != 0:
        stderr_tail = (proc.stderr or "").strip().splitlines()[-5:]
        raise DistillationError(
            f"classification command exited {proc.returncode}: "
            + (" / ".join(stderr_tail) or "(no stderr)")
        )

    return parse_classification_response(proc.stdout)


def _detect_subheaders(text: str, *, min_count: int = 3) -> list[tuple[str, str]] | None:
    """Detect ``Header: value`` subheaders in ``text``.

    Common pattern in description-stuffed cards (e.g. Veranna):
    `Full Name: ...`, `Age: ...`, `Appearance: ...`. Returns
    ``[(header, body), ...]`` if at least ``min_count`` subheaders are
    found at column 0; otherwise None.

    A subheader is:
    - At column 0 (no leading whitespace)
    - 1-5 title-cased words ending with a colon
    - Followed by at least one space and non-whitespace content on the
      same line

    This is a deterministic preprocessor — when it succeeds, the LLM
    sees a structurally-flagged input and produces cleaner classification.
    When it fails, the LLM gets the raw text and figures it out.
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


def _format_source_for_prompt(data: dict[str, Any]) -> str:
    """Stringify the relevant card fields for the LLM, applying
    subheader-detection on description for cleaner LLM input."""
    sections: list[str] = []

    description = data.get("description") or ""
    if isinstance(description, str) and description.strip():
        subheaders = _detect_subheaders(description)
        if subheaders:
            sections.append("=== description (already structured by subheaders) ===")
            for header, body in subheaders:
                sections.append(f"### {header}\n{body}")
        else:
            sections.append("=== description ===")
            sections.append(description)

    for field_name in ("personality", "scenario", "first_mes", "mes_example",
                       "system_prompt", "post_history_instructions"):
        value = data.get(field_name)
        if isinstance(value, str) and value.strip():
            sections.append(f"=== {field_name} ===")
            sections.append(value)

    greetings = data.get("alternate_greetings") or []
    if isinstance(greetings, list):
        for i, greeting in enumerate(greetings, start=1):
            if isinstance(greeting, str) and greeting.strip():
                sections.append(f"=== alternate_greeting #{i} ===")
                sections.append(greeting)

    return "\n\n".join(sections)


def build_classification_prompt(data: dict[str, Any], *, char_name: str) -> str:
    source = _format_source_for_prompt(data)
    cats_block = "\n".join(
        f"- **{cat}**: {CATEGORY_DESCRIPTIONS[cat]}" for cat in CATEGORIES
    )
    xml_template = "\n".join(
        f"<{cat}>\n...source content for {cat}, or empty if none...\n</{cat}>"
        for cat in CATEGORIES
    )
    return f"""You are organizing a SillyTavern character card for a Hermes
agent. Read the source material below and **redistribute it** into the
eight standard categories listed.

This is editorial work, not creative writing.

Hard rules:

- **Preserve the source's wording.** Move sentences and paragraphs from
  the source into the right category as-is. Do not paraphrase, do not
  rewrite for tone, do not invent new framing.
- **Do not narrate in italics or novelistic prose.** No `*she leaned
  closer*`, no purple description. The source provides the voice.
- **One category may have content from multiple source fields.**
  Example: appearance details often live inside the description field
  but belong in the `appearance` bucket.
- **Empty categories are fine.** If the source has nothing for a
  category (e.g. no kinks mentioned), output an empty section. Do not
  invent content to fill it.
- **No need to shorten** — these go into per-category files on disk,
  not into a budget-constrained prompt slot. Only drop content that is
  truly redundant (the same trait repeated three times, etc.).

Categories:

{cats_block}

Reply with **exactly** the following XML structure and nothing else.
All eight tags must appear; use empty content for categories with no
source material:

{xml_template}

Character name: {char_name}

Source material:
<source>
{source}
</source>
"""


def _block(name: str, text: str) -> str | None:
    pattern = re.compile(rf"<{name}>(.*?)</{name}>", re.DOTALL | re.IGNORECASE)
    m = pattern.search(text)
    if not m:
        return None
    return m.group(1).strip()


def parse_classification_response(text: str) -> Classification:
    """Extract per-category content from the LLM response.

    Missing categories silently become empty strings (the LLM either
    decided there was nothing to put there, or chose not to engage with
    that category — both are observable signals via Classification.non_empty()).
    """
    categories: dict[str, str] = {}
    for cat in CATEGORIES:
        body = _block(cat, text)
        categories[cat] = body if body else ""
    return Classification(categories=categories, raw_response=text)
