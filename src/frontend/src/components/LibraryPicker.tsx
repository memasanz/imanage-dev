import { Button, Checkbox } from '@fluentui/react-components';
import type { Library } from '../api/client';

export function LibraryPicker({ libraries, selected, setSelected }: { libraries: Library[]; selected: string[]; setSelected: (ids: string[]) => void }) {
  const allSelected = libraries.length > 0 && selected.length === libraries.length;
  const toggle = (id: string, checked: boolean) => setSelected(checked ? [...new Set([...selected, id])] : selected.filter((item) => item !== id));
  return <div className="library-bar" aria-label="Library scope">
    <strong>Libraries:</strong>
    {libraries.length === 0 && <span className="muted small">No libraries returned yet.</span>}
    {libraries.map((library) => <Checkbox key={library.id} label={library.name || library.id} checked={selected.includes(library.id)} onChange={(_, data) => toggle(library.id, Boolean(data.checked))} />)}
    <Button size="small" onClick={() => setSelected(allSelected ? [] : libraries.map((library) => library.id))}>{allSelected ? 'Clear all' : 'Select all'}</Button>
    <span className="muted small" title="Selecting every library omits the library filter and searches all.">All = no filter</span>
  </div>;
}
