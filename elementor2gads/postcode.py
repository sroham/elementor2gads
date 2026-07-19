"""Australian suburb and postcode helpers."""

from __future__ import annotations

import csv
import difflib
import re
import unicodedata
from collections.abc import Iterator
from pathlib import Path

PostcodeLookup = dict[str, dict[str, set[str]]]

STATE_ABBRS = ("ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA")
STATE_FULL = {
    "australian capital territory": "ACT",
    "new south wales": "NSW",
    "northern territory": "NT",
    "queensland": "QLD",
    "south australia": "SA",
    "tasmania": "TAS",
    "victoria": "VIC",
    "western australia": "WA",
}
STREET_TYPES = {
    "av",
    "ave",
    "avenue",
    "blvd",
    "boulevard",
    "cct",
    "circuit",
    "cl",
    "close",
    "ct",
    "court",
    "cr",
    "cres",
    "crescent",
    "dr",
    "drive",
    "hwy",
    "highway",
    "ln",
    "lane",
    "pde",
    "parade",
    "pl",
    "place",
    "rd",
    "road",
    "st",
    "street",
    "tce",
    "terrace",
    "way",
}

_PUNCTUATION_TRANSLATION = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "‛": "'",
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "―": "-",
    }
)


def normalize_suburb_key(value: str) -> str:
    """Normalize a locality while retaining meaningful apostrophes/hyphens."""

    value = (
        unicodedata.normalize("NFKC", value or "").translate(_PUNCTUATION_TRANSLATION).casefold()
    )
    value = re.sub(r"[^\w'\- ]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def normalize_state(value: str) -> str:
    normalized = normalize_suburb_key(value)
    return STATE_FULL.get(normalized, normalized.upper())


def load_au_postcodes(path: Path | None) -> PostcodeLookup:
    """Load a ``suburb,state,postcode`` CSV into a normalized lookup."""

    if path is None:
        return {}
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"postcode CSV not found: {source}")

    lookup: PostcodeLookup = {}
    try:
        with source.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, strict=True)
            if not reader.fieldnames:
                raise ValueError("postcode CSV is empty or has no header row")
            normalized_headings = [name.strip().casefold() for name in reader.fieldnames if name]
            duplicate_headings = sorted(
                heading
                for heading in set(normalized_headings)
                if normalized_headings.count(heading) > 1
            )
            if duplicate_headings:
                raise ValueError(
                    f"postcode CSV contains duplicate headings: {', '.join(duplicate_headings)}"
                )
            headings = {name.strip().casefold(): name for name in reader.fieldnames if name}
            missing = {"suburb", "state", "postcode"} - headings.keys()
            if missing:
                raise ValueError(
                    f"postcode CSV is missing required columns: {', '.join(sorted(missing))}"
                )

            for row in reader:
                extra_values = row.get(None)
                if extra_values and any(str(value).strip() for value in extra_values):
                    raise ValueError("postcode CSV contains more values than headers")
                suburb = normalize_suburb_key(row.get(headings["suburb"]) or "")
                state = normalize_state(row.get(headings["state"]) or "")
                postcode = (row.get(headings["postcode"]) or "").strip()
                if not suburb or state not in STATE_ABBRS or not re.fullmatch(r"\d{4}", postcode):
                    continue
                lookup.setdefault(suburb, {}).setdefault(state, set()).add(postcode)
    except csv.Error as error:
        raise ValueError(f"invalid postcode CSV data: {error}") from error

    if not lookup:
        raise ValueError("postcode CSV contains no valid suburb/state/postcode rows")
    return lookup


def extract_state_from_text(value: str) -> str | None:
    """Extract an Australian state abbreviation or full state name."""

    text = normalize_suburb_key(value)
    candidates: list[tuple[int, str]] = []
    for abbreviation in STATE_ABBRS:
        for match in re.finditer(rf"(?i)(?<![A-Za-z]){abbreviation}(?![A-Za-z])", value or ""):
            candidates.append((match.start(), abbreviation))
    for full_name, abbreviation in STATE_FULL.items():
        for match in re.finditer(rf"(?<!\w){re.escape(full_name)}(?!\w)", text):
            tail = text[match.end() :]
            if re.fullmatch(r"[\s,;()/.\-]*(?:\d{4})?[\s,;()/.\-]*", tail):
                candidates.append((match.start(), abbreviation))
    return max(candidates, default=(0, None), key=lambda item: item[0])[1]


