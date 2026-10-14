import { Button } from '@fluentui/react-components';
import {
  DocumentRegular,
  MailRegular,
  FolderRegular,
  PeopleTeamRegular,
  BriefcaseRegular,
} from '@fluentui/react-icons';
import type { EntityType } from '../api/client';
import type { ReactElement } from 'react';

const labels: Record<EntityType, string> = { documents: 'Documents', emails: 'Emails', folders: 'Folders', clients: 'Clients', matters: 'Matters' };
const icons: Record<EntityType, ReactElement> = {
  documents: <DocumentRegular />,
  emails: <MailRegular />,
  folders: <FolderRegular />,
  clients: <PeopleTeamRegular />,
  matters: <BriefcaseRegular />,
};

export function ScopeChips({ entities, value, onChange }: { entities: EntityType[]; value: EntityType; onChange: (entity: EntityType) => void }) {
  return <div className="scope-grid" role="tablist" aria-label="Search scope">
    {entities.map((entity) => <Button key={entity} role="tab" icon={icons[entity]} appearance={value === entity ? 'primary' : 'secondary'} onClick={() => onChange(entity)}>{labels[entity] ?? entity}</Button>)}
  </div>;
}
