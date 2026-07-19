from pathlib import Path

import pytest

from elementor2gads.postcode import (
    extract_postcode_from_text,
    extract_state_from_text,
    infer_postcode_from_suburb,
    load_au_postcodes,
    normalize_suburb_key,
)


@pytest.fixture
def lookup():
    return {
        "adelaide": {"SA": {"5000"}},
        "brisbane city": {"QLD": {"4000"}},
        "denham court": {"NSW": {"2565"}},
        "exampleville": {"QLD": {"4999"}, "NSW": {"2999"}},
        "lane cove": {"NSW": {"2066"}},
        "north sydney": {"NSW": {"2060"}},
        "o'connor": {"ACT": {"2602"}},
        "raymond terrace": {"NSW": {"2324"}},
        "springfield": {"QLD": {"4300"}, "NSW": {"2250"}},
        "st lucia": {"QLD": {"4067"}},
        "victoria point": {"QLD": {"4165"}},
    }


def test_normalize_suburb_key() -> None:
    assert normalize_suburb_key("  O'Connor (North) ") == "o'connor north"
    assert normalize_suburb_key("O’Connor") == "o'connor"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Brisbane QLD", "QLD"),
        ("Sydney, New South Wales", "NSW"),
        ("Springfield Queensland Australia", "QLD"),
        ("unknown", None),
    ],
)
def test_extract_state(text: str, expected: str | None) -> None:
    assert extract_state_from_text(text) == expected


def test_extract_postcode_uses_last_candidate() -> None:
    assert extract_postcode_from_text("1234 Example Road, Brisbane QLD 4000") == "4000"
    assert extract_postcode_from_text("Brisbane QLD 4000, requested in 2025") == "4000"


def test_exact_match_prefers_state_and_longer_locality(lookup) -> None:
    assert infer_postcode_from_suburb("1 Adelaide Street, Brisbane City QLD", lookup) == "4000"
    assert infer_postcode_from_suburb("North Sydney NSW", lookup) == "2060"


def test_street_name_is_not_mistaken_for_a_misspelled_locality(lookup) -> None:
    assert (
        infer_postcode_from_suburb("1 Adelaide Street, Brisban City QLD", lookup, fuzzy=True)
        == "4000"
    )
    assert (
        infer_postcode_from_suburb("1 Adelaide St, Brisban City QLD", lookup, fuzzy=True) == "4000"
    )


@pytest.mark.parametrize(
    ("text", "postcode"),
    [
        ("Victoria Point QLD", "4165"),
        ("Lane Cove NSW", "2066"),
        ("Raymond Terrace NSW", "2324"),
        ("Denham Court NSW", "2565"),
        ("St Lucia QLD", "4067"),
        ("O’Connor ACT", "2602"),
        ("Springfield Queensland Australia", "4300"),
    ],
)
def test_locality_words_are_not_treated_as_state_or_street_suffixes(
    lookup, text: str, postcode: str
) -> None:
    assert infer_postcode_from_suburb(text, lookup, fuzzy=False) == postcode


def test_ambiguous_locality_requires_state(lookup) -> None:
    assert infer_postcode_from_suburb("Exampleville", lookup) is None
    assert infer_postcode_from_suburb("Exampleville NSW", lookup) == "2999"


def test_multiple_postcodes_in_one_state_are_ambiguous(lookup) -> None:
    lookup["multi"] = {"QLD": {"4000", "4001"}}
    assert infer_postcode_from_suburb("Multi QLD", lookup) is None


def test_fuzzy_match_can_be_disabled(lookup) -> None:
    assert infer_postcode_from_suburb("Brisban City QLD", lookup, fuzzy=True) == "4000"
    assert infer_postcode_from_suburb("Brisban City QLD", lookup) is None


def test_load_postcodes_validates_file(tmp_path: Path) -> None:
    path = tmp_path / "postcodes.csv"
    path.write_text(
        "suburb,state,postcode\nExampleville,Queensland,4999\nBad,XX,123\n",
        encoding="utf-8",
    )
    assert load_au_postcodes(path) == {"exampleville": {"QLD": {"4999"}}}


def test_load_postcodes_rejects_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "postcodes.csv"
    path.write_text("name,postcode\nExampleville,4999\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required columns: state, suburb"):
        load_au_postcodes(path)


def test_load_postcodes_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_au_postcodes(tmp_path / "missing.csv")


def test_load_postcodes_rejects_malformed_csv(tmp_path: Path) -> None:
    path = tmp_path / "postcodes.csv"
    path.write_text('suburb,state,postcode\n"Exampleville,QLD,4999\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid postcode CSV data"):
        load_au_postcodes(path)
