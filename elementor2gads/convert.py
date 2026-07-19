"""Elementor export to Google Ads Customer Match conversion."""

from __future__ import annotations

import csv
import hashlib
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .postcode import (
    PostcodeLookup,
    extract_postcode_from_text,
    infer_postcode_from_suburb,
    load_au_postcodes,
)

OUTPUT_FIELDS = ("Email", "Phone", "First Name", "Last Name", "Country", "Zip")

INPUT_ALIASES: Mapping[str, Sequence[str]] = {
    "name": ("Name", "Full Name", "Your Name"),
    "email": ("Email", "Email Address", "E-mail"),
    "phone": ("Phone", "Phone Number", "Mobile", "Mobile Number", "Telephone"),
    "pickup": ("Pickup Location", "Pickup", "Pickup Address", "Address", "Suburb"),
}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")
_NAME_PREFIXES = {"dr", "miss", "mr", "mrs", "ms", "prof"}
_NAME_SUFFIXES = {"ii", "iii", "iv", "jr", "sr"}
MAX_CSV_FIELD_SIZE = 10 * 1024 * 1024


class ConversionError(ValueError):
    """Raised when an input cannot be safely converted."""


@dataclass(frozen=True)
class ConversionStats:
    """Aggregate conversion results; never includes customer values."""

    rows_read: int
    rows_written: int
    rows_skipped: int
    invalid_emails: int
    invalid_phones: int
    explicit_postcodes: int
    inferred_postcodes: int
    unresolved_postcodes: int
    incomplete_addresses: int
    hashed: bool


def _collapse_whitespace(value: str) -> str:
    return " ".join((value or "").split())


def normalize_email(email: str, *, canonicalize_google: bool = False) -> str:
    """Normalize an email for Customer Match, optionally canonicalizing Gmail."""

    value = re.sub(r"\s+", "", email or "").lower()
    if not canonicalize_google or "@" not in value:
        return value

    local, domain = value.rsplit("@", 1)
    if domain in {"gmail.com", "googlemail.com"}:
        local = local.split("+", 1)[0].replace(".", "")
    return f"{local}@{domain}"


def normalize_name(value: str) -> str:
    """Lowercase a name and collapse surrounding/intermediate whitespace."""

    return _collapse_whitespace(value).lower()


def normalize_name_for_hash(value: str) -> str:
    """Apply Google's stricter API-compatible name normalization."""

    return re.sub(r"[^\w\s]", "", normalize_name(value), flags=re.UNICODE)


def split_name(full_name: str) -> tuple[str, str]:
    """Split a display name into given and family names.

    Titles and common suffixes are removed because Google asks uploaders not to
    include them. Middle names remain with the given name.
    """

    parts = _collapse_whitespace(full_name).split()
    if len(parts) > 1 and parts[0].rstrip(".").lower() in _NAME_PREFIXES:
        parts.pop(0)
    if len(parts) > 1 and parts[-1].rstrip(".").lower() in _NAME_SUFFIXES:
        parts.pop()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def _valid_e164(value: str) -> str:
    return value if _E164_RE.fullmatch(value) else ""


def normalize_phone(phone: str, *, country_code: str = "AU") -> str:
    """Normalize a phone to strict E.164.

    Australian national numbers can be inferred. For other countries, callers
    must provide an explicit international number beginning with ``+`` or ``00``.
    Invalid or ambiguous values return an empty string.
    """

    value = (phone or "").strip()
    if not value:
        return ""

    value = re.sub(r"(?i)(?:ext\.?|extension|x)\s*\d+\s*$", "", value)
    if value.startswith("+"):
        digits = re.sub(r"\D", "", value[1:])
        if digits.startswith("610"):
            digits = "61" + digits[3:]
        return _valid_e164("+" + digits)

    digits = re.sub(r"\D", "", value)
    if digits.startswith("0011"):
        return _valid_e164("+" + digits[4:])
    if digits.startswith("00"):
        return _valid_e164("+" + digits[2:])

    country = normalize_country(country_code)
    if country != "AU":
        return ""
    if digits.startswith("61"):
        if digits.startswith("610"):
            digits = "61" + digits[3:]
        return _valid_e164("+" + digits)
    if len(digits) == 10 and digits.startswith("0"):
        return _valid_e164("+61" + digits[1:])
    if len(digits) == 9 and digits[0] in "23478":
        return _valid_e164("+61" + digits)
    return ""


def to_e164_au(phone: str) -> str:
    """Backward-compatible wrapper for Australian phone normalization."""

    return normalize_phone(phone, country_code="AU")


