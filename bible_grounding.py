"""
bible_grounding.py — Scripture extraction and grounding for ChristianAI

Responsibilities:
  - Extract scripture references from AI responses
  - Flag potential verse hallucinations
  - Format citations consistently
  - Provide a reference verse database for common passages (offline fallback)
"""

import re
from typing import NamedTuple

# ─── Bible Book Metadata ─────────────────────────────────────────────
# Maps lowercase book name variants → (canonical name, max chapters)
# Used to validate references and catch hallucinations.

BIBLE_BOOKS: dict[str, tuple[str, int]] = {
    # Old Testament
    "genesis": ("Genesis", 50), "gen": ("Genesis", 50),
    "exodus": ("Exodus", 40), "exo": ("Exodus", 40), "ex": ("Exodus", 40),
    "leviticus": ("Leviticus", 27), "lev": ("Leviticus", 27),
    "numbers": ("Numbers", 36), "num": ("Numbers", 36),
    "deuteronomy": ("Deuteronomy", 34), "deut": ("Deuteronomy", 34), "dt": ("Deuteronomy", 34),
    "joshua": ("Joshua", 24), "josh": ("Joshua", 24),
    "judges": ("Judges", 21), "judg": ("Judges", 21),
    "ruth": ("Ruth", 4),
    "1 samuel": ("1 Samuel", 31), "1sam": ("1 Samuel", 31),
    "2 samuel": ("2 Samuel", 24), "2sam": ("2 Samuel", 24),
    "1 kings": ("1 Kings", 22), "1kgs": ("1 Kings", 22),
    "2 kings": ("2 Kings", 25), "2kgs": ("2 Kings", 25),
    "1 chronicles": ("1 Chronicles", 29), "1chr": ("1 Chronicles", 29),
    "2 chronicles": ("2 Chronicles", 36), "2chr": ("2 Chronicles", 36),
    "ezra": ("Ezra", 10),
    "nehemiah": ("Nehemiah", 13), "neh": ("Nehemiah", 13),
    "esther": ("Esther", 10),
    "job": ("Job", 42),
    "psalms": ("Psalms", 150), "psalm": ("Psalms", 150), "ps": ("Psalms", 150),
    "proverbs": ("Proverbs", 31), "prov": ("Proverbs", 31),
    "ecclesiastes": ("Ecclesiastes", 12), "ecc": ("Ecclesiastes", 12),
    "song of solomon": ("Song of Solomon", 8), "song": ("Song of Solomon", 8),
    "isaiah": ("Isaiah", 66), "isa": ("Isaiah", 66),
    "jeremiah": ("Jeremiah", 52), "jer": ("Jeremiah", 52),
    "lamentations": ("Lamentations", 5), "lam": ("Lamentations", 5),
    "ezekiel": ("Ezekiel", 48), "ezek": ("Ezekiel", 48),
    "daniel": ("Daniel", 12), "dan": ("Daniel", 12),
    "hosea": ("Hosea", 14), "hos": ("Hosea", 14),
    "joel": ("Joel", 3),
    "amos": ("Amos", 9),
    "obadiah": ("Obadiah", 1), "obad": ("Obadiah", 1),
    "jonah": ("Jonah", 4), "jon": ("Jonah", 4),
    "micah": ("Micah", 7), "mic": ("Micah", 7),
    "nahum": ("Nahum", 3), "nah": ("Nahum", 3),
    "habakkuk": ("Habakkuk", 3), "hab": ("Habakkuk", 3),
    "zephaniah": ("Zephaniah", 3), "zeph": ("Zephaniah", 3),
    "haggai": ("Haggai", 2), "hag": ("Haggai", 2),
    "zechariah": ("Zechariah", 14), "zech": ("Zechariah", 14),
    "malachi": ("Malachi", 4), "mal": ("Malachi", 4),
    # New Testament
    "matthew": ("Matthew", 28), "matt": ("Matthew", 28), "mt": ("Matthew", 28),
    "mark": ("Mark", 16), "mk": ("Mark", 16),
    "luke": ("Luke", 24), "lk": ("Luke", 24),
    "john": ("John", 21), "jn": ("John", 21),
    "acts": ("Acts", 28),
    "romans": ("Romans", 16), "rom": ("Romans", 16),
    "1 corinthians": ("1 Corinthians", 16), "1cor": ("1 Corinthians", 16),
    "2 corinthians": ("2 Corinthians", 13), "2cor": ("2 Corinthians", 13),
    "galatians": ("Galatians", 6), "gal": ("Galatians", 6),
    "ephesians": ("Ephesians", 6), "eph": ("Ephesians", 6),
    "philippians": ("Philippians", 4), "phil": ("Philippians", 4),
    "colossians": ("Colossians", 4), "col": ("Colossians", 4),
    "1 thessalonians": ("1 Thessalonians", 5), "1thess": ("1 Thessalonians", 5),
    "2 thessalonians": ("2 Thessalonians", 3), "2thess": ("2 Thessalonians", 3),
    "1 timothy": ("1 Timothy", 6), "1tim": ("1 Timothy", 6),
    "2 timothy": ("2 Timothy", 4), "2tim": ("2 Timothy", 4),
    "titus": ("Titus", 3),
    "philemon": ("Philemon", 1), "phlm": ("Philemon", 1),
    "hebrews": ("Hebrews", 13), "heb": ("Hebrews", 13),
    "james": ("James", 5), "jas": ("James", 5),
    "1 peter": ("1 Peter", 5), "1pet": ("1 Peter", 5),
    "2 peter": ("2 Peter", 3), "2pet": ("2 Peter", 3),
    "1 john": ("1 John", 5), "1jn": ("1 John", 5),
    "2 john": ("2 John", 1), "2jn": ("2 John", 1),
    "3 john": ("3 John", 1), "3jn": ("3 John", 1),
    "jude": ("Jude", 1),
    "revelation": ("Revelation", 22), "rev": ("Revelation", 22),
}

