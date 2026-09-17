# GPU Budget Decision

## Evidence-linked GPU capacity decisions for a research cluster

GPU Budget Decision is a Track 2 — Cluster efficiency dashboard for deciding where a
research cluster can reduce GPU capacity without slowing valid research work.

It turns historical GPU telemetry into bounded, reviewable operating decisions. The
dashboard separates measured usage from modeled recovery and reference-price
equivalents. It does not treat every failed or cancelled job as infrastructure waste.
Instead, it ranks narrow pilot cohorts, shows the cost of a wrong decision, and lets an
operator trace each recommendation to the underlying jobs, nodes, findings, and
physical GPU records.

## What the dashboard shows

- **Executive View** — the first-screen decision: where measured usage went, which
  action ranks first, the recovery range, and the downside if the decision is wrong.
- **Facility Tour** — operational context for the selected action and affected cluster
  surface.
- **Evidence Drawer** — a drill-down from a recommendation to the supporting finding,
  job record, and physical GPU rows.
- **Read-only AI explanation** — optional evidence-grounded explanations through the
  decision API and MantisGrid MCP interfaces. The AI layer cannot cancel, requeue, or
  drain scheduler resources.

The release scenario evaluates two guarded pilots:

1. Move a validated cohort of zero-compute completed jobs to CPU.
2. Reclaim long, low-activity interactive or cancelled sessions after notice and a
   grace period.

The dashboard uses whole-job deduplication, conservative walltime caps, and explicit
scenario ranges. A reference-price equivalent is not presented as an invoice or a
guaranteed cash saving.

## Run locally

The data is not committed. The source-data licence requires each evaluator to generate
the prepared tables and findings locally.

From the repository root, follow `data/README.md` to obtain the source archive, then
run:

```bash
make prep
make generate
make check-data
docker compose up --build
```

The dashboard must be reachable at:

```text
http://localhost:3000
```

The core decision cards run without an LLM API key. The optional read-only AI layer
may require the environment configured by the local deployment; it does not own the
arithmetic or change scheduler state.

## Reproducibility and safeguards

- Analysis starts at physical GPU grain rather than a row-weighted utilization
  average.
- Candidate capacity is capped by job walltime and deduplicated at whole-job grain.
- CANCELLED, FAILED, TIMEOUT, and NODE_FAIL are not automatically treated as waste.
- Unallocated idle GPUs are not inferred from per-job telemetry alone.
- Synthetic shared-volume findings are kept distinct from real scheduler and GPU
  telemetry.
- Scenario ranges describe modeled recovery, not calibrated confidence intervals.
- The sample covers four months of MIT SuperCloud workload telemetry and is not a
  complete next-quarter demand or billing forecast.

See [`hackathon-report.md`](hackathon-report.md) for the analysis, assumptions,
limitations, and MCP audit, and [`hackathon-pitch.html`](hackathon-pitch.html) for the
four-minute presentation deck.

## AI use and authorship disclosure

### AI models

- OpenAI GPT-5, used through the OpenAI Codex environment for analysis assistance,
  implementation assistance, and documentation support.

### Coding assistants

- OpenAI Codex Desktop.

### Agent frameworks and tool interfaces

- FastMCP-compatible MCP tooling for the optional, read-only MantisGrid evidence and
  audit path.
- The core dashboard does not depend on an external agent framework or an LLM API key.

### What was AI-assisted versus team-written

AI assistance was used for code suggestions, implementation support, copy editing,
documentation structure, and presentation formatting. The team owns and reviewed the
problem framing, data interpretation, candidate predicates, scenario arithmetic,
whole-job deduplication policy, pilot ownership, evidence-drilldown design, MCP audit
interpretation, validation, and final product decisions. The final repository and its
claims should be reviewed by the team before submission.

## Track

**Track 2 — Cluster efficiency**

