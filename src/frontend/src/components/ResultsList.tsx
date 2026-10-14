import { useMemo, useRef, useState } from 'react';
import { Button, Checkbox, Menu, MenuItemCheckbox, MenuList, MenuPopover, MenuTrigger, Spinner } from '@fluentui/react-components';
import { BriefcaseRegular, DocumentBulletListRegular, DocumentPdfRegular, DocumentRegular, DocumentTableRegular, DocumentTextRegular, FolderRegular, MailRegular, PersonRegular, SlideTextRegular } from '@fluentui/react-icons';
import type { ReactNode } from 'react';
import type { ConfigField, SearchResponse, SearchResultItem } from '../api/client';
import { docNumber, fieldValue, formatBytes, formatDate, libraryOf, neutralText } from '../utils/format';
import { getColumnVisibility, getColumnWidths, setColumnVisibility, setColumnWidths } from '../utils/storage';

export type SortKey = 'name' | 'version' | 'doc' | 'updated' | 'size' | 'workspace';

function fileTypeIcon(extension?: string) {
  switch (String(extension || '').toLowerCase().replace(/^\./, '')) {
    case 'pdf': return <DocumentPdfRegular aria-label="PDF" />;
    case 'xlsx':
    case 'xls':
    case 'csv': return <DocumentTableRegular aria-label="Spreadsheet" />;
    case 'pptx':
    case 'ppt': return <SlideTextRegular aria-label="Presentation" />;
    case 'txt':
    case 'rtf': return <DocumentBulletListRegular aria-label="Text" />;
    case 'doc':
    case 'docx': return <DocumentTextRegular aria-label="Word document" />;
    default: return <DocumentRegular aria-label="Document" />;
  }
}

export function TypeIcon({ type, extension }: { type?: string; extension?: string }) {
  const ext = String(extension || '').toLowerCase().replace(/^\./, '');
  switch (String(type)) {
    case 'folder': return <FolderRegular aria-label="Folder" />;
    case 'client': return <PersonRegular aria-label="Client" />;
    case 'matter':
    case 'workspace': return <BriefcaseRegular aria-label="Matter" />;
    case 'email': return <MailRegular aria-label="Email" />;
    default:
      if (ext === 'eml' || ext === 'msg') return <MailRegular aria-label="Email" />;
      return fileTypeIcon(ext);
  }
}

interface Column {
  key: string;
  label: string;
  sortKey?: SortKey;
  defaultVisible: boolean;
  defaultWidth: number;
  render: (item: SearchResultItem) => ReactNode;
}

const BASE_COLUMNS: Column[] = [
  { key: 'name', label: 'Title', sortKey: 'name', defaultVisible: true, defaultWidth: 280,
    render: (item) => <div className="row" style={{ gap: 8, alignItems: 'flex-start' }}><span className="result-type-icon" aria-hidden={false}><TypeIcon type={item.type} extension={item.extension} /></span><span><div className="result-title">{item.name}</div><div className="muted small">{item.type} {item.extension ? `· ${item.extension}` : ''}</div></span></div> },
  { key: 'version', label: 'Version', sortKey: 'version', defaultVisible: true, defaultWidth: 90, render: (item) => item.version ?? '—' },
  { key: 'doc', label: 'Document Number', sortKey: 'doc', defaultVisible: true, defaultWidth: 150, render: (item) => docNumber(item) },
  { key: 'updated', label: 'Edit Date', sortKey: 'updated', defaultVisible: true, defaultWidth: 160, render: (item) => formatDate(item.updated_at) },
  { key: 'created', label: 'Create Date', defaultVisible: false, defaultWidth: 160, render: (item) => formatDate(item.created_at) },
  { key: 'size', label: 'File Size', sortKey: 'size', defaultVisible: true, defaultWidth: 110, render: (item) => formatBytes(Number(item.size ?? item.file_size ?? 0)) },
  { key: 'workspace', label: 'Workspace Name', sortKey: 'workspace', defaultVisible: true, defaultWidth: 180, render: (item) => fieldValue(item, 'workspace_name') || item.workspace_name || '—' },
  { key: 'author', label: 'Author', defaultVisible: true, defaultWidth: 150, render: (item) => neutralText(item.author) || '—' },
  { key: 'typist', label: 'Typist', defaultVisible: false, defaultWidth: 150, render: (item) => neutralText(item.typist) || '—' },
  { key: 'library', label: 'Library', defaultVisible: false, defaultWidth: 120, render: (item) => libraryOf(item) || '—' },
  { key: 'doctype', label: 'Doctype', defaultVisible: false, defaultWidth: 130, render: (item) => neutralText(item.doctype ?? item.class) || '—' },
];

