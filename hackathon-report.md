# GPU Budget Decision

## Evidence-linked GPU capacity decisions for a research cluster

### Executive Summary

GPU Budget Decision helps a CFO answer a practical question: where can the cluster reduce GPU capacity without slowing valid research work?

The product turns historical GPU telemetry into bounded, reviewable decisions. It does not label every failed or cancelled job as waste. Instead, it identifies narrow pilot cohorts, estimates their recoverable capacity under explicit scenarios, shows the cost of a wrong decision, and lets an operator trace each recommendation to the underlying physical GPU records.

The release scenario supports two pilots:

- Move a validated cohort of zero-compute completed jobs to CPU.
- Reclaim long, low-activity interactive or cancelled sessions after notice and a grace period.

Together, the pilots cover **2,148 unique jobs** after whole-job deduplication. Their scenario recovery range is **0 to 56,586 GPU-hours**, with a **28,293 GPU-hour point scenario**. At a reference price of **$2.50 per GPU-hour**, that corresponds to a **$0 to $141,464 reference-price equivalent**, with a **$70,732 point scenario**.

The high scenario reaches **9.53% of the historical sample hours**, below the 20% comparison target. That gap is intentional and visible. The product presents a credible first move rather than claiming that a historical sample is a next-quarter budget forecast.

## 1. Business Problem

The cluster contains four months of real MIT SuperCloud workload telemetry:

| Measure | Value |
| --- | ---: |
| Jobs | 74,849 |
| Physical GPU records | 96,893 |
| Measured GPU-hours | 594,003.84 |
| Reference-priced usage at $2.50/GPU-hour | $1,485,009.60 |

An initial utilization proxy suggests that **83.03% of allocated compute did not turn into completed work**. That signal is useful for prioritizing investigation, but it is not a savings number. A cancelled job may be waste, user work in progress, a retry, or an intentional interactive session. The system therefore separates four different quantities:

1. Historical measured GPU-hours.
2. Capped candidate capacity that meets strict intervention predicates.
3. Scenario recovery after applying an explicit recovery fraction.
4. Realized cash savings, which require billing and capacity-realization evidence.

This separation prevents the most dangerous failure mode in cost optimization: turning a large utilization statistic into an unsupported financial promise.

## 2. Analysis Method

### 2.1 Physical GPU grain

The analysis begins with physical GPU records rather than a row-level average or a single job summary. Each candidate retains device duration, SM utilization, job outcome, attempt count, and supporting record completeness.

### 2.2 Strict candidate predicates

The CPU migration cohort requires a completed job, zero average and maximum SM utilization, more than one measured GPU-hour, one attempt, a valid walltime, and complete physical GPU rows. The idle-session cohort requires the exact interactive or cancelled predicate associated with the finding, walltime above four hours, average SM utilization below 5%, one attempt, and valid supporting rows.

These filters narrow the intervention to cases with a defensible operational interpretation. The product does not treat all `CANCELLED`, `FAILED`, `TIMEOUT`, or `NODE_FAIL` jobs as recoverable.

### 2.3 Conservative capacity caps

Candidate GPU duration is capped at the job walltime. Idle-session capacity is capped at elapsed GPU time beyond four hours because the dataset does not contain an idle-time series. The system therefore reports a modeled capacity proxy, not observed idle-tail duration.

### 2.4 Scenario arithmetic

The core calculation is:

```text
scenario recovery = capped candidate capacity × recovery fraction
reference-price equivalent = scenario recovery × $2.50/GPU-hour
```

Default recovery ranges are explicit scenarios rather than confidence intervals. The default low bound is zero because the pilots have not yet measured recovery. No calibrated probability of success is implied.

### 2.5 Whole-job deduplication

There are **109 jobs eligible for both actions**. The release portfolio assigns each whole job to CPU migration first, then idle-session reclaim. This keeps the portfolio additive without splitting a job across interventions or counting the same GPU-hours twice.

## 3. Product and Frontend Innovation

The dashboard is designed as one decision path with two levels of detail.

### Executive View

The first screen answers four questions in under thirty seconds:

- Where did the measured GPU usage go?
- Which action ranks first?
- What is the scenario range?
- What could it cost if the decision is wrong?

The screen keeps measured baseline, modeled recovery, and reference pricing visually separate. It gives a non-engineer an action without requiring them to understand the raw telemetry first.

### Facility Tour

The Facility Tour moves from abstract recommendation to operational context. It gives an SRE a cluster-level view of the selected action and keeps the recommendation connected to the affected operating surface.

### Evidence Drawer

The Evidence Drawer is the key trust interaction. An operator can open an action, inspect the supporting detector finding, open the job record, and review the physical GPU rows that support the candidate. Evidence stays beside the decision instead of being pushed into a separate report or notebook.

### Controlled AI

The optional AI agent is read-only and evidence-grounded. It explains the applied evaluation through the existing decision API and official MantisGrid evidence interfaces. It cannot cancel, requeue, drain, or otherwise change scheduler state. The same evaluation identifier connects the dashboard cards, evidence drawer, chat response, and claims export.

This design makes the AI useful without making it the source of truth. Deterministic local analysis owns the arithmetic and the model explains the resulting decision context.