# ─── Verse Reference Regex ───────────────────────────────────────────
# Matches "Book Ch:V" or "Book Ch:V-V2" with optional translation tag
_REF_RE = re.compile(
    r"\b(\d?\s?[A-Za-z]+(?:\s[A-Za-z]+)?)\s+(\d{1,3}):(\d{1,3})(?:-\d{1,3})?"
    r"(?:\s*\(([A-Z]{2,5})\))?",
    re.IGNORECASE,
)

# ─── Well-known verses (offline reference) ───────────────────────────
KNOWN_VERSES: dict[str, str] = {
    "John 3:16":       "For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life. (NIV)",
    "Romans 8:28":     "And we know that in all things God works for the good of those who love him, who have been called according to his purpose. (NIV)",
    "Psalm 23:1":      "The Lord is my shepherd, I lack nothing. (NIV)",
    "Jeremiah 29:11":  "For I know the plans I have for you, declares the Lord, plans to prosper you and not to harm you, plans to give you hope and a future. (NIV)",
    "Philippians 4:13":"I can do all this through him who gives me strength. (NIV)",
    "Isaiah 40:31":    "But those who hope in the Lord will renew their strength. They will soar on wings like eagles; they will run and not grow weary, they will walk and not be faint. (NIV)",
    "Matthew 28:19":   "Therefore go and make disciples of all nations, baptizing them in the name of the Father and of the Son and of the Holy Spirit. (NIV)",
    "Romans 3:23":     "For all have sinned and fall short of the glory of God. (NIV)",
    "Ephesians 2:8":   "For it is by grace you have been saved, through faith—and this is not from yourselves, it is the gift of God. (NIV)",
    "John 14:6":       "Jesus answered, 'I am the way and the truth and the life. No one comes to the Father except through me.' (NIV)",
    "Proverbs 3:5":    "Trust in the Lord with all your heart and lean not on your own understanding. (NIV)",
    "Matthew 5:9":     "Blessed are the peacemakers, for they will be called children of God. (NIV)",
    "1 Corinthians 13:4": "Love is patient, love is kind. It does not envy, it does not boast, it is not proud. (NIV)",
    "Psalm 46:10":     "He says, 'Be still, and know that I am God.' (NIV)",
    "Romans 6:23":     "For the wages of sin is death, but the gift of God is eternal life in Christ Jesus our Lord. (NIV)",
}


