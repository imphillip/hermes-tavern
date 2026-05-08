from soultavern.sanitize import find_long_unbroken_tokens, sanitize


def test_strips_zero_width_chars():
    raw = "hi" + "​" + "there" + "‌" + "friend" + "‍" + "!"
    assert sanitize(raw) == "hitherefriend!"


def test_strips_rtl_override():
    # U+202E (RTL override) is a classic filename-spoof character
    raw = "harmless" + "‮" + "txt.exe"
    out = sanitize(raw)
    assert "‮" not in out
    assert out == "harmlesstxt.exe"


def test_strips_bom_and_word_joiner():
    raw = "﻿text" + "⁠" + "here"
    assert sanitize(raw) == "texthere"


def test_strips_control_chars_keeps_tab_newline():
    raw = "a\x00b\x07c\nd\te"
    assert sanitize(raw) == "abc\nd\te"


def test_directional_isolates_stripped():
    raw = "before⁦inside⁩after"
    assert sanitize(raw) == "beforeinsideafter"


def test_empty_and_none():
    assert sanitize("") == ""
    assert sanitize(None) == ""


def test_long_token_detection():
    text = "normal sentence " + ("A" * 250) + " end"
    tokens = find_long_unbroken_tokens(text)
    assert len(tokens) == 1
    assert len(tokens[0]) == 250


def test_short_tokens_not_flagged():
    assert find_long_unbroken_tokens("just normal sentence with words") == []


def test_threshold_is_configurable():
    text = "AAAA"
    assert find_long_unbroken_tokens(text, threshold=3) == ["AAAA"]
    assert find_long_unbroken_tokens(text, threshold=10) == []