## 4. Recommended Pilots

### Pilot A: Move zero-compute completed jobs to CPU

**Owner:** Platform Engineering
**Eligible jobs:** 463
**Capped candidate capacity:** 11,985.85 GPU-hours
**Point scenario:** 5,992.93 GPU-hours at a 50% recovery fraction

The pilot targets completed jobs with consistent zero compute activity. Before rollout, the team should validate output correctness and CPU queue capacity. The pilot should stop on output mismatch, interruption of valid work, or a pre-agreed duration or rerun threshold breach.

### Pilot B: Reclaim long, low-activity sessions

**Owner:** Research Platform Operations
**Eligible jobs:** 1,794
**Capped candidate capacity:** 92,158.36 GPU-hours
**Standalone point scenario:** 23,039.59 GPU-hours at a 25% recovery fraction

The pilot notifies the owner at 3.5 hours, allows a 0.5-hour grace period, and reclaims only after owner protections are applied. Because there is no idle-time series, the number is a capped elapsed-time proxy rather than measured idle duration.

### Portfolio allocation

When both actions are selected, CPU migration receives overlapping jobs first. The resulting portfolio point is **28,292.80 GPU-hours**, not the simple sum of both standalone points. This preserves a clear ownership model and prevents double counting.

## 5. Results

| Portfolio metric | Release scenario |
| --- | ---: |
| Unique jobs | 2,148 |
| Overlap jobs assigned once | 109 |
| Scenario recovery | 0 / 28,292.80 / 56,585.60 GPU-hours |
| Reference-price equivalent | $0 / $70,732.00 / $141,463.99 |
| High scenario as share of sample hours | 9.53% |
| Comparison target | 20% of sample hours |

The result is actionable because it ranks specific cohorts and assigns owners. It is credible because the product also shows what the result does not prove: a scenario ceiling is not measured savings, reference pricing is not an invoice, and the sample is not a complete next-quarter forecast.

## 6. MCP Audit and Reliability Guardrails

The deterministic MCP audit completed one `tools/list` discovery call plus 25 business calls across `health`, `list_rules`, `recommendations`, `underperforming`, `list_findings`, `causal`, and `neighbor`.

The audit reviewed five nodes and returned **partial / revise**. It corrected a count-based drain recommendation by requiring bounded causal diagnosis. One node reported 259 findings but returned 200, so the investigation marks the page as truncated. Three nodes received `no_drain` because synthetic shared-volume evidence cannot support a real hardware conclusion. Two remained `cannot_determine`, including one with no causal chain.

This is a bounded investigation, not a fleet-wide reliability audit. The system treats missing causal evidence as a reason to investigate further, not as evidence that a node is healthy.

## 7. Technical Architecture

The application combines deterministic decision logic, a FastAPI service, and a React plus TypeScript frontend.

```text
Official telemetry
        |
        v
Prepared and value-checked tables
        |
        +--> Deterministic decision API --> Executive View
        |                              --> Facility Tour
        |                              --> Evidence Drawer
        |
        +--> Official MCP server --> bounded audit record
        |
        +--> Claims evaluation --> reproducible export
```

The browser uses same-origin relative API paths. The frontend formats returned values but does not reimplement the financial formulas. The application runs without an LLM API key for the core decision cards. The optional chat agent adds explanation and tool-grounded investigation without changing the underlying arithmetic.

## 8. Limitations

- Reference-price equivalents are not realized cash savings. Billing, procurement, reservations, and capacity realization are not measured.
- The 20% comparison uses historical sample GPU-hours. It is not a next-quarter demand or spend forecast.
- Recovery ranges are scenarios with no calibrated probability or confidence level.
- The system proposes guarded pilots. It does not operate the scheduler.
- Idle-session capacity is a capped elapsed-time proxy because idle time series are unavailable.
- SM utilization is a compute proxy and does not prove that a job produced no useful work.
- CPU capacity, CPU unit price, rerun demand, delay cost, and research impact remain to be measured during a pilot.
- The MCP investigation is bounded, partial, mixed-origin, and truncated on at least one node.

## 9. Reproducibility

The release scenario uses the official prepared MIT SuperCloud TX-GAIA dataset and the repository's deterministic preparation and generation steps. The verified dataset identifier is:

```text
d14fde0446cdb405fc44831dbf1ac17d58503ee9d7cdb5f5475d158a75e1d6aa
```

To reproduce the application from a clean checkout:

```bash
make download-data
make prep
make generate
make check-data
docker compose up
```

The application can then be tested with contract checks, API tests, UI tests, end-to-end checks, and the decision smoke test. Final claims should be exported from the intended applied request with the actual team name. The application intentionally does not invent a team identity.

## 10. Conclusion

GPU Budget Decision turns a noisy utilization problem into a controlled operating decision. Its strongest contribution is not a single savings number. It is the combination of strict candidate logic, conservative scenario math, explicit downside, a frontend that makes evidence navigable, and a read-only AI layer that explains rather than improvises.

The recommended next step is a measured pilot. Validate output correctness, CPU capacity, owner protections, rerun load, and completion-time impact. Scale only when those observations support the modeled recovery.
