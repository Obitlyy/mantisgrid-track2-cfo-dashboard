# Track 2 data

The telemetry is licensed CC BY-NC-ND 4.0 and must not be committed. Download the
official archive from `https://mantisgrid-hackathon.s3.us-east-1.amazonaws.com/track-2-raw.zip`,
then run `make prep`, `make generate`, and `make check-data`.

The archive must contain exactly `dcgm.csv`, `scheduler_data.csv`, `LICENSE`, and
`README.md`. If this checkout already contains the official Track 2 data, use
`make reuse-data`; the command checks every destination before copying and never
overwrites different content.
