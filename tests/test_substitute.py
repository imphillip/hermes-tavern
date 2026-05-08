from soultavern.substitute import substitute


def test_basic_replacements():
    out = substitute("hello {{user}}, I am {{char}}", "Alice", "friend")
    assert out == "hello friend, I am Alice"


def test_case_insensitive():
    out = substitute("{{Char}} <BOT> {{USER}} <user>", "Alice", "friend")
    assert out == "Alice Alice friend friend"


def test_legacy_tokens():
    out = substitute("<BOT> meets <USER>", "Alice", "the visitor")
    assert out == "Alice meets the visitor"


def test_non_recursive():
    # If user_noun itself contains a placeholder, it is not re-expanded.
    out = substitute("{{user}}", "Alice", "{{char}}")
    assert out == "{{char}}"


def test_empty_and_none():
    assert substitute("", "Alice", "friend") == ""
    assert substitute(None, "Alice", "friend") == ""


def test_no_placeholders():
    assert substitute("just text", "Alice", "friend") == "just text"
