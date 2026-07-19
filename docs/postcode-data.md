# Australian postcode data

`elementor2gads` does not bundle a full suburb-to-postcode dataset. The internal prototype used a
dataset whose provenance and redistribution rights were not clear enough for an open-source
release.

## Required format

Supply a UTF-8 CSV with exactly these headings:

```csv
suburb,state,postcode
Exampleville,QLD,4000
Sample Bay,NSW,2000
```

- `suburb` is normalised for case, punctuation, and whitespace.
- `state` must resolve to `ACT`, `NSW`, `NT`, `QLD`, `SA`, `TAS`, `VIC`, or `WA`.
- `postcode` must contain a four-digit value.
- Multiple postcodes for the same suburb and state are permitted, but make inference ambiguous.

Use it with:

```bash
elementor2gads --input submissions.csv --output customer-match.csv \
  --au-postcodes /path/to/au-postcodes.csv
```

Without a lookup, the converter can still extract an explicit four-digit postcode from location
text. It cannot resolve a suburb-only value.

Exact locality matches are used by default. Add `--fuzzy-postcodes` only when you deliberately want
confidence-gated typo matching, and review every inferred result before upload.

## Preparing a source file

The optional helper can select locality, state, and postcode columns from a wider CSV, normalise the
values, remove duplicate rows, and filter states:

```bash
elementor2gads-postcodes \
  --input /path/to/licensed-localities.csv \
  --output /path/to/au-postcodes.csv \
  --only-states QLD,NSW,VIC
```

Use `--force` only when replacing the intended generated file. Conversion does not change or remove
the source dataset's licence obligations.

## Provenance and licensing checklist

Before using or redistributing a dataset, record:

- the publisher and exact product name;
- the authoritative source URL;
- release/version and retrieval date;
- the licence text or URL;
- whether commercial use, modification, and redistribution are permitted;
- required attribution and notices;
- third-party components or additional restrictions; and
- every transformation used to create the lookup.

Do not assume public accessibility means open licensing. In particular, Australia Post states that
postcode extracts have restrictions on modification, derivative works, sublicensing, and making the
data available to others. Review the current
[Australia Post postcode terms](https://auspost.com.au/about-us/corporate-information/our-organisation/policies/assignment-of-postcodes)
and obtain permission or an appropriate licence where necessary.

Some Australian Bureau of Statistics products are available under CC BY 4.0, subject to exclusions
and attribution. Confirm the licence on the specific product and do not assume it covers a postcode
mapping obtained from another source.

## Accuracy limitations

Suburbs and postal localities are not interchangeable in every case. Names can occur in multiple
states, a locality can have multiple postcodes, datasets become stale, and a street name can resemble
a suburb. Inference is best effort and is not address validation. Review inferred values before
upload and prefer a postcode explicitly supplied by the customer.

See [data/README.md](../data/README.md) for repository handling rules.
