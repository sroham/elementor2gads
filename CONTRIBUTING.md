# Contributing to elementor2gads

Thank you for helping improve `elementor2gads`. The project is maintained by
[Elasyn](https://elasyn.com.au) for the open-source community.

## Before you start

- Use an issue to discuss substantial behaviour or interface changes before investing in a large
  pull request.
- Report security vulnerabilities privately as described in [SECURITY.md](SECURITY.md).
- Never submit a real Elementor export, Customer Match file, personal information, credentials, or
  confidential business data. Reproduce problems with synthetic records only.
- Do not add postcode or other third-party data without documented provenance and a licence that
  permits redistribution in this repository.

## Development setup

Use Python 3.11 or newer:

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
```

Activate the environment with `source .venv/bin/activate` on macOS or Linux, or
`.\.venv\Scripts\Activate.ps1` in Windows PowerShell.

Run the checks before opening a pull request:

```bash
python -m ruff check .
python -m pytest
python -m build
python -m twine check dist/*
```

## Making a change

1. Keep the change focused and avoid unrelated formatting or refactoring.
2. Add or update tests for observable behaviour.
3. Use only synthetic fixtures. Reserved domains such as `example.test` and officially reserved
   fictional phone numbers are preferred.
4. Update user-facing documentation and `CHANGELOG.md` when behaviour changes.
5. Preserve local-only processing unless a networked feature has first been discussed and its
   privacy implications documented.

Postcode resolver changes should cover ambiguous suburb names, state hints, missing datasets, and
deterministic results. Customer Match changes should be checked against current primary Google
documentation.

## Pull requests

Explain the problem, the chosen approach, and how the change was tested. Complete the privacy and
licensing checks in the pull request template. Maintainers may ask for a smaller change, additional
tests, or documentation before merging.

By contributing, you agree that your contribution is licensed under the repository's
[MIT License](LICENSE). Participation is also subject to the
[Code of Conduct](CODE_OF_CONDUCT.md).
