import csv
import hashlib
from pathlib import Path

import pytest

from elementor2gads.convert import (
    ConversionError,
    convert_file,
    normalize_email,
    normalize_phone,
    split_name,
)


def write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" Alice.Example+tag@GMAIL.com ", "alice.example+tag@gmail.com"),
        ("a l i c e@example.com", "alice@example.com"),
        ("", ""),
    ],
)
def test_normalize_email(raw: str, expected: str) -> None:
    assert normalize_email(raw) == expected


def test_google_email_canonicalization_is_opt_in() -> None:
    assert (
        normalize_email("Alice.Example+tag@gmail.com", canonicalize_google=True)
        == "aliceexample@gmail.com"
    )
    assert (
        normalize_email("alice.example+tag@example.com", canonicalize_google=True)
        == "alice.example+tag@example.com"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Dr Alice Mary Example Jr.", ("Alice Mary", "Example")),
        ("Prince", ("Prince", "")),
        ("  Zoe   O'Connor  ", ("Zoe", "O'Connor")),
        ("", ("", "")),
    ],
)
def test_split_name(raw: str, expected: tuple[str, str]) -> None:
    assert split_name(raw) == expected


@pytest.mark.parametrize(
    ("raw", "country", "expected"),
    [
        ("0491 570 006", "AU", "+61491570006"),
        ("(07) 5550 1234", "AU", "+61755501234"),
        ("491 570 006", "AU", "+61491570006"),
        ("61 491 570 006", "AU", "+61491570006"),
        ("+61 (0) 491 570 006", "AU", "+61491570006"),
        ("0011 44 20 7946 0958", "AU", "+442079460958"),
        ("+44 20 7946 0958", "GB", "+442079460958"),
        ("020 7946 0958", "GB", ""),
        ("123", "AU", ""),
    ],
)
def test_normalize_phone(raw: str, country: str, expected: str) -> None:
    assert normalize_phone(raw, country_code=country) == expected


def test_convert_plaintext_with_aliases_and_inferred_postcode(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "nested" / "output.csv"
    postcodes = tmp_path / "postcodes.csv"
    write_csv(
        source,
        [
            ["Full Name", "Email Address", "Mobile Number", "Pickup"],
            ["Alice Example", " Alice@Example.com ", "0491 570 006", "Exampleville QLD"],
        ],
    )
    write_csv(postcodes, [["suburb", "state", "postcode"], ["Exampleville", "QLD", "4999"]])

    stats = convert_file(source, output, postcodes)

    assert stats.rows_read == 1
    assert stats.rows_written == 1
    assert stats.inferred_postcodes == 1
    assert list(csv.reader(output.open(encoding="utf-8"))) == [
        ["Email", "Phone", "First Name", "Last Name", "Country", "Zip"],
        ["alice@example.com", "+61491570006", "alice", "example", "AU", "4999"],
    ]


def test_hash_mode_hashes_identifiers_but_not_country_or_postcode(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    write_csv(
        source,
        [
            ["Name", "Email", "Phone", "Pickup Location"],
            ["Alice Example", "Alice.Example+tag@gmail.com", "0491 570 006", "Brisbane QLD 4000"],
        ],
    )

    stats = convert_file(source, output, hash_identifiers=True)
    row = list(csv.reader(output.open(encoding="utf-8")))[1]

    def digest(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    assert stats.hashed is True
    assert row == [
        digest("aliceexample@gmail.com"),
        digest("+61491570006"),
        digest("alice"),
        digest("example"),
        "AU",
        "4000",
    ]


def test_hash_mode_removes_name_punctuation(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    write_csv(source, [["Name", "Email"], ["Anne-Marie O'Connor", "anne@example.com"]])

    convert_file(source, output, hash_identifiers=True)
    row = list(csv.reader(output.open(encoding="utf-8")))[1]

    assert row[2] == hashlib.sha256(b"annemarie").hexdigest()
    assert row[3] == hashlib.sha256(b"oconnor").hexdigest()


def test_unusable_rows_are_skipped_and_counted(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    write_csv(source, [["Email", "Phone"], ["not-an-email", "123"]])

    stats = convert_file(source, output)

    assert stats.rows_read == 1
    assert stats.rows_written == 0
    assert stats.rows_skipped == 1
    assert stats.invalid_emails == 1
    assert stats.invalid_phones == 1


def test_strict_mode_preserves_existing_output_on_failure(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    write_csv(source, [["Email"], ["not-an-email"]])
    output.write_text("original\n", encoding="utf-8")

    with pytest.raises(ConversionError, match="row 2: invalid email"):
        convert_file(source, output, strict=True, overwrite=True)

    assert output.read_text(encoding="utf-8") == "original\n"


def test_malformed_csv_preserves_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text(
        'Email,Message\nalice@example.com,"unterminated\nbob@example.com,second row\n',
        encoding="utf-8",
    )
    output.write_text("original\n", encoding="utf-8")

    with pytest.raises(ConversionError, match="invalid CSV data"):
        convert_file(source, output, overwrite=True)

    assert output.read_text(encoding="utf-8") == "original\n"


def test_large_elementor_message_field_is_supported(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    write_csv(source, [["Email", "Message"], ["alice@example.com", "x" * 140_000]])

    stats = convert_file(source, output)

    assert stats.rows_written == 1


def test_existing_output_requires_force(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    write_csv(source, [["Email"], ["alice@example.com"]])
    output.touch()
    with pytest.raises(FileExistsError, match="--force"):
        convert_file(source, output)


def test_input_and_output_must_differ(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    write_csv(source, [["Email"], ["alice@example.com"]])
    with pytest.raises(ConversionError, match="must be different"):
        convert_file(source, source, overwrite=True)


def test_rejects_missing_identifier_headings(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    write_csv(source, [["Message"], ["Hello"]])
    with pytest.raises(ConversionError, match="no usable customer identifier"):
        convert_file(source, output)


def test_rejects_unquoted_extra_columns(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text("Email,Pickup Location\nalice@example.com,Brisbane, QLD\n", encoding="utf-8")
    with pytest.raises(ConversionError, match="more values than headers"):
        convert_file(source, output)


def test_rejects_duplicate_headings(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text("Email,email\nalice@example.com,other@example.com\n", encoding="utf-8")
    with pytest.raises(ConversionError, match="duplicate headings: email"):
        convert_file(source, output)


def test_non_au_mode_does_not_invent_an_au_postcode(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    write_csv(
        source,
        [["Email", "Pickup Location"], ["alice@example.com", "London 4000"]],
    )

    convert_file(source, output, default_country="GB")

    assert list(csv.reader(output.open(encoding="utf-8")))[1][-2:] == ["GB", ""]
