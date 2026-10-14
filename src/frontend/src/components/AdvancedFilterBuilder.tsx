import { Button, Dropdown, Input, Option } from '@fluentui/react-components';
import type { ConfigField, EntityType, SearchFilter } from '../api/client';

interface DraftFilter extends SearchFilter { id: string }
const builtin = ['title', 'keyword', 'author', 'doctype'];
const doctypeOptions = ['Any Type', 'Word', 'Excel', 'PDF', 'PowerPoint', 'Email', 'Text', 'HTML'];
const entityFieldNames: Record<EntityType, string[]> = {
  documents: ['application','author','author_typist','bcc','body','cc','category','client','comments','create_date','department','document_number','doctype','edit_date','from','keyword','last_user','matter','matter_lead','received','sent','subclass','to','typist','version'],
  emails: ['application','author','author_typist','bcc','body','cc','category','client','comments','create_date','department','document_number','doctype','edit_date','from','keyword','last_user','matter','matter_lead','received','sent','subclass','to','typist','version'],
  matters: ['category','client','create_date','department','description','edit_date','keyword','matter','matter_close_date','matter_lead','matter_open_date','matteruno','author','title'],
  folders: ['author'],
  clients: ['keyword']
};

export function AdvancedFilterBuilder({ entity, configFields, filters, onChange, onEnter }: { entity: EntityType; configFields: ConfigField[]; filters: SearchFilter[]; onChange: (filters: SearchFilter[]) => void; onEnter: () => void }) {
  const options = Array.from(new Set([...builtin, ...entityFieldNames[entity], ...configFields.filter((field) => field.filterable || field.searchable).map((field) => field.key)]));
  const drafts: DraftFilter[] = filters.map((filter, index) => ({ ...filter, id: `${filter.key}-${index}` }));
  const label = (key: string) => configFields.find((field) => field.key === key)?.label ?? key.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
  const update = (index: number, patch: Partial<SearchFilter>) => onChange(drafts.map((filter, current) => current === index ? { ...filter, ...patch } : filter).map(({ id: _id, ...filter }) => filter));
  return <div>
    <div className="row between"><strong>Advanced filters</strong><span className="muted small">Neutral keys only; unmapped custom fields are hidden.</span></div>
    {drafts.map((filter, index) => <div className="filter-grid" key={filter.id}>
      <Dropdown value={label(filter.key)} selectedOptions={[filter.key]} onOptionSelect={(_, data) => update(index, { key: data.optionValue ?? 'keyword' })} aria-label="Filter field">
        {options.map((option) => <Option key={option} value={option}>{label(option)}</Option>)}
      </Dropdown>
      <Dropdown value={filter.op === 'contains' ? 'Contains' : filter.op === 'not_contains' ? 'Does Not Contain' : 'Contains Exactly'} selectedOptions={[filter.op]} onOptionSelect={(_, data) => update(index, { op: (data.optionValue ?? 'contains') as SearchFilter['op'] })} aria-label="Operator" disabled={filter.key === 'doctype'}>
        <Option value="contains">Contains</Option><Option value="is">Contains Exactly</Option><Option value="not_contains">Does Not Contain</Option>
      </Dropdown>
      {filter.key === 'doctype' ? <Dropdown value={filter.value || 'Any Type'} selectedOptions={[filter.value || 'Any Type']} onOptionSelect={(_, data) => update(index, { op: 'is', value: data.optionValue === 'Any Type' ? '' : data.optionValue ?? '' })}>{doctypeOptions.map((type) => <Option key={type} value={type}>{type}</Option>)}</Dropdown> : <Input value={filter.value} onChange={(_, data) => update(index, { value: data.value })} onKeyDown={(event) => { if (event.key === 'Enter') onEnter(); }} aria-label="Filter value" />}
      <Button onClick={() => onChange(drafts.filter((_, current) => current !== index).map(({ id: _id, ...item }) => item))}>Remove</Button>
    </div>)}
    <Button style={{ marginTop: 8 }} onClick={() => onChange([...filters, { key: 'keyword', op: 'contains', value: '' }])}>Add another field</Button>
  </div>;
}
