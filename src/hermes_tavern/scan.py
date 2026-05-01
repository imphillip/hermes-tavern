"""Red-flag pattern scanning for character cards.

Findings are reported as warnings (stderr); they never block import. The
goal is to surface the kind of patterns that prompt-injection cards rely
on so the operator can eyeball them before activation. False positives are
expected — the scan is a smoke detector, not a quarantine wall.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .sanitize import find_long_unbroken_tokens


@dataclass(frozen=True)
class Finding:
    category: str
    field: str
    snippet: str

    def format(self) -> str:
        snippet = self.snippet.replace("\n", " ")
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
        return f"[{self.category}] {self.field}: {snippet}"


_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("override-instruction",
     re.compile(r"\bignore\s+(?:(?:all|any|the|previous|prior|above|earlier)\s+){1,3}"
                r"(?:instructions?|prompts?|rules?|guidelines?|directives?)\b",
                re.IGNORECASE)),
    ("override-instruction",
     re.compile(r"\b(?:disregard|forget|override)\s+(?:everything|all|previous|prior)\b",
                re.IGNORECASE)),
    ("role-override",
     re.compile(r"\byou\s+are\s+now\s+(?:a|an|the|going\s+to)\b", re.IGNORECASE)),
    ("role-override",
     re.compile(r"\bpretend\s+(?:you\s+are|to\s+be|that\s+you)\b", re.IGNORECASE)),
    ("role-override",
     re.compile(r"\bact\s+as\s+(?:if|though)\s+you\s+(?:are|were)\b", re.IGNORECASE)),
    ("jailbreak",
     re.compile(r"\b(?:developer|god|root|admin|debug)\s+mode\b", re.IGNORECASE)),
    ("jailbreak",
     re.compile(r"\b(?:DAN|do\s+anything\s+now)\b", re.IGNORECASE)),
    ("fake-structural-marker",
     re.compile(r"<\|\s*(?:system|im_start|im_end|user|assistant|tool)\s*\|>",
                re.IGNORECASE)),
    ("fake-structural-marker",
     re.compile(r"</?\s*(?:tool_call|tool_use|tool_result|function_call|function_response)\s*>",
                re.IGNORECASE)),
    ("fake-role-marker",
     re.compile(r"(?:^|\n)\s*(?:system|developer|operator)\s*:\s",
                re.IGNORECASE)),
    ("external-network",
     re.compile(r"\b(?:curl|wget|fetch)\s+https?://", re.IGNORECASE)),
    ("templated-url",
     re.compile(r"https?://\S*[?&]\S*=\$?\{?[A-Za-z_][\w\.]*\}?")),
    ("code-execution",
     re.compile(r"\b(?:eval|exec|os\.system|subprocess|child_process)\s*\(",
                re.IGNORECASE)),
    ("encoded-payload-hint",
     re.compile(r"\bbase64[_\-\s]?(?:decode|encoded?)\b", re.IGNORECASE)),
)


_TEXT_FIELDS: tuple[str, ...] = (
    "description",
    "personality",
    "scenario",
    "first_mes",
    "mes_example",
    "system_prompt",
    "post_history_instructions",
)


def scan_card(data: dict[str, Any]) -> list[Finding]:
    """Walk the parsed card and return all suspicious findings."""
    findings: list[Finding] = []
    for field in _TEXT_FIELDS:
        value = data.get(field)
        if isinstance(value, str):
            findings.extend(_scan_text(value, field))
    for i, greeting in enumerate(data.get("alternate_greetings") or []):
        if isinstance(greeting, str):
            findings.extend(_scan_text(greeting, f"alternate_greetings[{i}]"))
    book = data.get("character_book")
    if isinstance(book, dict):
        for j, entry in enumerate(book.get("entries") or []):
            if not isinstance(entry, dict):
                continue
            content = entry.get("content")
            if isinstance(content, str):
                findings.extend(_scan_text(content, f"character_book.entries[{j}].content"))
    return findings


def _scan_text(text: str, field: str) -> list[Finding]:
    findings: list[Finding] = []
    for category, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            findings.append(Finding(category=category, field=field,
                                    snippet=match.group(0)))
    for token in find_long_unbroken_tokens(text):
        findings.append(Finding(category="long-unbroken-token", field=field,
                                snippet=token))
    return findings
