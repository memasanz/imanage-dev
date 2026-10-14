import { useState, type ReactNode } from 'react';
import { Button } from '@fluentui/react-components';
import { ChevronDownRegular, ChevronRightRegular } from '@fluentui/react-icons';

export function CollapsibleSection({ title, defaultOpen = false, actions, children, className }: {
  title: ReactNode;
  defaultOpen?: boolean;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return <section className={`panel collapsible${className ? ` ${className}` : ''}`}>
    <div className="row between">
      <Button appearance="subtle" size="small" icon={open ? <ChevronDownRegular /> : <ChevronRightRegular />} onClick={() => setOpen((value) => !value)} aria-expanded={open}>{title}</Button>
      {actions}
    </div>
    {open && <div className="collapsible-body">{children}</div>}
  </section>;
}
