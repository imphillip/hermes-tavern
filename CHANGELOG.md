# Changelog

## 2.0.0 — Skill-folder only (drop CLI install, drop third-party deps)

v2.0 collapses SoulTavern to a single self-contained skill folder. There
is no `soultavern` binary on PATH any more, no wheel to install, no
`pipx` / `uv tool` / venv shim, no third-party Python dependencies. The
skill is one folder; you invoke it by running scripts in `scripts/`
directly. Drop the folder anywhere your runtime reads skills from and
it works.

### Breaking changes

- **No CLI on PATH.** `soultavern` and the `hermes-tavern` backward-compat
  alias are both gone. Replace `soultavern <subcommand> ...` with
  `python3 <skill_dir>/scripts/<subcommand>.py ...`. Same flags, same
  exit codes, same output.
- **No wheel.** `assets/soultavern-*.whl` removed; `pyproject.toml`
  loses `[project.scripts]` and the build-system block. The project is
  no longer "built" — it's distributed as a skill folder.
- **No install scripts.** `scripts/install.sh`, `scripts/uninstall.sh`,
  and `scripts/import_card.sh` are gone.
- **YAML cards no longer supported.** `.yaml` / `.yml` inputs raise
  `UnsupportedCardError`. JSON and PNG remain. Convert YAML cards to
  JSON if you have any (rare in the SillyTavern ecosystem).
- **Source layout.** `src/soultavern/` moved to
  `skills/soultavern/scripts/soultavern/` (the engine package lives
  beside the entry shims; `lib/` would be non-standard for a skill
  folder). Tests pick this up via `conftest.py`; external code that
  did `pip install -e .` should switch to invoking the scripts.

### Implementation changes

- **Pillow → stdlib.** PNG `chara` chunk parsing reimplemented in pure
  stdlib (`struct` + `zlib`). Supports `tEXt` / `iTXt` / `zTXt`. Test
  fixtures use a stdlib PNG builder in `tests/conftest.py`.
- **Jinja2 → Python functions.** All eight `.j2` templates rewritten
  as Python rendering functions colocated with each `Target` instance
  in `skills/soultavern/scripts/soultavern/targets/{hermes,openclaw}.py`.
  `Target.soul_template` (str) replaced with `Target.soul_renderer`
  (callable); same for companion / curated / extra-file fields.
- **PyYAML → removed.** YAML branch in `parse.py` deleted along with
  the import.
- **Zero runtime dependencies.** `pyproject.toml` `dependencies = []`.
  pyproject is now dev-tooling-only (pytest / ruff / mypy).

### What's the same

- Output bytes for `--target hermes` and `--target openclaw` match v1.0
  for the small-card path. (212 tests still pass; the openclaw e2e suite
  asserts on real output.)
- All flag names, help text, exit codes, error wording.
- All references in `references/` are unchanged.
- `<home>/cards/.active.json` schema unchanged. Existing imported
  workspaces don't need migration.

### Migration

```bash
# Old (v1.0):
soultavern import --card foo.png --home ~/ws --target openclaw

# New (v2.0):
python3 /path/to/SoulTavern/skills/soultavern/scripts/import.py \
    --card foo.png --home ~/ws --target openclaw
```

If you have a v1.0 install with `soultavern` on PATH, remove it (it's
no longer maintained). Then `git pull` (or re-clone) SoulTavern and
point your runtime / agent at the new skill folder.

---

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
