import '@testing-library/jest-dom/vitest';
import { useState } from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import evaluation from '../../../contracts/fixtures/evaluation.json';
import type { Evaluation } from '../api/contracts.generated';
import { ChatAgentPanel } from '../components/ChatAgentPanel';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function FloatingChat() {
  const [open, setOpen] = useState(false);
  return <ChatAgentPanel
    evaluation={evaluation as Evaluation}
    open={open}
    onOpen={() => setOpen(true)}
    onClose={() => setOpen(false)}
  />;
}

test('opens from a floating launcher and Escape closes back to the launcher', () => {
  render(<FloatingChat/>);
  const launcher = screen.getByRole('button', { name: 'Ask AI' });
  expect(screen.queryByRole('dialog', { name: 'Ask the cluster' })).not.toBeInTheDocument();

  fireEvent.click(launcher);
  expect(screen.getByRole('dialog', { name: 'Ask the cluster' })).toBeVisible();
  expect(screen.getByLabelText('Ask about this analysis')).toHaveFocus();

  fireEvent.keyDown(window, { key: 'Escape' });
  expect(screen.queryByRole('dialog', { name: 'Ask the cluster' })).not.toBeInTheDocument();
  expect(launcher).toHaveFocus();
});

test('clicking outside closes the floating chat and restores launcher focus', () => {
  render(<FloatingChat/>);
  const launcher = screen.getByRole('button', { name: 'Ask AI' });

  fireEvent.click(launcher);
  fireEvent.mouseDown(document.body);

  expect(screen.queryByRole('dialog', { name: 'Ask the cluster' })).not.toBeInTheDocument();
  expect(launcher).toHaveFocus();
});

test('asks about the applied evaluation and shows receipts and token usage', async () => {
  vi.stubGlobal('fetch', vi.fn(async (_path: string, init?: RequestInit) => {
    const request = JSON.parse(String(init?.body));
    expect(request.dataset_id).toBe(evaluation.meta.dataset_id);
    expect(request.evaluation_request).toEqual(evaluation.request);
    return new Response(JSON.stringify({
      meta: evaluation.meta,
      answer: 'Start with the CPU migration pilot.',
      model: 'deepseek-fixture',
      usage: { prompt_tokens: 12, completion_tokens: 8, total_tokens: 20 },
      tool_calls: [{ tool_name: 'get_decision_summary', arguments: {}, status: 'success', error: null }],
    }), { headers: { 'Content-Type': 'application/json' } });
  }));

  render(<FloatingChat/>);
  fireEvent.click(screen.getByRole('button', { name: 'Ask AI' }));
  fireEvent.change(screen.getByLabelText('Ask about this analysis'), { target: { value: 'What should we do first?' } });
  fireEvent.click(screen.getByRole('button', { name: 'Ask agent' }));

  expect(await screen.findByText('Start with the CPU migration pilot.')).toBeVisible();
  expect(screen.getByText(/get_decision_summary/)).toBeVisible();
  expect(screen.getByText(/20 tokens/)).toBeVisible();
});

test('chat failure leaves the panel available for retry', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
    error: { code: 'AGENT_NOT_CONFIGURED', message: 'The chat agent is not configured.', details: {} },
    schema_version: '1.0.0',
  }), { status: 503, headers: { 'Content-Type': 'application/json' } })));

  render(<FloatingChat/>);
  fireEvent.click(screen.getByRole('button', { name: 'Ask AI' }));
  fireEvent.change(screen.getByLabelText('Ask about this analysis'), { target: { value: 'Explain the result' } });
  fireEvent.click(screen.getByRole('button', { name: 'Ask agent' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('not configured');
  expect(screen.getByRole('button', { name: 'Ask agent' })).toBeEnabled();
});
