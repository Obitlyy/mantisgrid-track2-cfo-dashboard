import '@testing-library/jest-dom/vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import evaluation from '../../../contracts/fixtures/evaluation.json';
import evidence from '../../../contracts/fixtures/evidence-cpu-default.json';
import job from '../../../contracts/fixtures/job.json';
import finding from '../../../contracts/fixtures/finding.json';
import audit from '../../../contracts/fixtures/investigation.json';
import type { Evaluation } from '../api/contracts.generated';
import { EvidenceDrawer } from '../evidence/EvidenceDrawer';
import { McpAuditPanel } from '../components/McpAuditPanel';
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const response = (body: unknown) => new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } });
test('backdrop interaction and outside focus cannot escape the modal with Shift+Tab', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => response(evidence)));
  const { unmount } = render(<><button>Background action</button><EvidenceDrawer evaluation={evaluation as Evaluation} actionId="cpu_migration" onClose={() => {}}/></>);
  await screen.findByRole('button', { name: `View job ${job.job_id}` });
  const background = screen.getByRole('button', { name: 'Background action' });
  const backdrop = screen.getByRole('dialog').parentElement!;
  fireEvent.mouseDown(backdrop);
  background.focus();
  fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
  expect(screen.getByRole('dialog')).toContainElement(document.activeElement as HTMLElement);
  expect(background.inert).toBe(true);
  unmount();
  expect(background.inert).toBe(false);
});
test('returning to evidence invalidates a late job request', async () => {
  let finish!: (value: Response) => void;
  vi.stubGlobal('fetch', vi.fn((path: string) => path.includes('/jobs/') ? new Promise(resolve => { finish = resolve; }) : Promise.resolve(response(evidence))));
  render(<EvidenceDrawer evaluation={evaluation as Evaluation} actionId="cpu_migration" onClose={() => {}}/>);
  fireEvent.click(await screen.findByRole('button', { name: `View job ${job.job_id}` }));
  fireEvent.click(screen.getByRole('button', { name: /Back to evidence/ }));
  await act(async () => { finish(response(job)); await Promise.resolve(); });
  expect(screen.queryByRole('table', { name: 'Physical GPU records' })).not.toBeInTheDocument();
});
test('failed next page keeps the current rows and retries the server offset', async () => {
  let calls = 0;
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    if (path.includes('offset=50')) { calls++; return calls === 1 ? new Response('Unavailable', { status: 503 }) : response({ ...evidence, rows: [], offset: 50, next_offset: null }); }
    return response({ ...evidence, next_offset: 50 });
  }));
  render(<EvidenceDrawer evaluation={evaluation as Evaluation} actionId="cpu_migration" onClose={() => {}}/>);
  fireEvent.click(await screen.findByRole('button', { name: 'Next page' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Service unavailable');
  expect(screen.getByRole('button', { name: `View job ${job.job_id}` })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
  expect(await screen.findByText('No matching jobs')).toBeVisible();
  expect(screen.getByText(/offset 50/)).toBeVisible();
});
test('dataset mismatch clears prior evidence instead of presenting stale rows', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => path.includes('offset=50') ? new Response(JSON.stringify({ schema_version: '1.0.0', error: { code: 'DATASET_MISMATCH', message: 'Changed', details: {} } }), { status: 409, headers: { 'Content-Type': 'application/json' } }) : response({ ...evidence, next_offset: 50 })));
  render(<EvidenceDrawer evaluation={evaluation as Evaluation} actionId="cpu_migration" onClose={() => {}}/>);
  fireEvent.click(await screen.findByRole('button', { name: 'Next page' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Dataset changed — reload analysis');
  expect(screen.queryByRole('button', { name: `View job ${job.job_id}` })).not.toBeInTheDocument();
});
test('keyboard focus wraps within the drawer and Escape closes it', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => response(evidence)));
  const close = vi.fn();
  render(<EvidenceDrawer evaluation={evaluation as Evaluation} actionId="cpu_migration" onClose={close}/>);
  await screen.findByRole('button', { name: `View job ${job.job_id}` });
  expect(screen.getByRole('heading', { name: 'Decision evidence' })).toHaveFocus();
  fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
  expect(screen.getByRole('button', { name: `View job ${job.job_id}` })).toHaveFocus();
  fireEvent.keyDown(document, { key: 'Tab' });
  expect(screen.getByRole('button', { name: 'Close evidence' })).toHaveFocus();
  fireEvent.keyDown(document, { key: 'Escape' });
  expect(close).toHaveBeenCalledOnce();
});
test('finding navigation shows complete provenance and raw job fields', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => response(path.includes('/findings/') ? finding : path.includes('/jobs/') ? job : evidence)));
  render(<EvidenceDrawer evaluation={evaluation as Evaluation} actionId="cpu_migration" onClose={() => {}}/>);
  fireEvent.click(await screen.findByRole('button', { name: `View finding ${finding.finding_id}` }));
  expect(await screen.findByText('Impact scope')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: `View job ${job.job_id}` }));
  expect(await screen.findByText(/Node failure nodes/)).toBeVisible();
  expect(screen.getByRole('table', { name: 'Physical GPU records' }).querySelectorAll('tbody tr')).toHaveLength(job.gpus.length);
});
test('audit identifies not-run execution and unknown token usage', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => response(audit)));
  render(<McpAuditPanel datasetId={audit.meta.dataset_id}/>);
  fireEvent.click(screen.getByText('MCP investigation record'));
  expect(await screen.findByText('Investigation not run')).toBeVisible();
  expect(screen.getByText('Token usage: Unknown')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Refresh investigation' })).toBeVisible();
});
test('audit finding IDs can be inspected without expanding thousands of IDs by default', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => response({ ...audit, investigation: { ...audit.investigation, finding_ids: ['audit-finding-1'] } })));
  render(<McpAuditPanel datasetId={audit.meta.dataset_id}/>);
  fireEvent.click(screen.getByText('MCP investigation record'));
  const ids = await screen.findByText(/audit-finding-1/);
  expect(ids).not.toBeVisible();
  fireEvent.click(screen.getByText('Finding IDs (1)'));
  expect(ids).toBeVisible();
});
