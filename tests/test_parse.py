import json
from pathlib import Path

import pytest

from hermes_tavern.parse import (
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
    from PIL import Image

    bad = tmp_path / "plain.png"
    Image.new("RGB", (2, 2), color="black").save(bad, "PNG")
    with pytest.raises(InvalidCardError):
        load_card(bad)


def test_yaml_card(tmp_path: Path):
    src = json.loads((Path(__file__).parent / "fixtures" / "v2_minimal.json").read_text())
    yaml_path = tmp_path / "card.yaml"
    import yaml

    yaml_path.write_text(yaml.safe_dump(src), "utf-8")
    data = load_card(yaml_path)
    assert data["name"] == "Echo"
