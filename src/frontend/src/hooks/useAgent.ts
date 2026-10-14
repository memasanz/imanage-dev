import { useCallback, useEffect, useState } from 'react';
import { apiClient, ApiError, type AgentCitation, type AgentTraceItem, type SearchResultItem } from '../api/client';

export interface ChatTurn {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  citations?: AgentCitation[];
  trace?: AgentTraceItem[];
  correlationId?: string;
  needsConsent?: boolean;
  consentUrl?: string;
}

export function useAgent() {
  const [conversationId, setConversationId] = useState<string>(() => crypto.randomUUID());
  const [selected, setSelected] = useState<SearchResultItem[]>([]);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiClient.context().catch(() => undefined);
  }, []);

  const isSelected = useCallback((id: string) => selected.some((item) => item.id === id), [selected]);

  const add = useCallback(async (item: SearchResultItem) => {
    if (!['document', 'email'].includes(String(item.type)) && !item.extension) return;
    setSelected((current) => current.some((doc) => doc.id === item.id) || current.length >= 5 ? current : [...current, item]);
    try { await apiClient.addContext({ id: item.id }); } catch { /* selection remains local for mock/offline UX */ }
  }, []);

  const remove = useCallback(async (id: string) => {
    setSelected((current) => current.filter((doc) => doc.id !== id));
    try { await apiClient.removeContext(id); } catch { /* local state already cleared */ }
  }, []);

  const clear = useCallback(async () => {
    setSelected([]);
    try { await apiClient.clearContext(); } catch { /* local state already cleared */ }
  }, []);

  const toggle = useCallback((item: SearchResultItem, checked: boolean) => checked ? add(item) : remove(item.id), [add, remove]);

  const newChat = useCallback(async () => {
    setTurns([]);
    setSelected([]);
    setLoading(false);
    setConversationId(crypto.randomUUID());
    try { await apiClient.clearContext(); } catch { /* local state already cleared */ }
  }, []);

  const send = useCallback(async (message: string) => {
    const trimmed = message.trim();
    if (!trimmed || loading) return;
    const docs = selected.slice(0, 5);
    setTurns((current) => [...current, { id: crypto.randomUUID(), role: 'user', text: trimmed }]);
    setLoading(true);
    try {
      await Promise.all(docs.map((doc) => apiClient.addContext({ id: doc.id }).catch(() => undefined)));
      const response = await apiClient.agentTurn({ message: trimmed, document_ids: docs.map((doc) => doc.id) });
      setTurns((current) => [...current, {
        id: crypto.randomUUID(), role: 'assistant', text: response.answer, citations: response.citations,
        trace: response.trace, correlationId: response.correlation_id,
        needsConsent: response.needs_consent, consentUrl: response.consent_url
      }]);
    } catch (err: unknown) {
      const text = err instanceof ApiError ? err.friendlyMessage() : 'The agent could not answer right now.';
      setTurns((current) => [...current, { id: crypto.randomUUID(), role: 'assistant', text }]);
    } finally {
      setLoading(false);
    }
  }, [loading, selected]);

  return { conversationId, selected, turns, loading, isSelected, add, remove, clear, toggle, send, newChat };
}
