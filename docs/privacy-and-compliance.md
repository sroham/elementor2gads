# Privacy and compliance

`elementor2gads` formats customer data; it does not establish a lawful basis, obtain consent, or
decide whether a person may be included in a Customer Match audience. This page is operational
guidance, not legal advice.

## Data handled by the tool

An input export may contain names, email addresses, phone numbers, street or pickup locations,
messages, IP addresses, submission metadata, and other personal or confidential information. The
converter reads only configured matching fields, but the source file remains sensitive. Its output
contains direct identifiers or deterministic hashes of them.

Hashing is not anonymisation. Likely email addresses and phone numbers can be guessed, normalised,
hashed, and compared with a leaked digest. Protect plaintext and hashed files to the same
organisational standard.

Version 1.0.0 processes files locally and does not upload them, call Google or Elementor, or collect
telemetry. The operator controls the input path, output path, optional postcode dataset, and any
subsequent upload.

## Operator responsibilities

Before processing or uploading data, confirm that your organisation:

- collected the information through an authorised first-party interaction;
- gave appropriate privacy disclosures and obtained consent where required;
- has authority to use the data for advertising and Customer Match;
- excludes records that must not be used, including withdrawn or expired consent;
- complies with applicable privacy, advertising, industry, and record-retention obligations; and
- can make Google's in-product Customer Match compliance attestation truthfully.

Requirements vary by location and can change. Review current official Google policy and obtain
qualified advice for your circumstances. The dated technical references used by this project are in
[Google Customer Match requirements](google-customer-match.md).

## Safe operating practices

1. Export only the fields and records needed for the task.
2. Work in an access-controlled directory outside source repositories and shared sync folders.
3. Do not use production data in tests, screenshots, issue reports, shell history, or support
   requests.
4. Prefer the `--hash` mode when the intended Google workflow accepts pre-hashed data, while still
   treating the result as sensitive.
5. Review output row counts, unresolved postcodes, and warnings before upload.
6. Upload only through the intended Google interface and choose the plaintext or hashed option that
   matches the file.
7. Restrict access to generated files and backups, then delete them according to the applicable
   retention policy.
8. Record the source, purpose, consent basis, operator, and deletion date where your governance
   process requires it.

The repository ignores CSV files by default, but ignore rules are only a safeguard. They do not
protect files copied elsewhere, added forcibly, included in archives, or captured in container
layers and backups.

## Public collaboration

Never attach a real CSV or paste personal information into a GitHub issue or pull request. Replace
all values with synthetic records, use reserved example domains and fictional phone numbers, and
check logs for paths or values that reveal customer or business information.

If customer data is accidentally exposed, remove public access promptly and follow the relevant
organisational incident-response and notification process. Do not create a second copy of the data
while reporting the incident. Suspected software vulnerabilities should be reported through
[SECURITY.md](../SECURITY.md).
