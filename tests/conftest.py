"""Shared pytest fixtures."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures"

sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(scope="session")
def png_card(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A real PNG with a `chara` tEXt chunk built from v2_minimal.json."""
    from PIL import Image, PngImagePlugin

    payload = json.loads((FIXTURES / "v2_minimal.json").read_text("utf-8"))
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")

    target = tmp_path_factory.mktemp("png") / "echo.png"
    img = Image.new("RGB", (4, 4), color="white")
    info = PngImagePlugin.PngInfo()
    info.add_text("chara", encoded)
    img.save(target, "PNG", pnginfo=info)
    return target


@pytest.fixture()
def home(tmp_path: Path) -> Path:
    target = tmp_path / "home"
    target.mkdir()
    return target
