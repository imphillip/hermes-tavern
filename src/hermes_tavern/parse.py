"""Parse SillyTavern character cards (JSON / PNG / YAML, V1 or V2)."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import yaml


class CardError(Exception):
    """Base class for card-related errors."""


class UnsupportedCardError(CardError):
    """File extension is not a recognised character card format."""


class InvalidCardError(CardError):
    """File looks like a card but cannot be parsed."""


_SUPPORTED_SUFFIXES = {".json", ".png", ".yaml", ".yml"}


def load_card(path: Path) -> dict[str, Any]:
    """Load a character card from disk and return the V2 ``data`` dict.

    V1 (flat) cards are lifted to the V2 shape so callers do not need to
    branch on spec version.
    """
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            raw = json.loads(path.read_text("utf-8"))
        except json.JSONDecodeError as exc:
            raise InvalidCardError(f"{path}: malformed JSON ({exc.msg})") from exc
    elif suffix == ".png":
        raw = _read_png_chara(path)
    elif suffix in (".yaml", ".yml"):
        try:
            raw = yaml.safe_load(path.read_text("utf-8"))
        except yaml.YAMLError as exc:
            raise InvalidCardError(f"{path}: malformed YAML ({exc})") from exc
    else:
        raise UnsupportedCardError(
            f"{path.suffix!r} is not a recognised card format "
            f"(expected one of {sorted(_SUPPORTED_SUFFIXES)})"
        )
    if not isinstance(raw, dict):
        raise InvalidCardError(f"{path}: top-level value is not an object")
    return _normalize(raw)


def _read_png_chara(path: Path) -> dict[str, Any]:
    from PIL import Image

    try:
        img = Image.open(path)
    except Exception as exc:
        raise InvalidCardError(f"{path}: cannot open as PNG ({exc})") from exc
    chara = img.info.get("chara") if hasattr(img, "info") else None
    if not chara:
        raise InvalidCardError(f"{path}: PNG has no `chara` tEXt chunk")
    try:
        decoded = base64.b64decode(chara).decode("utf-8")
        return json.loads(decoded)
    except Exception as exc:
        raise InvalidCardError(f"{path}: `chara` chunk is not valid base64-JSON ({exc})") from exc


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """V1 (flat) / V2 (nested) → return the V2 ``data`` payload."""
    if raw.get("spec") == "chara_card_v2" and isinstance(raw.get("data"), dict):
        return raw["data"]
    return raw
