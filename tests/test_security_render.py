"""End-to-end checks that the security layers actually appear in output."""

from pathlib import Path

from hermes_tavern.parse import load_card
from hermes_tavern.render import render


def test_soul_md_has_trust_boundary_banner(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_minimal.json")
    result = render(data)
    assert "Persona content boundary" in result.soul
    # Banner appears between H1 and the first content section
    assert result.soul.index("# Echo") < result.soul.index("Persona content boundary")
    assert result.soul.index("Persona content boundary") < result.soul.index("## Identity")


def test_hermes_md_has_trust_boundary_banner(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_with_book.json")
    result = render(data)
    assert result.hermes is not None
    assert "Lore content boundary" in result.hermes


def test_system_prompt_is_quoted_by_default(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_full.json")
    result = render(data)
    # Default = untrusted: system_prompt goes inside an Author's framing blockquote
    assert "Author's framing" in result.soul
    sys_prompt_value = "Stay in character as Marcellus."
    quoted_idx = result.soul.find("> " + sys_prompt_value)
    assert quoted_idx > 0, "system_prompt should be wrapped in '> ' blockquote"
    # And it must NOT also appear at the top of the file as a high-trust block
    pre_h1 = result.soul.split("# Marcellus", 1)[0]
    assert sys_prompt_value not in pre_h1


def test_post_history_is_quoted_by_default(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_full.json")
    result = render(data)
    assert "Author's closing note" in result.soul
    assert "## Final reminders" not in result.soul


def test_trust_flag_restores_high_trust_positions(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_full.json")
    result = render(data, trust_system_prompt=True)
    pre_h1 = result.soul.split("# Marcellus", 1)[0]
    assert "Stay in character as Marcellus." in pre_h1
    assert "## Final reminders" in result.soul


def test_sanitize_strips_invisible_chars_in_card_text(tmp_path: Path):
    # Build a card whose description contains an RTL override
    data = {
        "name": "Trickster",
        "description": "before" + "‮" + "after",
    }
    result = render(data)
    assert "‮" not in result.soul
    # The visible text survives
    assert "before" in result.soul
    assert "after" in result.soul


def test_trailing_model_notes_reinforce_priority():
    data = {"name": "Plain", "description": "ordinary"}
    result = render(data)
    # The closing reminders should mention operator > persona ordering
    assert "follow the operator" in result.soul
