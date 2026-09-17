# Track 2 decision report

## 1. Executive decision

Pilot two bounded actions rather than treating all non-completed work as waste:

1. Move a validated cohort of zero-compute completed jobs to CPU, owned by Platform engineering.
2. Reclaim long, low-activity interactive or cancelled sessions after notice and a grace period, owned by Research platform operations.

For the release scenario—default parameter values with both actions selected—the deduplicated portfolio covers 2,148 unique jobs. Its scenario recovery is **0 to 56,585.597619 GPU-hours**, with a **28,292.798810 GPU-hour point**, and its reference-price equivalent at $2.50/GPU-hour is **$0 to $141,463.99**, with a **$70,732.00 point**. The low bound is zero by design: no recovery has yet been observed.

The 20% comparison is 118,800.768029 GPU-hours, computed from this historical sample, not from a next-quarter forecast. The portfolio point is 4.76% of sample hours and the high scenario is 9.53%, leaving a point gap of 90,507.969219 GPU-hours and even a high-scenario gap of 62,215.170409. These comparisons do not establish cash savings; `cash_savings_usd` remains null.

## 2. Data and scope

The analysis uses the official MIT SuperCloud TX-GAIA Track 2 data after the repository's official preparation and generation steps. The verified dataset identifier is:

`d14fde0446cdb405fc44831dbf1ac17d58503ee9d7cdb5f5475d158a75e1d6aa`

The sample contains 74,849 jobs and 96,893 physical GPU records across the official 225-machine dataset. Its source-offset window is mapped to 2026-02-25 21:58:51 UTC through 2026-06-30 23:59:59 UTC; those are mapped display dates, not claimed original wall-clock timestamps. Physical GPU duration is the grain used for measured GPU-hours. `make check-data` verified all five generated files against the trusted value-level checks.

This is a bounded historical sample, not a complete fleet audit. The raw and generated data are excluded from version control under the MIT dataset's CC BY-NC-ND 4.0 license. The separate shared-volume incident records are synthetic and explicitly marked.

## 3. Cost baseline

Historical measured usage totals **594,003.840144 GPU-hours**. At the configurable reference price of $2.50/GPU-hour, that is **$1,485,009.60 of reference-priced usage**, not an invoice or realized spend.

| Terminal outcome | Jobs | Measured GPU-hours | Reference USD |
| --- | ---: | ---: | ---: |
| COMPLETED | 45,334 | 229,040.571769 | $572,601.43 |
| CANCELLED | 9,290 | 203,929.576064 | $509,823.94 |
| FAILED | 18,587 | 50,033.157061 | $125,082.89 |
| TIMEOUT | 1,544 | 107,951.521208 | $269,878.80 |
| NODE_FAIL | 10 | 2,027.890883 | $5,069.73 |
| UNDECODED_11 | 83 | 1,021.114400 | $2,552.79 |
| UNDECODED_1024 | 1 | 0.008758 | $0.02 |

SM utilization produces a separate compute proxy: 228,903.837428 proxy GPU-hours, of which 100,788.834958 are in completed jobs. The resulting 83.03% non-completed share is a proxy and a starting point for investigation, not proof that those hours were waste. The candidate model below uses stricter predicates and caps; it does not label every cancelled, failed, timed-out, or node-failed job as recoverable.

## 4. Actions and ownership

**CPU migration.** Platform engineering owns a pilot after output-correctness and CPU queue-capacity checks. Eligibility requires a COMPLETED job, zero average and maximum SM utilization, more than one measured GPU-hour, one attempt, valid walltime, complete physical GPU rows, and consistent zero-utilization evidence. Per-GPU duration is capped at job walltime. The verified cohort has 463 candidates and 11,985.854564 capped candidate GPU-hours. With the default 0/50%/100% recovery scenario, its point is 5,992.927282 GPU-hours. This is candidate capacity transformed by an assumption, not measured savings.

**Idle-session reclaim.** Research platform operations owns a pilot that notifies at 3.5 hours, allows a 0.5-hour grace period, then reclaims only with owner protections. Eligibility requires the exact interactive or cancelled predicate associated with the finding, walltime above four hours, average SM utilization below 5%, one attempt, and valid supporting GPU rows. Because the dataset has no idle time series, candidate capacity is capped elapsed GPU time beyond four hours—not observed idle-tail duration. The verified eligible cohort has 1,794 candidates and 92,158.356944 capped candidate GPU-hours; three requeued jobs are excluded. Its standalone default 0/25%/50% scenario has a 23,039.589236 GPU-hour point.

Both actions are proposals for guarded pilots. The application does not submit, cancel, requeue, drain, or otherwise change scheduler state.

## 5. Recovery and overlap

Historical measured hours, candidate capacity, scenario recovery, reference-price savings, and cash savings are different quantities:

| Quantity | Meaning | Release-scenario value |
| --- | --- | ---: |
| Historical measured hours | Physical GPU duration across all terminal outcomes | 594,003.840144 GPU-h |
| Standalone capped candidate capacity | CPU plus Idle before cross-action deduplication | 104,144.211508 GPU-h |
| Portfolio scenario recovery | Deduplicated capacity multiplied by assumed recovery fractions | 0 / 28,292.798810 / 56,585.597619 GPU-h |
| Reference-price equivalent | Recovery scenario multiplied by $2.50/GPU-hour | $0 / $70,732.00 / $141,463.99 |
| Realized cash savings | Requires billing and capacity-realization evidence | Unknown / null |

