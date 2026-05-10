"""Parse SillyTavern character cards (JSON / PNG, V1 or V2). Stdlib only."""

from __future__ import annotations

import base64
import json
import struct
import zlib
from pathlib import Path
from typing import Any


class CardError(Exception):
    """Base class for card-related errors."""


class UnsupportedCardError(CardError):
    """File extension is not a recognised character card format."""


class InvalidCardError(CardError):
    """File looks like a card but cannot be parsed."""


_SUPPORTED_SUFFIXES = {".json", ".png"}
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


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
    else:
        raise UnsupportedCardError(
            f"{path.suffix!r} is not a recognised card format "
            f"(expected one of {sorted(_SUPPORTED_SUFFIXES)})"
        )
    if not isinstance(raw, dict):
        raise InvalidCardError(f"{path}: top-level value is not an object")
    return _normalize(raw)


def _read_png_chara(path: Path) -> dict[str, Any]:
    """Find the `chara` text chunk in a PNG and return its base64-JSON payload.

    Walks the chunk stream and matches `chara` against tEXt / iTXt / zTXt
    keywords (the three SillyTavern-flavored encodings ever seen in the
    wild). Pure stdlib — no pillow.
    """
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise InvalidCardError(f"{path}: cannot read file ({exc})") from exc

    if not data.startswith(_PNG_SIGNATURE):
        raise InvalidCardError(f"{path}: not a PNG (bad signature)")

    chara: str | None = None
    offset = len(_PNG_SIGNATURE)
    end = len(data)
    while offset + 8 <= end:
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        ctype = data[offset + 4 : offset + 8]
        body_start = offset + 8
        body_end = body_start + length
        if body_end + 4 > end:
            raise InvalidCardError(f"{path}: truncated PNG chunk {ctype!r}")
        body = data[body_start:body_end]
        offset = body_end + 4  # skip CRC

        if ctype == b"IEND":
            break
        if ctype not in (b"tEXt", b"iTXt", b"zTXt"):
            continue

        keyword, value = _decode_text_chunk(ctype, body, path)
        if keyword == "chara" and value:
            chara = value
            break

    if not chara:
        raise InvalidCardError(f"{path}: PNG has no `chara` text chunk")

    try:
        decoded = base64.b64decode(chara).decode("utf-8")
        return json.loads(decoded)
    except Exception as exc:
        raise InvalidCardError(f"{path}: `chara` chunk is not valid base64-JSON ({exc})") from exc


def _decode_text_chunk(ctype: bytes, body: bytes, path: Path) -> tuple[str, str]:
    """Return ``(keyword, text)`` for a tEXt / iTXt / zTXt chunk body."""
    null = body.find(b"\x00")
    if null < 0:
        raise InvalidCardError(f"{path}: malformed {ctype.decode()} chunk (no null)")
    keyword = body[:null].decode("latin-1", errors="replace")
    rest = body[null + 1 :]

    if ctype == b"tEXt":
        return keyword, rest.decode("latin-1", errors="replace")

    if ctype == b"zTXt":
        if not rest:
            return keyword, ""
        method = rest[0]
        if method != 0:
            raise InvalidCardError(f"{path}: zTXt unsupported compression method {method}")
        try:
            return keyword, zlib.decompress(rest[1:]).decode("latin-1", errors="replace")
        except zlib.error as exc:
            raise InvalidCardError(f"{path}: zTXt decompression failed ({exc})") from exc

    # iTXt: compression_flag(1) compression_method(1) language\0 translated\0 text
    if len(rest) < 2:
        raise InvalidCardError(f"{path}: malformed iTXt chunk (header)")
    compression_flag = rest[0]
    compression_method = rest[1]
    after_flags = rest[2:]
    lang_end = after_flags.find(b"\x00")
    if lang_end < 0:
        raise InvalidCardError(f"{path}: malformed iTXt chunk (language)")
    after_lang = after_flags[lang_end + 1 :]
    trans_end = after_lang.find(b"\x00")
    if trans_end < 0:
        raise InvalidCardError(f"{path}: malformed iTXt chunk (translated keyword)")
    text_bytes = after_lang[trans_end + 1 :]
    if compression_flag == 1:
        if compression_method != 0:
            raise InvalidCardError(
                f"{path}: iTXt unsupported compression method {compression_method}"
            )
        try:
            text_bytes = zlib.decompress(text_bytes)
        except zlib.error as exc:
            raise InvalidCardError(f"{path}: iTXt decompression failed ({exc})") from exc
    return keyword, text_bytes.decode("utf-8", errors="replace")


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """V1 (flat) / V2 (nested) → return the V2 ``data`` payload."""
    if raw.get("spec") == "chara_card_v2" and isinstance(raw.get("data"), dict):
        return raw["data"]
    return raw
