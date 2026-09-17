import { describe, expect, test } from 'vitest';
import oneRaw from '../../../contracts/fixtures/evaluation.json';
import bothRaw from '../../../contracts/fixtures/evaluation-both-actions.json';
import type { Evaluation } from './contracts.generated';

describe('hand-authored contract fixtures', () => {
  test('preserves independently checked portfolio points', () => {
    const one = oneRaw as Evaluation;
    const both = bothRaw as Evaluation;
    expect(one.portfolio.recoverable_gpu_hours.point).toBe(15);
    expect(both.portfolio.recoverable_gpu_hours.point).toBe(17);
  });
});
