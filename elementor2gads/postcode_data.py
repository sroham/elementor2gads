"""Prepare third-party locality data for use by the postcode resolver."""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path

from .postcode import STATE_ABBRS, normalize_state, normalize_suburb_key

LOCALITY_HEADINGS = ("suburb", "locality")
STATE_HEADINGS = ("state", "state_code", "state_name", "state_code_2021", "state_code_2016")
POSTCODE_HEADINGS = ("postcode", "post_code", "poa_code", "poa", "poa_name")


def _find_column(headers: Iterable[str], candidates: Sequence[str]) -> str | None:
    available = {header.strip().casefold(): header for header in headers if header}
    return next((available[candidate] for candidate in candidates if candidate in available), None)


def prepare_postcode_file(
    input_csv: Path,
    output_csv: Path,
    *,
    only_states: set[str] | None = None,
    overwrite: bool = False,
) -> int:
    """Convert a wide locality CSV to ``suburb,state,postcode``.

    The caller remains responsible for confirming that the source dataset's
    licence permits the intended use and redistribution.
    """

    source_path = Path(input_csv)
    output_path = Path(output_csv)
    if os.path.normcase(os.path.realpath(source_path)) == os.path.normcase(
        os.path.realpath(output_path)
    ):
        raise ValueError("input and output paths must be different")
    if not source_path.is_file():
        raise FileNotFoundError(f"input CSV not found: {source_path}")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {output_path} (use --force to replace it)")

    states = {normalize_state(value) for value in only_states} if only_states else None
    invalid_states = (states or set()) - set(STATE_ABBRS)
    if invalid_states:
        raise ValueError(f"unknown Australian state codes: {', '.join(sorted(invalid_states))}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    kept = 0
    try:
        with source_path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source, strict=True)
            if not reader.fieldnames:
                raise ValueError("input CSV is empty or has no header row")
            normalized_headings = [name.strip().casefold() for name in reader.fieldnames if name]
            duplicate_headings = sorted(
                heading
                for heading in set(normalized_headings)
                if normalized_headings.count(heading) > 1
            )
            if duplicate_headings:
                raise ValueError(
                    f"input CSV contains duplicate headings: {', '.join(duplicate_headings)}"
                )
            locality_column = _find_column(reader.fieldnames, LOCALITY_HEADINGS)
            state_column = _find_column(reader.fieldnames, STATE_HEADINGS)
            postcode_column = _find_column(reader.fieldnames, POSTCODE_HEADINGS)
            if not all((locality_column, state_column, postcode_column)):
                raise ValueError(
                    "could not identify locality, state, and postcode columns "
                    f"(found: {locality_column}, {state_column}, {postcode_column})"
                )

            with tempfile.NamedTemporaryFile(
                mode="w",
                newline="",
                encoding="utf-8",
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                dir=output_path.parent,
                delete=False,
            ) as destination:
                temporary_name = destination.name
                writer = csv.writer(destination, lineterminator="\n")
                writer.writerow(("suburb", "state", "postcode"))
                seen = set()
                for row in reader:
                    extra_values = row.get(None)
                    if extra_values and any(str(value).strip() for value in extra_values):
                        raise ValueError("input CSV contains more values than headers")
                    suburb = normalize_suburb_key(row.get(locality_column) or "")
                    state = normalize_state(row.get(state_column) or "")
                    raw_postcode = (row.get(postcode_column) or "").strip()
                    if re.fullmatch(r"\d{1,4}", raw_postcode):
                        postcode = raw_postcode.zfill(4)
                    else:
                        match = re.search(r"(?<!\d)(\d{4})(?!\d)", raw_postcode)
                        postcode = match.group(1) if match else ""
                    if not suburb or state not in STATE_ABBRS or not postcode:
                        continue
                    if states and state not in states:
                        continue
                    item = (suburb, state, postcode)
                    if item in seen:
                        continue
                    seen.add(item)
                    writer.writerow(item)
                    kept += 1

        if kept == 0:
            raise ValueError("input CSV produced no valid postcode rows")
        os.replace(temporary_name, output_path)
        temporary_name = None
    except csv.Error as error:
        raise ValueError(f"invalid CSV data: {error}") from error
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)
    return kept


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="elementor2gads-postcodes",
        description="Convert a locality CSV into suburb,state,postcode format.",
    )
    parser.add_argument("--input", "-i", required=True, type=Path, help="source locality CSV")
    parser.add_argument(
        "--output", "-o", required=True, type=Path, help="postcode lookup CSV to create"
    )
    parser.add_argument("--only-states", help="comma-separated Australian state codes")
    parser.add_argument("--force", action="store_true", help="replace an existing output file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    only_states = (
        {value.strip() for value in args.only_states.split(",") if value.strip()}
        if args.only_states
        else None
    )
    try:
        count = prepare_postcode_file(
            args.input,
            args.output,
            only_states=only_states,
            overwrite=args.force,
        )
    except (
        csv.Error,
        FileNotFoundError,
        FileExistsError,
        PermissionError,
        ValueError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {count} postcode rows to {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
