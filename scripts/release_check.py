"""Fail a release when private or unexpected data appears in the repository."""

from __future__ import annotations

import argparse
import subprocess
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

ALLOWED_CSV = {
    "examples/sample_input.csv",
    "examples/sample_output.csv",
}
FORBIDDEN_NAMES = {
    "customer_match.csv",
    "elementor_export.csv",
    "au_postcodes.csv",
    "simple.csv",
    "suburbs.csv",
}
SENSITIVE_MARKERS = (
    b"Submission ID,Created At,User ID,User Agent,User IP,Referrer",
    b"Customer list\tLast updated",
)
REQUIRED_SDIST_FILES = {
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
    "THIRD_PARTY_NOTICES.md",
    "docs/google-customer-match.md",
    "docs/postcode-data.md",
    "docs/privacy-and-compliance.md",
}


def repository_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [root / line for line in result.stdout.splitlines() if line]


def check_repository(root: Path) -> list[str]:
    errors: list[str] = []
    for path in repository_files(root):
        relative = path.relative_to(root).as_posix()
        if path.name.casefold() in FORBIDDEN_NAMES:
            errors.append(f"forbidden data filename: {relative}")
        if path.suffix.casefold() == ".csv" and relative not in ALLOWED_CSV:
            errors.append(f"CSV is not explicitly allowlisted: {relative}")
        if (
            relative != "scripts/release_check.py"
            and path.is_file()
            and path.stat().st_size <= 5_000_000
        ):
            content = path.read_bytes()
            for marker in SENSITIVE_MARKERS:
                if marker in content:
                    errors.append(f"sensitive export marker found in: {relative}")
    return errors


def archive_members(path: Path) -> list[str]:
    if path.suffix == ".whl" or path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    if path.name.endswith((".tar.gz", ".tar.bz2", ".tar.xz")):
        with tarfile.open(path) as archive:
            return archive.getnames()
    return []


def check_distributions(dist: Path) -> list[str]:
    errors: list[str] = []
    archives = sorted(path for path in dist.glob("*") if path.is_file())
    if not archives:
        return [f"no distributions found in {dist}"]
    for archive in archives:
        members = archive_members(archive)
        for member in members:
            name = PurePosixPath(member).name.casefold()
            if name in FORBIDDEN_NAMES or member.casefold().endswith(".csv"):
                errors.append(f"unexpected data in {archive.name}: {member}")
        if archive.name.endswith(".tar.gz"):
            normalized = {"/".join(PurePosixPath(member).parts[1:]) for member in members}
            missing = REQUIRED_SDIST_FILES - normalized
            if missing:
                errors.append(
                    f"sdist {archive.name} is missing required files: {', '.join(sorted(missing))}"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, help="also inspect wheel/sdist contents")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    errors = check_repository(root)
    if args.dist:
        errors.extend(check_distributions(args.dist))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Release data-safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
