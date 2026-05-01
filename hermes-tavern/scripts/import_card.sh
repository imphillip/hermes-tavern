#!/usr/bin/env bash
# Skill entry point for hermes-tavern.
#
# Thin wrapper around `hermes-tavern import` so Hermes can invoke the skill
# uniformly without knowing the underlying CLI shape. All flags and arguments
# pass through unchanged. Run `hermes-tavern import --help` for the full
# option list.
#
# Examples:
#   ./import_card.sh --card aldous.png --home ~/.hermes-roleplay
#   ./import_card.sh --card huge.png --home ~/.hermes-roleplay --no-distill

set -euo pipefail

if ! command -v hermes-tavern >/dev/null 2>&1; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo "import_card.sh: hermes-tavern CLI not on PATH." >&2
    echo "import_card.sh: run the bundled installer once to set it up:" >&2
    echo "    bash $SCRIPT_DIR/install.sh" >&2
    echo "import_card.sh: (the installer tries pipx → uv tool → dedicated venv.)" >&2
    exit 127
fi

exec hermes-tavern import "$@"
