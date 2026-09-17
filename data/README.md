# Track 2 data

The telemetry is licensed CC BY-NC-ND 4.0 and must not be committed. From the
repository root, download the official 9.3 MB archive and then run the three
reproducibility steps:

```bash
make download-data
make prep
make generate
make check-data
```

The archive must contain exactly `dcgm.csv`, `scheduler_data.csv`, `LICENSE`, and
`README.md`. `make check-data` compares the five generated files against the trusted
value-level checksums and should print `ok` for every line. If this checkout already
contains the official Track 2 data under the original layout, use `make reuse-data`;
the command checks every destination before copying and never overwrites different
content.

The source files, prepared tables, and generated findings remain in ignored
`data/raw/`, `data/prepped/`, and `data/synthetic/` directories. Only this README and
`checksums.txt` are committed.
