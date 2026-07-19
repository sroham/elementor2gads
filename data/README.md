# Local postcode data

This directory intentionally contains no postcode dataset. Files placed here are ignored by Git and
must not be committed unless their provenance and redistribution licence have been reviewed and
documented.

For local use, prepare or place a UTF-8 CSV with this schema:

```csv
suburb,state,postcode
Exampleville,QLD,4000
Sample Bay,NSW,2000
```

You can convert a suitably licensed wide locality file with:

```bash
elementor2gads-postcodes \
  --input /path/to/source.csv \
  --output data/au-postcodes.csv
```

Then pass it explicitly to the converter:

```bash
elementor2gads \
  --input /path/to/submissions.csv \
  --output /path/to/customer-match.csv \
  --au-postcodes data/au-postcodes.csv
```

Keep customer exports and generated Customer Match files outside this directory and outside the
repository. Never combine personal information with a reusable locality lookup.

See [Australian postcode data](../docs/postcode-data.md) for schema details, accuracy limitations,
and the provenance checklist. The repository's MIT License does not grant rights to third-party data.
