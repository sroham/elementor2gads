# elementor2gads

`elementor2gads` converts an Elementor form-submission CSV into a CSV formatted for Google Ads Customer Match. It normalises email addresses, names, and Australian phone numbers, and can extract or infer Australian postcodes from a pickup-location field.

The converter is a small, local-first Python command-line tool with no runtime dependencies. It was created and is maintained by [Elasyn](https://elasyn.com.au).

> [!CAUTION]
> Input and output files can contain personal information. Keep them out of source control, restrict access, and delete them in line with your organisation's retention policy. SHA-256 hashing reduces exposure during upload but does **not** anonymise predictable data such as email addresses or phone numbers. Hashed files must still be protected.

## What it does

- Reads Elementor CSV exports using common aliases for name, email, phone, and pickup location.
- Normalises Australian phone numbers to international `+61` form.
- Extracts a four-digit postcode when one is present in the pickup location.
- Optionally infers a postcode using a caller-supplied suburb dataset.
- Writes the six supported Google Customer Match contact headers:

  ```text
  Email,Phone,First Name,Last Name,Country,Zip
  ```

- Optionally SHA-256 hashes the fields Google treats as private customer data.
- Refuses to overwrite an existing output file unless `--force` is supplied.

The tool does not upload data, connect to Elementor or Google Ads, decide whether you have consent, validate Google Ads account eligibility, or guarantee a Google match. It is a formatter, not an audience-management service.

## Requirements

- Python 3.11 or newer
- An Elementor CSV export
- Optionally, a suitably licensed Australian postcode dataset

## Install

After the package is published, install the isolated command with `pipx`:

```bash
pipx install elementor2gads
```

To install from a source checkout, create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

On Windows PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Check the available options:

```bash
elementor2gads --help
```

The package can also be run without the installed console script:

```bash
python -m elementor2gads --help
```

## Usage

Convert a file for manual plaintext upload to Google Ads:

```bash
elementor2gads \
  --input submissions.csv \
  --output customer-match.csv \
  --country AU
```

Supply a postcode lookup and pre-hash private fields:

```bash
elementor2gads \
  --input submissions.csv \
  --output customer-match-hashed.csv \
  --au-postcodes /path/to/au-postcodes.csv \
  --country AU \
  --hash
```

Overwrite a previously generated file deliberately:

```bash
elementor2gads \
  --input submissions.csv \
  --output customer-match.csv \
  --force
```

`--hash` hashes `Email`, `Phone`, `First Name`, and `Last Name` after normalisation. `Country` and `Zip` remain unhashed, as required by Google. Without `--hash`, the output contains normalised plaintext for the manual Google Ads upload flow; choose **plain text data file** when uploading it.

Useful safety and matching options include:

| Option | Behaviour |
| --- | --- |
| `--strict` | Stop on the first invalid email, phone, or unusable record. |
| `--fuzzy-postcodes` | Opt in to confidence-gated fuzzy suburb matching. |
| `--force` | Deliberately replace an existing output file. |
| `--quiet` | Suppress aggregate conversion output. |

National phone and postcode inference is currently Australian. A different `--country` can be
used with valid international phone numbers, but Australian postcode lookup is disabled.

### Input columns

The converter recognises these Elementor headings:

| Value | Accepted headings |
| --- | --- |
| Full name | `Name`, `Full Name`, `Your Name` |
| Email | `Email`, `Email Address`, `E-mail` |
| Phone | `Phone`, `Phone Number`, `Mobile`, `Mobile Number`, `Telephone` |
| Pickup location | `Pickup Location`, `Pickup`, `Pickup Address`, `Address`, `Suburb` |

For example, this entirely synthetic input:

```csv
Name,Email,Phone,Pickup Location
Avery Morgan,avery@example.test,0491 570 006,"Exampleville QLD 4000"
```

produces plaintext output shaped like:

```csv
Email,Phone,First Name,Last Name,Country,Zip
avery@example.test,+61491570006,avery,morgan,AU,4000
```

The `.test` domain is reserved for examples and will not match a real Google account.

### Australian postcode data

No postcode dataset is bundled. The original project's dataset did not have sufficiently clear provenance and licensing for redistribution in an open-source release.

You can provide your own UTF-8 CSV using `--au-postcodes`. It must have these headers:

```csv
suburb,state,postcode
Exampleville,QLD,4000
Sample Bay,NSW,2000
```

Use a source whose licence permits your intended use and redistribution. Without a dataset, explicit four-digit postcodes can still be extracted from pickup-location text, but suburb-only locations cannot be resolved.

Exact suburb matching is the default. Fuzzy matching is opt-in with `--fuzzy-postcodes` and remains
best effort. Review the generated file before upload, particularly where suburb names occur in
multiple states.

## Docker

Build the image:

```bash
docker build -t elementor2gads .
```

Run it with the working directory mounted at `/work`:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/work" \
  elementor2gads \
  --input /work/submissions.csv \
  --output /work/customer-match.csv \
  --au-postcodes /work/au-postcodes.csv
```

Add `--hash` for a pre-hashed output or `--force` to replace an existing output file.

On Linux, `--user "$(id -u):$(id -g)"` lets the non-root process write to a directory owned by
your host user. Docker Desktop users on Windows or macOS can normally omit `--user`. In PowerShell:

```powershell
docker run --rm `
  --mount "type=bind,source=$((Get-Location).Path),target=/work" `
  elementor2gads `
  --input /work/submissions.csv `
  --output /work/customer-match.csv
```

## Privacy and Google policy

Only process data you are authorised to use. Google requires Customer Match data to be collected in a first-party context, requires appropriate privacy disclosures and consent where applicable, and prohibits certain data and targeting uses. A manual upload requires an in-product compliance attestation.

Google currently accepts manual Customer Match CSV files in ASCII or UTF-8 with exact English headers. For mailing-address matching, `First Name`, `Last Name`, `Country`, and `Zip` must all be present. Google accepts plaintext through its manual UI, but API uploads require normalised, SHA-256-hashed private identifiers. See [Google Customer Match requirements](https://github.com/elasyn/elementor2gads/blob/main/docs/google-customer-match.md) for the dated implementation notes and primary sources.

## Development

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
```

Contributions are welcome. Please read the [contributing guide](https://github.com/elasyn/elementor2gads/blob/main/CONTRIBUTING.md), [code of conduct](https://github.com/elasyn/elementor2gads/blob/main/CODE_OF_CONDUCT.md), and [security policy](https://github.com/elasyn/elementor2gads/blob/main/SECURITY.md) before opening an issue or change.

## Credits

Built by [Elasyn](https://elasyn.com.au) and released for the open-source community.

## Licence

[MIT](https://github.com/elasyn/elementor2gads/blob/main/LICENSE)

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Google or Elementor. Google Ads, Customer Match, and Elementor are trademarks of their respective owners. Google requirements and product behaviour can change; verify the current official documentation before uploading production data. This project is provided as-is and is not legal, privacy, or compliance advice.
