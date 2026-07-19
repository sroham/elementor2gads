"""Command-line interface for Elementor to Customer Match conversion."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .convert import ConversionError, convert_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="elementor2gads",
        description="Convert an Elementor form CSV to a Google Ads Customer Match CSV.",
    )
    parser.add_argument("--input", "-i", required=True, type=Path, help="Elementor export CSV")
    parser.add_argument(
        "--output", "-o", required=True, type=Path, help="Customer Match CSV to create"
    )
    parser.add_argument(
        "--au-postcodes",
        type=Path,
        help="optional CSV with suburb,state,postcode columns for address enrichment",
    )
    parser.add_argument("--country", default="AU", help="two-letter country code (default: AU)")
    parser.add_argument(
        "--hash",
        dest="hash_identifiers",
        action="store_true",
        help="SHA-256 hash email, phone, and name fields locally",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="stop at the first invalid email, phone, or unusable record",
    )
    parser.add_argument(
        "--fuzzy-postcodes",
        action="store_true",
        help="opt in to confidence-gated fuzzy suburb matching",
    )
    parser.add_argument("--force", action="store_true", help="replace an existing output file")
    parser.add_argument("--quiet", action="store_true", help="suppress the conversion summary")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        stats = convert_file(
            args.input,
            args.output,
            args.au_postcodes,
            default_country=args.country,
            hash_identifiers=args.hash_identifiers,
            strict=args.strict,
            overwrite=args.force,
            fuzzy_postcodes=args.fuzzy_postcodes,
        )
    except (
        ConversionError,
        FileNotFoundError,
        FileExistsError,
        PermissionError,
        ValueError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"error: could not complete conversion: {error}", file=sys.stderr)
        return 1

    if not args.quiet:
        mode = "pre-hashed" if stats.hashed else "plaintext"
        print(
            f"Wrote {stats.rows_written} {mode} rows to {args.output} "
            f"({stats.rows_skipped} skipped, {stats.inferred_postcodes} postcodes inferred)."
        )
        print(
            "Privacy: the output contains customer data. Keep it out of source control "
            "and delete it securely when no longer needed.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
