import type { ActionId, ChatHistoryTurn, ChatRequest, ChatResponse, ClaimsResponse, DecisionConfig, ErrorResponse, Evaluation, EvaluationRequest, EvidencePage, FindingDetail, InvestigationResponse, JobDetail } from './contracts.generated';
import { validResponse, type ResponseContract } from './validateResponse';

export class ApiError extends Error {
  constructor(public status: number, public body?: ErrorResponse) {
    super(body?.error.message ? `${body.error.message}${body.error.details && Object.keys(body.error.details).length ? ` — ${JSON.stringify(body.error.details)}` : ''}` : 'Service unavailable');
  }
}

const base = import.meta.env.VITE_API_BASE_URL ?? '';
export async function requestJson<T>(path: string, init: RequestInit = {}, contract?: ResponseContract): Promise<T> {
  let response: Response;
  try { response = await fetch(`${base}${path}`, init); }
  catch (error) { if (init.signal?.aborted) throw error; throw new ApiError(0); }
  const isJson = response.headers.get('content-type')?.includes('json');
  if (!isJson) throw new ApiError(response.status);
  let body: any;
  try { body = await response.json(); } catch { throw new ApiError(response.status); }
  if (!body || typeof body !== 'object') throw new ApiError(response.status);
  if (!response.ok) throw new ApiError(response.status, typeof body.error?.message === 'string' ? body as ErrorResponse : undefined);
  if (!body.meta || typeof body.meta !== 'object') throw new ApiError(response.status);
  if (body.meta?.schema_version !== '1.0.0') throw new Error('Unsupported schema version');
  if (typeof body.meta.dataset_id !== 'string' || !body.meta.sample_window) throw new ApiError(response.status);
  if (contract && !validResponse(contract, body)) throw new ApiError(response.status);
  return body as T;
}
const json = (body: unknown, signal?: AbortSignal): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal });
export const getConfig = () => requestJson<DecisionConfig>('/v1/decision/config', {}, 'DecisionConfig');
export const sameValue = (a: unknown, b: unknown): boolean => {
  if (a === b) return true;
  if (!a || !b || typeof a !== 'object' || typeof b !== 'object') return false;
  const x = a as Record<string, unknown>, y = b as Record<string, unknown>;
  return Object.keys(x).length === Object.keys(y).length && Object.keys(x).every(key => sameValue(x[key], y[key]));
};
function provenance(valid: boolean) { if (!valid) throw new Error('Response provenance does not match the applied analysis'); }
export const evaluate = async (request: EvaluationRequest, signal?: AbortSignal) => {
  const result = await requestJson<Evaluation>('/v1/decision/evaluate', json(request, signal), 'Evaluation');
  if (result.actions.length === 0) throw new ApiError(200);
  provenance(sameValue(result.request, request) && typeof result.meta.evaluation_id === 'string');
  return result;
};
export const getEvidence = async (evaluation: Evaluation, actionId: ActionId, offset = 0, signal?: AbortSignal, scope = evaluation.portfolio.selected_action_ids.includes(actionId) ? 'marginal' : 'standalone') => {
  const result = await requestJson<EvidencePage>(`/v1/decision/actions/${actionId}/evidence?${new URLSearchParams({ scope, offset: String(offset), limit: '50' })}`, json(evaluation.request, signal), 'EvidencePage');
  provenance(result.meta.dataset_id === evaluation.meta.dataset_id && result.meta.evaluation_id === evaluation.meta.evaluation_id && result.action_id === actionId && result.scope === scope && result.offset === offset);
  return result;
};
const datasetQuery = (datasetId: string) => new URLSearchParams({ dataset_id: datasetId });
export const getJob = async (id: string, datasetId: string, signal?: AbortSignal) => { const result = await requestJson<JobDetail>(`/v1/decision/jobs/${encodeURIComponent(id)}?${datasetQuery(datasetId)}`, { signal }, 'JobDetail'); provenance(result.meta.dataset_id === datasetId && result.job_id === id); return result; };
export const getFinding = async (id: string, datasetId: string, signal?: AbortSignal) => { const result = await requestJson<FindingDetail>(`/v1/decision/findings/${encodeURIComponent(id)}?${datasetQuery(datasetId)}`, { signal }, 'FindingDetail'); provenance(result.meta.dataset_id === datasetId && result.finding_id === id); return result; };
export const getInvestigation = async (datasetId: string, signal?: AbortSignal) => { const result = await requestJson<InvestigationResponse>(`/v1/decision/investigations/node_recommendation_audit?${datasetQuery(datasetId)}`, { signal }, 'InvestigationResponse'); provenance(result.meta.dataset_id === datasetId && result.investigation.dataset_id === datasetId); return result; };
export const getClaims = async (team: string, evaluation: Evaluation) => {
  const result = await requestJson<ClaimsResponse>('/v1/decision/claims', json({ team, evaluation_request: evaluation.request }), 'ClaimsResponse');
  const source = result.claims.analysis_provenance as Record<string, unknown> | undefined;
  provenance(result.meta.dataset_id === evaluation.meta.dataset_id && result.meta.evaluation_id === evaluation.meta.evaluation_id && source?.dataset_id === evaluation.meta.dataset_id && source?.evaluation_id === evaluation.meta.evaluation_id && sameValue(source?.evaluation_request, evaluation.request));
  return result;
};
export const askAgent = async (message: string, evaluation: Evaluation, history: ChatHistoryTurn[] = [], signal?: AbortSignal) => {
  const payload: ChatRequest = {
    message,
    dataset_id: evaluation.meta.dataset_id,
    evaluation_request: evaluation.request,
    history: history.slice(-6) as ChatRequest['history'],
  };
  const result = await requestJson<ChatResponse>('/v1/decision/chat', json(payload, signal), 'ChatResponse');
  provenance(result.meta.dataset_id === evaluation.meta.dataset_id && result.meta.evaluation_id === evaluation.meta.evaluation_id);
  return result;
};
