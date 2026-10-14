import { useEffect, useState } from 'react';
import { Badge, Button, Spinner, Tab, TabList } from '@fluentui/react-components';
import { apiClient, ApiError, type ConfigField, type DocumentDetail as Detail, type DocumentVersion, type SearchResultItem } from '../api/client';
import { docNumber, dynamicDetailRows, extractTextFromUnknown, formatBytes, formatDate, imanageDeepLink, libraryOf, neutralText } from '../utils/format';

export function DocumentDetail({ item, configFields, onClose, onChat }: { item: SearchResultItem; configFields: ConfigField[]; onClose: () => void; onChat: (item: SearchResultItem) => void }) {
  const [tab, setTab] = useState('properties');
  const [detail, setDetail] = useState<Detail>(item);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState('');
  const [source, setSource] = useState<string | undefined>();
  const [previewState, setPreviewState] = useState('Not loaded');
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    const controller = new AbortController();
    setDetail(item); setVersions([]); setError(undefined); setTab('properties'); setPreview(''); setPreviewState('Not loaded');
    setLoading(true);
    Promise.all([
      apiClient.document(item.id, controller.signal).then(setDetail).catch(() => setDetail(item)),
      apiClient.documentVersions(item.id, controller.signal).then((response) => setVersions(response.versions)).catch(() => setVersions([]))
    ]).finally(() => setLoading(false));
    return () => controller.abort();
  }, [item]);

  const loadPreview = async () => {
    setPreviewState('Loading 0 of 1 chunk(s)…'); setError(undefined);
    try {
      const response = await apiClient.documentText(item.id);
      const text = response.text ?? extractTextFromUnknown(response);
      setPreview(text || 'No extracted text is available for this document.');
      setSource(response.source);
      setPreviewState(`Loaded ${text ? 1 : 0} of 1 chunk(s)`);
    } catch (err: unknown) {
      setPreview(''); setPreviewState('Preview error');
      setError(err instanceof ApiError ? err.friendlyMessage() : 'Preview error.');
    }
  };

  const link = imanageDeepLink(detail);
  const rows = [
    ['Name', detail.name], ['Version', detail.version], ['Document Number', docNumber(detail)], ['Library', libraryOf(detail)],
    ['Edit Date', formatDate(detail.updated_at)], ['Create Date', formatDate(detail.created_at)], ['File Size', formatBytes(Number(detail.size ?? detail.file_size ?? 0))],
    ['Author', neutralText(detail.author)], ['Typist', neutralText(detail.typist)], ['Comments', detail.comments], ['Application', detail.application],
    ['Doctype', neutralText(detail.doctype ?? detail.class)], ['Workspace', detail.workspace_name], ['Category', detail.category], ['Department', detail.department],
    ['Office', detail.office], ['Security', detail.default_security ?? 'Public'], ...dynamicDetailRows(detail, configFields).map((row) => [row.label, row.value])
  ].filter(([, value]) => value !== undefined && value !== null && value !== '' && value !== '—');

  return <div className="detail" aria-label="Document detail">
    <div className="row between"><h2 style={{ margin: 0, fontSize: 18 }}>{detail.name}</h2><Button size="small" onClick={onClose}>Close</Button></div>
    <div className="row"><Button appearance="primary" onClick={() => onChat(detail)}>Chat with this document</Button>{link && <Button as="a" href={link}>Open in iManage</Button>}{loading && <Spinner size="tiny" />}</div>
    <TabList selectedValue={tab} onTabSelect={(_, data) => setTab(String(data.value))}>
      <Tab value="properties">Properties</Tab><Tab value="preview">Preview</Tab><Tab value="versions">Versions</Tab><Tab value="security">Security</Tab>
    </TabList>
    {tab === 'properties' && <dl className="detail-grid">{rows.map(([label, value]) => <div key={String(label)}><dt>{label}</dt><dd>{String(value)}</dd></div>)}</dl>}
    {tab === 'preview' && <div>
      <div className="row"><Button onClick={() => void loadPreview()}>{preview ? 'Refresh' : 'Load Preview'}</Button>{source && <Badge>{source} text</Badge>}<span className="muted small">{previewState}</span></div>
      {error && <p>{error}</p>}<div className="preview-box">{preview || 'Use Load Preview to fetch extracted text.'}</div>
    </div>}
    {tab === 'versions' && <div className="table-wrap"><table className="results"><thead><tr><th>Version</th><th>Edit Date</th><th>File Size</th></tr></thead><tbody>{(versions.length ? versions : [{ version: detail.version ?? 1, updated_at: detail.updated_at, size: Number(detail.size ?? detail.file_size ?? 0) }]).map((version) => <tr key={version.version}><td>{version.version}</td><td>{formatDate(version.updated_at)}</td><td>{formatBytes(version.size)}</td></tr>)}</tbody></table></div>}
    {tab === 'security' && <p>Default security: <strong>{detail.default_security ?? 'Public'}</strong></p>}
  </div>;
}
