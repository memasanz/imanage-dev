import { useEffect, useState } from 'react';
import { Button, Spinner } from '@fluentui/react-components';
import { apiClient, type SearchResultItem } from '../api/client';
import { TypeIcon } from './ResultsList';
import { CollapsibleSection } from './CollapsibleSection';

export interface BreadcrumbItem { id: string; name: string; type: 'workspace' | 'folder' }

export function BrowsePanel({ active, trail, onTrailChange, onResults, onOpenDetail }: { active: boolean; trail: BreadcrumbItem[]; onTrailChange: (trail: BreadcrumbItem[]) => void; onResults: (items: SearchResultItem[]) => void; onOpenDetail: (item: SearchResultItem) => void }) {
  const [items, setItems] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  const loadRecent = async () => {
    setLoading(true); setError(undefined); onTrailChange([]);
    try { const response = await apiClient.recentWorkspaces(); setItems(response.results); onResults(response.results.map((item) => ({ ...item, type: item.type || 'matter' }))); }
    catch { setError('Unable to load recent matters.'); }
    finally { setLoading(false); }
  };

  useEffect(() => { if (active) void loadRecent(); }, [active]);

  const openContainer = async (container: SearchResultItem | BreadcrumbItem, keepTrail?: BreadcrumbItem[]) => {
    setLoading(true); setError(undefined);
    const type = String(container.type) === 'folder' ? 'folder' : 'workspace';
    try {
      const response = type === 'folder' ? await apiClient.folderChildren(container.id) : await apiClient.workspaceChildren(container.id);
      setItems(response.results); onResults(response.results);
      const nextTrail = keepTrail ?? [...trail, { id: container.id, name: container.name, type }];
      onTrailChange(nextTrail);
    } catch { setError('Unable to open this container.'); }
    finally { setLoading(false); }
  };

  return <CollapsibleSection title="Recent Matters & Browse" defaultOpen={false} actions={<Button size="small" onClick={() => void loadRecent()}>Root</Button>}>
    <div className="breadcrumb" aria-label="Breadcrumb"><Button appearance="transparent" onClick={() => void loadRecent()}>Recent Matters</Button>{trail.map((crumb, index) => <span key={crumb.id} className="row"><span>/</span>{index === trail.length - 1 ? <strong>{crumb.name}</strong> : <Button appearance="transparent" onClick={() => void openContainer(crumb, trail.slice(0, index + 1))}>{crumb.name}</Button>}</span>)}</div>
    {loading && <div className="row"><Spinner size="tiny" /> Loading…</div>}{error && <p>{error}</p>}
    <div className="row" style={{ marginTop: 8 }}>{items.slice(0, 20).map((item) => <Button key={item.id} icon={<TypeIcon type={item.type} extension={item.extension} />} onClick={() => ['folder','matter','workspace'].includes(String(item.type)) ? void openContainer(item) : onOpenDetail(item)}>{item.name}</Button>)}</div>
  </CollapsibleSection>;
}
