# Changelog

## 1.0.0 — SoulTavern (rename + multi-target)

The HermesTavern → SoulTavern rebrand, with multi-target support
landing as the v1.0 milestone. Default `--target hermes` reproduces
v0.5.x behavior unchanged; `--target openclaw` is the new addition.

### Project rename

- Repo: `imphillip/hermes-tavern` → `imphillip/SoulTavern` (GitHub
  301-redirects the old URL).
- Python package: `hermes_tavern` → `soultavern`. PyPI name will be
  `soultavern` when first published.
- CLI binary: `soultavern` (canonical). `hermes-tavern` retained as a
  backward-compat alias entry point — same module, identical behavior.
- Skill name (SKILL.md frontmatter): `hermes-tavern` → `soultavern`.
- Skills bundle filename: `hermes-tavern-skills.zip` →
  `soultavern-skills.zip`.

### Multi-target architecture

- New `--target` flag on `import` / `validate` / `finalize` / `switch`,
  with three registered targets:
  - `hermes` (default, fully implemented) — writes `SOUL.md` + `HERMES.md`
  - `openclaw` (fully implemented in v1.0) — writes `SOUL.md` (replace)
    + `AGENTS.md` (managed-section append; preserves user content
    outside the soultavern markers) + `IDENTITY.md` (replace)
  - `generic` (skeleton, lands later) — single-file fallback
- New `Target` dataclass with `companion_write_mode`,
  `companion_section_marker`, `extra_files`, `implemented` fields.
- New `targets/` module: `base.py` (`Target` + `ExtraFile` dataclasses),
  `hermes.py`, `openclaw.py`, `generic.py`,
  `openclaw_writers.py` (managed-section append/strip helpers).
- `ActiveRecord` gains a `target: str` field (backward-compat default
  `"hermes"` for legacy `.active.json` files).

### OpenClaw target details

- Loader-order spike confirmed: `AGENTS.md` outranks `SOUL.md`, so the
  IDENTITY DIRECTIVE goes in the AGENTS.md managed section.
- Real budget constants from OpenClaw source:
  `DEFAULT_BOOTSTRAP_MAX_CHARS = 12_000` per file,
  `DEFAULT_BOOTSTRAP_TOTAL_MAX_CHARS = 60_000` total.
- Managed-section markers: `<!-- BEGIN soultavern:character -->` …
  `<!-- END soultavern:character -->`. Existing user content in
  AGENTS.md is preserved on import / switch / delete / revert.
- Default OpenClaw templates carry agent-philosophy framing rather
  than work-agent framing; the IDENTITY DIRECTIVE wording can be
  shorter than HermesTavern's. Spike documented in
  `references/openclaw-target.md`; directive draft in
  `references/openclaw-identity-directive.md`.

### Migration from v0.5.x

- The `hermes-tavern` CLI alias keeps existing scripts working
  unchanged. `--target hermes` is the default.
- Hub users: `hermes skills uninstall hermes-tavern && hermes skills
  install soultavern`. Or drop the new `soultavern-skills.zip` to
  Hermes via Telegram — the bundled installer handles the rest.
- `~/.local/share/hermes-tavern-venv` (if present from a v0.5.x
  fallback install) is recognised by the new `uninstall.sh` and
  cleaned up correctly.
- Existing `<HERMES_HOME>/cards/.active.json` files load without
  modification — the new `target` field defaults to `"hermes"`.

### Testing

- 212 tests passing (149 functional regression + 12 OpenClaw e2e + 23
  managed-section unit + others new under v0.6/v1.0).
- New test files: `test_openclaw_writers.py` (managed-section helpers),
  `test_openclaw_templates.py` (Jinja render isolation),
  `test_openclaw_target_e2e.py` (small-card + oversized-card +
  user-content preservation + delete cleanup).

---

## 0.5.1

scripts/uninstall.sh + uninstall docs. See git history.

## 0.5.0

Single-skill consolidation: merged `hermes-tavern-cards` into
`hermes-tavern`. See git history.

## 0.4.5

Agent-driven oversized-card flow (replaced subprocess `hermes -q`
shell-out from v0.4.0). See git history.
