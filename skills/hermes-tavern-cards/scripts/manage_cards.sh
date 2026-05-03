#!/usr/bin/env bash
# Skill entry point for hermes-tavern-cards.
#
# Thin dispatcher over hermes-tavern's library subcommands. The first
# argument is the action; remaining arguments pass through. Run
# `hermes-tavern <action> --help` for the full option list of any action.
#
# Examples:
#   ./manage_cards.sh list    --home ~/.hermes-roleplay
#   ./manage_cards.sh current --home ~/.hermes-roleplay
#   ./manage_cards.sh switch  --card alice --home ~/.hermes-roleplay
#   ./manage_cards.sh delete  --card bob   --home ~/.hermes-roleplay
#   ./manage_cards.sh restore --card bob   --home ~/.hermes-roleplay

set -euo pipefail

if ! command -v hermes-tavern >/dev/null 2>&1; then
    echo "manage_cards.sh: hermes-tavern CLI not on PATH." >&2
    echo "manage_cards.sh: install the sibling 'hermes-tavern' skill first" >&2
    echo "manage_cards.sh: — it ships the CLI bootstrap (scripts/install.sh)." >&2
    exit 127
fi

action="${1:-}"
shift || true

case "$action" in
    list|current|switch|delete|restore)
        exec hermes-tavern "$action" "$@"
        ;;
    "")
        echo "manage_cards.sh: missing action" >&2
        echo "Usage: manage_cards.sh {list|current|switch|delete|restore} [args...]" >&2
        exit 2
        ;;
    *)
        echo "manage_cards.sh: unknown action '$action'" >&2
        echo "Usage: manage_cards.sh {list|current|switch|delete|restore} [args...]" >&2
        exit 2
        ;;
esac
