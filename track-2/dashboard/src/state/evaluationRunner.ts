import type { Evaluation, EvaluationRequest } from '../api/contracts.generated';

export function createEvaluationRunner(
  run: (request: EvaluationRequest, signal: AbortSignal) => Promise<Evaluation>,
  publish: (result: Evaluation) => void,
) {
  let sequence = 0;
  let controller: AbortController | undefined;
  return {
    async submit(request: EvaluationRequest) {
      const current = ++sequence;
      controller?.abort();
      controller = new AbortController();
      try {
        const result = await run(structuredClone(request), controller.signal);
        if (current !== sequence) return false;
        publish(result);
        return true;
      } catch (error) {
        if (current !== sequence || (error instanceof DOMException && error.name === 'AbortError')) return false;
        throw error;
      }
    },
    dispose() { sequence++; controller?.abort(); },
  };
}
