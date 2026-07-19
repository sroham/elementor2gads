import csv
from pathlib import Path

import pytest

from elementor2gads.postcode_data import prepare_postcode_file


def test_prepare_postcode_file_normalizes_filters_and_deduplicates(tmp_path: Path) -> None:
    source = tmp_path / "wide.csv"
    output = tmp_path / "simple.csv"
    source.write_text(
        "locality,state_name,poa_code\n"
        "Exampleville,Queensland,4999\n"
        "Exampleville,Queensland,4999\n"
        "Sampletown,New South Wales,2999\n",
        encoding="utf-8",
    )

    count = prepare_postcode_file(source, output, only_states={"QLD"})

    assert count == 1
    assert list(csv.reader(output.open(encoding="utf-8"))) == [
        ["suburb", "state", "postcode"],
        ["exampleville", "QLD", "4999"],
    ]


def test_prepare_postcode_file_protects_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "wide.csv"
    output = tmp_path / "simple.csv"
    source.write_text("suburb,state,postcode\nExampleville,QLD,4999\n", encoding="utf-8")
    output.touch()
    with pytest.raises(FileExistsError):
        prepare_postcode_file(source, output)


def test_prepare_postcode_file_validates_state_filter(tmp_path: Path) -> None:
    source = tmp_path / "wide.csv"
    source.write_text("suburb,state,postcode\nExampleville,QLD,4999\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown Australian state"):
        prepare_postcode_file(source, tmp_path / "out.csv", only_states={"XX"})


def test_prepare_postcode_file_prefers_suburb_and_preserves_leading_zero(tmp_path: Path) -> None:
    source = tmp_path / "wide.csv"
    output = tmp_path / "simple.csv"
    source.write_text(
        "name,suburb,state,postcode\nWrong Name,Exampleville,NT,800\n",
        encoding="utf-8",
    )

    assert prepare_postcode_file(source, output) == 1
    assert list(csv.reader(output.open(encoding="utf-8")))[1] == ["exampleville", "NT", "0800"]


def test_prepare_postcode_file_rejects_zero_valid_rows(tmp_path: Path) -> None:
    source = tmp_path / "wide.csv"
    source.write_text("suburb,state,postcode\nExampleville,XX,123\n", encoding="utf-8")
    with pytest.raises(ValueError, match="produced no valid postcode rows"):
        prepare_postcode_file(source, tmp_path / "out.csv")


def test_prepare_postcode_file_rejects_duplicate_headings(tmp_path: Path) -> None:
    source = tmp_path / "wide.csv"
    source.write_text(
        "suburb,SUBURB,state,postcode\nExampleville,Other,QLD,4999\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate headings"):
        prepare_postcode_file(source, tmp_path / "out.csv")


def test_prepare_postcode_file_rejects_malformed_csv(tmp_path: Path) -> None:
    source = tmp_path / "wide.csv"
    source.write_text('suburb,state,postcode\n"Exampleville,QLD,4999\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid CSV data"):
        prepare_postcode_file(source, tmp_path / "out.csv")
