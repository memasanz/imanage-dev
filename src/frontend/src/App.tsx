import { useEffect, useMemo, useState } from 'react';
import { Button, FluentProvider, Spinner, Switch, webLightTheme, webDarkTheme } from '@fluentui/react-components';
import { WeatherMoonRegular, WeatherSunnyRegular } from '@fluentui/react-icons';
import { ConnectBar } from './components/ConnectBar';
import { ScopeChips } from './components/ScopeChips';
import { SearchBar } from './components/SearchBar';
import { AdvancedFilterBuilder } from './components/AdvancedFilterBuilder';
import { LibraryPicker } from './components/LibraryPicker';
import { ResultsList, type SortKey } from './components/ResultsList';
import { BrowsePanel, type BreadcrumbItem } from './components/BrowsePanel';
import { RightPanel } from './components/RightPanel';
import { useConfig } from './hooks/useConfig';
import { useAuthStatus } from './hooks/useAuthStatus';
import { useLibraries } from './hooks/useLibraries';
import { useSearch } from './hooks/useSearch';
import { useAgent } from './hooks/useAgent';
import { addRecentSearch, clearRecentSearches, getRecentSearches, getSavedSearches, saveSearch, type StoredSearch } from './utils/storage';
import { apiClient, type EntityType, type SearchFilter, type SearchMode, type SearchResultItem } from './api/client';
import { docNumber, fieldValue } from './utils/format';
import './styles.css';

