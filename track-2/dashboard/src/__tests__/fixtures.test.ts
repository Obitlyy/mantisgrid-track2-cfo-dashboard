import { afterAll, beforeAll, expect, test } from 'vitest';
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';
import evaluation from '../../../contracts/fixtures/evaluation.json';
import job from '../../../contracts/fixtures/job.json';
const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterAll(() => server.close());
test('fixture detail rejects absent or mismatched dataset IDs', async () => {
  expect((await fetch(`/v1/decision/jobs/${job.job_id}?dataset_id=other`)).status).toBe(422);
  expect((await fetch(`/v1/decision/jobs/${job.job_id}`)).status).toBe(422);
});
test('fixture claims reject unsupported scenarios rather than substituting defaults', async () => {
  const response = await fetch('/v1/decision/claims', { method: 'POST', body: JSON.stringify({ team: 'Test', evaluation_request: { ...evaluation.request, pricing: { usd_per_gpu_hour: 99 } } }) });
  expect(response.status).toBe(422);
});
test('fixture evidence rejects unsupported pagination', async () => {
  const response = await fetch('/v1/decision/actions/cpu_migration/evidence?scope=marginal&offset=50&limit=50', { method: 'POST', body: JSON.stringify(evaluation.request) });
  expect(response.status).toBe(422);
});