export function ResultsList({ response, loading, error, authRequired, hasSearched, sortKey, sortDir, onSort, selectedIds, onToggle, onOpen, onDrill, onLoadMore, onCancel, onSignIn, onSelectFirstFive, configFields = [] }: {
  response?: SearchResponse;
  loading: boolean;
  error?: string;
  authRequired: boolean;
  hasSearched: boolean;
  sortKey: SortKey;
  sortDir: 'asc' | 'desc';
  onSort: (key: SortKey) => void;
  selectedIds: Set<string>;
  onToggle: (item: SearchResultItem, checked: boolean) => void;
  onOpen: (item: SearchResultItem) => void;
  onDrill: (item: SearchResultItem) => void;
  onLoadMore: () => void;
  onCancel: () => void;
  onSignIn: () => void;
  onSelectFirstFive: (items: SearchResultItem[]) => void;
  configFields?: ConfigField[];
}) {
  const columns = useMemo<Column[]>(() => {
    const dynamic: Column[] = configFields
      .filter((field) => !BASE_COLUMNS.some((col) => col.key === field.key))
      .map((field) => ({ key: field.key, label: field.label || field.key, defaultVisible: false, defaultWidth: 150, render: (item: SearchResultItem) => neutralText(item.fields?.[field.key]) || '—' }));
    return [...BASE_COLUMNS, ...dynamic];
  }, [configFields]);

  const [visibility, setVisibility] = useState<Record<string, boolean>>(() => getColumnVisibility());
  const [widths, setWidths] = useState<Record<string, number>>(() => getColumnWidths());
  const drag = useRef<{ key: string; startX: number; startWidth: number } | null>(null);

  const isVisible = (col: Column) => visibility[col.key] ?? col.defaultVisible;
  const widthOf = (col: Column) => widths[col.key] ?? col.defaultWidth;
  const visibleColumns = columns.filter(isVisible);

  const setColumnsVisible = (checkedKeys: string[]) => {
    const next = Object.fromEntries(columns.map((col) => [col.key, checkedKeys.includes(col.key)]));
    setVisibility(next); setColumnVisibility(next);
  };

  const startResize = (col: Column, event: React.MouseEvent) => {
    event.preventDefault(); event.stopPropagation();
    drag.current = { key: col.key, startX: event.clientX, startWidth: widthOf(col) };
    const onMove = (move: MouseEvent) => {
      if (!drag.current) return;
      const delta = move.clientX - drag.current.startX;
      const width = Math.max(60, drag.current.startWidth + delta);
      setWidths((prev) => ({ ...prev, [drag.current!.key]: width }));
    };
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      setWidths((prev) => { setColumnWidths(prev); return prev; });
      drag.current = null;
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  if (loading) return <div className="panel row"><Spinner size="tiny" /> <strong>Searching…</strong><Button onClick={onCancel}>Cancel</Button></div>;
  if (authRequired) return <div className="panel"><h3>Sign In Required</h3><p>Connect to the Work API to complete this action.</p><Button appearance="primary" onClick={onSignIn}>Sign In</Button></div>;
  if (error) return <div className="panel"><h3>Search error</h3><p>{error}</p></div>;
  if (!hasSearched) return <div className="panel"><h3>Start with search or Recent Matters</h3><p className="muted">Choose a scope, enter criteria, and press Search. No search-as-you-type is used.</p></div>;
  if (!response || response.results.length === 0) return <div className="panel"><h3>No Matches!</h3><p className="muted">Try another term, library, or filter.</p></div>;

  const loaded = response.results.length;
  const moreMayExist = loaded >= response.page_size && response.page_size < 5000;
  return <div className="panel">
    <div className="results-header">
      <strong>1 – {loaded} of {response.total}{moreMayExist ? '+' : ''}</strong>
      <div className="row">
        <Menu>
          <MenuTrigger disableButtonEnhancement><Button>Columns</Button></MenuTrigger>
          <MenuPopover><MenuList checkedValues={{ columns: visibleColumns.map((col) => col.key) }} onCheckedValueChange={(_, data) => setColumnsVisible(data.checkedItems)}>
            {columns.map((col) => <MenuItemCheckbox key={col.key} name="columns" value={col.key}>{col.label}</MenuItemCheckbox>)}
          </MenuList></MenuPopover>
        </Menu>
        <Button disabled={!moreMayExist} onClick={onLoadMore}>Load more</Button>
      </div>
    </div>
    <div className="table-wrap"><table className="results">
      <colgroup>
        <col style={{ width: 40 }} />
        {visibleColumns.map((col) => <col key={col.key} style={{ width: widthOf(col) }} />)}
        <col style={{ width: 200 }} />
      </colgroup>
      <thead><tr>
        <th><Checkbox aria-label="Select first five sorted results" checked={response.results.slice(0, 5).filter((item) => ['document','email'].includes(String(item.type)) || item.extension).every((item) => selectedIds.has(item.id))} onChange={(_, data) => onSelectFirstFive(Boolean(data.checked) ? response.results.slice(0, 5) : [])} /></th>
        {visibleColumns.map((col) => <th key={col.key} style={{ width: widthOf(col) }} className="resizable-th">
          {col.sortKey
            ? <Button appearance="transparent" onClick={() => onSort(col.sortKey!)}>{col.label}{sortKey === col.sortKey ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}</Button>
            : <span className="col-label">{col.label}</span>}
          <span className="col-resizer" onMouseDown={(event) => startResize(col, event)} role="separator" aria-label={`Resize ${col.label}`} />
        </th>)}
        <th>Actions</th>
      </tr></thead>
      <tbody>{response.results.map((item) => <tr key={item.id}>
        <td><Checkbox checked={selectedIds.has(item.id)} onChange={(_, data) => onToggle(item, Boolean(data.checked))} aria-label={`Select ${item.name}`} /></td>
        {visibleColumns.map((col) => <td key={col.key} className="cell-clip">{col.render(item)}</td>)}
        <td className="row"><Button size="small" onClick={() => onOpen(item)}>Open</Button>{['folder','matter'].includes(String(item.type)) && <Button size="small" onClick={() => onDrill(item)}>Drill in</Button>}<Button size="small" onClick={() => onOpen(item)}>Versions</Button></td>
      </tr>)}</tbody>
    </table></div>
  </div>;
}
