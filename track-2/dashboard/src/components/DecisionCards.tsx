import type { ActionId, Estimate, Evaluation, RiskResult } from '../api/contracts.generated';

const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 });
const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });

export function EstimateView({ estimate, label }: { estimate: Estimate | null; label: string }) {
  if (!estimate) return <div className="metric"><span>{label}</span><strong>Unknown</strong><small>Evidence is not available for this scenario.</small></div>;
  const format = estimate.unit === 'usd' ? usd.format : number.format;
  return <div className="metric"><span>{label}</span><strong>{format(estimate.point)} <small>point · {estimate.unit.replaceAll('_', ' ')}</small></strong><div className="range-plot" aria-label={`${label}: low ${format(estimate.low)}, point ${format(estimate.point)}, high ${format(estimate.high)}`}><i/><div className="range-labels"><b>LOW {format(estimate.low)}</b><b>POINT {format(estimate.point)}</b><b>HIGH {format(estimate.high)}</b></div></div><p>{estimate.basis}</p></div>;
}

export function RiskMetrics({ risk }: { risk: RiskResult }) {
  return <><EstimateView label="Rerun GPU-hours" estimate={risk.rerun_gpu_hours}/><EstimateView label="Rerun reference cost" estimate={risk.rerun_reference_cost_usd}/><EstimateView label="Additional CPU core-hours" estimate={risk.additional_cpu_core_hours}/><EstimateView label="Additional CPU cost" estimate={risk.additional_cpu_cost_usd}/><EstimateView label="Added job hours" estimate={risk.added_job_hours}/><div className="unknown"><strong>Cash savings</strong><span>Unknown — no billing evidence</span></div>{risk.unknowns.length > 0 && <ul>{risk.unknowns.map(item => <li key={item}>{item}</li>)}</ul>}</>;
}

export function DecisionCards({ evaluation, inspected, onInspect, onEvidence }: { evaluation: Evaluation; inspected: ActionId; onInspect: (id: ActionId) => void; onEvidence: (id: ActionId) => void }) {
  const action = evaluation.actions.find(item => item.action_id === inspected) ?? evaluation.actions[0];
  const selected = evaluation.portfolio.selected_action_ids.includes(action.action_id);
  const risk = selected ? action.marginal_risk : action.standalone_risk;
  return <section className="decision-cards" aria-label="Decision summary">
    <article className="card" data-evaluation-id={evaluation.meta.evaluation_id}>
      <p className="card-index">01 · HISTORICAL SAMPLE</p><h2>Where the money goes</h2><div className="hero-number">{usd.format(evaluation.baseline.reference_cost_usd)}</div><p>Reference USD across {number.format(evaluation.baseline.measured_gpu_hours)} measured GPU-hours.</p>
      <div className="outcome-chart" aria-label="Outcome share chart">{evaluation.baseline.outcomes.map((row, index) => <div key={row.state_name}><span>{row.state_name}</span><i data-tone={index % 4} style={{ width: `${Math.max(row.share_of_measured_gpu_hours * 100, 1)}%` }}/><strong>{number.format(row.share_of_measured_gpu_hours * 100)}%</strong></div>)}</div>
      <details className="analysis-details"><summary>Expand analysis</summary><p className="chart-note">Cancelled and non-completed outcomes are observed categories, not verified waste.</p><div className="table-wrap"><table aria-label="Accessible outcome data summary"><thead><tr><th>Outcome</th><th>Jobs</th><th>GPU-h</th><th>Reference USD</th><th>Share</th></tr></thead><tbody>{evaluation.baseline.outcomes.map(row => <tr key={row.state_name}><td>{row.state_name}</td><td>{row.jobs}</td><td>{number.format(row.measured_gpu_hours)}</td><td>{usd.format(row.reference_cost_usd)}</td><td>{number.format(row.share_of_measured_gpu_hours * 100)}%</td></tr>)}</tbody></table></div><h3>Method and caveats</h3><p>Computed utilization is a proxy, not verified waste.</p>{evaluation.baseline.caveats.map(c => <p key={c}>{c}</p>)}</details>
    </article>
    <article className="card" data-evaluation-id={evaluation.meta.evaluation_id}>
      <p className="card-index">02 · RECOMMENDED ACTION</p><h2>Where to cut</h2><div className="action-ranking" aria-label="Action ranking chart">{evaluation.actions.map(item => <button aria-label={item.title} aria-pressed={item.action_id === action.action_id} key={item.action_id} onClick={() => onInspect(item.action_id)}><span>#{item.rank} {item.title}</span><i className={`rank-${item.rank}`}/><strong>{number.format(item.standalone_recoverable_gpu_hours.point)} GPU-h</strong></button>)}</div><p className="owner">Rank {action.rank} · Owner {action.owner_role} · Effort {action.effort}</p><p>{action.action}</p>
      <details className="analysis-details"><summary>Expand analysis</summary><EstimateView label="Standalone recoverable capacity" estimate={action.standalone_recoverable_gpu_hours}/><EstimateView label="Standalone reference savings" estimate={action.standalone_reference_savings_usd}/>{selected ? <><EstimateView label="Marginal recoverable capacity" estimate={action.marginal_recoverable_gpu_hours}/><EstimateView label="Marginal reference savings" estimate={action.marginal_reference_savings_usd}/></> : <p>Not selected in the applied portfolio; standalone scope.</p>}<p>{action.candidate_jobs} candidate jobs · {evaluation.portfolio.overlap_jobs} overlap jobs</p></details>
      <button className="primary" data-testid={`evidence-${action.action_id}`} onClick={() => onEvidence(action.action_id)}>View evidence</button>
    </article>
    <article className="card" data-evaluation-id={evaluation.meta.evaluation_id}>
      <p className="card-index">03 · DOWNSIDE</p><h2>If this decision is wrong</h2><p className="scope-pill">{selected ? 'Marginal scope' : 'Standalone scope'} · {action.title}</p><div className="risk-preview"><span>Current evidence</span><strong>{risk ? risk.unknowns.length ? 'Incomplete' : 'Scenario available' : 'Unknown'}</strong></div>
      <details className="analysis-details"><summary>Expand analysis</summary>{risk ? <RiskMetrics risk={risk}/> : <p>Unknown risk for this scope</p>}<h3>Pilot guardrails</h3><h4>Success metrics</h4><ul>{action.pilot.success_metrics.map(item => <li key={item}>{item}</li>)}</ul><h4>Stop conditions</h4><ul>{action.pilot.stop_conditions.map(item => <li key={item}>{item}</li>)}</ul><h4>Rollback</h4><ul>{action.pilot.rollback_steps.map(item => <li key={item}>{item}</li>)}</ul></details>
    </article>
  </section>;
}
