import json
from pathlib import Path

import pytest

from soultavern.parse import (
    InvalidCardError,
    UnsupportedCardError,
    load_card,
)


def test_load_v2_minimal(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_minimal.json")
    assert data["name"] == "Echo"
    # V2 nesting is flattened
    assert "spec" not in data


def test_load_v1_legacy(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v1_legacy.json")
    assert data["name"] == "Old Tom"
    assert "<BOT>" in data["first_mes"]


def test_load_v2_full_has_all_fields(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_full.json")
    assert data["personality"] == "Curt but not unkind. Loves maps."
    assert data["alternate_greetings"]


def test_load_png(png_card: Path):
    data = load_card(png_card)
    assert data["name"] == "Echo"


def test_unsupported_extension(tmp_path: Path):
    bad = tmp_path / "card.txt"
    bad.write_text("nope")
    with pytest.raises(UnsupportedCardError):
        load_card(bad)


def test_malformed_json(tmp_path: Path):
    bad = tmp_path / "broken.json"
    bad.write_text("{not json")
    with pytest.raises(InvalidCardError):
        load_card(bad)


def test_png_without_chara(tmp_path: Path):
    from conftest import build_png

    bad = tmp_path / "plain.png"
    bad.write_bytes(build_png(chara_value=None))
    with pytest.raises(InvalidCardError):
        load_card(bad)


def test_yaml_no_longer_supported(tmp_path: Path):
    """v2.0 dropped YAML support — .yaml/.yml cards now hit
    UnsupportedCardError."""
    yaml_path = tmp_path / "card.yaml"
    yaml_path.write_text("name: Echo\n", "utf-8")
    with pytest.raises(UnsupportedCardError):
        load_card(yaml_path)
