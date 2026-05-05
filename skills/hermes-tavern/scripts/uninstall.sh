#!/usr/bin/env bash
# Uninstaller for the hermes-tavern CLI.
#
# Mirrors install.sh's three-branch logic: detects which install method
# was used and removes accordingly. Safe by design:
#
#   - Never touches user data in <HERMES_HOME>/ (cards, SOUL.md,
#     HERMES.md, snapshots — those are personal content, not part of
#     the install).
#   - Never deletes the skill files themselves (skills/hermes-tavern/).
#     If installed via the Hermes hub: `hermes skills uninstall
#     hermes-tavern` after this script. If dropped in via zip: rm the
#     skill folder by hand.
#   - The dedicated-venv branch only removes paths matching the
#     conventional layout (or HERMES_TAVERN_VENV / HERMES_TAVERN_BIN
#     overrides). It refuses to delete arbitrary paths.
#
# Pass `--dry-run` to print actions without executing them.
#
# Override paths via env vars (must match what install.sh used):
#   HERMES_TAVERN_VENV — venv location (default ~/.local/share/hermes-tavern-venv)
#   HERMES_TAVERN_BIN  — shim directory (default ~/.local/bin)

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

if ! command -v hermes-tavern >/dev/null 2>&1; then
    echo "uninstall.sh: hermes-tavern is not on PATH — nothing to uninstall."
    echo "uninstall.sh: (if you removed only the shim and the venv is still around,"
    echo "uninstall.sh:  re-check ~/.local/share/hermes-tavern-venv manually.)"
    exit 0
fi

CLI_PATH="$(command -v hermes-tavern)"
echo "uninstall.sh: found hermes-tavern at $CLI_PATH"
echo "uninstall.sh: $(hermes-tavern --version 2>&1 || true)"

# Branch 1: pipx
if command -v pipx >/dev/null 2>&1 \
   && pipx list --short 2>/dev/null | grep -qE '^hermes-tavern\b'; then
    echo "uninstall.sh: detected pipx-managed install"
    run pipx uninstall hermes-tavern
    exit 0
fi

# Branch 2: uv tool
if command -v uv >/dev/null 2>&1 \
   && uv tool list 2>/dev/null | grep -qE '^hermes-tavern\b'; then
    echo "uninstall.sh: detected uv-tool install"
    run uv tool uninstall hermes-tavern
    exit 0
fi

# Branch 3: dedicated venv + shim (the install.sh fallback path)
VENV_DIR="${HERMES_TAVERN_VENV:-$HOME/.local/share/hermes-tavern-venv}"
SHIM_DIR="${HERMES_TAVERN_BIN:-$HOME/.local/bin}"
EXPECTED_SHIM="$SHIM_DIR/hermes-tavern"
EXPECTED_VENV_BIN="$VENV_DIR/bin/hermes-tavern"

# Refuse to nuke arbitrary paths. The CLI must either be the expected
# shim, or directly inside the expected venv.
if [ "$CLI_PATH" = "$EXPECTED_SHIM" ] && [ -L "$CLI_PATH" ]; then
    LINK_TARGET="$(readlink "$CLI_PATH")"
    if [ "$LINK_TARGET" = "$EXPECTED_VENV_BIN" ]; then
        echo "uninstall.sh: detected dedicated-venv install"
        run rm "$EXPECTED_SHIM"
        if [ -d "$VENV_DIR" ]; then
            run rm -rf "$VENV_DIR"
        fi
        exit 0
    fi
fi

if [ "$CLI_PATH" = "$EXPECTED_VENV_BIN" ]; then
    echo "uninstall.sh: detected dedicated-venv install (no shim)"
    if [ -d "$VENV_DIR" ]; then
        run rm -rf "$VENV_DIR"
    fi
    exit 0
fi

echo "uninstall.sh: could not classify the install method."
echo "uninstall.sh: hermes-tavern lives at: $CLI_PATH"
echo "uninstall.sh:"
echo "uninstall.sh: this is unusual — install.sh only knows pipx / uv tool /"
echo "uninstall.sh: a dedicated venv at $VENV_DIR with a shim at $EXPECTED_SHIM."
echo "uninstall.sh: remove it by hand with whatever installer manages that path."
echo "uninstall.sh: (or pass HERMES_TAVERN_VENV / HERMES_TAVERN_BIN to match"
echo "uninstall.sh:  the locations you used at install time.)"
exit 1
