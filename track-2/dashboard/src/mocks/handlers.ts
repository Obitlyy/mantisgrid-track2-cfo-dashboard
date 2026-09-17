import { http, HttpResponse } from 'msw';
import config from '../../../contracts/fixtures/config.json';
import one from '../../../contracts/fixtures/evaluation.json';
import both from '../../../contracts/fixtures/evaluation-both-actions.json';
import cpuDefault from '../../../contracts/fixtures/evidence-cpu-default.json';
import idleStandalone from '../../../contracts/fixtures/evidence-idle-standalone.json';
import cpuBoth from '../../../contracts/fixtures/evidence-cpu.json';
import idleBoth from '../../../contracts/fixtures/evidence-idle.json';
import job from '../../../contracts/fixtures/job.json';
import finding from '../../../contracts/fixtures/finding.json';
import investigation from '../../../contracts/fixtures/investigation.json';

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
const unavailable = () => HttpResponse.json({ error: { code: 'INVALID_REQUEST', message: 'Scenario unavailable in fixture mode', details: {} }, schema_version: '1.0.0' }, { status: 422 });
export const handlers = [
  http.get('/v1/decision/config', () => HttpResponse.json(config)),
  http.post('/v1/decision/evaluate', async ({ request }) => { const body = await request.json(); return same(body, one.request) ? HttpResponse.json(one) : same(body, both.request) ? HttpResponse.json(both) : unavailable(); }),
  http.post('/v1/decision/actions/:action/evidence', async ({ request, params }) => { const body = await request.json(); const query = new URL(request.url).searchParams; if ((query.get('offset') ?? '0') !== '0' || (query.get('limit') ?? '50') !== '50') return unavailable(); const scope = query.get('scope'); if (same(body, one.request) && params.action === 'cpu_migration' && scope === 'marginal') return HttpResponse.json(cpuDefault); if (same(body, one.request) && params.action === 'idle_session_reclaim' && scope === 'standalone') return HttpResponse.json(idleStandalone); if (same(body, both.request) && params.action === 'cpu_migration' && scope === 'marginal') return HttpResponse.json(cpuBoth); if (same(body, both.request) && params.action === 'idle_session_reclaim' && scope === 'marginal') return HttpResponse.json(idleBoth); return unavailable(); }),
  http.get('/v1/decision/jobs/:id', ({ params, request }) => new URL(request.url).searchParams.get('dataset_id') !== job.meta.dataset_id ? unavailable() : String(params.id) === job.job_id ? HttpResponse.json(job) : new HttpResponse(null, { status: 404 })),
  http.get('/v1/decision/findings/:id', ({ params, request }) => new URL(request.url).searchParams.get('dataset_id') !== finding.meta.dataset_id ? unavailable() : String(params.id) === finding.finding_id ? HttpResponse.json(finding) : new HttpResponse(null, { status: 404 })),
  http.get('/v1/decision/investigations/node_recommendation_audit', ({ request }) => new URL(request.url).searchParams.get('dataset_id') !== investigation.meta.dataset_id ? unavailable() : HttpResponse.json(investigation)),
  http.post('/v1/decision/claims', () => unavailable()),
];
