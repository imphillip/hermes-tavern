"""V2 semantic classification — the LLM-driven step that redistributes
character content into the eight V2-aligned categories.

The classification call replaces the v0.3 single-shot "compress soul +
lore" distillation with a structured editorial pass that:

- Preserves source wording (no creative rewriting)
- Outputs every category, including empty ones (silence is signal)
- Lets us observe LLM content tolerance via empty/refused categories
- Auto-detects subheaders inside `description` for cleaner LLM input
"""
from __future__ import annotations

from dataclasses import dataclass

from hermes_tavern.classify import (
    CATEGORIES,
    SOUL_PICKS,
    Classification,
    _detect_subheaders,
    build_classification_prompt,
    parse_classification_response,
)


@dataclass
class FakeProc:
    stdout: str
    stderr: str = ""
    returncode: int = 0


def test_categories_are_the_eight_v2_aligned_buckets():
    assert CATEGORIES == (
        "identity", "appearance", "personality", "backstory",
        "scenario", "kinks", "roleplay_guides", "examples",
    )


def test_soul_picks_are_a_strict_subset_of_categories():
    assert set(SOUL_PICKS).issubset(set(CATEGORIES))
    # The "always-on core" picks: who the character is + how to play them.
    # appearance / backstory / scenario / kinks / examples live in extended/.
    assert SOUL_PICKS == ("identity", "personality", "roleplay_guides")


def test_detect_subheaders_finds_veranna_style_labels():
    text = (
        "Full Name: Veranna Li\n"
        "Age: 22 years old\n"
        "Ethnicity: Chinese\n"
        "Height: 181 cm\n"
        "Appearance: long dark hair, hazel eyes\n"
    )
    parts = _detect_subheaders(text)
    assert parts is not None
    assert len(parts) == 5
    headers = [h for h, _ in parts]
    assert headers == ["Full Name", "Age", "Ethnicity", "Height", "Appearance"]


def test_detect_subheaders_returns_none_when_no_structure():
    text = "Just a regular paragraph of prose. She said: 'Hi.'"
    assert _detect_subheaders(text) is None


def test_detect_subheaders_preserves_multiline_body():
    text = (
        "Appearance: long dark hair.\n"
        "Eyes are hazel.\n"
        "Height is tall.\n"
        "\n"
        "Personality: reserved.\n"
        "Speaks softly.\n"
        "Listens well.\n"
    )
    parts = _detect_subheaders(text, min_count=2)
    assert parts is not None
    assert len(parts) == 2
    assert parts[0][0] == "Appearance"
    assert "Eyes are hazel" in parts[0][1]
    assert "Height is tall" in parts[0][1]
    assert parts[1][0] == "Personality"
    assert "Speaks softly" in parts[1][1]


def test_build_prompt_demands_faithful_redistribution():
    prompt = build_classification_prompt(
        {"name": "Aldous", "description": "Just text."},
        char_name="Aldous",
    )
    lower = prompt.lower()
    assert "preserve the source's wording" in lower
    assert "do not paraphrase" in lower
    assert "italic" in lower  # anti-novelistic guard
    assert "editorial work, not creative writing" in lower
    # All eight category tags appear in the XML template
    for cat in CATEGORIES:
        assert f"<{cat}>" in prompt
        assert f"</{cat}>" in prompt
    assert "Aldous" in prompt
    assert "Just text." in prompt


def test_build_prompt_uses_subheader_split_when_present():
    """Veranna-style subheaders should be passed to the LLM in already-
    structured form, so it doesn't have to discover them itself."""
    description = (
        "Full Name: Echo\n"
        "Age: 22\n"
        "Height: 181 cm\n"
        "Appearance: tall and dark-haired.\n"
    )
    prompt = build_classification_prompt(
        {"name": "Echo", "description": description},
        char_name="Echo",
    )
    assert "already structured by subheaders" in prompt
    assert "### Full Name" in prompt
    assert "### Appearance" in prompt


def test_build_prompt_passes_through_unstructured_description():
    """When description has no subheaders, just pass it as one block."""
    description = "Just a long paragraph of prose with no labels."
    prompt = build_classification_prompt(
        {"name": "X", "description": description},
        char_name="X",
    )
    assert "already structured by subheaders" not in prompt
    assert description in prompt


def test_parse_response_extracts_eight_categories():
    body = (
        "<identity>Echo, 22, ambivert.</identity>\n"
        "<appearance>Tall, dark-haired.</appearance>\n"
        "<personality>Quiet observer.</personality>\n"
        "<backstory></backstory>\n"
        "<scenario>Standing alone at a café.</scenario>\n"
        "<kinks></kinks>\n"
        "<roleplay_guides>Stay in voice.</roleplay_guides>\n"
        "<examples></examples>\n"
    )
    result = parse_classification_response(body)
    assert isinstance(result, Classification)
    assert set(result.categories.keys()) == set(CATEGORIES)
    assert result.categories["identity"] == "Echo, 22, ambivert."
    assert result.categories["backstory"] == ""
    assert result.categories["kinks"] == ""
    assert result.categories["scenario"] == "Standing alone at a café."


def test_parse_response_treats_missing_tags_as_empty_categories():
    """LLM refusal or partial output: missing tags become empty strings.
    This is the 'tolerance probe' signal — empty categories are observable
    without raising."""
    body = "<identity>Echo</identity>"  # only identity returned
    result = parse_classification_response(body)
    assert result.categories["identity"] == "Echo"
    for cat in CATEGORIES:
        if cat != "identity":
            assert result.categories[cat] == ""


def test_classification_non_empty_filters_blanks():
    """Convenience accessor for downstream consumers."""
    body = (
        "<identity>Echo</identity>\n"
        "<appearance></appearance>\n"
        "<personality>Quiet.</personality>\n"
        "<backstory></backstory>\n"
        "<scenario></scenario>\n"
        "<kinks></kinks>\n"
        "<roleplay_guides></roleplay_guides>\n"
        "<examples></examples>\n"
    )
    result = parse_classification_response(body)
    non_empty = result.non_empty()
    assert set(non_empty.keys()) == {"identity", "personality"}


def test_classify_uses_runner_injection(tmp_path):
    """The runner seam lets tests bypass the real subprocess call."""
    from hermes_tavern.classify import classify

    captured: dict = {}

    def runner(argv):
        captured["argv"] = argv
        return FakeProc(
            stdout=(
                "<identity>X.</identity>\n"
                "<appearance></appearance>\n"
                "<personality></personality>\n"
                "<backstory></backstory>\n"
                "<scenario></scenario>\n"
                "<kinks></kinks>\n"
                "<roleplay_guides></roleplay_guides>\n"
                "<examples></examples>\n"
            )
        )

    result = classify(
        {"name": "X", "description": "Just X."},
        char_name="X",
        runner=runner,
    )
    assert result.categories["identity"] == "X."
    # The argv passed in includes the prompt as a single trailing arg
    assert captured["argv"][0] == "hermes"
    assert any("editorial work" in arg for arg in captured["argv"])
