# SillyTavern V2 character card cheat sheet

Quick reference for the fields HermesTavern reads. Authoritative spec is
at <https://github.com/malfoyslastname/character-card-spec-v2>.

## Container shapes

A card on disk can be one of:

- **JSON V2 (preferred)** — `{ "spec": "chara_card_v2", "spec_version": "2.0", "data": { ... } }`
- **JSON V1 (legacy)** — flat object with `name`, `description`, `personality`, …
  HermesTavern lifts this into the V2 shape transparently.
- **PNG** — a regular PNG with a tEXt chunk under key `chara`. The value
  is base64-encoded JSON (V1 or V2).
- **YAML** — same content as JSON, less common.

## Fields under `data`

| Field | Purpose | Notes |
|---|---|---|
| `name` | Character name. | Replaces every `{{char}}` / `<BOT>`. |
| `description` | Who the character is. | Long free text. |
| `personality` | Behavioural traits. | Long free text. |
| `scenario` | Opening situation. | Long free text. |
| `first_mes` | Default opening message. | Single message. |
| `alternate_greetings[]` | Other openings. | Optional list. |
| `mes_example` | Example dialogue lines. | Often uses `<START>` markers. |
| `system_prompt` | Highest-priority system text. | Replaces ST default if present. |
| `post_history_instructions` | Instructions appended after history. | We render at end of SOUL.md. |
| `tags[]` | Free tags. | Stored only as comments. |
| `creator`, `creator_notes`, `creator_version` | Authoring metadata. | Comments only. |
| `extensions` | Vendor-specific blob. | Preserved as comment, not parsed. |
| `character_book` | Lorebook (see below). | Becomes HERMES.md if present. |

## `character_book`

| Field | Purpose |
|---|---|
| `name` | Lorebook title. |
| `description` | Lorebook overview. |
| `entries[]` | Knowledge fragments. |

Each entry can have:

- `keys[]` — keywords ST uses to gate injection; HermesTavern ignores
  gating but preserves the keys as a comment
- `content` — the entry body (rendered as the section content)
- `comment` — author label (preferred for the section heading)
- `constant` — bool; treated as informational only
- `priority`, `insertion_order` — only `insertion_order` affects rendering
  (entries are sorted ascending)
- `enabled` — `false` skips the entry entirely
- `extensions` — preserved as comment, not parsed

## Placeholders

These appear all over the text fields:

| Token | Means |
|---|---|
| `{{char}}` | The character itself |
| `{{user}}` | The user talking to the character |
| `<BOT>` | Legacy form of `{{char}}` |
| `<USER>` | Legacy form of `{{user}}` |

HermesTavern substitutes all four (case-insensitive, non-recursive).
`{{user}}` becomes whatever was passed to `--user-noun` (default
`"the visitor"`).

## What HermesTavern does NOT support

- Keyword-gated lorebook injection — the lorebook is rendered as one
  always-on document
- Group chats / multiple characters in one card
- The wider `extensions` ecosystem (Stable Diffusion expressions, regex
  scripts, world info recursion, etc.)
- Variable substitution beyond the four tokens above
