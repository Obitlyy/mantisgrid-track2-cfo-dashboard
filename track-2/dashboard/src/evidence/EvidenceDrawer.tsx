import { useEffect, useRef, useState } from 'react';
import type { ActionId, EvidencePage, Evaluation, FindingDetail, JobDetail } from '../api/contracts.generated';
import { ApiError, getEvidence, getFinding, getJob } from '../api/client';
import { EstimateView } from '../components/DecisionCards';

export function EvidenceDrawer({ evaluation, actionId, onClose }: { evaluation: Evaluation; actionId: ActionId; onClose: () => void }) {
  const [page, setPage] = useState<EvidencePage | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [finding, setFinding] = useState<FindingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const sequence = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const retry = useRef<() => void>(() => {});
  const cancel = () => { sequence.current++; controller.current?.abort(); };
  const run = async <T,>(request: (signal: AbortSignal) => Promise<T>, publish: (result: T) => void, again: () => void) => {
    cancel(); const current = sequence.current; const active = new AbortController(); controller.current = active;
    retry.current = again; setLoading(true); setError(null);
    try { const result = await request(active.signal); if (current === sequence.current) publish(result); }
    catch (reason) { if (current !== sequence.current) return;
      const code = reason instanceof ApiError ? reason.body?.error.code : undefined;
      if (code === 'DATASET_MISMATCH') { setPage(null); setJob(null); setFinding(null); setError('Dataset changed — reload analysis'); }
      else if (code === 'ACTION_NOT_SELECTED') { setNotice('Action is not selected — showing standalone evidence.'); load(0, 'standalone'); }
      else setError(reason instanceof ApiError ? `${reason.status === 404 ? 'Missing ID — ' : ''}${code ?? 'SERVICE_UNAVAILABLE'} — ${reason.message}` : String(reason));
    } finally { if (current === sequence.current) setLoading(false); }
  };
  const load = (offset = 0, scope = evaluation.portfolio.selected_action_ids.includes(actionId) ? 'marginal' : 'standalone') => { setDetail(false); void run(signal => getEvidence(evaluation, actionId, offset, signal, scope), setPage, () => load(offset, scope)); };
  const openJob = (id: string) => { setDetail(true); setJob(null); void run(signal => getJob(id, evaluation.meta.dataset_id, signal), setJob, () => openJob(id)); };
  const openFinding = (id: string) => { setDetail(true); setFinding(null); setJob(null); void run(signal => getFinding(id, evaluation.meta.dataset_id, signal), setFinding, () => openFinding(id)); };
  const back = () => { cancel(); setLoading(false); setError(null); setJob(null); setFinding(null); setDetail(false); };
  useEffect(() => { setPage(null); setJob(null); setFinding(null); load(); heading.current?.focus(); return cancel; }, [evaluation.meta.evaluation_id, evaluation.meta.dataset_id, actionId]);
  useEffect(() => {
    const background: Array<[HTMLElement, boolean]> = [];
    let branch = dialog.current?.parentElement;
    while (branch?.parentElement && branch !== document.body) {
      for (const sibling of Array.from(branch.parentElement.children)) {
        if (sibling instanceof HTMLElement && sibling !== branch) { background.push([sibling, Boolean(sibling.inert)]); sibling.inert = true; }
      }
      branch = branch.parentElement;
    }
    const keepFocus = (event: FocusEvent) => { if (dialog.current && !dialog.current.contains(event.target as Node)) heading.current?.focus(); };
    const key = (event: KeyboardEvent) => {
    if (event.key === 'Escape') { cancel(); onClose(); }
    if (event.key === 'Tab' && dialog.current) {
      const items = Array.from(dialog.current.querySelectorAll<HTMLElement>('button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])')).filter(item => !item.hasAttribute('disabled'));
      const first = items[0], last = items[items.length - 1];
      const outside = !dialog.current.contains(document.activeElement);
      if (event.shiftKey && (outside || document.activeElement === first || document.activeElement === heading.current)) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && (outside || document.activeElement === last || document.activeElement === heading.current)) { event.preventDefault(); first?.focus(); }
    }
    };
    document.addEventListener('keydown', key);
    document.addEventListener('focusin', keepFocus);
    return () => { document.removeEventListener('keydown', key); document.removeEventListener('focusin', keepFocus); background.forEach(([element, previous]) => { element.inert = previous; }); };
  }, [onClose]);
  return <div className="backdrop" onMouseDown={event => { if (event.target === event.currentTarget) { event.preventDefault(); heading.current?.focus(); } }}><div className="drawer" role="dialog" aria-modal="true" aria-labelledby="evidence-title" ref={dialog}>
    <header><div><p className="eyebrow">APPLIED EVALUATION · {evaluation.meta.evaluation_id?.slice(0, 12)}</p><h2 id="evidence-title" tabIndex={-1} ref={heading}>Decision evidence</h2></div><button onClick={() => { cancel(); onClose(); }} aria-label="Close evidence">Close</button></header>
    {detail && <button className="back" onClick={back}>← Back to evidence</button>}
    {notice && <p role="status">{notice}</p>}{error && <div className="error" role="alert"><p>{error}</p><button onClick={() => retry.current()}>Retry</button></div>}
    {loading && <p role="status">Loading evidence…</p>}
    {finding && !job && <section><h3>{finding.title}</h3><p>{finding.description}</p><dl><dt>Detector</dt><dd>{finding.detector_id}</dd><dt>Origin</dt><dd>{finding.evidence_origin}</dd><dt>Impact kind</dt><dd>{finding.impact_kind ?? 'Unknown'}</dd><dt>Impact scope</dt><dd>{finding.impact_scope ?? 'Unknown'}</dd><dt>Method</dt><dd>{finding.method}</dd><dt>Resources</dt><dd>{finding.resource_ids.join(', ') || 'Unknown'}</dd><dt>Nodes</dt><dd>{finding.node_names.join(', ') || 'Unknown'}</dd><dt>Root causes</dt><dd>{finding.root_cause_ids.join(', ') || 'Unknown'}</dd><dt>Reported impact</dt><dd>{finding.reported_impact_gpu_hours ?? 'Unknown'} GPU-hours (reported, not savings)</dd></dl>{finding.causal_status === 'no_chain' && <p>No causal chain available</p>}{finding.job_ids.map(id => <button key={id} onClick={() => openJob(id)}>View job {id}</button>)}</section>}
    {job && <section>{finding && <button onClick={() => { cancel(); setJob(null); }}>Back to finding</button>}<h3>Job {job.job_id}</h3><p>{job.state_name} · {job.job_type ?? 'Unknown job type'} · {job.attempts} attempt(s)</p><p>Node failure nodes: {job.nodefail_nodes.join(', ') || 'None'} · Exact: {String(job.nodefail_exact)}</p><p>Source offsets (seconds): submitted {job.time_submit_offset_sec ?? 'Unknown'} · started {job.time_start_offset_sec ?? 'Unknown'} · ended {job.time_end_offset_sec ?? 'Unknown'} · walltime {job.walltime_sec ?? 'Unknown'}</p><p>User: {job.user_id ?? 'Unknown'} · Quality: {job.quality_flags.join(', ') || 'Clear'}</p><div className="table-wrap"><table aria-label="Physical GPU records"><thead><tr><th>Node</th><th>GPU</th><th>Raw duration (s)</th><th>Measured hours</th><th>Capped hours</th><th>SM avg %</th><th>SM max %</th><th>Quality flags</th></tr></thead><tbody>{job.gpus.map((gpu, index) => <tr key={index}><td>{gpu.node}</td><td>{gpu.gpu_id}</td><td>{gpu.totalexecutiontime_sec ?? 'Unknown'}</td><td>{gpu.measured_gpu_hours ?? 'Unknown'}</td><td>{gpu.capped_gpu_hours ?? 'Unknown'}</td><td>{gpu.smutilization_pct_avg ?? 'Unknown'}</td><td>{gpu.smutilization_pct_max ?? 'Unknown'}</td><td>{gpu.quality_flags.join(', ') || 'Clear'}</td></tr>)}</tbody></table></div></section>}
    {!detail && page && <><p>{page.scope} scope · {page.total} candidate records · offset {page.offset}</p>{page.rows.length === 0 ? <p>No matching jobs</p> : <div className="evidence-list">{page.rows.map(row => <article key={row.job_id} data-eligibility={row.eligibility}><div><strong>Job {row.job_id}</strong><span>{row.eligibility.replaceAll('_', ' ')} · {row.state_name}</span></div><p>Measured: {row.measured_gpu_hours} GPU-h · capped: {row.capped_gpu_hours ?? 'Unknown'} · candidate: {row.candidate_gpu_hours ?? 'Unknown'} · GPUs: {row.gpu_count}</p><p>Nodes: {row.nodes.join(', ')} · User: {row.user_id ?? 'Unknown'}</p><EstimateView label="Contribution GPU-hours" estimate={row.contribution_gpu_hours}/>{row.reasons.map(reason => <p key={reason}>{reason} — {reason === 'DURATION_CAPPED' ? 'Duration adjusted to walltime; this is a warning, not exclusion.' : reason === 'OVERLAP_ASSIGNED_TO_CPU_MIGRATION' ? 'Overlapping capacity is assigned to CPU migration and is not counted again.' : reason === 'UNSAFE_SOURCE_IDENTIFIER' ? 'Source identifier cannot be represented safely; Unknown.' : reason.toLowerCase().replaceAll('_', ' ')}</p>)}<div>{row.finding_ids.map(id => <button key={id} onClick={() => openFinding(id)}>View finding {id}</button>)}<button onClick={() => openJob(row.job_id)}>View job {row.job_id}</button></div></article>)}</div>}{page.offset > 0 && <button disabled={loading} onClick={() => load(0)}>First page</button>}{page.next_offset !== null && <button disabled={loading} onClick={() => load(page.next_offset!)}>Next page</button>}</>}
  </div></div>;
}
