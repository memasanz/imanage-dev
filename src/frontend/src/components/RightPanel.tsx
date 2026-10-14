import { useEffect, useState } from 'react';
import { Button, Tab, TabList } from '@fluentui/react-components';
import { AddRegular } from '@fluentui/react-icons';
import { AgentChatPanel } from './AgentChatPanel';
import { DocumentDetail } from './DocumentDetail';
import { TypeIcon } from './ResultsList';
import type { ChatTurn } from '../hooks/useAgent';
import type { ConfigField, SearchResultItem } from '../api/client';

export function RightPanel({ detail, configFields, onCloseDetail, onChatWithDetail, onNewChat, agentProps }: {
  detail?: SearchResultItem;
  configFields: ConfigField[];
  onCloseDetail: () => void;
  onChatWithDetail: (item: SearchResultItem) => void;
  onNewChat: () => void;
  agentProps: React.ComponentProps<typeof AgentChatPanel>;
}) {
  const [tab, setTab] = useState<'ask' | 'properties'>('ask');

  useEffect(() => { if (detail) setTab('properties'); }, [detail]);

  return <aside className="panel agent-panel" aria-label="Workspace side panel">
    <TabList selectedValue={tab} onTabSelect={(_, data) => setTab(data.value as 'ask' | 'properties')}>
      <Tab value="ask">Ask AI</Tab>
      <Tab value="properties" disabled={!detail} icon={detail ? <TypeIcon type={detail.type} extension={detail.extension} /> : undefined}>Properties</Tab>
    </TabList>
    <div className="right-panel-body">
      {tab === 'ask' && <>
        <div className="ask-ai-header">
          <div><h2 style={{ margin: 0, fontSize: 18 }}>Ask AI</h2><div className="muted small">Ground answers in up to 5 selected documents. Conversation {agentProps.conversationId.slice(0, 8)}</div></div>
          <Button size="small" icon={<AddRegular />} onClick={onNewChat}>New chat</Button>
        </div>
        <AgentChatPanel {...agentProps} />
      </>}
      {tab === 'properties' && detail && <DocumentDetail item={detail} configFields={configFields} onClose={() => { onCloseDetail(); setTab('ask'); }} onChat={(item) => { onChatWithDetail(item); setTab('ask'); }} />}
      {tab === 'properties' && !detail && <div className="muted small">Open a document from the results to see its properties here.</div>}
    </div>
  </aside>;
}

export type { ChatTurn };
