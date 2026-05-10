"""Shared pytest fixtures."""

from __future__ import annotations

import base64
import json
import struct
import sys
import zlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures"
SCRIPTS_DIR = REPO_ROOT / "skills" / "soultavern" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Minimal PNG builder (stdlib only)
# ---------------------------------------------------------------------------
#
# v2.0 dropped the pillow dependency. Tests that need a tiny "real" PNG
# build it from raw bytes here. The PNG is a 1x1 pixel image, but the
# only thing the parser actually reads is the tEXt chunk for "chara".

_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _chunk(ctype: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(ctype + data)
    return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)


def _ihdr_1x1_rgb() -> bytes:
    # 1x1, 8-bit, color type 2 (RGB), no compression / filter / interlace.
    return _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))


def _idat_1x1_white() -> bytes:
    # one scanline = filter byte (0) + 3 bytes white pixel
    raw = b"\x00\xff\xff\xff"
    return _chunk(b"IDAT", zlib.compress(raw))


def _iend() -> bytes:
    return _chunk(b"IEND", b"")


def _text_chunk(keyword: str, value: str) -> bytes:
    # tEXt: keyword (Latin-1) + null + text (Latin-1).
    payload = keyword.encode("latin-1") + b"\x00" + value.encode("latin-1")
    return _chunk(b"tEXt", payload)


def build_png(chara_value: str | None) -> bytes:
    """Return a minimal valid PNG. If ``chara_value`` is given, embed it
    as a tEXt chunk with key ``chara``."""
    parts = [_PNG_SIG, _ihdr_1x1_rgb()]
    if chara_value is not None:
        parts.append(_text_chunk("chara", chara_value))
    parts += [_idat_1x1_white(), _iend()]
    return b"".join(parts)


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(scope="session")
def png_card(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A real PNG with a `chara` tEXt chunk built from v2_minimal.json."""
    payload = json.loads((FIXTURES / "v2_minimal.json").read_text("utf-8"))
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    target = tmp_path_factory.mktemp("png") / "echo.png"
    target.write_bytes(build_png(encoded))
    return target


@pytest.fixture()
def home(tmp_path: Path) -> Path:
    target = tmp_path / "home"
    target.mkdir()
    return target
