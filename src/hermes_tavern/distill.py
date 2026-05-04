"""LLM-driven distillation for oversized cards.

When the rendered SOUL.md or HERMES.md exceeds 75% of the Hermes 20k slot
budget, HermesTavern shells out to the user's already-configured Hermes
CLI to compress the prompt-loaded portion. The full original content is
written to ``cards/<stem>/extended/`` and indexed from ``AGENTS.md`` so
the model can grep / read it on demand.

This module owns: threshold detection, prompt construction, the
subprocess call, and response parsing. It does **not** know about the
filesystem layout or AGENTS.md index — those live in ``library`` and
``extended``.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass

# 75% of the 20k Hermes slot, rounded down for a one-character margin.
DISTILL_THRESHOLD = 15_000

# What we *ask* the LLM to produce; well below the threshold so the result
# leaves room for the trust banner / headings the templates also emit.
SOUL_TARGET = 12_000
LORE_TARGET = 12_000

DEFAULT_DISTILL_CMD = "hermes -q"
DEFAULT_TIMEOUT_SECONDS = 180


class DistillationError(Exception):
    """Raised when the configured distillation command fails or produces
    output that cannot be parsed."""


@dataclass
class DistillResult:
    soul: str
    lore: str | None
    raw_response: str


def needs_distillation(
    soul: str,
    hermes: str | None,
    *,
    threshold: int = DISTILL_THRESHOLD,
) -> bool:
    """True iff either rendered file exceeds the soft threshold."""
    if len(soul) > threshold:
        return True
    if hermes is not None and len(hermes) > threshold:
        return True
    return False


def distill(
    soul: str,
    hermes: str | None,
    *,
    char_name: str,
    command: str = DEFAULT_DISTILL_CMD,
    soul_target: int = SOUL_TARGET,
    lore_target: int = LORE_TARGET,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    runner: object | None = None,
) -> DistillResult:
    """Compress ``soul`` and ``hermes`` via the configured CLI command.

    ``runner`` is an injection seam for tests; pass a callable
    ``(argv, stdin) -> CompletedProcess`` to bypass real subprocess.
    """
    prompt = build_prompt(
        soul=soul,
        lore=hermes,
        char_name=char_name,
        soul_target=soul_target,
        lore_target=lore_target,
    )
    argv = shlex.split(command)
    if not argv:
        raise DistillationError("--distill-cmd cannot be empty")

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
                f"distillation command {argv[0]!r} not found on PATH; "
                f"install hermes-agent or pass --no-distill"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise DistillationError(
                f"distillation command timed out after {timeout}s"
            ) from exc
    else:
        proc = runner(argv + [prompt])  # type: ignore[operator]

    if proc.returncode != 0:
        stderr_tail = (proc.stderr or "").strip().splitlines()[-5:]
        raise DistillationError(
            f"distillation command exited {proc.returncode}: "
            + (" / ".join(stderr_tail) or "(no stderr)")
        )

    return parse_response(proc.stdout)


def build_prompt(
    *,
    soul: str,
    lore: str | None,
    char_name: str,
    soul_target: int,
    lore_target: int,
) -> str:
    lore_section = lore if lore else "(no lorebook in this card)"
    return f"""You are shrinking a SillyTavern character card down to fit a Hermes
agent's always-on context slot. The two rendered files below exceed
the budget; output trimmed versions that fit, **using the source's
own wording wherever possible**.

This is editorial work, not creative writing.

Hard rules:

- **Preserve the source's wording.** If a sentence already says it,
  reuse the sentence. Do not paraphrase into a "smoother" version,
  do not invent new framing, do not rewrite for tone.
- **Do not narrate in italics or novelistic prose.** No `*she leaned
  closer*`, no purple description, no third-person scene-painting.
  The source provides the voice; you are only choosing what to keep.
- **If the source has labeled fields** (e.g. `Full Name: ...`,
  `Appearance: ...`, `Personality: ...`), preserve those labels and
  the structure they imply. Don't merge labeled fields into one
  paragraph.
- **Cut by removing redundancy, not by reframing.** Drop duplicate
  alternate greetings, repeated descriptions of the same trait,
  encyclopedic world filler. Keep the lines that are actually
  load-bearing for who this character is.
- **The full original is preserved on disk for retrieval.** You are
  not "saving" content by including more of it here — anything you
  cut is still available via the extended/ files indexed in HERMES.md.

Hard limits (after trimming):

- SOUL.md: {soul_target} characters maximum
- HERMES lore: {lore_target} characters maximum (or `NONE` if no
  world content is worth retaining as always-on context)

Reply with **exactly** the following XML structure and nothing else.
Both tags must appear; use `<lore>NONE</lore>` if you keep no lore:

<soul>
...trimmed SOUL.md content here, including the H1 with the character's name...
</soul>
<lore>
...trimmed always-on lore here, or NONE...
</lore>

Character name: {char_name}

Original SOUL.md ({len(soul)} chars):
<original-soul>
{soul}
</original-soul>

Original HERMES.md lore ({len(lore) if lore else 0} chars):
<original-lore>
{lore_section}
</original-lore>
"""


_SOUL_RE = re.compile(r"<soul>(.*?)</soul>", re.DOTALL | re.IGNORECASE)
_LORE_RE = re.compile(r"<lore>(.*?)</lore>", re.DOTALL | re.IGNORECASE)


def parse_response(text: str) -> DistillResult:
    soul_match = _SOUL_RE.search(text)
    if not soul_match:
        raise DistillationError(
            "distillation response did not contain a <soul>...</soul> block"
        )
    soul = soul_match.group(1).strip() + "\n"

    lore_match = _LORE_RE.search(text)
    lore: str | None
    if not lore_match:
        lore = None
    else:
        body = lore_match.group(1).strip()
        if not body or body.upper() == "NONE":
            lore = None
        else:
            lore = body + "\n"

    return DistillResult(soul=soul, lore=lore, raw_response=text)