There are 109 jobs eligible for both actions. Allocation is deterministic and assigns each whole overlapping job to CPU first, then Idle; hours are not split. With both selected, CPU keeps its 5,992.927282 GPU-hour point and Idle's marginal point becomes 22,299.871528, for the 28,292.798810 portfolio point. Idle's standalone point remains 23,039.589236 for independent inspection. Ranking and allocation are separate: Idle ranks first on standalone scenario recovery, while fixed whole-job assignment remains CPU then Idle.

Every default low bound is zero. The high values are scenario ceilings on capped candidate capacity, not confidence bounds. Requeued jobs are retained in evidence but excluded from eligible capacity so repeated attempts are not double-counted as a recoverable cohort.

## 6. Cost of being wrong

The application refuses to turn missing evidence into zero cost. For CPU migration, rerun GPU-hours, added job hours, additional CPU core-hours, CPU reference price, additional CPU cost, and realized cash savings are unknown under the default request. For Idle reclaim, rerun GPU-hours, added job hours, and realized cash savings are unknown; CPU cost is explicitly not applicable rather than unknown.

There is no calibrated probability of failure. Optional scenario ranges describe consequences if supplied; they are not incident likelihoods or confidence intervals. The pilot succeeds only if output correctness, queue capacity, completion time, and rerun load stay within a pre-agreed envelope. Stop on output mismatch, interruption of valid work, or a duration/rerun threshold breach. Roll back by restoring the original queue and resource request and disabling automation while protections are reviewed.

## 7. MCP audit

The deterministic MCP audit completed `tools/list` plus 25 successful business calls spanning `health`, `list_rules`, `recommendations`, `underperforming`, `list_findings`, `causal`, and `neighbor`. It reviewed five nodes and returned **partial / revise** with mixed real and synthetic evidence. Model and token usage are null because this audit path was deterministic.

The audit corrects a count-based node-drain recommendation: replace automatic drain-by-finding-count with bounded causal diagnosis. One node reported 259 findings but returned only 200, so the investigation explicitly marks truncation. Three nodes received `no_drain` because synthetic shared-volume evidence cannot support a real hardware conclusion; two remain `cannot_determine`, including one where causal returned no chain. Absence of a causal chain is not evidence of health.

The audit's 240 nominal GPU-hours over 24 hours is nameplate capacity at stake, not measured loss, recovery, risk, or cash. It is excluded from the action arithmetic. Coverage is limited to the call budget and five nodes; this is not a complete fleet reliability audit, and raw finding counts are not converted into hardware-attributable failure claims.

## 8. Reproducibility

- Schema version: `1.0.0`
- Analysis version: `track2-decision-v1`
- Dataset: `d14fde0446cdb405fc44831dbf1ac17d58503ee9d7cdb5f5475d158a75e1d6aa`
- Verified release-scenario evaluation: `019d9c44720216ec41af27a2c99ccfae42ae5fc655470d0898d256561cf6b09f`
- Pricing: $2.50/GPU-hour; CPU price null
- Selected actions: CPU migration and Idle session reclaim
- CPU recovery bounds: 0 / 0.5 / 1.0
- Idle recovery bounds: 0 / 0.25 / 0.5
- Rerun, added-delay, and CPU-capacity inputs: null

From a clean checkout, run:

```bash
make download-data
make prep
make generate
make check-data
docker compose up
```

In a second shell:

```bash
make check-contracts
make test-api
make test-ui
make test-e2e
python3 track-2/scripts/smoke_decision.py --url http://localhost:3000
make audit
```

Final claims must be rebuilt from the intended request and actual team identity, then checked against the running same-origin application:

```bash
make export-claims TEAM='Actual Team Name' REQUEST=out/release-request.json
make validate CLAIMS=claims.json URL=http://localhost:3000
```

The actual team name has not been supplied, so final root claims export remains pending. No team name, member roster, or user-supplied project title is inferred here.

## 9. Limitations

- Reference-price savings are not realized cash savings; there is no billing, reservation, procurement, or capacity-realization evidence. `cash_savings_usd` is null.
- The 20% comparison uses this sample's historical GPU-hours. There is no quarterly demand or spend forecast.
- Scenario intervals have no calibrated probability or confidence level; the default low bound is deliberately zero.
- No scheduler action was executed. All recommendations are proposed pilots with stop and rollback controls.
- The sample is not a complete fleet audit, and the MCP audit is bounded, partial, mixed-origin, and truncated on at least one node.
- No idle time series exists. Idle candidate hours are a capped elapsed-time proxy after four hours, not measured idle duration.
- SM utilization is a compute proxy and does not prove that a job produced no useful work.
- CPU capacity, CPU unit cost, rerun demand, delay cost, and user/research impact remain unknown under the default request.
- Mapped calendar dates are presentation labels derived from source offsets.

## 10. AI disclosure

OpenAI Codex and OpenAI GPT-family coding/review agents were used for repository analysis, implementation assistance, test generation, code review, debugging support, release verification, and documentation drafting. The application itself uses deterministic local analysis and does not require an LLM or API key. The MCP audit described above is deterministic; its model and token fields are null.

All published numbers in this report were checked against current code, the official prepared dataset, live API responses, stored MCP receipts, or the release validation reports. AI output was not used as a source of telemetry. Model token counts for the development and review work were not recorded.
