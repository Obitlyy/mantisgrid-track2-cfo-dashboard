import '@testing-library/jest-dom/vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import one from '../../../contracts/fixtures/evaluation.json';
import config from '../../../contracts/fixtures/config.json';
import investigation from '../../../contracts/fixtures/investigation.json';
import type { Evaluation } from '../api/contracts.generated';
import { App } from '../App';
import { DecisionCards } from '../components/DecisionCards';
import { validScenario } from '../components/ScenarioForm';
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
test('malformed successful update preserves the previous evaluation and shows service unavailable', async () => {
  let calls = 0;
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    const body = path.endsWith('/config') ? config : path.includes('/investigations/') ? investigation : calls++ === 0 ? one : { meta: one.meta, request: one.request };
    return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } });
  }));
  render(<App/>);
  await screen.findByRole('heading', { name: 'Where to cut' });
  fireEvent.click(screen.getByRole('button', { name: 'Apply scenario' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Service unavailable');
  expect(screen.getByRole('heading', { name: 'Where to cut' })).toBeVisible();
  for (const card of Array.from(document.querySelectorAll('.decision-cards > article'))) expect(card).toHaveAttribute('data-evaluation-id', one.meta.evaluation_id);
});
test('a changed dataset during boot never publishes cards', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => new Response(JSON.stringify(path.endsWith('/config') ? config : { ...one, meta: { ...one.meta, dataset_id: 'different-dataset' } }), { headers: { 'Content-Type': 'application/json' } })));
  render(<App/>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Dataset changed');
  expect(screen.queryByRole('heading', { name: 'Where to cut' })).not.toBeInTheDocument();
});
test('range validation accepts zero prices and empty selections but rejects invalid bounds', () => {
  const request = structuredClone(one.request) as Evaluation['request'];
  request.pricing.usd_per_gpu_hour = 0;
  request.selected_action_ids = [];
  expect(validScenario(request)).toBe(true);
  request.cpu_migration.recoverable_fraction = { low: 0.5, point: 0.3, high: 1 };
  expect(validScenario(request)).toBe(false);
  request.cpu_migration.recoverable_fraction = { low: 0, point: 1, high: 1.1 };
  expect(validScenario(request)).toBe(false);
});
test('edits made while applying remain unapplied after the response arrives', async () => {
  let complete!: (value: Response) => void;
  let evaluations = 0;
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith('/evaluate') && evaluations++ > 0) return new Promise(resolve => { complete = resolve; });
    return new Response(JSON.stringify(path.endsWith('/config') ? config : path.includes('/investigations/') ? investigation : one), { headers: { 'Content-Type': 'application/json' } });
  }));
  render(<App/>);
  await screen.findByRole('heading', { name: 'Where to cut' });
  fireEvent.change(screen.getByLabelText('GPU reference price'), { target: { value: '3' } });
  fireEvent.click(screen.getByRole('button', { name: 'Apply scenario' }));
  fireEvent.change(screen.getByLabelText('GPU reference price'), { target: { value: '4' } });
  await act(async () => complete(new Response(JSON.stringify({ ...one, request: { ...one.request, pricing: { ...one.request.pricing, usd_per_gpu_hour: 3 } } }), { headers: { 'Content-Type': 'application/json' } })));
  expect(screen.getByLabelText('GPU reference price')).toHaveValue(4);
  expect(screen.getByText('Unapplied changes')).toBeVisible();
});
test('cards expose standalone and marginal values and complete risk units', () => {
  render(<DecisionCards evaluation={one as Evaluation} inspected="cpu_migration" onInspect={() => {}} onEvidence={() => {}}/>);
  for (const summary of screen.getAllByText('Expand analysis')) fireEvent.click(summary);
  expect(screen.getByText('Standalone recoverable capacity')).toBeVisible();
  expect(screen.getByText('Marginal recoverable capacity')).toBeVisible();
  expect(screen.getByText('Rerun GPU-hours')).toBeVisible();
  expect(screen.getByText('Additional CPU core-hours')).toBeVisible();
});
test('idle not-applicable CPU cost remains zero while rerun and cash stay unknown', () => {
  render(<DecisionCards evaluation={one as Evaluation} inspected="idle_session_reclaim" onInspect={() => {}} onEvidence={() => {}}/>);
  fireEvent.click(screen.getAllByText('Expand analysis')[2]);
  expect(screen.getByText('Additional CPU cost').parentElement).toHaveTextContent('$0.00');
  expect(screen.getByText('Additional CPU cost').parentElement).toHaveTextContent('Not applicable to this action.');
  expect(screen.getByText('Rerun GPU-hours').parentElement).toHaveTextContent('Unknown');
  expect(screen.getByText('Unknown — no billing evidence')).toBeVisible();
});
test('selection and inspection stay separate; unknown optional inputs cannot become zero', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => new Response(JSON.stringify(path.endsWith('/config') ? config : path.includes('/investigations/') ? investigation : one), { headers: { 'Content-Type': 'application/json' } })));
  render(<App/>);
  await screen.findByRole('heading', { name: 'Where to cut' });
  expect(screen.queryByText('Decision Room Map')).not.toBeInTheDocument();
  const idle = one.actions[1];
  const idleSelection = screen.getByRole('region', { name: 'Scenario inputs' }).querySelector(`[aria-label="Actions"]`)!.querySelectorAll('button')[1];
  expect(idleSelection).toHaveAttribute('aria-pressed', 'false');
  fireEvent.click(idleSelection);
  expect(idleSelection).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByText('Unapplied changes')).toBeVisible();
  expect(screen.getByText(/Marginal scope/)).toHaveTextContent(one.actions[0].title);
  fireEvent.click(document.querySelector(`.action-ranking [aria-label="${idle.title}"]`)!);
  expect(screen.getByText(/Standalone scope/)).toHaveTextContent(idle.title);
  fireEvent.click(screen.getByText('Advanced scenario assumptions'));
  fireEvent.click(screen.getByLabelText('CPU rerun fraction Unknown'));
  expect(screen.getByRole('button', { name: 'Apply scenario' })).toBeDisabled();
  for (const bound of ['low', 'point', 'high']) fireEvent.change(screen.getByLabelText(`CPU rerun fraction ${bound}`), { target: { value: '0' } });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Apply scenario' })).toBeEnabled());
  fireEvent.change(screen.getByLabelText('GPU reference price'), { target: { value: '' } });
  expect(screen.getByRole('button', { name: 'Apply scenario' })).toBeDisabled();
});

