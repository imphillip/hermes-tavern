"""``hermes-tavern`` command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__, library
from .distill import DEFAULT_DISTILL_CMD, DistillationError
from .parse import CardError, load_card
from .render import BudgetExceededError, render
from .scan import Finding, scan_card
from .snapshots import SnapshotError

_EXIT_OK = 0
_EXIT_USAGE = 2
_EXIT_FAIL = 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return _EXIT_USAGE
    try:
        return handler(args)
    except CardError as exc:
        print(f"hermes-tavern: card error: {exc}", file=sys.stderr)
        return _EXIT_USAGE
    except library.LibraryError as exc:
        print(f"hermes-tavern: {exc}", file=sys.stderr)
        return _EXIT_USAGE
    except SnapshotError as exc:
        print(f"hermes-tavern: {exc}", file=sys.stderr)
        return _EXIT_USAGE
    except DistillationError as exc:
        print(f"hermes-tavern: distillation failed: {exc}", file=sys.stderr)
        print("hermes-tavern: pass --no-distill to fall back and surface the original "
              "budget error instead.", file=sys.stderr)
        return _EXIT_FAIL
    except BudgetExceededError as exc:
        print(
            f"hermes-tavern: {exc.kind} is too large ({exc.size}/{exc.limit} chars). "
            "Trim description / personality / mes_example or split the lorebook.",
            file=sys.stderr,
        )
        return _EXIT_FAIL


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermes-tavern",
        description="Import and manage SillyTavern V2 character cards for Hermes-Agent.",
    )
    parser.add_argument("--version", action="version", version=f"hermes-tavern {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p_import = sub.add_parser("import", help="Import a card and make it the active persona.")
    p_import.add_argument("--card", required=True, type=Path, help="Path to .json/.png/.yaml card")
    p_import.add_argument("--home", required=True, type=Path, help="Target HERMES_HOME directory")
    p_import.add_argument("--user-noun", default=library.DEFAULT_USER_NOUN,
                          help="How {{user}} should be addressed (default: 'the visitor')")
    p_import.add_argument("--overwrite", action="store_true", help="Replace existing SOUL.md / HERMES.md")
    p_import.add_argument("--dry-run", action="store_true", help="Render to stdout without touching disk")
    p_import.add_argument("--trust-system-prompt", action="store_true",
                          help="Render the card's system_prompt and post_history_instructions in their "
                               "high-trust V2 positions instead of inside untrusted blockquotes. Only use "
                               "for cards from authors you trust.")
    p_import.add_argument("--no-distill", dest="allow_distill", action="store_false", default=True,
                          help="Do not invoke the distillation command for oversized cards; fail with "
                               "the original budget error instead.")
    p_import.add_argument("--distill-cmd", default=DEFAULT_DISTILL_CMD,
                          help=f"Command to shell out to for distillation (default: {DEFAULT_DISTILL_CMD!r}). "
                               "The prompt is appended as a final argument.")
    soul_only_grp = p_import.add_mutually_exclusive_group()
    soul_only_grp.add_argument("--no-hermes-md", dest="soul_only", action="store_true",
                               help="Skip HERMES.md even if the card has a lorebook")
    soul_only_grp.add_argument("--soul-only", dest="soul_only", action="store_true",
                               help="Alias for --no-hermes-md")
    p_import.set_defaults(handler=_cmd_import, soul_only=False)

    p_validate = sub.add_parser("validate", help="Parse a card and report field completeness / budget.")
    p_validate.add_argument("--card", required=True, type=Path)
    p_validate.add_argument("--user-noun", default=library.DEFAULT_USER_NOUN)
    p_validate.set_defaults(handler=_cmd_validate)

    p_list = sub.add_parser("list", help="List cards stored in <HERMES_HOME>/cards/.")
    p_list.add_argument("--home", required=True, type=Path)
    p_list.add_argument("--all", dest="include_trash", action="store_true",
                        help="Also show soft-deleted cards in cards/.trash/")
    p_list.set_defaults(handler=_cmd_list)

    p_current = sub.add_parser("current", help="Show the currently active character.")
    p_current.add_argument("--home", required=True, type=Path)
    p_current.set_defaults(handler=_cmd_current)

    p_switch = sub.add_parser("switch", help="Switch active persona to a card already in the library.")
    p_switch.add_argument("--card", required=True,
                          help="Card filename or character name (case-insensitive prefix match)")
    p_switch.add_argument("--home", required=True, type=Path)
    p_switch.add_argument("--user-noun", default=None,
                          help="Override the user noun (defaults to previously active value)")
    p_switch.add_argument("--soul-only", dest="soul_only", action="store_true", default=None,
                          help="Force SOUL-only output for this switch")
    p_switch.add_argument("--trust-system-prompt", dest="trust_system_prompt",
                          action="store_true", default=None,
                          help="Override stored trust setting; render system_prompt/"
                               "post_history_instructions in their high-trust positions.")
    p_switch.add_argument("--no-distill", dest="allow_distill", action="store_false", default=True,
                          help="Do not invoke the distillation command for oversized cards.")
    p_switch.add_argument("--distill-cmd", default=DEFAULT_DISTILL_CMD,
                          help=f"Command to shell out to for distillation (default: {DEFAULT_DISTILL_CMD!r}).")
    p_switch.set_defaults(handler=_cmd_switch)

    p_delete = sub.add_parser("delete", help="Soft-delete a card (move to cards/.trash/).")
    p_delete.add_argument("--card", required=True)
    p_delete.add_argument("--home", required=True, type=Path)
    p_delete.set_defaults(handler=_cmd_delete)

    p_restore = sub.add_parser("restore", help="Restore a previously deleted card from cards/.trash/.")
    p_restore.add_argument("--card", required=True)
    p_restore.add_argument("--home", required=True, type=Path)
    p_restore.set_defaults(handler=_cmd_restore)

    p_history = sub.add_parser(
        "history",
        help="Show the chronological list of SOUL.md / HERMES.md snapshots.",
    )
    p_history.add_argument("--home", required=True, type=Path)
    p_history.set_defaults(handler=_cmd_history)

    p_revert = sub.add_parser(
        "revert",
        help="Restore SOUL.md / HERMES.md from a snapshot in the history.",
    )
    p_revert.add_argument("--home", required=True, type=Path)
    target_grp = p_revert.add_mutually_exclusive_group(required=True)
    target_grp.add_argument(
        "--to",
        dest="target",
        help="Snapshot id (e.g. '0001'), name prefix (e.g. 'Aldous'), "
             "or the special tokens 'pristine' / 'previous'.",
    )
    target_grp.add_argument(
        "--previous",
        dest="target",
        action="store_const",
        const="previous",
        help="Shortcut for --to previous (one snapshot back).",
    )
    p_revert.set_defaults(handler=_cmd_revert)

    return parser


def _cmd_import(args: argparse.Namespace) -> int:
    data = load_card(args.card)
    findings = scan_card(data)
    _emit_findings(findings, trust_system_prompt=args.trust_system_prompt)
    if args.dry_run:
        rendered = render(
            data,
            user_noun=args.user_noun,
            include_hermes_md=not args.soul_only,
            trust_system_prompt=args.trust_system_prompt,
        )
        _print_dry_run(rendered)
        return _EXIT_OK
    outcome, library_path = library.import_card(
        args.home,
        args.card,
        user_noun=args.user_noun,
        soul_only=args.soul_only,
        overwrite=args.overwrite,
        trust_system_prompt=args.trust_system_prompt,
        allow_distill=args.allow_distill,
        distill_command=args.distill_cmd,
    )
    _report_outcome(args.home, outcome, library_path, soul_only=args.soul_only)
    return _EXIT_OK


def _cmd_validate(args: argparse.Namespace) -> int:
    from .distill import DISTILL_THRESHOLD
    from .render import SOUL_BUDGET

    data = load_card(args.card)
    # Always render without budget enforcement: validate is informational,
    # so an oversized card should produce a report (the operator then decides
    # whether to import with distillation, --no-distill, or trim by hand).
    rendered = render(data, user_noun=args.user_noun, include_hermes_md=True,
                      enforce_budget=False)
    name = data.get("name") or "(no name)"
    print(f"name: {name}")
    fields = ["description", "personality", "scenario", "first_mes",
              "alternate_greetings", "mes_example", "system_prompt",
              "post_history_instructions", "character_book"]
    for field in fields:
        marker = "y" if data.get(field) else "."
        print(f"  [{marker}] {field}")

    print(f"SOUL.md size:   {len(rendered.soul):>5} / {SOUL_BUDGET} chars"
          f"{_budget_marker(len(rendered.soul))}")
    if rendered.hermes is not None:
        size = len(rendered.hermes)
        print(f"HERMES.md size: {size:>5} / {SOUL_BUDGET} chars{_budget_marker(size)}")
        if rendered.truncated_entries:
            print(f"warning: would drop {rendered.truncated_entries} lorebook entries")

    distill_needed = (
        len(rendered.soul) > DISTILL_THRESHOLD
        or (rendered.hermes is not None and len(rendered.hermes) > DISTILL_THRESHOLD)
    )
    if distill_needed:
        print("note: would trigger distillation on import (over 75% threshold)")

    findings = scan_card(data)
    print(f"scan: {len(findings)} suspicious pattern(s)")
    for finding in findings:
        print(f"  - {finding.format()}")
    return _EXIT_OK


def _budget_marker(size: int) -> str:
    from .distill import DISTILL_THRESHOLD
    from .render import SOUL_BUDGET
    if size > SOUL_BUDGET:
        return "  [over hard cap — distillation required]"
    if size > DISTILL_THRESHOLD:
        return "  [over 75% threshold]"
    return ""


def _cmd_list(args: argparse.Namespace) -> int:
    entries = library.list_cards(args.home, include_trash=args.include_trash)
    if not entries:
        print("(library is empty)")
        return _EXIT_OK
    for entry in entries:
        marker = "*" if entry.active else (" " if not entry.trashed else "x")
        location = "trash" if entry.trashed else "cards"
        ts = entry.imported_at or "?"
        print(f"{marker} {entry.file:48s}  {entry.name:32s}  {ts}  ({location})")
    return _EXIT_OK


def _cmd_current(args: argparse.Namespace) -> int:
    record = library.read_active(args.home)
    if record is None:
        print("(no active character)")
        return _EXIT_OK
    print(f"name:                {record.name}")
    print(f"card file:           {record.card_file}")
    print(f"imported at:         {record.imported_at}")
    print(f"user noun:           {record.user_noun}")
    print(f"trust system prompt: {record.trust_system_prompt}")
    print(f"distilled:           {record.distilled}")
    print(f"SOUL.md:             {library.soul_path(args.home)}"
          f" {'(missing!)' if not library.soul_path(args.home).exists() else ''}")
    if record.has_hermes_md:
        print(f"HERMES.md:           {library.hermes_path(args.home)}"
              f" {'(missing!)' if not library.hermes_path(args.home).exists() else ''}")
    if record.extended_dir:
        ext = args.home / record.extended_dir
        marker = "" if ext.exists() else " (missing!)"
        print(f"extended/:           {ext}{marker}")
    return _EXIT_OK


def _cmd_switch(args: argparse.Namespace) -> int:
    target, outcome = library.switch_to(
        args.home,
        args.card,
        user_noun=args.user_noun,
        soul_only=args.soul_only,
        trust_system_prompt=args.trust_system_prompt,
        allow_distill=args.allow_distill,
        distill_command=args.distill_cmd,
    )
    data = load_card(target)
    findings = scan_card(data)
    _emit_findings(findings, trust_system_prompt=bool(args.trust_system_prompt))
    print(f"switched to {target.name}")
    _report_outcome(args.home, outcome, target, soul_only=outcome.rendered.hermes is None and not outcome.distilled)
    return _EXIT_OK


def _cmd_delete(args: argparse.Namespace) -> int:
    dest = library.delete_card(args.home, args.card)
    print(f"moved to {dest}")
    active = library.read_active(args.home)
    if active is None:
        print("note: deleted card was the active one; SOUL.md/HERMES.md left in place but no active record")
    return _EXIT_OK


def _cmd_restore(args: argparse.Namespace) -> int:
    dest = library.restore_card(args.home, args.card)
    print(f"restored to {dest}")
    print("run `hermes-tavern switch --card <name> --home <home>` to activate it")
    return _EXIT_OK


def _cmd_history(args: argparse.Namespace) -> int:
    snaps = library.list_history(args.home)
    if not snaps:
        print("(no snapshots — run `hermes-tavern import` first)")
        return _EXIT_OK
    print(f"{'id':<6} {'when':<20} {'action':<10} {'name':<30} files")
    for s in snaps:
        marker = ("S" if s.has_soul_md else "-") + ("H" if s.has_hermes_md else "-")
        when = s.created_at.split("+")[0]
        print(f"{s.id:<6} {when:<20} {s.action:<10} {s.name:<30} {marker}")
    print("\n(files: S=SOUL.md present, H=HERMES.md present; "
          "'--' = pristine state with no HermesTavern files)")
    return _EXIT_OK


def _cmd_revert(args: argparse.Namespace) -> int:
    target = library.revert_to(args.home, args.target)
    soul_state = "yes" if target.has_soul_md else "(none — live SOUL.md removed)"
    hermes_state = "yes" if target.has_hermes_md else "(none — live HERMES.md removed)"
    print(f"reverted to snapshot {target.id} ({target.action}: {target.name})")
    print(f"  SOUL.md:   {soul_state}")
    print(f"  HERMES.md: {hermes_state}")
    print(f"\nto activate: cd {args.home} && hermes", file=sys.stderr)
    print("(if hermes is already running in a channel, use /new for a fresh "
          "session — or /reset to clear and reload — to apply this revert)",
          file=sys.stderr)
    return _EXIT_OK


def _report_outcome(home: Path, outcome: library.ApplyOutcome, library_path: Path,
                    *, soul_only: bool) -> None:
    """Print a one-screen summary of what was written."""
    print(f"wrote {library.soul_path(home)}")
    if outcome.distilled:
        print(f"  (SOUL distilled from {len(outcome.rendered.soul)} → "
              f"{outcome.distilled_soul_size} chars)")
        print(f"wrote {library.hermes_path(home)}"
              + (f" (with {outcome.distilled_lore_size}-char distilled lore + "
                 f"{outcome.extended_files}-file index)"
                 if outcome.distilled_lore_size
                 else f" (extended-file index only — no lore retained)"))
        print(f"wrote {outcome.extended_files} extended file(s) under "
              f"{home / 'cards' / library_path.stem / 'extended'}")
    else:
        if outcome.wrote_hermes_md:
            print(f"wrote {library.hermes_path(home)}")
        elif soul_only:
            print("HERMES.md skipped (--soul-only)")
        else:
            print("no character_book in this card; HERMES.md not written")
    print(f"backed up card to {library_path}")
    if outcome.rendered.truncated_entries:
        print(
            f"warning: dropped {outcome.rendered.truncated_entries} lorebook "
            "entries to fit budget",
            file=sys.stderr,
        )
    print(f"\nto activate: cd {home} && hermes", file=sys.stderr)
    print("(HERMES.md is read from cwd, not HERMES_HOME — must launch from "
          "inside the home directory)", file=sys.stderr)
    print("(if hermes is already running in a channel, use /new for a fresh "
          "session — or /reset to clear and reload — to apply this card)",
          file=sys.stderr)


def _emit_findings(findings: list[Finding], *, trust_system_prompt: bool) -> None:
    """Print scan warnings to stderr. Never blocks; only informs."""
    if not findings:
        return
    print(f"hermes-tavern: scan found {len(findings)} suspicious pattern(s):",
          file=sys.stderr)
    for finding in findings:
        print(f"  WARN {finding.format()}", file=sys.stderr)
    if trust_system_prompt:
        print(
            "hermes-tavern: --trust-system-prompt is on; the card's system_prompt and "
            "post_history_instructions are rendered with operator-level trust. Review the "
            "above warnings carefully before activating.",
            file=sys.stderr,
        )


def _print_dry_run(rendered) -> None:
    print("--- SOUL.md ---")
    print("```markdown")
    print(rendered.soul, end="" if rendered.soul.endswith("\n") else "\n")
    print("```")
    if rendered.hermes is not None:
        print("--- HERMES.md ---")
        print("```markdown")
        print(rendered.hermes, end="" if rendered.hermes.endswith("\n") else "\n")
        print("```")


if __name__ == "__main__":
    sys.exit(main())
