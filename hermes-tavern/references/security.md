# Security model

SillyTavern character cards are **third-party content**. A card can come
from `chub.ai`, a forum download, or a friend who got it from somewhere
they don't remember. Treat them the way you'd treat a random `.docx`
attachment: probably fine, occasionally weaponised.

HermesTavern's threat model focuses on the *card-to-prompt* boundary.
Three defence layers run on every import / switch / validate. None of
them stops a determined attacker; together they make the most common
prompt-injection patterns visible and reduce the attack surface that
naive operators trip over.

## Layer 1 — visible trust boundary

`SOUL.md` and `HERMES.md` open with a banner block telling the model
that everything below it is third-party persona content, not operator
instruction. The trailing model-notes section reinforces operator >
persona priority.

The two highest-risk V2 fields (`system_prompt` and
`post_history_instructions`) are **demoted by default** into clearly
labelled `## Author's framing (untrusted ...)` and `## Author's closing
note (untrusted ...)` sections, with their bodies wrapped in `>` block
quotes. This breaks the prompt-injection technique where a card author
puts operator-style instructions in `system_prompt` so they get rendered
in the highest-trust slot of the file.

To restore the V2-spec high-trust positions for these fields, pass
`--trust-system-prompt`. Use it only for cards from authors you trust
yourself — never as a blanket override.

## Layer 2 — parse-time hygiene

Every card text field is passed through `sanitize()` before being
written to disk:

- All Unicode `Cc` (control) and `Cf` (format) categories are stripped,
  except for `\t` and `\n`. This removes:
  - U+200B–U+200D zero-width space / non-joiner / joiner
  - U+200E, U+200F LTR / RTL marks
  - U+202A–U+202E embedding / override (incl. RLO, the spoofing classic)
  - U+2060 word joiner
  - U+2066–U+2069 directional isolates
  - U+FEFF zero-width no-break space (BOM)
  - All other C0 / C1 control codes

YAML cards are loaded with `yaml.safe_load`; PNG cards extract only the
`chara` tEXt chunk. There is no execution path for embedded code in any
supported format.

## Layer 3 — red-flag pattern scan

`hermes-tavern validate` and every `import` / `switch` run `scan_card()`
over the parsed payload and report any matches to stderr (or to stdout
in the `validate` listing). Findings are tagged by category:

| Category | What it flags |
|---|---|
| `override-instruction` | "ignore previous instructions", "disregard everything", … |
| `role-override` | "you are now …", "pretend you are …", "act as if you were …" |
| `jailbreak` | "developer mode", "DAN", "do anything now", "god mode" |
| `fake-structural-marker` | `<\|im_start\|>`, `<\|system\|>`, `<tool_call>`, `<function_call>`, … |
| `fake-role-marker` | line-leading `system:` / `developer:` / `operator:` |
| `external-network` | `curl https://`, `wget https://`, `fetch https://` |
| `templated-url` | `https://...?key=${VAR}` style exfil patterns |
| `code-execution` | `eval(`, `os.system(`, `subprocess(`, `child_process(` |
| `encoded-payload-hint` | mentions of `base64 decode` / `base64 encoded` |
| `long-unbroken-token` | runs of ≥ 200 non-whitespace chars (suspicious encoded blob) |

The scan **never blocks** import. False positives are expected — a card
about a hacker character will legitimately mention `curl`. The scan is a
smoke detector: it tells the operator what's in the card so they can
decide whether to keep it.

## What this does not protect against

- **Determined prompt injection** against a weak model. Layer 1 reduces
  but does not eliminate the attack surface; ultimately the model
  decides whether to comply.
- **Tool / channel abuse.** If the model is convinced to call a
  destructive tool, the damage happens at the Hermes side. Configure
  `platform_toolsets` allowlists, rate limits, and channel-level safety
  on Hermes — that is the real perimeter. HermesTavern is explicitly
  out of scope for runtime defence.
- **Card metadata exfiltration.** Cards can carry arbitrary
  `extensions` blobs. We preserve them as HTML comments so they don't
  enter the prompt; they are visible in the rendered file if you grep
  for them.
- **Novel injection techniques** invented after this scan was written.
  The pattern list is small and conservative on purpose; expect to
  revise it.

## Operator workflow recommendations

1. Run `hermes-tavern validate --card <card>` on any new download
   *before* importing.
2. If the scan output looks clean and the card author is unknown, do a
   `--dry-run` import to read the rendered SOUL.md before writing.
3. If you intend to use `--trust-system-prompt`, re-read those two
   fields in the source card and confirm they look like author notes,
   not operator directives.
4. Configure your Hermes channel-level safety (`platform_toolsets`,
   allowlists) independently. HermesTavern does not, will not, and
   should not touch that.