test('the executive dashboard omits the agent panel', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => new Response(JSON.stringify(path.endsWith('/config') ? config : path.includes('/investigations/') ? investigation : one), { headers: { 'Content-Type': 'application/json' } })));
  render(<App/>);
  await screen.findByRole('heading', { name: 'Where to cut' });
  expect(screen.queryByRole('heading', { name: 'Ask AI' })).not.toBeInTheDocument();
});

test('AI chat and decision evidence are mutually exclusive', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => new Response(JSON.stringify(path.endsWith('/config') ? config : path.includes('/investigations/') ? investigation : one), { headers: { 'Content-Type': 'application/json' } })));
  render(<App/>);
  await screen.findByRole('heading', { name: 'Where to cut' });

  fireEvent.click(screen.getByRole('button', { name: 'Ask AI' }));
  expect(screen.getByRole('dialog', { name: 'Ask AI' })).toBeVisible();

  fireEvent.click(screen.getAllByRole('button', { name: 'View evidence' })[0]);
  expect(screen.queryByRole('dialog', { name: 'Ask AI' })).not.toBeInTheDocument();
  expect(screen.getByRole('dialog', { name: 'Decision evidence' })).toBeVisible();

  fireEvent.click(screen.getByRole('button', { name: 'Ask AI' }));
  expect(screen.queryByRole('dialog', { name: 'Decision evidence' })).not.toBeInTheDocument();
  expect(screen.getByRole('dialog', { name: 'Ask AI' })).toBeVisible();
});

test('the executive dashboard omits the historical sample and applied evaluation card', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => new Response(JSON.stringify(path.endsWith('/config') ? config : path.includes('/investigations/') ? investigation : one), { headers: { 'Content-Type': 'application/json' } })));
  render(<App/>);
  await screen.findByRole('heading', { name: 'Where to cut' });
  expect(screen.queryByText('Historical sample')).not.toBeInTheDocument();
  expect(screen.queryByText('Applied evaluation')).not.toBeInTheDocument();
});

test('the executive headline is presented as one continuous desktop line', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => new Response(JSON.stringify(path.endsWith('/config') ? config : path.includes('/investigations/') ? investigation : one), { headers: { 'Content-Type': 'application/json' } })));
  render(<App/>);
  const heading = await screen.findByRole('heading', { name: 'Make the next GPU decision with evidence.' });
  expect(heading).toHaveClass('hero-headline');
  expect(heading.querySelector('br')).not.toBeInTheDocument();
});

test('outcome shares use solid grayscale tones instead of patterned bars', () => {
  render(<DecisionCards evaluation={one as Evaluation} inspected="cpu_migration" onInspect={() => {}} onEvidence={() => {}}/>);
  const bars = screen.getByLabelText('Outcome share chart').querySelectorAll('i');
  expect(bars.length).toBeGreaterThan(0);
  bars.forEach((bar, index) => {
    expect(bar).toHaveAttribute('data-tone', String(index % 4));
    expect(bar.className).not.toMatch(/pattern/);
  });
});

test('decision cards keep dense analysis collapsed until requested', () => {
  render(<DecisionCards evaluation={one as Evaluation} inspected="cpu_migration" onInspect={() => {}} onEvidence={() => {}}/>);
  const details = screen.getAllByText('Expand analysis').map(summary => summary.closest('details'));
  expect(details).toHaveLength(3);
  for (const detail of details) expect(detail).not.toHaveAttribute('open');
  fireEvent.click(screen.getAllByText('Expand analysis')[0]);
  expect(details[0]).toHaveAttribute('open');
});
