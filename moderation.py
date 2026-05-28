"""
moderation.py — Input & output safety layer for ChristianAI

Two-pass approach:
  1. Rule-based keyword / pattern checks (fast, deterministic)
  2. Structural checks on AI output

Returns dicts: { blocked: bool, reason: str }
"""

import re

# ─── Blocked Patterns (Input) ────────────────────────────────────────
# These trigger immediate refusal regardless of context.

_HARD_BLOCK_PATTERNS = [
    # Hate / violence against groups
    r"\b(kill|murder|massacre|exterminate)\s+(all\s+)?(jews|muslims|christians|catholics|infidels|pagans)\b",
    r"\b(white\s+supremac|christian\s+nationalism\s+violence|crusade\s+against)\b",
    r"\bhate\s+(jews|muslims|gays|immigrants)\b",

    # Explicit sexual content
    r"\b(porn|explicit\s+sex|nude|naked\s+(jesus|god|mary))\b",

    # Satanic / blasphemous rewrites of sacred Christian texts
    r"\b(satanic\s+bible\s+verse|rewrite.*scripture.*to\s+(promote|support)\s+(violence|hate|racism))\b",
    r"\brewrite\s+(the\s+)?(lord.s\s+prayer|our\s+father|hail\s+mary|apostles.\s+creed|nicene\s+creed)\s+(for|to\s+worship|dedicated\s+to|in\s+honor\s+of)\s+(satan|lucifer|the\s+devil|baphomet|beelzebub)\b",
    r"\b(prayer|hymn|psalm|worship\s+song)\s+(to|for|dedicated\s+to)\s+(satan|lucifer|the\s+devil|baphomet)\b",
    r"\b(satanic|demonic|devil.s)\s+(version\s+of\s+)?(lord.s\s+prayer|our\s+father|bible\s+verse|scripture|prayer)\b",
    r"\bpraise\s+(satan|lucifer|the\s+devil)\b",
    r"\bworship\s+(satan|lucifer|the\s+devil|baphomet)\b",

    # Scripture rewritten for harmful purposes
    r"\brewrite\s+(john\s*3:16|the\s+gospel|the\s+bible|scripture|the\s+lord.s\s+prayer)\s+(for|to\s+support|to\s+promote)\s+(satan|atheism|communism|nazism|violence|hate)\b",
    r"\b(fake|fabricate|invent|make\s+up)\s+(a\s+)?(bible\s+verse|scripture|gospel)\b",

    # Self-harm facilitation
    r"\b(how\s+to\s+(commit\s+suicide|kill\s+myself|self.harm))\b",

    # Offensive imagery of sacred figures
    r"\b(sexual|nude|naked|pornographic)\s+(image|picture|photo|drawing)\s+of\s+(jesus|god|mary|the\s+pope|apostles)\b",
]

# ─── Soft-Warning Patterns (Input) ──────────────────────────────────
# These block in strict mode, add caution in standard mode.

_SOFT_WARN_PATTERNS = [
    r"\brewrite\s+(the\s+)?(bible|scripture|verse|gospel|lord.s\s+prayer)\b",
    r"\bprove\s+(god\s+)?(does\s+not\s+exist|is\s+fake|is\s+evil)\b",
    r"\bgod\s+(hates|wants\s+us\s+to\s+kill)\b",
    r"\bsupremac",
    r"\b(mock|make\s+fun\s+of|ridicule)\s+(jesus|christianity|the\s+bible|god|the\s+church)\b",
    r"\bwrite\s+a\s+(fake|false|heretical)\s+(sermon|gospel|bible\s+verse|prayer)\b",
]

# ─── Fake Scripture Detection Patterns ──────────────────────────────
_FAKE_BOOKS = [
    "2 hezekiah", "3 john 2", "4 kings", "1 peter 3:22b",
    "gospel of thomas",
    "revelation 22:3[3-9]",
    "2 samuel 24:25b",
    "hezekiah", "jasher chapter 91",
]

_VERSE_REF_PATTERN = re.compile(
    r"\b(\d?\s?[A-Za-z]+(?:\s[A-Za-z]+)?)\s+(\d{1,3}):(\d{1,3})\b"
)

# ─── Human-readable block reasons by category ───────────────────────
_BLOCK_REASONS = {
    "hate":     "This request contains hateful content targeting a group of people. I can't help with that.",
    "satanic":  (
        "I'm not able to rewrite sacred Christian prayers, scripture, or worship content "
        "for Satanic or blasphemous purposes. This goes against the core purpose of ChristianAI. "
        "I'm happy to explain the meaning of prayers like the Lord's Prayer instead. ✝️"
    ),
    "sexual":   "This request involves inappropriate sexual content. I can't help with that.",
    "selfharm": "It sounds like you may be struggling. Please reach out to a trusted person or counsellor.",
    "rewrite":  "I'm not able to rewrite or fabricate scripture or sacred texts. I can help you explore what they genuinely mean.",
    "default":  "I'm not able to help with that request. Please ask me something about Christianity in a constructive way. ✝️",
}


