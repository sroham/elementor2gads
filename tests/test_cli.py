import csv
from pathlib import Path

from elementor2gads.cli import main
from elementor2gads.postcode_data import main as postcode_main


def test_cli_converts_and_prints_privacy_notice(tmp_path: Path, capsys) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text("Email\nalice@example.com\n", encoding="utf-8")

    assert main(["--input", str(source), "--output", str(output)]) == 0

    captured = capsys.readouterr()
    assert "Wrote 1 plaintext rows" in captured.out
    assert "Privacy:" in captured.err
    assert next(csv.reader(output.open(encoding="utf-8"))) == [
        "Email",
        "Phone",
        "First Name",
        "Last Name",
        "Country",
        "Zip",
    ]


def test_cli_returns_nonzero_for_missing_input(tmp_path: Path, capsys) -> None:
    result = main(["--input", str(tmp_path / "missing.csv"), "--output", str(tmp_path / "out.csv")])
    assert result == 1
    assert "input CSV not found" in capsys.readouterr().err


def test_cli_reports_malformed_csv_without_a_traceback(tmp_path: Path, capsys) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text('Email,Message\nalice@example.com,"unterminated\n', encoding="utf-8")

    assert main(["--input", str(source), "--output", str(output)]) == 1

    captured = capsys.readouterr()
    assert "invalid CSV data" in captured.err
    assert "Traceback" not in captured.err
    assert not output.exists()


def test_postcode_cli(tmp_path: Path) -> None:
    source = tmp_path / "wide.csv"
    output = tmp_path / "postcodes.csv"
    source.write_text("suburb,state,postcode\nExampleville,QLD,4999\n", encoding="utf-8")
    assert postcode_main(["--input", str(source), "--output", str(output)]) == 0
    assert output.exists()
