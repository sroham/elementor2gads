# Security policy

## Supported versions

Security fixes are provided for the latest `1.x` release. Older pre-release and development copies
are not supported; reproduce the issue against the latest release where it is safe to do so.

| Version | Supported |
| --- | --- |
| Latest 1.x | Yes |
| Earlier versions | No |

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Contact Elasyn privately through
[elasyn.com.au](https://elasyn.com.au) and identify the message as an `elementor2gads security
report`.

Include:

- the affected version and platform;
- the security impact and conditions required to reproduce it;
- minimal reproduction steps using synthetic data; and
- any suggested mitigation.

Never send a real Elementor export, Customer Match file, credentials, customer identifiers, or
other personal information. If evidence cannot be safely sanitised, describe it first and wait for
handling instructions.

Elasyn will assess reports in good faith, coordinate remediation when appropriate, and ask reporters
to avoid public disclosure until users have had a reasonable opportunity to update. No response or
fix deadline is guaranteed.

## Data exposure

Input and output CSV files are sensitive operational data, even when identifiers are hashed.
Accidentally publishing a customer file is primarily a data incident rather than a software defect.
Remove public access, preserve only the evidence needed for investigation, and notify the relevant
repository owner or organisational incident-response contact immediately. Do not repeat exposed
values in an issue.

Formatting questions, Google match-rate problems, and feature requests that do not have a security
impact may be reported through the normal issue templates with synthetic data.
