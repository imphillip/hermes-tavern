#!/usr/bin/env bash
# Uninstaller for the soultavern CLI (and its hermes-tavern alias).
#
# Mirrors install.sh's three-branch logic: detects which install method
# was used and removes accordingly. Safe by design:
#
#   - Never touches user data in <HERMES_HOME>/ (cards, SOUL.md,
#     HERMES.md / AGENTS.md, snapshots — those are personal content,
#     not part of the install).
#   - Never deletes the skill files themselves (skills/soultavern/).
#     If installed via the Hermes hub: `hermes skills uninstall
#     soultavern` after this script. If dropped in via zip: rm the
#     skill folder by hand.
#   - The dedicated-venv branch only removes paths matching the
#     conventional layout (or SOULTAVERN_VENV / SOULTAVERN_BIN
#     overrides). It refuses to delete arbitrary paths.
#   - If you installed v0.5.x or earlier, the binary was named
#     `hermes-tavern` and lived in `~/.local/share/hermes-tavern-venv`.
#     This script also recognises that legacy layout and cleans it up.
#
# Pass `--dry-run` to print actions without executing them.
#
# Override paths via env vars (must match what install.sh used):
#   SOULTAVERN_VENV — venv location (default ~/.local/share/soultavern-venv)
#   SOULTAVERN_BIN  — shim directory (default ~/.local/bin)

set -euo pipefail

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -h|--help)
            sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "uninstall.sh: unknown argument: $arg" >&2
            exit 2
            ;;
    esac
done

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "uninstall.sh: [dry-run] $*"
    else
        echo "uninstall.sh: $*"
        "$@"
    fi
}

# Detect which CLI binary is on PATH (post-v1.0 = soultavern;
# legacy v0.5.x = hermes-tavern).
PRIMARY_CLI=""
if command -v soultavern >/dev/null 2>&1; then
    PRIMARY_CLI="soultavern"
elif command -v hermes-tavern >/dev/null 2>&1; then
    PRIMARY_CLI="hermes-tavern"
fi

if [ -z "$PRIMARY_CLI" ]; then
    echo "uninstall.sh: neither soultavern nor hermes-tavern is on PATH — nothing to uninstall."
    echo "uninstall.sh: (if you removed only the shim and the venv is still around,"
    echo "uninstall.sh:  re-check ~/.local/share/soultavern-venv manually.)"
    exit 0
fi

CLI_PATH="$(command -v "$PRIMARY_CLI")"
echo "uninstall.sh: found $PRIMARY_CLI at $CLI_PATH"
echo "uninstall.sh: $("$PRIMARY_CLI" --version 2>&1 || true)"

# Branch 1: pipx — the package name is `soultavern` post-v1.0,
# `hermes-tavern` pre-v1.0. Try both.
if command -v pipx >/dev/null 2>&1; then
    if pipx list --short 2>/dev/null | grep -qE '^soultavern\b'; then
        echo "uninstall.sh: detected pipx-managed install (soultavern)"
        run pipx uninstall soultavern
        exit 0
    fi
    if pipx list --short 2>/dev/null | grep -qE '^hermes-tavern\b'; then
        echo "uninstall.sh: detected pipx-managed install (legacy hermes-tavern package)"
        run pipx uninstall hermes-tavern
        exit 0
    fi
fi

# Branch 2: uv tool
if command -v uv >/dev/null 2>&1; then
    if uv tool list 2>/dev/null | grep -qE '^soultavern\b'; then
        echo "uninstall.sh: detected uv-tool install (soultavern)"
        run uv tool uninstall soultavern
        exit 0
    fi
    if uv tool list 2>/dev/null | grep -qE '^hermes-tavern\b'; then
        echo "uninstall.sh: detected uv-tool install (legacy hermes-tavern package)"
        run uv tool uninstall hermes-tavern
        exit 0
    fi
fi

# Branch 3: dedicated venv + shim (the install.sh fallback path).
# Recognise both the v1.0+ layout and the legacy v0.5.x layout.
SHIM_DIR="${SOULTAVERN_BIN:-$HOME/.local/bin}"
NEW_VENV="${SOULTAVERN_VENV:-$HOME/.local/share/soultavern-venv}"
LEGACY_VENV="$HOME/.local/share/hermes-tavern-venv"

NEW_VENV_BIN="$NEW_VENV/bin/$PRIMARY_CLI"
LEGACY_VENV_BIN="$LEGACY_VENV/bin/$PRIMARY_CLI"
EXPECTED_SHIM="$SHIM_DIR/$PRIMARY_CLI"

# Refuse to nuke arbitrary paths. The CLI must either be the expected
# shim, or directly inside the expected venv (new or legacy layout).
remove_layout() {
    local venv="$1"
    # Remove BOTH the soultavern and hermes-tavern shims if they
    # point into this venv (post-v1.0 installs both).
    for shim_name in soultavern hermes-tavern; do
        local shim="$SHIM_DIR/$shim_name"
        if [ -L "$shim" ]; then
            local target
            target="$(readlink "$shim")"
            if [ "$target" = "$venv/bin/soultavern" ] \
               || [ "$target" = "$venv/bin/hermes-tavern" ]; then
                run rm "$shim"
            fi
        fi
    done
    if [ -d "$venv" ]; then
        run rm -rf "$venv"
    fi
}

if [ "$CLI_PATH" = "$EXPECTED_SHIM" ] && [ -L "$CLI_PATH" ]; then
    LINK_TARGET="$(readlink "$CLI_PATH")"
    if [ "$LINK_TARGET" = "$NEW_VENV_BIN" ]; then
        echo "uninstall.sh: detected dedicated-venv install (v1.0+ layout)"
        remove_layout "$NEW_VENV"
        exit 0
    fi
    if [ "$LINK_TARGET" = "$LEGACY_VENV_BIN" ]; then
        echo "uninstall.sh: detected dedicated-venv install (legacy v0.5.x layout)"
        remove_layout "$LEGACY_VENV"
        exit 0
    fi
fi

# CLI lives directly in a venv (no shim) — either layout
if [ "$CLI_PATH" = "$NEW_VENV_BIN" ]; then
    echo "uninstall.sh: detected dedicated-venv install (no shim, v1.0+)"
    remove_layout "$NEW_VENV"
    exit 0
fi
if [ "$CLI_PATH" = "$LEGACY_VENV_BIN" ]; then
    echo "uninstall.sh: detected dedicated-venv install (no shim, legacy v0.5.x)"
    remove_layout "$LEGACY_VENV"
    exit 0
fi

echo "uninstall.sh: could not classify the install method."
echo "uninstall.sh: $PRIMARY_CLI lives at: $CLI_PATH"
echo "uninstall.sh:"
echo "uninstall.sh: this is unusual — install.sh only knows pipx / uv tool /"
echo "uninstall.sh: a dedicated venv at $NEW_VENV (or legacy $LEGACY_VENV)."
echo "uninstall.sh: remove it by hand with whatever installer manages that path."
echo "uninstall.sh: (or pass SOULTAVERN_VENV / SOULTAVERN_BIN to match"
echo "uninstall.sh:  the locations you used at install time.)"
exit 1
