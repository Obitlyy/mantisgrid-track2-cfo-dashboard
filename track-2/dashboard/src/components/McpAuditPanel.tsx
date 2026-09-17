import { useEffect, useRef, useState } from 'react';
import type { InvestigationResponse } from '../api/contracts.generated';
import { getInvestigation } from '../api/client';

function FindingIds({ ids }: { ids: string[] }) {
  return <details><summary>Finding IDs ({ids.length})</summary><pre>{ids.join('\n') || 'None'}</pre></details>;
}

export function McpAuditPanel({ datasetId }: { datasetId: string }) {
  const [data, setData] = useState<InvestigationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [readAt, setReadAt] = useState('');
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const load = () => {
    const current = ++generation.current;
    controller.current?.abort();
    controller.current = new AbortController();
    setError(null);
    getInvestigation(datasetId, controller.current.signal).then(result => {
      if (current === generation.current) { setData(result); setReadAt(new Date().toLocaleTimeString()); }
    }).catch(reason => { if (current === generation.current) setError(String(reason)); });
  };
  useEffect(() => {
    setData(null); load();
    return () => { generation.current++; controller.current?.abort(); };
  }, [datasetId]);
  const investigation = data?.investigation;
  return <details className="audit">
    <summary>MCP investigation record</summary>
    <button onClick={load}>Refresh investigation</button>
    {error && <p role="alert">Investigation unavailable. {error}</p>}
    {!data && !error && <p>Loading investigation…</p>}
    {investigation && <>
      <p><strong>{investigation.status.replace('_', ' ')}</strong> · verdict {investigation.verdict} · Read at {readAt}</p>
      <p>{investigation.status === 'not_run' ? 'Investigation not run' : investigation.model_used === null && investigation.tool_calls.length > 0 ? 'Deterministic MCP investigation' : investigation.model_used ?? 'Model unknown'}</p>
      <p>Token usage: {investigation.token_usage === null ? 'Unknown' : JSON.stringify(investigation.token_usage)}</p>
      <p>Evidence origin: {investigation.evidence_origin}{['synthetic_incident', 'mixed'].includes(investigation.evidence_origin) ? ' — includes synthetic incident scenario' : ''}</p>
      <FindingIds ids={investigation.finding_ids}/>
      <p>{investigation.summary}</p>
      {investigation.limitations.map(item => <p key={item}>{item}</p>)}
      <p>Nominal capacity at stake over 24 hours: {investigation.nominal_drain_gpu_hours_24h} GPU-hours. This is nominal capacity, not measured loss or cash; it is excluded from savings and risk totals.</p>
      {investigation.nodes.map(node => <article key={node.resource_id}>
        <strong>{node.node_name}</strong> · {node.cause} · {node.verdict}
        {node.truncated && <span> · Truncated evidence — investigation is incomplete</span>}
        <p>{node.scope_description}</p>
        <p>{node.returned_findings} returned / {node.reported_findings} reported findings</p>
        <p>{node.reasoning}</p>
        <FindingIds ids={node.finding_ids}/>
      </article>)}
      {[...investigation.tool_calls].sort((a, b) => a.sequence - b.sequence).map(call => <details className="tool-call" key={call.call_id}>
        <summary>{call.sequence}. {call.tool_name} — {call.status}</summary>
        <p>{call.started_at_utc} · {call.duration_ms} ms</p>
        <pre>{JSON.stringify({ arguments: call.arguments, result: call.result, error: call.error }, null, 2)}</pre>
      </details>)}
    </>}
  </details>;
}