class VerseRef(NamedTuple):
    raw: str          # original matched text
    book: str         # canonical book name
    chapter: int
    verse: int
    translation: str
    valid: bool       # passes basic structural validation
    warning: str      # non-empty if suspicious


def _normalise_book(raw_book: str) -> tuple[str, int] | None:
    """Return (canonical_name, max_chapters) or None if unrecognised."""
    key = raw_book.strip().lower()
    # Try direct match
    if key in BIBLE_BOOKS:
        return BIBLE_BOOKS[key]
    # Try without leading digit space (e.g. "1samuel" -> "1 samuel")
    spaced = re.sub(r"^(\d)", r"\1 ", key)
    if spaced in BIBLE_BOOKS:
        return BIBLE_BOOKS[spaced]
    return None


def validate_ref(book_raw: str, chapter: int, verse: int) -> tuple[bool, str]:
    """Return (is_valid, warning_message)."""
    book_info = _normalise_book(book_raw)
    if book_info is None:
        return False, f"Unrecognised book: {book_raw}"
    canonical, max_chapters = book_info
    if chapter > max_chapters:
        return False, f"{canonical} only has {max_chapters} chapters (cited ch. {chapter})"
    if verse == 0:
        return False, "Verse numbers start at 1"
    if verse > 200:
        return False, f"Verse {verse} is implausibly high"
    return True, ""


def extract_refs(text: str) -> list[VerseRef]:
    """Pull all scripture references out of a text string and validate them."""
    refs = []
    for match in _REF_RE.finditer(text):
        book_raw   = match.group(1).strip()
        chapter    = int(match.group(2))
        verse      = int(match.group(3))
        translation = match.group(4) or ""
        valid, warning = validate_ref(book_raw, chapter, verse)
        refs.append(VerseRef(
            raw=match.group(0),
            book=book_raw,
            chapter=chapter,
            verse=verse,
            translation=translation,
            valid=valid,
            warning=warning,
        ))
    return refs


def ground_scripture(ai_text: str) -> list[str]:
    """
    Given the full AI response text, return a list of grounded verse strings
    to display in the UI.

    - Validates each reference found.
    - Looks up known verses from local DB.
    - Flags invalid/suspicious references.
    """
    refs = extract_refs(ai_text)
    grounded: list[str] = []

    for ref in refs:
        canonical_key = f"{ref.book.title()} {ref.chapter}:{ref.verse}"
        if not ref.valid:
            grounded.append(
                f"⚠️ Potentially invalid reference: {ref.raw} — {ref.warning}"
            )
        elif canonical_key in KNOWN_VERSES:
            grounded.append(f"📖 {canonical_key} — {KNOWN_VERSES[canonical_key]}")
        else:
            # Reference looks structurally valid but not in local DB
            grounded.append(
                f"📖 {canonical_key} — "
                f"*(Verify at Bible.com or YouVersion for exact wording)*"
            )

    return grounded


def detect_fake_verses(user_text: str) -> list[str]:
    """
    Public API: detect suspicious scripture in user input.
    Returns list of warning strings (empty = all OK).
    """
    refs = extract_refs(user_text)
    warnings = []

    # Common misquotes
    MISQUOTES = {
        "god helps those who help themselves": "Benjamin Franklin, not the Bible",
        "money is the root of all evil": "1 Tim 6:10 says 'love of money', not 'money'",
        "spare the rod spoil the child": "paraphrase of Proverbs 13:24, not a direct quote",
        "cleanliness is next to godliness": "not in the Bible — often attributed to John Wesley",
        "this too shall pass": "not a Bible verse",
        "the lion shall lay down with the lamb": "Isaiah 11:6 says 'wolf', not 'lion'",
        "god works in mysterious ways": "not a Bible verse — derived from William Cowper hymn",
    }
    text_lower = user_text.lower()
    for phrase, correction in MISQUOTES.items():
        if phrase in text_lower:
            warnings.append(f'Common misquote — "{phrase}" ({correction})')

    for ref in refs:
        if not ref.valid:
            warnings.append(f"Suspicious reference in prompt: {ref.raw} — {ref.warning}")

    return warnings
