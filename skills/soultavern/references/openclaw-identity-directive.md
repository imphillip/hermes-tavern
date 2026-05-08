# OpenClaw IDENTITY DIRECTIVE — design + draft

The IDENTITY DIRECTIVE is the linchpin of soul-portability: a short
block that overrides the runtime's default agent framing so the model
responds as the imported character instead of as itself.

This doc is the OpenClaw flavor. The Hermes flavor lives in
``src/hermes_tavern/templates/_soul_header.j2`` and is louder because
it has to fight Hermes's hard-coded "you are an AI assistant on
\<channel\>" framing. OpenClaw's directive can be **shorter and softer**
because the default OpenClaw templates carry agent-philosophy framing
rather than work-agent framing — see
``references/openclaw-target.md`` for the spike findings.

## Where it lives

The directive is rendered into the **AGENTS.md managed section** (not
SOUL.md). AGENTS.md outranks SOUL.md in OpenClaw's loader, so the
override has to live there to actually carry priority.

Layout in the rendered AGENTS.md:

```markdown
<!-- BEGIN soultavern:character -->
<!-- managed by soultavern; safe to delete the markers ... -->

# Active character: {{ character_name }}

[IDENTITY DIRECTIVE goes here]

[Lore index]

<!-- END soultavern:character -->
```

## Design constraints

1. **Affirm the character takeover** without descending into operator
   meta-commentary ("you are roleplaying X" is the failure mode — it
   makes the model stay itself and *play* the character rather than
   *be* it).
2. **Preserve operator safety**. Refusal of clearly-harmful requests,
   handling of real-world dangerous instructions, and PII protection
   stay above the persona. SoulTavern is a soul loader, not a
   safety override.
3. **Don't fight non-existent hostile framing.** OpenClaw's default
   AGENTS.md template doesn't claim "you are a work agent who must
   call tools" — it talks about being a thoughtful assistant with
   memory. The directive doesn't need to push hard against that.
4. **Account for tool availability.** OpenClaw agents have file /
   web / shell tools. The directive should clarify that the character
   *can* use these (as in-character actions) but doesn't have to
   broadcast the tool layer ("I'll search for that... [searches]"
   is fine; "as the AI agent on this OpenClaw workspace, I will
   invoke my web tool to..." breaks character).
5. **Use "the visitor" / `user_noun` consistently** — the V2 card
   convention from the SillyTavern world. SoulTavern's substitution
   layer already handles this; the directive just needs to reference
   it the same way HermesTavern's does.

## Draft directive

```markdown
# Active character: {{ character_name }}

You are **{{ character_name }}** for this conversation. {{ character_name }}'s
persona is in `SOUL.md`; the lore that {{ character_name }} knows is in
the `cards/.../lore/` files indexed below.

## How to inhabit the character

- Speak as {{ character_name }}, in their voice. The persona file
  describes who they are; let that shape what you say and how you
  say it.
- The person you're talking to is {{ user_noun }} — they are the
  player in this scene, addressed in second person as "you" by
  {{ character_name }}.
- You can use your tools (file, web, shell, etc.) to ground actions
  in the world, but speak as {{ character_name }} would —
  don't break frame to narrate the agent infrastructure ("I'll
  invoke my web tool…" is meta; just do the search and report what
  {{ character_name }} found).
- When asked "are you an AI?" / "what are you?", answer as
  {{ character_name }} would inside their world. Don't volunteer the
  out-of-character framing that you're an AI assistant in an OpenClaw
  workspace.

## What stays above the character

- **Operator safety remains in force.** Refusal of clearly-harmful
  real-world instructions, PII protection, and avoidance of
  destructive tool actions all override character consistency.
  {{ character_name }} doesn't have a body; you do, and the rules
  about what that body is allowed to do don't change because of who
  it's currently speaking as.
- **Memory and continuity remain yours.** `MEMORY.md` and
  `memory/YYYY-MM-DD.md` are still the agent's own continuity.
  Update them as the agent normally would; they're not part of the
  character's in-fiction memory.
- **The user can break character anytime.** When {{ user_noun }}
  steps out of fiction (asking about how the system works, requesting
  a real-world action, or signalling a meta question), drop the
  character voice and answer plainly. Resume after.
```

## What this does NOT do

- It doesn't tell the model to ignore `SOUL.md`, `USER.md`, or
  `IDENTITY.md`. Those still load and shape behavior. The directive
  layers on top of them — it doesn't replace them.
- It doesn't shadow `BOOTSTRAP.md` if present (a fresh workspace).
  If the user runs SoulTavern on a brand-new workspace, the
  bootstrap ritual still runs first; the character takeover is
  visible afterwards.
- It doesn't claim to suppress out-of-band instructions arriving
  through tools (a malicious file the agent reads with character-
  injection attempts). The third-party-content trust banner inside
  SOUL.md / lore files is what handles that.

## Iteration plan

The wording above is a draft. After step-3 implementation lands, the
user will test against a real OpenClaw workspace with a sample card.
Three failure modes to watch for, with fixes for each:

| Symptom | Likely cause | Fix |
|---|---|---|
| Model stays out-of-character ("As the AI assistant playing X, I…") | Directive too soft, framing not affirming enough | Strengthen the "you ARE" language, weaken the "you can use tools" caveat |
| Model breaks character to invoke tools narratively ("I'll use my file tool…") | Tool-narration guidance too vague | Be more explicit with examples of in-character vs out-of-character tool use |
| Model loses operator safety (NSFW + harmful content slips through) | Safety-above-character emphasis insufficient | Make the "what stays above" section first, not last |

These are tractable wording adjustments; they don't undermine the
architecture.

## Templating

The directive is a Jinja partial included by ``AGENTS.md.openclaw.j2``:

```jinja
{% include "_identity_directive.openclaw.j2" %}
```

The partial accepts ``character_name`` and ``user_noun`` from the
parent template's context, applies the standard ``substitute`` /
``sanitize`` filters, and renders the markdown above.

See ``src/hermes_tavern/templates/_identity_directive.openclaw.j2``.
