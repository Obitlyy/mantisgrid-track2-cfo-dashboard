import { useEffect, useRef, useState } from 'react';
import type { ChatHistoryTurn, ChatResponse, Evaluation } from '../api/contracts.generated';
import { ApiError, askAgent } from '../api/client';

type Exchange = { question: string; response: ChatResponse };

export function ChatAgentPanel({ evaluation, open, onOpen, onClose }: {
  evaluation: Evaluation;
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
}) {
  const [question, setQuestion] = useState('');
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const launcher = useRef<HTMLButtonElement | null>(null);
  const panel = useRef<HTMLElement | null>(null);
  const input = useRef<HTMLTextAreaElement | null>(null);

  const close = () => {
    onClose();
    launcher.current?.focus();
  };

  useEffect(() => {
    if (!open) return;
    input.current?.focus();
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close();
    };
    const outside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!panel.current?.contains(target) && !launcher.current?.contains(target)) close();
    };
    window.addEventListener('keydown', escape);
    document.addEventListener('mousedown', outside);
    return () => {
      window.removeEventListener('keydown', escape);
      document.removeEventListener('mousedown', outside);
    };
  }, [open, onClose]);

  const ask = async () => {
    const message = question.trim();
    if (!message || busy) return;
    setBusy(true);
    setError(null);
    controller.current?.abort();
    controller.current = new AbortController();
    const history: ChatHistoryTurn[] = exchanges.flatMap(item => [
      { role: 'user' as const, content: item.question },
      { role: 'assistant' as const, content: item.response.answer },
    ]).slice(-6);
    try {
      const response = await askAgent(message, evaluation, history, controller.current.signal);
      setExchanges(items => [...items, { question: message, response }]);
      setQuestion('');
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  };

  return <div className="chat-float">
    <button ref={launcher} type="button" className="chat-launcher" aria-expanded={open}
      aria-controls="chat-agent-dialog" onClick={onOpen}>
      <span aria-hidden="true">✦</span><strong>Ask AI</strong>
    </button>
    {open && <section ref={panel} id="chat-agent-dialog" className="chat-agent" role="dialog" aria-modal="false" aria-labelledby="chat-agent-title">
    <div className="chat-agent-heading">
      <div><p className="eyebrow">CONTROLLED TOOL USE</p><h2 id="chat-agent-title">Ask the cluster</h2></div>
      <div className="chat-agent-controls"><span>Read-only · evidence grounded</span><button type="button" onClick={close} aria-label="Close AI chat">×</button></div>
    </div>
    <p>Ask a basic question about the applied scenario. The agent can inspect decision results and official MantisGrid evidence, but cannot operate the scheduler.</p>
    <div className="chat-starters" aria-label="Starter questions">
      {['What should we do first?', 'Why is this recoverable?', 'What could make this recommendation wrong?'].map(item =>
        <button key={item} type="button" onClick={() => setQuestion(item)}>{item}</button>)}
    </div>
    <div className="chat-history" aria-live="polite">
      {exchanges.map((item, index) => <article key={`${index}-${item.question}`}>
        <p className="chat-question"><strong>You</strong> {item.question}</p>
        <p className="chat-answer"><strong>Agent</strong> {item.response.answer}</p>
        <small>{item.response.model} · {item.response.usage.total_tokens} tokens
          {item.response.tool_calls.length > 0 && ` · tools: ${item.response.tool_calls.map(call => call.tool_name).join(', ')}`}
        </small>
      </article>)}
    </div>
    {error && <p className="chat-error" role="alert">{error}</p>}
    <div className="chat-compose">
      <label htmlFor="agent-question">Ask about this analysis</label>
      <textarea ref={input} id="agent-question" maxLength={2000} rows={3} value={question} disabled={busy}
        onChange={event => setQuestion(event.target.value)}
        onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void ask(); } }}/>
      <button type="button" className="primary" disabled={busy || !question.trim()} onClick={() => void ask()}>{busy ? 'Investigating…' : 'Ask agent'}</button>
    </div>
  </section>}
  </div>;
}
