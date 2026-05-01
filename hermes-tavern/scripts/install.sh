#!/usr/bin/env bash
# One-time installer for the hermes-tavern CLI.
#
# The CLI is shipped as a wheel inside this skill's assets/ (because the
# package is not yet published to PyPI). This script tries the installation
# methods most likely to be on the host, in order of preference:
#
#   1. pipx       — cleanest for CLI tools, isolates dependencies
#   2. uv tool    — modern alternative
#   3. dedicated venv at $HOME/.local/share/hermes-tavern-venv with a shim in
#                  $HOME/.local/bin (the shim dir must be on PATH)
#
# Override paths via env vars:
#   HERMES_TAVERN_VENV — venv location (default ~/.local/share/hermes-tavern-venv)
#   HERMES_TAVERN_BIN  — shim directory (default ~/.local/bin)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

shopt -s nullglob
wheels=( "$SKILL_DIR"/assets/hermes_tavern-*.whl )
shopt -u nullglob

if [ ${#wheels[@]} -eq 0 ]; then
    echo "install.sh: no wheel found in $SKILL_DIR/assets/" >&2
    echo "install.sh: this skill is missing its bundled hermes_tavern-*.whl —" >&2
    echo "install.sh: please re-download or re-package the skill." >&2
    exit 1
fi
WHEEL="${wheels[0]}"
echo "install.sh: bundled wheel: $WHEEL"

if command -v hermes-tavern >/dev/null 2>&1; then
    echo "install.sh: hermes-tavern is already on PATH:"
    echo "  $(command -v hermes-tavern)"
    echo "  $(hermes-tavern --version 2>&1 || true)"
    echo "install.sh: nothing to do."
    echo "install.sh: (uninstall the existing install first if you want to reinstall.)"
    exit 0
fi

if command -v pipx >/dev/null 2>&1; then
    echo "install.sh: installing via pipx"
    pipx install "$WHEEL"
    echo "install.sh: done — try 'hermes-tavern --version'"
    exit 0
fi

if command -v uv >/dev/null 2>&1; then
    echo "install.sh: installing via uv tool"
    uv tool install "$WHEEL"
    echo "install.sh: done — try 'hermes-tavern --version'"
    exit 0
fi

# Fallback: dedicated venv + shim
VENV_DIR="${HERMES_TAVERN_VENV:-$HOME/.local/share/hermes-tavern-venv}"
SHIM_DIR="${HERMES_TAVERN_BIN:-$HOME/.local/bin}"

echo "install.sh: pipx and uv not found; falling back to a dedicated venv"
echo "install.sh:   venv: $VENV_DIR"
echo "install.sh:   shim: $SHIM_DIR/hermes-tavern"

if ! command -v python3 >/dev/null 2>&1; then
    echo "install.sh: python3 not found on PATH; cannot continue." >&2
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null 2>&1 || true
"$VENV_DIR/bin/pip" install --quiet "$WHEEL"

mkdir -p "$SHIM_DIR"
ln -sf "$VENV_DIR/bin/hermes-tavern" "$SHIM_DIR/hermes-tavern"

echo "install.sh: installed; linked $SHIM_DIR/hermes-tavern"
case ":$PATH:" in
    *":$SHIM_DIR:"*)
        echo "install.sh: $SHIM_DIR is already on PATH — try 'hermes-tavern --version'"
        ;;
    *)
        echo "install.sh: WARNING — $SHIM_DIR is NOT on PATH."
        echo "install.sh: add this to your shell rc:"
        echo "    export PATH=\"$SHIM_DIR:\$PATH\""
        ;;
esac
