import { useState } from 'react';
import { Button, Dropdown, Input, Option } from '@fluentui/react-components';
import { ChevronDownRegular, ChevronRightRegular } from '@fluentui/react-icons';
import type { EntityType, SearchMode } from '../api/client';
import type { StoredSearch } from '../utils/storage';

const modeLabels: Record<SearchMode, string> = { keyword: 'Keyword', title: 'Title', author: 'Author / Owner', number: 'Number' };

export function SearchBar({ entity, text, mode, onTextChange, onModeChange, onSearch, onSave, recent, saved, onPickSearch, onClearRecent }: {
  entity: EntityType;
  text: string;
  mode: SearchMode;
  onTextChange: (value: string) => void;
  onModeChange: (mode: SearchMode) => void;
  onSearch: () => void;
  onSave: (name: string) => void;
  recent: StoredSearch[];
  saved: StoredSearch[];
  onPickSearch: (search: StoredSearch) => void;
  onClearRecent: () => void;
}) {
  const modes: SearchMode[] = entity === 'folders' || entity === 'clients' ? ['keyword'] : entity === 'matters' ? ['keyword', 'title', 'author'] : ['keyword', 'title', 'author', 'number'];
  const placeholder = entity === 'folders' ? 'Folder name (optional)' : entity === 'clients' ? 'Client query (optional)' : 'Search documents, emails, matters, folders, or clients';
  const [historyOpen, setHistoryOpen] = useState(false);
  const historyCount = recent.length + saved.length;
  const saveCurrent = () => {
    const name = window.prompt('Name this saved search');
    if (name) onSave(name);
  };
  return <div>
    <div className="search-row">
      <Input size="large" value={text} placeholder={placeholder} aria-label="Search text" onChange={(_, data) => onTextChange(data.value)} onKeyDown={(event) => { if (event.key === 'Enter') onSearch(); }} />
      <Dropdown value={modeLabels[mode]} selectedOptions={[mode]} onOptionSelect={(_, data) => onModeChange((data.optionValue ?? 'keyword') as SearchMode)} aria-label="Search mode">
        {modes.map((item) => <Option key={item} value={item}>{modeLabels[item]}</Option>)}
      </Dropdown>
      <Button appearance="primary" size="large" onClick={onSearch}>Search</Button>
    </div>
    <div className="row between" style={{ marginTop: 10 }}>
      <div className="row">
        <Button size="small" onClick={saveCurrent} disabled={!text.trim()}>Save search</Button>
        {historyCount > 0 && <Button size="small" appearance="subtle" icon={historyOpen ? <ChevronDownRegular /> : <ChevronRightRegular />} onClick={() => setHistoryOpen((value) => !value)} aria-expanded={historyOpen}>Recent & saved ({historyCount})</Button>}
        {recent.length > 0 && <Button size="small" onClick={onClearRecent}>Clear recent</Button>}
      </div>
      <span className="muted small">Search runs on Enter or Search only.</span>
    </div>
    {historyOpen && (recent.length > 0 || saved.length > 0) && <div className="saved-searches" style={{ marginTop: 10 }}>
      {recent.length > 0 && <div><strong className="small">Recent</strong><div className="row">{recent.slice(0, 5).map((item) => <Button key={`${item.entity}-${item.text}-${item.timestamp}`} size="small" onClick={() => onPickSearch(item)}>{item.entity}: {item.text || '(blank)'}</Button>)}</div></div>}
      {saved.length > 0 && <div><strong className="small">Saved</strong><div className="row">{saved.slice(0, 5).map((item) => <Button key={item.id} size="small" onClick={() => onPickSearch(item)}>{item.name}</Button>)}</div></div>}
    </div>}
  </div>;
}
