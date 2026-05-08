#!/usr/bin/env bash
# Skill entry point for soultavern.
#
# Thin wrapper around `soultavern import` so Hermes can invoke the skill
# uniformly without knowing the underlying CLI shape. All flags and arguments
# pass through unchanged. Run `soultavern import --help` for the full
# option list.
#
# Examples:
#   ./import_card.sh --card aldous.png --home ~/.hermes-roleplay
#   ./import_card.sh --card aldous.png --home ~/.hermes-roleplay --trust-system-prompt
#   ./import_card.sh --card aldous.png --home ~/.openclaw/workspace --target openclaw
#
# Oversized cards exit with code 2 and stage source.md for the agent;
# the agent then writes extended/<category>.md files and the user runs
#   soultavern finalize --card <name> --home <home>
# to assemble SOUL.md and the companion file. See SKILL.md
# "Oversized card procedure".

set -euo pipefail

# Prefer the canonical `soultavern` binary; fall back to the legacy
# `hermes-tavern` alias if installed (pre-v1.0).
if command -v soultavern >/dev/null 2>&1; then
    exec soultavern import "$@"
elif command -v hermes-tavern >/dev/null 2>&1; then
    exec hermes-tavern import "$@"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "import_card.sh: soultavern CLI not on PATH." >&2
echo "import_card.sh: run the bundled installer once to set it up:" >&2
echo "    bash $SCRIPT_DIR/install.sh" >&2
echo "import_card.sh: (the installer tries pipx → uv tool → dedicated venv.)" >&2
exit 127
