import { useCallback, useEffect, useRef, useState } from 'react';
import type { ActionId, Evaluation, EvaluationRequest } from './api/contracts.generated';
import { ApiError, evaluate, getClaims, getConfig } from './api/client';
import { ScenarioForm } from './components/ScenarioForm';
import { DecisionCards, EstimateView, RiskMetrics } from './components/DecisionCards';
import { McpAuditPanel } from './components/McpAuditPanel';
import { EvidenceDrawer } from './evidence/EvidenceDrawer';
import { createEvaluationRunner } from './state/evaluationRunner';
import './styles.css';

type Phase = 'booting' | 'ready' | 'updating' | 'error';
export function App() {
  const [phase, setPhase] = useState<Phase>('booting');
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [draft, setDraft] = useState<EvaluationRequest | null>(null);
  const [inspected, setInspected] = useState<ActionId>('cpu_migration');
  const [drawer, setDrawer] = useState<ActionId | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const trigger = useRef<HTMLElement | null>(null);
  const dataset = useRef<string | null>(null);
  const runner = useRef(createEvaluationRunner(async (request, signal) => { const result = await evaluate(request, signal); if (result.meta.dataset_id !== dataset.current) throw new Error('Dataset changed — reload analysis'); return result; }, setEvaluation));
  const boot = useCallback(async () => { setPhase('booting'); setMessage(null); try { const config = await getConfig(); dataset.current = config.meta.dataset_id; const request = structuredClone(config.default_request); setDraft(request); if (await runner.current.submit(request)) setPhase('ready'); } catch (reason) { setMessage(reason instanceof ApiError ? `${reason.body?.error.code ?? 'SERVICE_UNAVAILABLE'} — ${reason.message}` : String(reason)); setPhase('error'); } }, []);
  useEffect(() => { void boot(); return () => runner.current.dispose(); }, [boot]);
  const apply = async () => { if (!draft) return; setPhase('updating'); setMessage(null); try { const applied = await runner.current.submit(draft); if (applied) { setPhase('ready'); setDrawer(null); } } catch (reason) { setMessage(String(reason)); setPhase('ready'); } };
  const openEvidence = (id: ActionId) => { trigger.current = document.activeElement as HTMLElement; setDrawer(id); };
  const closeEvidence = () => { setDrawer(null); requestAnimationFrame(() => trigger.current?.focus()); };
  const download = async () => { if (!evaluation) return; const team = window.prompt('Team name for claims export'); if (!team?.trim()) return; try { const result = await getClaims(team, evaluation); const url = URL.createObjectURL(new Blob([JSON.stringify(result.claims, null, 2)], { type: 'application/json' })); const link = document.createElement('a'); link.href = url; link.download = 'claims.json'; link.click(); URL.revokeObjectURL(url); } catch (reason) { setMessage(String(reason)); } };
  if (phase === 'booting' && !evaluation) return <main className="loading"><p className="eyebrow">GPU BUDGET DECISION</p><h1>Loading the historical sample…</h1><div className="skeleton"/></main>;
  if (!evaluation) return <main className="loading"><p className="eyebrow">DECISION DATA UNAVAILABLE</p><h1>We could not load this analysis.</h1><p role="alert">{message}</p><button className="primary" onClick={boot}>Retry</button></main>;
  const fixture = evaluation.meta.data_origin === 'test_fixture';
  return <main>
    {fixture && <div className="fixture-banner" role="status">Fixture data — not real findings</div>}
    <nav className="topbar"><div><span className="mark">MG</span><strong>GPU Budget Decision</strong></div><div><span className={`status ${evaluation.audit_status}`}>{evaluation.audit_status.replace('_', ' ')}</span><button onClick={download}>Download claims</button></div></nav>
    {message && <div className="status-banner" role="alert">Previous scenario — request failed. {message} <button onClick={apply}>Retry scenario</button></div>}
    {phase === 'updating' && <div className="status-banner" role="status">Previous scenario — updating</div>}
    <header className="page-intro"><p className="eyebrow">HISTORICAL CAPACITY · REFERENCE PRICING</p><h1>Make the next GPU decision with evidence.</h1><p>Compare capacity recovery, inspect the downside, and trace each recommendation to physical GPU records.</p></header>
    <section className="context"><div><span>Historical sample</span><strong>{new Date(evaluation.meta.sample_window.mapped_start_utc).toLocaleDateString()} – {new Date(evaluation.meta.sample_window.mapped_end_utc).toLocaleDateString()}</strong><small>Calendar dates mapped from source offsets</small></div><div><span>Applied evaluation</span><strong title={evaluation.meta.evaluation_id ?? ''}>{evaluation.meta.evaluation_id?.slice(0, 14)}</strong><small>{evaluation.price_book_version}</small></div></section>
    {draft && <ScenarioForm draft={draft} evaluation={evaluation} updating={phase === 'updating'} onChange={setDraft} onApply={apply}/>}
    <DecisionCards evaluation={evaluation} inspected={inspected} onInspect={setInspected} onEvidence={openEvidence}/>
    <section className="portfolio"><h2>Portfolio context</h2><p>Fixed allocation order: CPU migration, then idle reclaim. {evaluation.portfolio.unique_jobs} unique jobs · {evaluation.portfolio.overlap_jobs} overlap jobs.</p><EstimateView label="Portfolio recoverable GPU-hours" estimate={evaluation.portfolio.recoverable_gpu_hours}/><EstimateView label="Portfolio reference savings" estimate={evaluation.portfolio.reference_savings_usd}/><details><summary>Portfolio risk</summary><RiskMetrics risk={evaluation.portfolio.risk}/></details><details><summary>Gap to 20% of sample GPU-hours</summary><EstimateView label="Sample capacity gap" estimate={evaluation.portfolio.sample_capacity_gap_gpu_hours}/><p>Not a next-quarter budget commitment.</p>{evaluation.portfolio.caveats.map(item => <p key={item}>{item}</p>)}</details><McpAuditPanel datasetId={evaluation.meta.dataset_id}/></section>
    {drawer && <EvidenceDrawer evaluation={evaluation} actionId={drawer} onClose={closeEvidence}/>}
  </main>;
}