def normalize_country(country_code: str) -> str:
    """Return an uppercase, two-ASCII-letter country code."""

    value = (country_code or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", value):
        raise ConversionError("country must contain exactly two ASCII letters")
    return value


def sha256_hex(value: str) -> str:
    """Return Google's supported lowercase hexadecimal SHA-256 encoding."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value else ""


def _header_key(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def _resolve_columns(fieldnames: Sequence[str]) -> dict[str, str | None]:
    available = {_header_key(name): name for name in fieldnames if name}
    return {
        logical: next(
            (available[_header_key(alias)] for alias in aliases if _header_key(alias) in available),
            None,
        )
        for logical, aliases in INPUT_ALIASES.items()
    }


def _validate_columns(columns: Mapping[str, str | None]) -> None:
    has_direct_identifier = bool(columns["email"] or columns["phone"])
    has_address_identifier = bool(columns["name"] and columns["pickup"])
    if has_direct_identifier or has_address_identifier:
        return
    accepted = "; ".join(f"{key}: {', '.join(values)}" for key, values in INPUT_ALIASES.items())
    raise ConversionError(
        f"no usable customer identifier columns found; accepted headings are {accepted}"
    )


def _value(row: Mapping[str | None, str | None], column: str | None) -> str:
    return (row.get(column) or "") if column else ""


def _same_file(first: Path, second: Path) -> bool:
    return os.path.normcase(os.path.realpath(first)) == os.path.normcase(os.path.realpath(second))


def convert_file(
    input_csv: Path,
    output_csv: Path,
    au_postcodes_csv: Path | None = None,
    default_country: str = "AU",
    *,
    hash_identifiers: bool = False,
    strict: bool = False,
    overwrite: bool = False,
    fuzzy_postcodes: bool = False,
) -> ConversionStats:
    """Convert an Elementor CSV to a manual Google Ads Customer Match CSV.

    The output is written atomically. Existing files are protected unless
    ``overwrite`` is explicitly enabled.
    """

    input_path = Path(input_csv)
    output_path = Path(output_csv)
    postcode_path = Path(au_postcodes_csv) if au_postcodes_csv else None

    if _same_file(input_path, output_path):
        raise ConversionError("input and output paths must be different")
    if not input_path.is_file():
        raise FileNotFoundError(f"input CSV not found: {input_path}")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {output_path} (use --force to replace it)")

    country = normalize_country(default_country)
    if postcode_path and country != "AU":
        raise ConversionError("--au-postcodes can only be used when --country is AU")
    lookup: PostcodeLookup = load_au_postcodes(postcode_path) if postcode_path else {}
    output_path.parent.mkdir(parents=True, exist_ok=True)

    counters = {
        "rows_read": 0,
        "rows_written": 0,
        "rows_skipped": 0,
        "invalid_emails": 0,
        "invalid_phones": 0,
        "explicit_postcodes": 0,
        "inferred_postcodes": 0,
        "unresolved_postcodes": 0,
        "incomplete_addresses": 0,
    }

    csv.field_size_limit(max(csv.field_size_limit(), MAX_CSV_FIELD_SIZE))
    temporary_name: str | None = None
    try:
        with input_path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source, strict=True)
            if not reader.fieldnames:
                raise ConversionError("input CSV is empty or has no header row")
            normalized_headings = [_header_key(name) for name in reader.fieldnames if name]
            duplicate_headings = sorted(
                heading
                for heading in set(normalized_headings)
                if normalized_headings.count(heading) > 1
            )
            if duplicate_headings:
                raise ConversionError(
                    f"input CSV contains duplicate headings: {', '.join(duplicate_headings)}"
                )
            columns = _resolve_columns(reader.fieldnames)
            _validate_columns(columns)

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
                writer.writerow(OUTPUT_FIELDS)

                for line_number, row in enumerate(reader, start=2):
                    extra_values = row.get(None)
                    if extra_values and any(str(value).strip() for value in extra_values):
                        raise ConversionError(
                            f"row {line_number}: more values than headers; "
                            "quote fields that contain commas"
                        )
                    if not any(
                        (value or "").strip() for value in row.values() if value is not None
                    ):
                        continue
                    counters["rows_read"] += 1

                    raw_email = _value(row, columns["email"])
                    raw_phone = _value(row, columns["phone"])
                    raw_name = _value(row, columns["name"])
                    pickup = _value(row, columns["pickup"])

                    email = normalize_email(raw_email)
                    if email and not _EMAIL_RE.fullmatch(email):
                        counters["invalid_emails"] += 1
                        if strict:
                            raise ConversionError(f"row {line_number}: invalid email address")
                        email = ""

                    phone = normalize_phone(raw_phone, country_code=country)
                    if raw_phone.strip() and not phone:
                        counters["invalid_phones"] += 1
                        if strict:
                            raise ConversionError(
                                f"row {line_number}: phone cannot be normalized to E.164"
                            )

                    first, last = split_name(raw_name)
                    first = normalize_name(first)
                    last = normalize_name(last)

                    postcode = extract_postcode_from_text(pickup) if country == "AU" else None
                    if postcode:
                        counters["explicit_postcodes"] += 1
                    elif pickup and lookup:
                        postcode = infer_postcode_from_suburb(
                            pickup,
                            lookup,
                            fuzzy=fuzzy_postcodes,
                        )
                        if postcode:
                            counters["inferred_postcodes"] += 1
                    if pickup and not postcode:
                        counters["unresolved_postcodes"] += 1

                    address_complete = bool(first and last and country and postcode)
                    if not address_complete:
                        counters["incomplete_addresses"] += 1

                    if not (email or phone or address_complete):
                        counters["rows_skipped"] += 1
                        if strict:
                            raise ConversionError(
                                f"row {line_number}: no usable Customer Match identifier"
                            )
                        continue

                    if hash_identifiers:
                        email = sha256_hex(normalize_email(email, canonicalize_google=True))
                        phone = sha256_hex(phone)
                        first = sha256_hex(normalize_name_for_hash(first))
                        last = sha256_hex(normalize_name_for_hash(last))

                    writer.writerow((email, phone, first, last, country, postcode or ""))
                    counters["rows_written"] += 1

        os.replace(temporary_name, output_path)
        temporary_name = None
    except csv.Error as error:
        raise ConversionError(f"invalid CSV data: {error}") from error
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)

    return ConversionStats(**counters, hashed=hash_identifiers)