def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_HARD_COMPILED  = _compile_patterns(_HARD_BLOCK_PATTERNS)
_SOFT_COMPILED  = _compile_patterns(_SOFT_WARN_PATTERNS)


def _get_reason(text: str) -> str:
    """Return a human-friendly block reason based on what matched."""
    t = text.lower()
    if any(w in t for w in ["satan", "lucifer", "devil", "baphomet", "demonic", "satanic"]):
        return _BLOCK_REASONS["satanic"]
    if any(w in t for w in ["kill", "murder", "massacre", "hate", "exterminate"]):
        return _BLOCK_REASONS["hate"]
    if any(w in t for w in ["porn", "nude", "naked", "sexual", "explicit"]):
        return _BLOCK_REASONS["sexual"]
    if any(w in t for w in ["suicide", "kill myself", "self-harm", "self harm"]):
        return _BLOCK_REASONS["selfharm"]
    if any(w in t for w in ["rewrite", "fake", "fabricate", "invent", "make up"]):
        return _BLOCK_REASONS["rewrite"]
    return _BLOCK_REASONS["default"]


def moderate_input(text: str, strict: bool = False) -> dict:
    """
    Check user input for policy violations.
    Returns { blocked: bool, reason: str }
    """
    # Hard blocks — always enforced
    for pattern in _HARD_COMPILED:
        if pattern.search(text):
            return {
                "blocked": True,
                "reason": _get_reason(text),
            }

    # Soft blocks — enforced in strict mode only
    if strict:
        for pattern in _SOFT_COMPILED:
            if pattern.search(text):
                return {
                    "blocked": True,
                    "reason": _get_reason(text),
                }

    # Extra: catch direct short phrases not covered by regex
    _DIRECT_BLOCK_PHRASES = [
        "prayer to satan", "prayer for satan", "pray to satan",
        "pray to lucifer", "prayer to lucifer",
        "rewrite the lord's prayer for satan",
        "lord's prayer for satan",
        "lord's prayer to satan",
        "our father for satan",
        "hymn to satan", "hymn to lucifer",
        "write a prayer to the devil",
        "write a sermon proving jesus never existed",
        "write a fake bible verse",
        "generate a fake bible verse",
        "make up a bible verse",
        "fabricate a bible verse",
        "invent a scripture",
    ]
    text_lower = text.lower()
    for phrase in _DIRECT_BLOCK_PHRASES:
        if phrase in text_lower:
            return {
                "blocked": True,
                "reason": _get_reason(text),
            }

    return {"blocked": False, "reason": ""}


def moderate_output(text: str) -> dict:
    """
    Check AI output before showing it to the user.
    """
    for pattern in _HARD_COMPILED:
        if pattern.search(text):
            return {
                "blocked": True,
                "reason": "Output contained potentially harmful content and was blocked.",
            }
    suspicious = _detect_suspicious_output(text)
    return {"blocked": False, "reason": "", "suspicious": suspicious}


def _detect_suspicious_output(text: str) -> list[str]:
    flags = []
    for match in _VERSE_REF_PATTERN.finditer(text):
        book  = match.group(1).strip().lower()
        verse = int(match.group(3))
        if verse > 200:
            flags.append(f"Suspicious reference: {match.group(0)} (verse too high)")
        for fake in _FAKE_BOOKS:
            if fake in book:
                flags.append(f"Non-canonical book reference: {match.group(0)}")
    return flags


def detect_fake_verses(text: str) -> list[str]:
    """Detect suspicious scripture references in user input."""
    flags = []
    for match in _VERSE_REF_PATTERN.finditer(text):
        book  = match.group(1).strip().lower()
        verse = int(match.group(3))
        if verse > 200:
            flags.append(match.group(0))
        for fake in _FAKE_BOOKS:
            if fake in book:
                flags.append(match.group(0))

    KNOWN_FAKE_QUOTES = [
        "god helps those who help themselves",
        "money is the root of all evil",
        "spare the rod spoil the child",
        "cleanliness is next to godliness",
        "this too shall pass",
        "the lion shall lay down with the lamb",
        "god works in mysterious ways",
    ]
    text_lower = text.lower()
    for fake_quote in KNOWN_FAKE_QUOTES:
        if fake_quote in text_lower:
            flags.append(f'Common misquote/non-verse: "{fake_quote}"')

    return flags
