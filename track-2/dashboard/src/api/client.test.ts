import { afterEach, expect, test, vi } from 'vitest';
import fixture from '../../../contracts/fixtures/evaluation.json';
import config from '../../../contracts/fixtures/config.json';
import job from '../../../contracts/fixtures/job.json';
import type { Evaluation } from './contracts.generated';
import { evaluate, getClaims, getConfig, getEvidence, getFinding, getInvestigation, getJob, requestJson } from './client';
afterEach(() => vi.unstubAllGlobals());
const respond = (value: unknown) => vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(value), { headers: { 'Content-Type': 'application/json' } })));
test.each([
  ['config', () => getConfig()],
  ['evaluation', () => evaluate(fixture.request as Evaluation['request'])],
  ['evidence', () => getEvidence(fixture as Evaluation, 'cpu_migration')],
  ['job', () => getJob(job.job_id, fixture.meta.dataset_id)],
  ['finding', () => getFinding('finding-102', fixture.meta.dataset_id)],
  ['investigation', () => getInvestigation(fixture.meta.dataset_id)],
  ['claims', () => getClaims('Test', fixture as Evaluation)],
] as const)('%s rejects a successful response missing its endpoint fields', async (_name, load) => {
  respond({ meta: fixture.meta, request: fixture.request });
  await expect(load()).rejects.toThrow('Service unavailable');
});
test('evaluation rejects malformed nested action fields before publish', async () => {
  respond({ ...fixture, actions: [{ ...fixture.actions[0], standalone_risk: { unknowns: [] } }] });
  await expect(evaluate(fixture.request as Evaluation['request'])).rejects.toThrow('Service unavailable');
});
test('evaluation rejects an empty action list that cannot support inspection', async () => {
  respond({ ...fixture, actions: [] });
  await expect(evaluate(fixture.request as Evaluation['request'])).rejects.toThrow('Service unavailable');
});
test('config rejects out-of-contract pricing inside numeric schema unions', async () => {
  respond({ ...config, default_request: { ...config.default_request, pricing: { ...config.default_request.pricing, usd_per_gpu_hour: -1 } } });
  await expect(getConfig()).rejects.toThrow('Service unavailable');
});
test('malformed JSON is reported as service unavailable', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response('{', { headers: { 'Content-Type': 'application/json' } })));
  await expect(requestJson('/test')).rejects.toThrow('Service unavailable');
});
test('a non-contract JSON body is reported as service unavailable', async () => {
  respond({ unexpected: 'body' });
  await expect(requestJson('/test')).rejects.toThrow('Service unavailable');
});
test('unsupported schema is rejected before rendering', async () => {
  respond({ ...fixture, meta: { ...fixture.meta, schema_version: '2.0.0' } });
  await expect(requestJson('/test')).rejects.toThrow('Unsupported schema version');
});
test('server validation errors retain the invalid field detail', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ schema_version: '1.0.0', error: { code: 'INVALID_REQUEST', message: 'Request validation failed.', details: { invalid_fields: ['body.pricing.usd_per_gpu_hour'] } } }), { status: 422, headers: { 'Content-Type': 'application/json' } })));
  await expect(requestJson('/test')).rejects.toThrow('body.pricing.usd_per_gpu_hour');
});
test('evaluation rejects a response for another request', async () => {
  respond(fixture);
  await expect(evaluate({ ...fixture.request, pricing: { usd_per_gpu_hour: 0 } } as Evaluation['request'])).rejects.toThrow('provenance');
});
test('detail rejects a different dataset or identifier', async () => {
  respond(job);
  await expect(getJob('another-job', job.meta.dataset_id)).rejects.toThrow('provenance');
  await expect(getJob(job.job_id, 'another-dataset')).rejects.toThrow('provenance');
});
test('claims rejects mismatched nested provenance', async () => {
  respond({ meta: fixture.meta, claims: { team: 'Test', analysis_provenance: { dataset_id: fixture.meta.dataset_id, evaluation_id: 'wrong' } } });
  await expect(getClaims('Test', fixture as Evaluation)).rejects.toThrow('provenance');
});
