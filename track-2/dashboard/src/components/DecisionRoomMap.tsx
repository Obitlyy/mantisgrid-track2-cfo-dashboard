import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import type { ActionId, Evaluation } from '../api/contracts.generated';

type Step = 'spend' | 'action' | 'downside';
type Server = { id: number; row: number; side: 'left' | 'right'; slot: number; actionId: ActionId | null; issueType: 'cpu' | 'idle' | 'evidence' | null };
const steps: { id: Step; label: string; title: string }[] = [{ id: 'spend', label: '01 / SPEND', title: 'Where the money goes' }, { id: 'action', label: '02 / ACTION', title: 'Where to cut' }, { id: 'downside', label: '03 / DOWNSIDE', title: 'If this decision is wrong' }];
const rows = Array.from({ length: 23 }, (_, index) => index + 1);

export function DecisionRoomMap({ evaluation, inspectedActionId, onEvidence, onExit, forceFallback = false }: { evaluation: Evaluation; inspectedActionId: ActionId; onEvidence: (id: ActionId) => void; onExit: () => void; forceFallback?: boolean }) {
  const [step, setStep] = useState<Step>('spend');
  const [activeRow, setActiveRow] = useState<number | null>(null);
  const [selected, setSelected] = useState<Server | null>(null);
  const incomplete = ['partial', 'running', 'not_run'].includes(evaluation.audit_status);
  const servers = useMemo(() => Array.from({ length: 225 }, (_, index): Server => {
    const row = Math.floor(index / 10) + 1;
    const position = index % 10;
    const primaryIssue = index % 37 === 0;
    const secondaryIssue = !primaryIssue && index % 53 === 0;
    const actionId = primaryIssue ? inspectedActionId : secondaryIssue ? evaluation.actions.find(item => item.action_id !== inspectedActionId)?.action_id ?? inspectedActionId : null;
    return { id: index + 1, row, side: position < 5 ? 'left' : 'right', slot: position < 5 ? position + 1 : position - 4, actionId, issueType: actionId ? (actionId === 'cpu_migration' ? 'cpu' : 'idle') : null };
  }), [evaluation.actions, incomplete, inspectedActionId]);
  const action = evaluation.actions.find(item => item.action_id === selected?.actionId) ?? evaluation.actions.find(item => item.action_id === inspectedActionId) ?? evaluation.actions[0];
  const isSelectedAction = evaluation.portfolio.selected_action_ids.includes(action.action_id);
  const estimate = step === 'spend' ? evaluation.portfolio.reference_savings_usd : step === 'action' ? (isSelectedAction ? action.marginal_reference_savings_usd : null) ?? action.standalone_reference_savings_usd : (isSelectedAction ? action.marginal_risk : action.standalone_risk)?.rerun_reference_cost_usd;

  useEffect(() => {
    const escape = (event: KeyboardEvent) => { if (event.key !== 'Escape') return; if (selected) setSelected(null); else if (activeRow !== null) setActiveRow(null); else onExit(); };
    window.addEventListener('keydown', escape);
    return () => window.removeEventListener('keydown', escape);
  }, [activeRow, onExit, selected]);
  const selectRow = (row: number | null) => { setActiveRow(row); setSelected(null); };

  return <section className="facility-shell" role="region" aria-label="Full-screen facility tour" data-active-row={activeRow ?? 'overview'} data-renderer={forceFallback ? 'accessible-2d' : 'css-perspective'}>
    <header className="facility-toolbar"><div><p className="eyebrow">GPU CAPACITY DECISION ROOM</p><strong>225 servers · 23 rows</strong></div><p>Decision layout — not physical rack location</p><button onClick={onExit}>Return to Executive View</button></header>
    <nav className="facility-minimap" aria-label="Facility row map"><div className="minimap-head"><span>ROW MAP</span><button aria-pressed={activeRow === null} onClick={() => selectRow(null)}>Overview</button></div><div className="minimap-rows">{rows.map(row => <button key={row} aria-label={`View row ${row}`} aria-pressed={activeRow === row} onClick={() => selectRow(row)}><i/><span>{String(row).padStart(2, '0')}</span><i/></button>)}</div><div className="issue-legend"><span><i className="cpu"/>CPU migration</span><span><i className="idle"/>Idle reclaim</span><span><i className="evidence"/>Evidence incomplete</span></div></nav>
    {selected && <aside className="server-detail" aria-label="Selected server details"><button className="callout-close" onClick={() => setSelected(null)} aria-label="Close server details">×</button><p className="eyebrow">SERVER {String(selected.id).padStart(3, '0')} · ROW {String(selected.row).padStart(2, '0')}</p><h2>{action.title}</h2><p>{action.action}</p><div className="detail-range"><span>{step === 'downside' ? 'Downside interval' : 'Reference interval'}</span><strong>{estimate ? `${estimate.low.toLocaleString()}–${estimate.high.toLocaleString()} ${estimate.unit.replaceAll('_', ' ')}` : 'Unknown'}</strong></div><dl><div><dt>Owner</dt><dd>{action.owner_role}</dd></div><div><dt>Scope</dt><dd>{isSelectedAction ? 'Marginal' : 'Standalone'}</dd></div><div><dt>Risk</dt><dd>{incomplete || action.warnings.length ? 'Evidence incomplete' : 'Scenario available'}</dd></div></dl><button className="primary" onClick={() => onEvidence(action.action_id)}>View evidence</button></aside>}
    <div className="facility-scene" aria-label="Central aisle server room"><div className="facility-ceiling" aria-hidden="true"/><div className="facility-floor" aria-hidden="true"/><div className="central-aisle" aria-hidden="true"/><div className="server-rows" style={{ '--focus-row': activeRow ?? 0 } as CSSProperties}>{rows.map(row => { const rowServers = servers.filter(server => server.row === row); const selectServer = (server: Server) => { setActiveRow(server.row); setSelected(server.issueType ? server : null); }; return <div className={`server-row${activeRow === row ? ' active' : ''}`} data-row={row} data-focus-layout={activeRow === row ? 'stacked' : undefined} key={row}><div className="server-bank left upper" aria-label={`Row ${row} upper servers`}>{rowServers.filter(server => server.side === 'left').map(server => <ServerUnit key={server.id} server={server} incomplete={incomplete} selected={selected?.id === server.id} onSelect={selectServer}/>)}</div><span className="row-marker">{String(row).padStart(2, '0')}</span><div className="server-bank right lower" aria-label={`Row ${row} lower servers`}>{rowServers.filter(server => server.side === 'right').map(server => <ServerUnit key={server.id} server={server} incomplete={incomplete} selected={selected?.id === server.id} onSelect={selectServer}/>)}</div></div>; })}</div></div>
    <div className="facility-steps" role="tablist" aria-label="Decision room views">{steps.map(item => <button key={item.id} role="tab" aria-selected={step === item.id} onClick={() => setStep(item.id)}><span>{item.label}</span><strong>{item.title}</strong></button>)}</div>
  </section>;
}

function ServerUnit({ server, incomplete, selected, onSelect }: { server: Server; incomplete: boolean; selected: boolean; onSelect: (server: Server) => void }) {
  const issueLabel = server.issueType ? `optimization opportunity, ${incomplete ? 'evidence incomplete' : server.issueType === 'cpu' ? 'CPU migration pattern' : 'idle reclaim pattern'}` : 'healthy';
  return <button className="server-unit" data-issue={server.issueType ?? 'healthy'} data-evidence={server.issueType && incomplete ? 'incomplete' : undefined} aria-pressed={selected} aria-label={`Server ${server.id}, row ${server.row}, ${server.side} ${server.slot}, ${issueLabel}`} onClick={() => onSelect(server)}><span className="server-label">S{String(server.id).padStart(3, '0')}</span><i className="server-vent"/><i className="server-handle"/><i className="server-led"/></button>;
}
