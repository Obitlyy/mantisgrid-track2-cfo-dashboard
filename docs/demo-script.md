# Four-minute Track 2 demo script

## Before the timer

1. From a clean checkout, prepare and verify the official data, then run `make audit`. Confirm the literal CLI summary includes `Audit: partial` and `calls=26`, and identifies an incomplete page. The 26 receipts are one `tools/list` discovery call plus 25 business calls. This creates the dataset-matched audit cache before the application starts.
2. Run `docker compose up`, open `http://localhost:3000` at a desktop width, and wait for the audit badge to show `partial`.
3. Expand `MCP investigation record`, click `Refresh investigation`, and verify `partial`, `verdict revise`, the two stated limitations, and a node with `200 returned / 259 reported findings`. Collapse it again.
4. Under `Scenario inputs`, check `Reclaim idle interactive sessions` and click `Apply scenario`. Wait for the update to finish and verify `2148 unique jobs · 109 overlap jobs` in `Portfolio context`.
5. In `Where to cut`, click `Move zero-compute completed jobs to CPU`. Start the timer with the CPU action inspected and both actions applied.

## 0:00–0:35 — Spend and sample

**Click/scroll:** Start at the top. Point to `Historical sample`, then the card `Where the money goes`. Do not click a terminal-outcome row; the full table is already visible.

**Say:** “This is a bounded historical sample: 74,849 jobs, 96,893 physical GPU records, and 594,003.84 measured GPU-hours. At the current $2.50 reference price that is $1.485 million of reference-priced usage, not an invoice. Every terminal outcome is shown. The 83% figure is a compute proxy for non-completed work, not a waste claim.”

## 0:35–1:25 — CPU pilot and owner

**Click:** In `Where to cut`, click `Move zero-compute completed jobs to CPU` if it is not already active. Point to `Owner Platform engineering`, the candidate count, and `Standalone recoverable capacity`. Expand `Method and caveats` in `Where the money goes` if it is closed.

**Say:** “The first pilot moves only completed jobs with zero average and maximum SM compute to CPU, after correctness and CPU queue-capacity checks. It contains 463 eligible jobs and 11,985.85 capped candidate GPU-hours. The point scenario applies a 50% recovery assumption, giving 5,992.93 GPU-hours. Candidate capacity and scenario recovery are not observed cash savings.”

**Click:** In `If this decision is wrong`, expand `Pilot guardrails`.

**Say:** “Platform engineering owns the pilot. We stop on output mismatch, valid-work interruption, or a pre-agreed duration or rerun breach, and can restore the original queue and resource request.”

## 1:25–2:10 — Wrong-decision risk and unknowns

**Point:** Stay on `If this decision is wrong`. Point to each `Unknown` risk and to `Cash savings — Unknown — no billing evidence`.

**Click:** Expand `Advanced scenario assumptions` above the cards. Do not enter invented values.

**Say:** “The cost of being wrong is not silently turned into zero. Rerun GPU-hours, added delay, CPU core-hours, CPU price, and cash realization are unknown. These editable low, point, and high inputs are scenarios—not confidence intervals—and the default recovery low bound is zero. There is no calibrated probability and no quarterly forecast.”

## 2:10–3:05 — Evidence and overlap

**Click:** Close `Advanced scenario assumptions`. Under `Where to cut`, click `View evidence`. Allow about 17 seconds for the real evidence request; while it loads, say: “This drawer uses the same applied evaluation.”

**Click:** In the first included evidence record that offers a finding, click `View finding …`. Point to `Detector` and `Method`.

**Click:** Click `View job …`, then point to the table labelled `Physical GPU records`, including `Raw duration (s)`, `Measured hours`, and `Capped hours`.

**Say:** “A candidate traces to its detector finding, job, and every physical GPU record; raw values and duration caps stay visible.”

**Click:** Click `Close evidence`.

**Click:** In `Where to cut`, click `Reclaim idle interactive sessions`.

**Point:** Point to `109 overlap jobs`, `Standalone recoverable capacity`, and `Marginal recoverable capacity`.

**Say:** “The already-applied scenario assigns 109 whole-job overlaps to CPU first, so Idle's standalone and marginal points differ without another calculation or double count.”

## 3:05–3:40 — MCP audit correction

**Click:** In `Portfolio context`, expand `MCP investigation record`. Point to `partial`, `verdict revise`, and the truncated node showing `200 returned / 259 reported findings`. If needed, expand one `causal — success` or `neighbor — success` receipt.

**Say:** “The deterministic audit completed tools/list plus 25 business calls across five nodes. It revises the count-based drain recommendation: use bounded causal diagnosis instead. One page truncated 259 reported findings to 200, and mixed synthetic evidence cannot justify a real hardware drain. This is a partial audit, not a fleet-wide reliability claim.”

## 3:40–4:00 — Pilot, rollback, and target gap

**Click:** Collapse `MCP investigation record`. In `Where to cut`, click `Move zero-compute completed jobs to CPU`. In `If this decision is wrong`, expand `Pilot guardrails` if needed and point to `Rollback`. In `Portfolio context`, expand `Gap to 20% of sample GPU-hours`.

**Say:** “The high scenario is still only 9.53% of historical sample hours, below the 20% comparison, so this is a pilot contribution—not a promise. Rollback restores the original queue and resource request and disables automation.”

Stop the timer.

## After the timed demo — Claims export

**Click:** Click `Download claims`. Enter the actual registered team name and confirm the browser downloads `claims.json`. If the actual name has not been supplied, cancel the prompt and state that final export is intentionally blocked rather than inventing submission identity.

**Say:** “Claims are generated from this same applied request and carry its dataset and evaluation identifiers. Cash savings remain unclaimed and null.”
