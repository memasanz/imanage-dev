import { useState } from 'react';
import { Button, Textarea } from '@fluentui/react-components';
import type { ChatTurn } from '../hooks/useAgent';
import type { SearchResultItem } from '../api/client';
import { libraryOf, markdownToSafeHtml, traceName } from '../utils/format';

export function AgentChatPanel({ selected, turns, loading, conversationId, onRemove, onClear, onSend, onCitationClick }: {
  selected: SearchResultItem[];
  turns: ChatTurn[];
  loading: boolean;
  conversationId: string;
  onRemove: (id: string) => void;
  onClear: () => void;
  onSend: (message: string) => void;
  onCitationClick: (id: string) => void;
}) {
  const [message, setMessage] = useState('');
  const send = () => { const value = message.trim(); if (!value || loading) return; setMessage(''); onSend(value); };
  return <div className="ask-ai-body" aria-label="Ask AI panel">
    <div className="context-list" aria-label="Selected document context">
      {selected.length === 0 && <span className="muted small">Select documents from results to ground the agent.</span>}
      {selected.map((doc) => <div className="context-pill" key={doc.id}><span title={doc.name}>{doc.name.length > 42 ? `${doc.name.slice(0, 42)}…` : doc.name}<br /><span className="muted small">{libraryOf(doc)}</span></span><Button size="small" onClick={() => onRemove(doc.id)}>Remove</Button></div>)}
    </div>
    {selected.length > 0 && <Button size="small" onClick={onClear}>Clear context</Button>}
    <div className="chat-log" role="log" aria-live="polite">
      {turns.length === 0 && <div className="chat-turn chat-assistant">Ask for a summary, obligations, risks, or key dates from selected documents.</div>}
      {turns.map((turn) => <div key={turn.id} className={`chat-turn ${turn.role === 'user' ? 'chat-user' : 'chat-assistant'}`}>
        {turn.role === 'assistant' ? <div dangerouslySetInnerHTML={{ __html: markdownToSafeHtml(turn.text) }} /> : <div>{turn.text}</div>}
        {turn.needsConsent && turn.consentUrl && <div className="consent-prompt"><Button appearance="primary" size="small" onClick={() => window.open(turn.consentUrl, 'imanage-consent', 'width=520,height=680')}>Connect iManage</Button></div>}
        {turn.citations && turn.citations.length > 0 && <div className="citation-list">{turn.citations.map((citation) => <Button key={citation.id} size="small" onClick={() => onCitationClick(citation.id)}>{truncate(citation.name || citation.id)}{citation.confidence ? ` · ${Math.round(citation.confidence * 100)}%` : ''}</Button>)}</div>}
        {turn.trace && turn.trace.length > 0 && <details><summary>Tool-run trace {turn.correlationId ? `· ${turn.correlationId}` : ''}</summary><div className="trace-list">{turn.trace.map((trace, index) => <code key={index}>{traceName(trace)} · {trace.status ?? 'ok'} · {trace.ms ?? trace.latency_ms ?? '—'} ms</code>)}</div></details>}
        {turn.correlationId && (!turn.trace || turn.trace.length === 0) && <div className="muted small">Correlation: {turn.correlationId}</div>}
      </div>)}
      {loading && <div className="chat-turn chat-assistant">Thinking…</div>}
    </div>
    <Textarea value={message} onChange={(_, data) => setMessage(data.value)} placeholder="Ask a grounded question…" resize="vertical" onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} />
    <Button appearance="primary" disabled={!message.trim() || loading} onClick={send}>Send</Button>
  </div>;
}
function truncate(value: string) { return value.length > 30 ? `${value.slice(0, 30)}…` : value; }
