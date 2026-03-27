import re
import unicodedata
from typing import List, Tuple


_WHITESPACE_RE = re.compile(r"\s+")
_SIZE_RE = re.compile(r"(\d+)[\s]*?(ml|cl|l)\b", re.IGNORECASE)
_PERCENT_RE = re.compile(r"(\d{1,2}[,.]?\d*)\s*%")
_PACK_RE = re.compile(r"(\d+)\s*(?:-?pack|-?p)\b", re.IGNORECASE)


def normalize_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip())


def strip_accents(text: str) -> str:
    """Return a basic ASCII-fied version of *text*.

    We keep the original label elsewhere; this is only for matching.
    """

    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def tokenize(text: str) -> List[str]:
    text = re.sub(r"[^0-9A-Za-zÅÄÖåäö%]+", " ", text)
    return [t for t in text.strip().split() if t]


def extract_size_ml(text: str) -> Tuple[str, int | None]:
    """Extract a bottle/can size in ml if present.

    Returns the cleaned text (with the size removed) and the parsed size.
    """

    size_ml: int | None = None

    def _repl(match: re.Match[str]) -> str:  # type: ignore[name-defined]
        nonlocal size_ml
        value = int(match.group(1))
        unit = match.group(2).lower()
        if unit == "cl":
            size = value * 10
        elif unit == "l":
            size = value * 1000
        else:  # ml
            size = value
        size_ml = size
        return " "

    cleaned = _SIZE_RE.sub(_repl, text)
    cleaned = normalize_whitespace(cleaned)
    return cleaned, size_ml


def extract_alcohol_percent(text: str) -> Tuple[str, float | None]:
    abv: float | None = None

    def _repl(match: re.Match[str]) -> str:  # type: ignore[name-defined]
        nonlocal abv
        raw = match.group(1).replace(",", ".")
        try:
            abv = float(raw)
        except ValueError:
            abv = None
        return " "

    cleaned = _PERCENT_RE.sub(_repl, text)
    cleaned = normalize_whitespace(cleaned)
    return cleaned, abv


def strip_pack_size(text: str) -> str:
    return normalize_whitespace(_PACK_RE.sub(" ", text))
