"""Tests for the managed-section helpers used by the OpenClaw target.

These are pure functions — string in, string out — so the tests are
all straightforward equality / regex assertions. Edge cases are the
point: malformed markers, empty files, sections that contain marker-
like text, repeated apply (idempotence), and round-trips
(apply → strip should restore).
"""

from __future__ import annotations

import pytest

from soultavern.targets.openclaw_writers import (
    DEFAULT_MARKER,
    apply_managed_section,
    has_managed_section,
    strip_managed_section,
)


# ---------- apply: empty file ----------


def test_apply_to_empty_file_produces_just_the_block():
    out = apply_managed_section("", "hello world")
    assert "<!-- BEGIN soultavern:character -->" in out
    assert "<!-- END soultavern:character -->" in out
    assert "hello world" in out
    assert out.endswith("\n")
    assert not out.startswith("\n")


def test_apply_to_whitespace_only_file_treats_as_empty():
    out = apply_managed_section("   \n\n  \n", "hello")
    assert out.startswith("<!-- BEGIN")
    assert "hello" in out


# ---------- apply: insertion into existing user content ----------


def test_apply_to_existing_content_inserts_at_top_by_default():
    user_content = "# My AGENTS.md\n\nMy customizations live here.\n"
    out = apply_managed_section(user_content, "character section")
    # Managed block first, then the user content
    begin_idx = out.index("<!-- BEGIN")
    user_idx = out.index("My customizations")
    assert begin_idx < user_idx
    # User content is preserved verbatim (modulo blank-line normalisation)
    assert "# My AGENTS.md" in out
    assert "My customizations live here." in out


def test_apply_at_bottom_position_appends():
    user_content = "# My AGENTS.md\n\nMy customizations.\n"
    out = apply_managed_section(user_content, "character section",
                                position="bottom")
    begin_idx = out.index("<!-- BEGIN")
    user_idx = out.index("My customizations")
    assert user_idx < begin_idx


def test_apply_with_invalid_position_raises():
    with pytest.raises(ValueError):
        apply_managed_section("anything", "section", position="middle")


# ---------- apply: replace existing managed section in place ----------


def test_apply_replaces_existing_block_in_place():
    initial = (
        "Some user prelude.\n"
        "\n"
        "<!-- BEGIN soultavern:character -->\n"
        "old content\n"
        "<!-- END soultavern:character -->\n"
        "\n"
        "Some user postlude.\n"
    )
    out = apply_managed_section(initial, "new content")
    # User content untouched
    assert "Some user prelude." in out
    assert "Some user postlude." in out
    # Old content gone, new content in
    assert "old content" not in out
    assert "new content" in out
    # Only one block (no duplication)
    assert out.count("<!-- BEGIN soultavern:character -->") == 1
    assert out.count("<!-- END soultavern:character -->") == 1


def test_apply_preserves_position_when_replacing():
    """If the existing block was at the bottom, replacement stays at
    the bottom — `position` only governs *new* insertions."""
    initial = (
        "User prelude.\n"
        "\n"
        "<!-- BEGIN soultavern:character -->\n"
        "old\n"
        "<!-- END soultavern:character -->\n"
    )
    out = apply_managed_section(initial, "new", position="top")
    user_idx = out.index("User prelude.")
    block_idx = out.index("<!-- BEGIN")
    assert user_idx < block_idx  # block stayed at bottom


def test_apply_is_idempotent():
    """Calling apply twice with the same input produces the same output."""
    initial = "User content.\n"
    once = apply_managed_section(initial, "section")
    twice = apply_managed_section(once, "section")
    assert once == twice


# ---------- strip ----------


def test_strip_removes_just_the_block():
    initial = (
        "User prelude.\n"
        "\n"
        "<!-- BEGIN soultavern:character -->\n"
        "managed content\n"
        "<!-- END soultavern:character -->\n"
        "\n"
        "User postlude.\n"
    )
    out = strip_managed_section(initial)
    assert "User prelude." in out
    assert "User postlude." in out
    assert "managed content" not in out
    assert "soultavern:character" not in out


def test_strip_returns_empty_when_block_was_only_content():
    initial = (
        "<!-- BEGIN soultavern:character -->\n"
        "managed content\n"
        "<!-- END soultavern:character -->\n"
    )
    assert strip_managed_section(initial) == ""


