"""Unit tests for the distill module — threshold + prompt + parsing."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from hermes_tavern.distill import (
    DISTILL_THRESHOLD,
    DistillationError,
    DistillResult,
    build_prompt,
    distill,
    needs_distillation,
    parse_response,
)


@dataclass
class FakeProc:
    stdout: str
    stderr: str = ""
    returncode: int = 0


def test_under_threshold_does_not_distill():
    assert needs_distillation("a" * 1000, "b" * 1000) is False


def test_over_soul_threshold_distills():
    assert needs_distillation("a" * (DISTILL_THRESHOLD + 1), None) is True


def test_over_lore_threshold_distills():
    assert needs_distillation("short", "x" * (DISTILL_THRESHOLD + 1)) is True


def test_lore_none_only_checks_soul():
    assert needs_distillation("a" * 1000, None) is False


def test_build_prompt_includes_caps_and_card_name():
    prompt = build_prompt(
        soul="SOUL CONTENT",
        lore="LORE CONTENT",
        char_name="Aldous",
        soul_target=12_000,
        lore_target=12_000,
    )
    assert "Aldous" in prompt
    assert "12000" in prompt
    assert "SOUL CONTENT" in prompt
    assert "LORE CONTENT" in prompt
    assert "<soul>" in prompt and "</soul>" in prompt
    assert "<lore>" in prompt and "</lore>" in prompt


def test_parse_response_extracts_blocks():
    text = """
<soul>
# Aldous

Compact persona.
</soul>
<lore>
# World

Compact lore.
</lore>
"""
    result = parse_response(text)
    assert "# Aldous" in result.soul
    assert "Compact persona." in result.soul
    assert result.lore is not None
    assert "Compact lore." in result.lore


def test_parse_response_lore_none_returns_none():
    text = "<soul>persona</soul>\n<lore>NONE</lore>"
    result = parse_response(text)
    assert result.lore is None


def test_parse_response_missing_soul_raises():
    with pytest.raises(DistillationError):
        parse_response("<lore>just lore</lore>")


def test_parse_response_handles_extra_whitespace_and_text():
    text = (
        "Sure, here is the distillation:\n\n"
        "<soul>\n  Compact persona.\n</soul>\n\n"
        "<lore>NONE</lore>\n\nDone."
    )
    result = parse_response(text)
    assert result.soul.strip() == "Compact persona."
    assert result.lore is None


def test_distill_with_runner_returns_parsed_result():
    def fake_runner(argv):
        # The prompt is the last arg
        assert "Aldous" in argv[-1]
        return FakeProc(
            stdout="<soul>compact</soul><lore>NONE</lore>"
        )
    result = distill(
        soul="A" * 16_000,
        hermes=None,
        char_name="Aldous",
        runner=fake_runner,
    )
    assert isinstance(result, DistillResult)
    assert result.soul.strip() == "compact"
    assert result.lore is None


def test_distill_with_runner_propagates_nonzero_exit():
    def boom(argv):
        return FakeProc(stdout="", stderr="model unavailable", returncode=1)
    with pytest.raises(DistillationError) as exc:
        distill(soul="x" * 16_000, hermes=None, char_name="X", runner=boom)
    assert "model unavailable" in str(exc.value)


def test_distill_with_unparseable_response_raises():
    def bad(argv):
        return FakeProc(stdout="garbage with no tags")
    with pytest.raises(DistillationError):
        distill(soul="x" * 16_000, hermes=None, char_name="X", runner=bad)


def test_distill_real_subprocess_missing_command():
    # Use an obviously-nonexistent command
    with pytest.raises(DistillationError) as exc:
        distill(
            soul="x" * 16_000,
            hermes=None,
            char_name="X",
            command="hermes-tavern-no-such-binary-12345",
        )
    assert "not found" in str(exc.value)
