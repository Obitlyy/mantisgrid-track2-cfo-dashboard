import { useState } from 'react';
import type { ActionId, Estimate, Evaluation } from '../api/contracts.generated';
import { DecisionCards } from './DecisionCards';
import { DecisionRoomMap } from './DecisionRoomMap';

const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 });

function estimateRange(estimate: Estimate | null, unit?: 'usd' | 'gpu_hours') {
  if (!estimate) return 'Unknown';
  const formatter = (unit ?? estimate.unit) === 'usd' ? usd : number;
  const suffix = (unit ?? estimate.unit) === 'gpu_hours' ? ' GPU-h' : '';
  return `${formatter.format(estimate.low)}–${formatter.format(estimate.high)}${suffix}`;
}

export function DashboardViews({ evaluation, inspected, onInspect, onEvidence }: {
  evaluation: Evaluation;
  inspected: ActionId;
  onInspect: (id: ActionId) => void;
  onEvidence: (id: ActionId) => void;
}) {
  const [view, setView] = useState<'executive' | 'facility'>('executive');
  const [selectedSummary, setSelectedSummary] = useState<number | null>(null);
  const action = evaluation.actions.find(item => item.action_id === inspected) ?? evaluation.actions[0];
  const selected = evaluation.portfolio.selected_action_ids.includes(action.action_id);
  const risk = selected ? action.marginal_risk : action.standalone_risk;
  const downside = risk?.rerun_reference_cost_usd ?? risk?.rerun_gpu_hours ?? null;
  const summaryProps = (index: number) => ({
    tabIndex: 0,
    'data-selected': selectedSummary === index ? 'true' : undefined,
    onClick: () => setSelectedSummary(index),
    onKeyDown: (event: React.KeyboardEvent<HTMLElement>) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelectedSummary(index); } },
  });

  return <section className="workspace" aria-label="Decision workspace">
    <div className="view-switch" role="tablist" aria-label="Dashboard view">
      <button role="tab" aria-selected={view === 'executive'} onClick={() => setView('executive')}>
        <span aria-hidden="true">▦</span> Executive View
      </button>
      <button role="tab" aria-selected={view === 'facility'} onClick={() => setView('facility')}>
        <span aria-hidden="true">◇</span> Facility Tour
      </button>
    </div>
    {view === 'facility'
      ? <DecisionRoomMap evaluation={evaluation} inspectedActionId={action.action_id} onEvidence={onEvidence} onExit={() => setView('executive')}/>
      : <>
        <section className="cfo-summary" aria-label="Executive summary">
          <article {...summaryProps(1)}>
            <span>01 · BASELINE</span>
            <h2>Observed GPU spend</h2>
            <strong>{usd.format(evaluation.baseline.reference_cost_usd)}</strong>
            <p>{number.format(evaluation.baseline.measured_gpu_hours)} measured GPU-hours</p>
          </article>
          <article {...summaryProps(2)}>
            <span>02 · OPPORTUNITY</span>
            <h2>Recoverable cost range</h2>
            <strong>{estimateRange(evaluation.portfolio.reference_savings_usd, 'usd')}</strong>
            <p>Reference pricing, not booked cash savings</p>
          </article>
          <article {...summaryProps(3)}>
            <span>03 · TARGET</span>
            <h2>Gap to the 20% target</h2>
            <strong>{estimateRange(evaluation.portfolio.sample_capacity_gap_gpu_hours, 'gpu_hours')}</strong>
            <p>Sample capacity target, not a budget forecast</p>
          </article>
          <article {...summaryProps(4)}>
            <span>04 · RISK</span>
            <h2>Downside if this decision is wrong</h2>
            <strong>{estimateRange(downside)}</strong>
            <p>{downside ? downside.basis : 'Risk evidence is not available for this scenario'}</p>
          </article>
        </section>
        <DecisionCards evaluation={evaluation} inspected={action.action_id} onInspect={onInspect} onEvidence={onEvidence}/>
      </>}
  </section>;
}