def extract_postcode_from_text(value: str) -> str | None:
    """Extract an Australian postcode candidate from address-like text."""

    state_terms = [re.escape(abbreviation) for abbreviation in STATE_ABBRS]
    state_terms.extend(re.escape(name) for name in STATE_FULL)
    state_pattern = "|".join(sorted(state_terms, key=len, reverse=True))
    state_postcodes = re.findall(
        rf"(?i)(?<![A-Za-z])(?:{state_pattern})(?![A-Za-z])"
        r"[\s,;()/.\-]*(\d{4})(?!\d)",
        value or "",
    )
    if state_postcodes:
        return state_postcodes[-1]
    matches = re.findall(r"(?<!\d)(\d{4})(?!\d)", value or "")
    return matches[-1] if matches else None


def _iter_ngrams(words: list[str], max_n: int) -> Iterator[tuple[str, int, int]]:
    for size in range(min(max_n, len(words)), 0, -1):
        for start in range(0, len(words) - size + 1):
            yield " ".join(words[start : start + size]), size, start


def _choose_postcode(states: dict[str, set[str]], state_hint: str | None) -> str | None:
    if state_hint:
        postcodes = states.get(state_hint, set())
        return next(iter(postcodes)) if len(postcodes) == 1 else None
    all_postcodes = {postcode for postcodes in states.values() for postcode in postcodes}
    return next(iter(all_postcodes)) if len(all_postcodes) == 1 else None


def _tokenize(value: str) -> list[str]:
    normalized = normalize_suburb_key(value)
    return re.findall(r"[\w][\w'\-]*", normalized, flags=re.UNICODE)


def infer_postcode_from_suburb(
    text: str,
    au_lookup: PostcodeLookup,
    *,
    fuzzy: bool = False,
    cutoff: float = 0.89,
) -> str | None:
    """Resolve a postcode from an address-like string.

    Exact suburb matches are preferred. Ambiguous cross-state matches require a
    state hint instead of silently choosing an arbitrary postcode.
    """

    if not au_lookup or not (text or "").strip():
        return None

    state_hint = extract_state_from_text(text)
    words = _tokenize(text)
    if not words:
        return None
    max_words = max(len(key.split()) for key in au_lookup)
    last_street_index = max(
        (index for index, word in enumerate(words) if index > 0 and word in STREET_TYPES),
        default=-1,
    )

    exact: list[tuple[bool, int, int, str]] = []
    for phrase, size, start in _iter_ngrams(words, max_words):
        if last_street_index >= 0 and start <= last_street_index:
            continue
        states = au_lookup.get(phrase)
        if not states:
            continue
        state_match = bool(state_hint and state_hint in states)
        exact.append((state_match, size, start, phrase))

    if exact:
        exact.sort(key=lambda item: (-int(item[0]), -item[1], -item[2], item[3]))
        for _, _, _, phrase in exact:
            postcode = _choose_postcode(au_lookup[phrase], state_hint)
            if postcode:
                return postcode

    if not fuzzy:
        return None

    fuzzy_words = words[last_street_index + 1 :] if last_street_index >= 0 else words
    candidate_words = [
        word for word in fuzzy_words if not word.isdigit() and word not in STREET_TYPES
    ]
    if not candidate_words:
        return None

    fuzzy_candidates: list[tuple[float, int, int, str]] = []
    pools: dict[tuple[str, str | None], list[str]] = {}
    for query, size, start in _iter_ngrams(candidate_words, max_words):
        if len(query) < 4 or (size == 1 and query in STREET_TYPES):
            continue
        pool_key = (query[0], state_hint)
        if pool_key not in pools:
            pools[pool_key] = [
                key
                for key, states in au_lookup.items()
                if key.startswith(query[0]) and (not state_hint or state_hint in states)
            ]
        pool = pools[pool_key]
        if not pool:
            continue
        for match in difflib.get_close_matches(query, pool, n=2, cutoff=cutoff):
            ratio = difflib.SequenceMatcher(None, query, match).ratio()
            fuzzy_candidates.append((ratio, size, start, match))

    fuzzy_candidates.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
    for _, _, _, suburb in fuzzy_candidates:
        postcode = _choose_postcode(au_lookup[suburb], state_hint)
        if postcode:
            return postcode
    return None
