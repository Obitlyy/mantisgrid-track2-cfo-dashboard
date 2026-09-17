import { expect, test, vi } from 'vitest';
import oneRaw from '../../../contracts/fixtures/evaluation.json';
import bothRaw from '../../../contracts/fixtures/evaluation-both-actions.json';
import type { Evaluation } from '../api/contracts.generated';
import { createEvaluationRunner } from '../state/evaluationRunner';

test('late response cannot replace the latest applied scenario', async () => {
  let resolveFirst!: (value: Evaluation) => void;
  let resolveSecond!: (value: Evaluation) => void;
  const run = vi.fn()
    .mockImplementationOnce(() => new Promise<Evaluation>(resolve => { resolveFirst = resolve; }))
    .mockImplementationOnce(() => new Promise<Evaluation>(resolve => { resolveSecond = resolve; }));
  const publish = vi.fn();
  const runner = createEvaluationRunner(run, publish);
  const first = runner.submit((oneRaw as Evaluation).request);
  const second = runner.submit((bothRaw as Evaluation).request);
  resolveSecond(bothRaw as Evaluation); await second;
  resolveFirst(oneRaw as Evaluation); await first;
  expect(publish).toHaveBeenCalledOnce();
  expect(publish).toHaveBeenCalledWith(bothRaw);
});