def test_strip_returns_empty_when_remaining_is_whitespace_only():
    initial = (
        "  \n"
        "<!-- BEGIN soultavern:character -->\n"
        "managed content\n"
        "<!-- END soultavern:character -->\n"
        "\n  \n"
    )
    assert strip_managed_section(initial) == ""


def test_strip_no_block_returns_input_unchanged_in_substance():
    initial = "User content with no managed block.\n"
    out = strip_managed_section(initial)
    assert out.strip() == initial.strip()


def test_strip_collapses_leftover_blank_lines():
    """Removing a block in the middle of content shouldn't leave a
    triple-blank gap behind."""
    initial = (
        "Line A\n"
        "\n"
        "<!-- BEGIN soultavern:character -->\n"
        "managed\n"
        "<!-- END soultavern:character -->\n"
        "\n"
        "Line B\n"
    )
    out = strip_managed_section(initial)
    assert "\n\n\n" not in out
    assert "Line A" in out
    assert "Line B" in out


# ---------- round-trip ----------


def test_apply_then_strip_restores_original():
    """For Hermes-style use case: apply a section, then delete it,
    should leave the user's original content intact."""
    original = "User content here.\n\nSection 2 of user content.\n"
    after_apply = apply_managed_section(original, "managed body")
    after_strip = strip_managed_section(after_apply)
    # Whitespace can differ slightly (trailing newlines), compare stripped
    assert after_strip.strip() == original.strip()


def test_apply_then_strip_on_empty_file_returns_empty():
    after_apply = apply_managed_section("", "managed body")
    after_strip = strip_managed_section(after_apply)
    assert after_strip == ""


# ---------- has_managed_section ----------


def test_has_managed_section_detects_complete_block():
    text = (
        "<!-- BEGIN soultavern:character -->\n"
        "x\n"
        "<!-- END soultavern:character -->\n"
    )
    assert has_managed_section(text) is True


def test_has_managed_section_false_when_only_begin():
    text = "<!-- BEGIN soultavern:character -->\nx\n"
    assert has_managed_section(text) is False


def test_has_managed_section_false_for_unrelated_content():
    text = "Just user content.\n"
    assert has_managed_section(text) is False


# ---------- custom marker ----------


def test_custom_marker_is_isolated_from_default():
    """If the user uses a different marker, the default-marker block
    in the same file shouldn't be touched."""
    initial = (
        "<!-- BEGIN soultavern:character -->\n"
        "default-marker content\n"
        "<!-- END soultavern:character -->\n"
        "\n"
        "<!-- BEGIN custom-thing -->\n"
        "custom-marker content\n"
        "<!-- END custom-thing -->\n"
    )
    # apply with the default marker — only that block changes
    out = apply_managed_section(initial, "new default content")
    assert "new default content" in out
    assert "default-marker content" not in out
    assert "custom-marker content" in out  # untouched
    assert "<!-- BEGIN custom-thing -->" in out


def test_custom_marker_round_trip():
    out = apply_managed_section("user.\n", "x", marker="my-app:state")
    assert "<!-- BEGIN my-app:state -->" in out
    assert has_managed_section(out, marker="my-app:state") is True
    assert has_managed_section(out, marker=DEFAULT_MARKER) is False
    stripped = strip_managed_section(out, marker="my-app:state")
    assert "x" not in stripped
    assert "user." in stripped


# ---------- output shape ----------


def test_block_includes_managed_note():
    """The BEGIN line should be followed by a comment explaining what
    the block is for — discoverability for users editing AGENTS.md."""
    out = apply_managed_section("", "body")
    assert "managed by soultavern" in out
    assert "safe to delete" in out


def test_section_with_surrounding_whitespace_is_normalised():
    """Caller might pass `\\n\\nbody\\n\\n`; the rendered block should
    still have predictable spacing."""
    out = apply_managed_section("", "\n\nbody\n\n")
    # Block should not have triple-blank lines internally
    assert "\n\n\n" not in out
    assert "body" in out


def test_output_always_ends_with_single_newline():
    inputs = ["", "user.\n", "user.\n\n\n", "no trailing newline"]
    for initial in inputs:
        out = apply_managed_section(initial, "x")
        assert out.endswith("\n")
        assert not out.endswith("\n\n")
