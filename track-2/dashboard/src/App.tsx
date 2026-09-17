import { useCallback, useEffect, useRef, useState } from 'react';
import type { ActionId, Evaluation, EvaluationRequest } from './api/contracts.generated';
import { ApiError, evaluate, getClaims, getConfig } from './api/client';
import { ScenarioForm } from './components/ScenarioForm';
import { EstimateView, RiskMetrics } from './components/DecisionCards';
import { DashboardViews } from './components/DashboardViews';
import { McpAuditPanel } from './components/McpAuditPanel';
import { ChatAgentPanel } from './components/ChatAgentPanel';
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
  const [chatOpen, setChatOpen] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const trigger = useRef<HTMLElement | null>(null);
  const dataset = useRef<string | null>(null);
  const runner = useRef(createEvaluationRunner(async (request, signal) => { const result = await evaluate(request, signal); if (result.meta.dataset_id !== dataset.current) throw new Error('Dataset changed — reload analysis'); return result; }, setEvaluation));
  const boot = useCallback(async () => { setPhase('booting'); setMessage(null); try { const config = await getConfig(); dataset.current = config.meta.dataset_id; const request = structuredClone(config.default_request); setDraft(request); if (await runner.current.submit(request)) setPhase('ready'); } catch (reason) { setMessage(reason instanceof ApiError ? `${reason.body?.error.code ?? 'SERVICE_UNAVAILABLE'} — ${reason.message}` : String(reason)); setPhase('error'); } }, []);
  useEffect(() => { void boot(); return () => runner.current.dispose(); }, [boot]);
  const apply = async () => { if (!draft) return; setPhase('updating'); setMessage(null); try { const applied = await runner.current.submit(draft); if (applied) { setPhase('ready'); setDrawer(null); setChatOpen(false); } } catch (reason) { setMessage(String(reason)); setPhase('ready'); } };
  const openEvidence = (id: ActionId) => { trigger.current = document.activeElement as HTMLElement; setChatOpen(false); setDrawer(id); };
  const closeEvidence = () => { setDrawer(null); requestAnimationFrame(() => trigger.current?.focus()); };
  const openChat = () => { setDrawer(null); setChatOpen(true); };
  const download = async () => { if (!evaluation) return; const team = window.prompt('Team name for claims export'); if (!team?.trim()) return; try { const result = await getClaims(team, evaluation); const url = URL.createObjectURL(new Blob([JSON.stringify(result.claims, null, 2)], { type: 'application/json' })); const link = document.createElement('a'); link.href = url; link.download = 'claims.json'; link.click(); URL.revokeObjectURL(url); } catch (reason) { setMessage(String(reason)); } };
  if (phase === 'booting' && !evaluation) return <main className="loading"><p className="eyebrow">GPU BUDGET DECISION</p><h1>Loading the historical sample…</h1><div className="skeleton"/></main>;
  if (!evaluation) return <main className="loading"><p className="eyebrow">DECISION DATA UNAVAILABLE</p><h1>We could not load this analysis.</h1><p role="alert">{message}</p><button className="primary" onClick={boot}>Retry</button></main>;
  const fixture = evaluation.meta.data_origin === 'test_fixture';
  return <main className="app-shell">
    {fixture && <div className="fixture-banner" role="status">Fixture data — not real findings</div>}
    <nav className="topbar"><div className="brand-lockup"><span className="mark">MG</span><span><strong>GPU Budget Decision</strong><small>Capacity intelligence</small></span></div><div><span className={`status ${evaluation.audit_status}`}>{evaluation.audit_status.replace('_', ' ')}</span><button className="quiet-button" onClick={download}>Download claims <span aria-hidden="true">↓</span></button></div></nav>
    {message && <div className="status-banner" role="alert">Previous scenario — request failed. {message} <button onClick={apply}>Retry scenario</button></div>}
    {phase === 'updating' && <div className="status-banner" role="status">Previous scenario — updating</div>}
    <header className="page-intro"><div><p className="eyebrow">HISTORICAL CAPACITY · REFERENCE PRICING</p><h1 className="hero-headline">Make the next GPU decision <span>with evidence.</span></h1></div><p className="intro-copy">Compare capacity recovery, inspect the downside, and trace each recommendation to physical GPU records.</p></header>
    {draft && <ScenarioForm draft={draft} evaluation={evaluation} updating={phase === 'updating'} onChange={setDraft} onApply={apply}/>}
    <DashboardViews evaluation={evaluation} inspected={inspected} onInspect={setInspected} onEvidence={openEvidence}/>
    <ChatAgentPanel evaluation={evaluation} open={chatOpen} onOpen={openChat} onClose={() => setChatOpen(false)}/>
    <section className="portfolio"><h2>Portfolio context</h2><p>Fixed allocation order: CPU migration, then idle reclaim. {evaluation.portfolio.unique_jobs} unique jobs · {evaluation.portfolio.overlap_jobs} overlap jobs.</p><EstimateView label="Portfolio recoverable GPU-hours" estimate={evaluation.portfolio.recoverable_gpu_hours}/><EstimateView label="Portfolio reference savings" estimate={evaluation.portfolio.reference_savings_usd}/><details><summary>Portfolio risk</summary><RiskMetrics risk={evaluation.portfolio.risk}/></details><details><summary>Gap to 20% of sample GPU-hours</summary><EstimateView label="Sample capacity gap" estimate={evaluation.portfolio.sample_capacity_gap_gpu_hours}/><p>Not a next-quarter budget commitment.</p>{evaluation.portfolio.caveats.map(item => <p key={item}>{item}</p>)}</details><McpAuditPanel datasetId={evaluation.meta.dataset_id}/></section>
    {drawer && <EvidenceDrawer evaluation={evaluation} actionId={drawer} onClose={closeEvidence}/>}
  </main>;
}
