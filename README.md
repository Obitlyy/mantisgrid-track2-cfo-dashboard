# MantisGrid Hackathon 2026 — Track 2 release

This repository contains both official hackathon tracks. The main deliverable is the English Track 2 application: a local, evidence-linked view of historical GPU usage, two operational pilot candidates, their scenario ranges, and the cost of being wrong.

- [Track 2 — Cluster efficiency](track-2/) is the implemented deliverable.
- [Track 1 — Root cause analysis](track-1/) remains available with its original context.
- [REPORT.md](REPORT.md) states the decision, method, reproducibility details, and limitations.
- [Hackathon report](hackathon-report.md) and [pitch presentation](hackathon-pitch.html) provide the submission narrative.
- [Four-minute demo script](docs/demo-script.md) gives the exact presentation path.

The dashboard answers three questions:

1. **Where the money goes** — historical measured GPU-hours and reference-priced cost by terminal outcome.
2. **Where to cut** — ranked CPU-migration and idle-session-reclaim pilots with owners, filters, scenario capacity, and row-level evidence.
3. **If this decision is wrong** — rerun, CPU, and delay inputs remain visibly unknown until supplied; `cash_savings_usd` remains null because billing realization was not measured.

These are historical capacity scenarios, not a quarterly forecast, calibrated probability, cash-savings claim, or instruction to change a scheduler automatically.

## Requirements

- Docker with Compose
- GNU Make
- Node.js/npm for dashboard tests outside Docker
- `uv` for local Python test and CLI targets

The default application uses deterministic analysis over the downloaded dataset. Its decision cards do **not** require an LLM, a local model, or an LLM API key. An optional read-only chat agent uses DeepSeek tool calling to explain the applied scenario through the existing Decision API and official MantisGrid evidence interfaces; set `DEEPSEEK_API_KEY` in an ignored `.env` file to enable it. The MCP audit also runs deterministically against the official local MCP server.

## Prepare the official data

Run commands from the repository root:

```bash
make download-data
make prep
make generate
make check-data
```

`make download-data` is idempotent when the four official raw files are already present. If data already exists under the original Track 2 layout, `make reuse-data` copies it only when destinations are safe. The three later commands build and value-check the five generated data files.

The Track 2 workload telemetry is the MIT SuperCloud TX-GAIA HPCA'22 release, licensed [CC BY-NC-ND 4.0](http://creativecommons.org/licenses/by-nc-nd/4.0/). It is not committed or redistributed. See [ATTRIBUTION.md](ATTRIBUTION.md) and [data/README.md](data/README.md) for attribution, license, provenance, and download details. The separate shared-volume incident scenario is synthetic and marked as such.

## Start the application

```bash
docker compose up
```

Open [http://localhost:3000](http://localhost:3000). The API is also exposed on `http://localhost:8000`. Plain `docker compose up` starts only the API and dashboard; it does not require the notebook or MCP process.

Optional tools:

```bash
make notebook  # JupyterLab on http://localhost:8888
make mcp       # official MCP stdio server
```

`docker compose up --build` or `make up` rebuilds the default application when needed.

## Test and audit

```bash
make check-contracts
make test-api
make test-ui
make test-e2e
python3 track-2/scripts/smoke_decision.py --url http://localhost:3000
make audit
```

`make test-e2e` and the smoke command expect the application to be running. `make audit` performs the bounded real MCP investigation and stores ignored local receipts under `out/`; it does not alter the decision arithmetic or operate the scheduler.

## Export and validate claims

Final export requires the actual team name. It has not been supplied, so the repository intentionally does not invent one or claim that the final root export is complete.

```bash
# Use the request saved from the intended release scenario.
make export-claims TEAM='Actual Team Name' REQUEST=out/release-request.json
make validate CLAIMS=claims.json URL=http://localhost:3000
```

If `REQUEST` is omitted, export uses the application's canonical CPU-only default request. The release numbers in [REPORT.md](REPORT.md) instead use the default parameter values with **both** actions selected. Export recomputes the evaluation; validation runs the official schema/structure checks plus project semantic and same-origin checks.

## AI disclosure

OpenAI Codex and OpenAI GPT-family coding/review agents were used to help analyze the repository, implement and review code and tests, and draft documentation. Deterministic tests, official data checks, live API responses, and browser flows were used to verify claims. Model token counts were not recorded. No model-generated number is treated as source data.

Submission identity remains intentionally incomplete: no team name, member roster, or user-supplied project title was available. See [REPORT.md](REPORT.md) for the full disclosure and remaining release gate.
