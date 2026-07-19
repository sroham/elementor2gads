# Google Customer Match requirements

This page records the Google requirements relevant to `elementor2gads`, verified against primary Google documentation on **19 July 2026**. Google may change these requirements. Treat the linked official documentation as authoritative.

This is implementation guidance, not legal or privacy advice.

## Manual CSV format

Google's manual Customer Match upload accepts CSV files encoded as ASCII or UTF-8. UTF-16 is not supported. Contact-data files use exact English header names selected from:

```text
Email,Phone,First Name,Last Name,Country,Zip
```

The matching modes have different minimum headers:

| Match data | Required headers |
| --- | --- |
| Email | `Email` |
| Phone | `Phone` |
| Mailing address | `First Name`, `Last Name`, `Country`, `Zip` |
| Combined contact data | All six headers |
| Mobile device ID | `Mobile Device ID` only; do not mix it with contact data |

Google permits repeated `Email`, `Phone`, and `Zip` columns when a person has multiple distinct identifiers or addresses. `elementor2gads` emits one of each supported contact header because its source schema supplies one value of each kind. Repeating an identical identifier does not add matching information.

Primary source: [Create a Customer Match list by uploading a data file](https://support.google.com/google-ads/answer/10589050?hl=en)

## Normalisation

Normalise values before hashing. Incorrectly normalised data can be accepted by an API while still failing to match.

### Email

For all email addresses:

1. Trim leading and trailing whitespace.
2. Remove intermediate whitespace.
3. Convert to lowercase.
4. Include a complete domain.

For `gmail.com` and `googlemail.com` only, current Data Manager guidance also requires removing dots from the local part and removing the `+` suffix and everything following it. Do not apply those two Gmail-specific rules to other domains.

### Phone

Use E.164 form: a `+`, country calling code, and digits only after the plus sign. For example, the synthetic Australian number `0412 345 678` becomes `+61412345678`.

Google's manual-upload documentation says the plus sign is optional for unhashed data, but Data Manager requires it. This project uses the stricter form consistently.

### Name

- Trim leading and trailing whitespace.
- Convert to lowercase before hashing.
- Do not include a prefix such as `Mrs.` in the first-name value.
- Do not include a suffix such as `Jr.` in the last-name value.
- Accented characters are allowed in manual files.

The current Data Manager `AddressInfo` reference additionally specifies no punctuation in given and family names. This is stricter than some examples in the manual-upload documentation.

### Country and postcode

- For API-compatible address data, use a two-letter ISO-3166-1 alpha-2 country code such as `AU`.
- Include the country even when every record is from the same country.
- International postal codes are supported.
- Do not include postal-code extensions outside the United States.
- Country and postcode are never hashed.

Primary sources:

- [Data Manager: format user data](https://developers.google.com/data-manager/api/devguides/concepts/formatting)
- [Data Manager `UserData` reference](https://developers.google.com/data-manager/api/reference/rest/v1/UserData)
- [Manual Customer Match file formatting](https://support.google.com/google-ads/answer/10589050?hl=en)

## Hashing

Google treats these contact fields as private customer data:

- `Email`
- `Phone`
- `First Name`
- `Last Name`

When pre-hashing, normalise each individual value and then calculate its SHA-256 digest. Data Manager accepts the digest bytes encoded as hexadecimal or Base64. Do not hash `Country` or `Zip`.

Manual Audience Manager upload supports either:

- **Plaintext:** select Google's plain text upload option. Google states that the private fields are hashed on the user's computer before secure transmission.
- **Pre-hashed:** select Google's hashed-data upload option and ensure the data was normalised before hashing.

API uploads must contain hashed private identifiers. Never send the tool's default plaintext output to an API field that expects a hash.

Hashing is deterministic and is not anonymisation. An attacker can guess a likely email address or phone number, hash it, and compare the result. Store and handle hashed exports as sensitive data.

Primary sources:

- [About the customer matching process](https://support.google.com/google-ads/answer/7474263?hl=en)
- [Data Manager: format user data](https://developers.google.com/data-manager/api/devguides/concepts/formatting)

## Multiple identifiers and matchability

Google recommends supplying as many available, distinct match keys as possible. A Data Manager `AudienceMember` can carry up to 10 user identifiers.

An address is matched as one unit and requires all of:

- hashed given name;
- hashed family name;
- unhashed two-letter region/country code; and
- unhashed postcode.

If one of those address components is missing, that address cannot match. An otherwise incomplete row may still match through a valid email address or phone number.

Primary source: [Data Manager `UserData` reference](https://developers.google.com/data-manager/api/reference/rest/v1/UserData)

## Consent and policy

Formatting a file does not establish permission to use its data. The advertiser or operator remains responsible for ensuring that:

- the customer information was collected in a first-party context through a direct interaction;
- the privacy policy discloses relevant sharing with service providers or third parties;
- consent has been obtained where required by law or Google policy;
- applicable privacy, data-protection, industry, and self-regulatory obligations are met;
- data is uploaded only through a Google-approved interface or API;
- the data does not concern a person known to be under 13 and was not collected from a child-directed site or app; and
- Customer Match is not used for prohibited sensitive-category or overly narrow targeting.

The manual upload flow requires a compliance attestation. Google's manual consent guidance says to upload only consented data.

For users in the European Economic Area, both consent signals must be granted for Customer Match personalisation:

- `ad_user_data`
- `ad_personalization`

If consent is missing, Google treats the EEA user as not consented and does not process that data for Customer Match personalisation. If consent is withdrawn, remove the person's identifiers from the audience or replace the list without them.

Data Manager Customer Match ingestion must indicate acceptance of the Customer Match terms. Consent may be supplied as a request default and overridden for an individual audience member.

Primary sources:

- [Customer Match policy](https://support.google.com/adspolicy/answer/6299717?hl=en)
- [Customer data policies](https://support.google.com/adspolicy/answer/7475709?hl=en)
- [How to provide consent for Customer Match](https://support.google.com/google-ads/answer/14546648?hl=en)
- [Data Manager `Consent` reference](https://developers.google.com/data-manager/api/reference/rest/v1/Consent)
- [Upload Customer Match audience members](https://developers.google.com/data-manager/api/devguides/audiences/google-ads/customer-match/upload-data)

## Manual upload workflow

At a high level:

1. Review the generated file and confirm that every record is authorised for Customer Match use.
2. In Google Ads, open Audience Manager and create a customer list.
3. Choose the email, phone, and/or mailing-address data type.
4. Select plaintext or hashed upload to match the file produced.
5. Upload the CSV.
6. Review data-use settings and the policy attestation.
7. Set the membership duration and create the list.
8. Review upload diagnostics and match rate when processing completes; Google advises that processing may take up to 48 hours.

Customer Match membership lasts at most 540 days. Google says a list must have at least 100 members added or refreshed within the previous 540 days to remain eligible and recommends regular refreshes.

Primary sources:

- [Manual upload instructions](https://support.google.com/google-ads/answer/10589050?hl=en)
- [Customer Match policy](https://support.google.com/adspolicy/answer/6299717?hl=en)

## API direction as of July 2026

For new automated Customer Match workflows, Google recommends the **Data Manager API**, not the Google Ads API.

Since 1 April 2026, Google Ads API developer tokens with no Customer Match requests between 1 October 2025 and 31 March 2026 are restricted from using `OfflineUserDataJobService` and `UserDataService` for Customer Match. Those requests fail with `CUSTOMER_NOT_ALLOWLISTED_FOR_THIS_FEATURE`.

The Data Manager API now supports the end-to-end Google Ads Customer Match audience workflow: creating an audience, ingesting members, retrieving results, contact information, mobile IDs, and user IDs. For contact uploads, current guidance recommends `compositeData.userData` rather than the older direct `userData` field so integrations are ready for future improvements.

`elementor2gads` intentionally does not call either API. If API upload is added in the future, it should use Data Manager, explicit terms acceptance, explicit consent handling, request validation, and upload diagnostics.

Primary sources:

- [Google Ads API feature deprecations](https://developers.google.com/google-ads/api/docs/deprecations)
- [Data Manager Customer Match overview](https://developers.google.com/data-manager/api/devguides/audiences/google-ads/customer-match)
- [Upload Customer Match audience members](https://developers.google.com/data-manager/api/devguides/audiences/google-ads/customer-match/upload-data)
- [Check upload results](https://developers.google.com/data-manager/api/devguides/audiences/google-ads/customer-match/check-results)

## Product terminology

Some older Google pages still mention Similar Audiences or Similar Segments. Google stopped generating that legacy feature for targeting and reporting on 1 May 2023. Demand Gen's Lookalike Segments are a separate feature. Avoid presenting legacy Similar Audiences as a current Customer Match capability.

Primary source: [Similar Audiences retirement notice](https://support.google.com/sa360/answer/13388565?hl=en)

## Primary reference index

- [Create a Customer Match list by uploading a data file](https://support.google.com/google-ads/answer/10589050?hl=en)
- [About the customer matching process](https://support.google.com/google-ads/answer/7474263?hl=en)
- [Customer Match policy](https://support.google.com/adspolicy/answer/6299717?hl=en)
- [Customer data policies](https://support.google.com/adspolicy/answer/7475709?hl=en)
- [How to provide consent for Customer Match](https://support.google.com/google-ads/answer/14546648?hl=en)
- [Data Manager Customer Match overview](https://developers.google.com/data-manager/api/devguides/audiences/google-ads/customer-match)
- [Data Manager user-data formatting](https://developers.google.com/data-manager/api/devguides/concepts/formatting)
- [Data Manager `UserData` reference](https://developers.google.com/data-manager/api/reference/rest/v1/UserData)
- [Google Ads API feature deprecations](https://developers.google.com/google-ads/api/docs/deprecations)
