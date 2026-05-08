"""End-to-end checks that the security layers actually appear in output."""

from pathlib import Path

from soultavern.parse import load_card
from soultavern.render import render


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


def test_identity_directive_is_at_the_top(fixtures_dir: Path):
    """The IDENTITY DIRECTIVE must be the very first content in SOUL.md so
    it overrides the platform-level "you are an AI assistant" framing
    that hermes hard-codes into its system prompt."""
    data = load_card(fixtures_dir / "v2_minimal.json")
    result = render(data)
    assert "# IDENTITY DIRECTIVE" in result.soul
    # Directive precedes both the metadata comment and the persona H1
    assert result.soul.index("# IDENTITY DIRECTIVE") < result.soul.index("# Echo")
    # It names the character so "you are X" is bound at render time
    directive_block = result.soul.split("---", 1)[0]
    assert "You are **Echo**" in directive_block


def test_identity_directive_forbids_meta_disclosure(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_minimal.json")
    result = render(data)
    # Cover the three failure modes we observed (AI-assistant default,
    # "I'm portraying X" framing, and tech-stack disclosure)
    assert "AI assistant" in result.soul  # named in the forbidden list
    assert "portraying" in result.soul
    assert "Hermes" in result.soul  # the Hermes / Telegram framing the directive defends against


def test_identity_directive_present_for_every_card(fixtures_dir: Path):
    """The directive is auto-injected — independent of card content, and
    not subject to --trust-system-prompt."""
    for fixture in ("v2_minimal.json", "v2_full.json", "v2_with_book.json", "v1_legacy.json"):
        data = load_card(fixtures_dir / fixture)
        for trust in (False, True):
            result = render(data, trust_system_prompt=trust)
            assert "# IDENTITY DIRECTIVE" in result.soul, (
                f"directive missing for {fixture} (trust_system_prompt={trust})"
            )


def test_directive_does_not_undercut_safety(fixtures_dir: Path):
    """The directive should explicitly preserve operator-level safety
    so users can't construct a 'be the character even when asked
    something harmful' loophole."""
    data = load_card(fixtures_dir / "v2_minimal.json")
    result = render(data)
    directive_block = result.soul.split("---", 1)[0]
    # Directive must preserve operator safety override
    assert "safety" in directive_block.lower()
    assert "operator" in directive_block.lower()


def test_trust_banner_does_not_say_roleplay_material(fixtures_dir: Path):
    """The persona-content boundary banner must not contain the phrase
    'roleplay material to perform' — that wording undercuts the
    IDENTITY DIRECTIVE's "you ARE this character" assertion."""
    data = load_card(fixtures_dir / "v2_minimal.json")
    result = render(data)
    assert "roleplay material" not in result.soul
    # But the security purpose stays
    assert "Persona content boundary" in result.soul
    assert "override safety" in result.soul