export default function App() {
  const { config, loading: configLoading, error: configError } = useConfig();
  const auth = useAuthStatus();
  const libraries = useLibraries();
  const search = useSearch();
  const agent = useAgent();
  const [entity, setEntity] = useState<EntityType>('documents');
  const [mode, setMode] = useState<SearchMode>('keyword');
  const [text, setText] = useState('');
  const [filters, setFilters] = useState<SearchFilter[]>([]);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [detail, setDetail] = useState<SearchResultItem | undefined>();
  const [trail, setTrail] = useState<BreadcrumbItem[]>([]);
  const [pageSize, setPageSize] = useState(500);
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [recent, setRecent] = useState<StoredSearch[]>(() => getRecentSearches());
  const [saved, setSaved] = useState<StoredSearch[]>(() => getSavedSearches());
  const [dark, setDark] = useState<boolean>(() => localStorage.getItem('imanage.ai.theme') === 'dark');
  const theme = dark ? webDarkTheme : webLightTheme;
  const toggleTheme = () => setDark((value) => { const next = !value; localStorage.setItem('imanage.ai.theme', next ? 'dark' : 'light'); return next; });

  useEffect(() => {
    const url = new URL(window.location.href);
    if (url.searchParams.has('code') || url.searchParams.has('state')) {
      window.history.replaceState({}, document.title, url.pathname + url.hash);
      void auth.refresh().then(() => {
        if (!auth.status.mcp) auth.startMcp();
      });
    }
  }, []);

  const entities: EntityType[] = config?.entities?.length ? config.entities : ['documents', 'emails', 'folders', 'clients', 'matters'];
  const cleanFilters = filters.filter((filter) => filter.value.trim() && !(filter.key === 'doctype' && filter.value === 'Any Type'));

  const sortedResponse = useMemo(() => {
    if (!search.response) return undefined;
    const sorted = [...search.response.results].sort((a, b) => compare(a, b, sortKey) * (sortDir === 'asc' ? 1 : -1));
    return { ...search.response, results: sorted };
  }, [search.response, sortDir, sortKey]);

  const executeSearch = async (override?: Partial<{ entity: EntityType; pageSize: number; text: string; mode: SearchMode }>) => {
    const nextEntity = override?.entity ?? entity;
    const nextText = override?.text ?? text;
    const nextMode = override?.mode ?? mode;
    const nextPageSize = override?.pageSize ?? pageSize;
    await search.run({ entity: nextEntity, mode: nextMode, text: nextText, libraries: libraries.effectiveLibraries, filters: cleanFilters, pageSize: nextPageSize });
    if (nextText.trim()) setRecent(addRecentSearch({ entity: nextEntity, text: nextText, mode: nextMode, libraries: libraries.selected }));
  };

  const handleScopeChange = (next: EntityType) => {
    if (next === entity) return;
    setEntity(next); setMode('keyword'); setDetail(undefined); setTrail([]); setSyntheticResults(undefined); setPageSize(500); setSortKey('name'); setSortDir('asc'); search.clear();
    const hasCriteria = text.trim() || cleanFilters.length > 0;
    if (next === 'folders' || next === 'clients') { setText(''); void executeSearch({ entity: next, mode: 'keyword', pageSize: 500, text: '' }); }
    else if (hasCriteria) void executeSearch({ entity: next, mode: 'keyword', pageSize: 500 });
  };

  const handleModeChange = (next: SearchMode) => { setMode(next); setSyntheticResults(undefined); search.clear(); };
  const handleTextChange = (value: string) => { setText(value); setSyntheticResults(undefined); search.clear(); };
  const handleSort = (key: SortKey) => { if (key === sortKey) setSortDir(sortDir === 'asc' ? 'desc' : 'asc'); else { setSortKey(key); setSortDir('asc'); } };
  const handleLoadMore = () => { setPageSize(5000); void executeSearch({ pageSize: 5000 }); };

  const applyStoredSearch = (stored: StoredSearch) => {
    setEntity(stored.entity); setText(stored.text); setMode(stored.mode); setDetail(undefined); search.clear();
    if (stored.libraries?.length) libraries.setSelected(stored.libraries);
  };

  const selectFirstFive = (items: SearchResultItem[]) => {
    if (items.length === 0) { void agent.clear(); return; }
    items.filter((item) => ['document','email'].includes(String(item.type)) || item.extension).slice(0, 5).forEach((item) => void agent.add(item));
  };

  const handleBrowseResults = (items: SearchResultItem[]) => {
    search.clear();
    setSyntheticResults(items);
  };

  const [syntheticResults, setSyntheticResults] = useState<SearchResultItem[] | undefined>();
  const displayedResponse = syntheticResults ? { total: syntheticResults.length, page: 1, page_size: syntheticResults.length || 500, results: syntheticResults } : sortedResponse;

  const drillContainer = async (item: SearchResultItem) => {
    const isFolder = String(item.type) === 'folder';
    const response = isFolder ? await apiClient.folderChildren(item.id) : await apiClient.workspaceChildren(item.id);
    setTrail((current) => [...current, { id: item.id, name: item.name, type: isFolder ? 'folder' : 'workspace' }]);
    handleBrowseResults(response.results);
  };

  const openChat = () => document.querySelector<HTMLElement>('[aria-label="Ask AI panel"]')?.focus();
  const openCitation = (id: string) => {
    const found = displayedResponse?.results.find((item) => item.id === id);
    if (found) setDetail(found);
  };

  if (configLoading) return <FluentProvider theme={theme}><div className="panel row" style={{ margin: 24 }}><Spinner /> Loading iManage AI Workspace…</div></FluentProvider>;

  return <FluentProvider theme={theme}>
    <div className="app">
      <header className="header"><div className="header-inner">
        <div className="brand"><h1>iManage AI Workspace</h1><span>Search, browse, and ask grounded questions over private Work content.</span></div>
        <div className="header-actions">
          <Button appearance="transparent" icon={dark ? <WeatherSunnyRegular /> : <WeatherMoonRegular />} onClick={toggleTheme} aria-label="Toggle theme">{dark ? 'Light' : 'Dark'}</Button>
          <ConnectBar status={auth.status} user={auth.user} mode={config?.mode} startWork={auth.startWork} startMcp={auth.startMcp} signOut={async () => { await auth.signOut(); search.clear(); setSyntheticResults(undefined); await agent.clear(); }} />
        </div>
      </div></header>
      <main className="shell">
        <div className="main-column">
          {configError && <section className="panel"><strong>Config error</strong><p>{configError}</p></section>}
          <section className="panel hero">
            <ScopeChips entities={entities} value={entity} onChange={handleScopeChange} />
            <div className="library-top"><LibraryPicker libraries={libraries.libraries} selected={libraries.selected} setSelected={libraries.setSelected} /></div>
            <SearchBar entity={entity} text={text} mode={mode} onTextChange={handleTextChange} onModeChange={handleModeChange} onSearch={() => { setSyntheticResults(undefined); void executeSearch(); }} onSave={(name) => setSaved(saveSearch({ name, entity, text, mode, libraries: libraries.selected }))} recent={recent} saved={saved} onPickSearch={applyStoredSearch} onClearRecent={() => { clearRecentSearches(); setRecent([]); }} />
            <div className="row between" style={{ marginTop: 12 }}><Switch checked={advancedOpen} onChange={(_, data) => setAdvancedOpen(Boolean(data.checked))} label="Advanced filters" /><span className="muted small">{entity === 'folders' || entity === 'clients' ? 'Term optional — empty lists all.' : 'Empty search is allowed when browsing a matter.'}</span></div>
            {advancedOpen && <AdvancedFilterBuilder entity={entity} configFields={config?.fields ?? []} filters={filters} onChange={(next) => { setFilters(next); search.clear(); }} onEnter={() => void executeSearch()} />}
          </section>
          {entity === 'matters' && <BrowsePanel active trail={trail} onTrailChange={setTrail} onResults={handleBrowseResults} onOpenDetail={setDetail} />}
          {agent.selected.length > 0 && <div className="selected-bar"><strong>{agent.selected.length} selected for AI context</strong><div className="row"><Button appearance="primary" onClick={openChat}>Open Chat</Button><Button onClick={() => void agent.clear()}>Clear</Button></div></div>}
          <ResultsList response={displayedResponse} loading={search.loading} error={search.error} authRequired={search.authRequired} hasSearched={Boolean(syntheticResults) || search.hasSearched} sortKey={sortKey} sortDir={sortDir} onSort={handleSort} selectedIds={new Set(agent.selected.map((item) => item.id))} onToggle={(item, checked) => void agent.toggle(item, checked)} onOpen={setDetail} onDrill={(item) => void drillContainer(item)} onLoadMore={handleLoadMore} onCancel={search.cancel} onSignIn={auth.startWork} onSelectFirstFive={selectFirstFive} configFields={config?.fields ?? []} />
        </div>
        <RightPanel detail={detail} configFields={config?.fields ?? []} onCloseDetail={() => setDetail(undefined)} onChatWithDetail={(item) => void agent.add(item)} onNewChat={() => { setDetail(undefined); void agent.newChat(); }} agentProps={{ selected: agent.selected, turns: agent.turns, loading: agent.loading, conversationId: agent.conversationId, onRemove: (id) => void agent.remove(id), onClear: () => void agent.clear(), onSend: (message) => void agent.send(message), onCitationClick: openCitation }} />
      </main>
    </div>
  </FluentProvider>;
}

function compare(a: SearchResultItem, b: SearchResultItem, key: SortKey) {
  const value = (item: SearchResultItem) => {
    if (key === 'name') return item.name ?? '';
    if (key === 'version') return Number(item.version ?? 0);
    if (key === 'doc') return docNumber(item);
    if (key === 'updated') return item.updated_at ?? '';
    if (key === 'size') return Number(item.size ?? item.file_size ?? 0);
    return fieldValue(item, 'workspace_name') || item.workspace_name || '';
  };
  const left = value(a); const right = value(b);
  return typeof left === 'number' && typeof right === 'number' ? left - right : String(left).localeCompare(String(right));
}
