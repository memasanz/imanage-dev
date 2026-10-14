import { Badge, Button } from '@fluentui/react-components';
import type { AuthStatusResponse, UserProfile } from '../api/client';

interface Props {
  status: AuthStatusResponse;
  user?: UserProfile;
  mode?: 'mock' | 'live';
  startWork: () => void;
  startMcp: () => void;
  signOut: () => Promise<void>;
}

export function ConnectBar({ status, user, mode, startWork, startMcp, signOut }: Props) {
  const userName = user?.display_name ?? user?.name ?? user?.text ?? user?.email;
  return <div className="connectbar" aria-label="Connection status">
    {mode === 'mock' && <Badge appearance="tint" color={status.work ? 'success' : 'informative'}>Demo data</Badge>}
    <Badge appearance="tint" color={status.work ? 'success' : 'danger'}>API {status.work ? '✓' : '✗'}</Badge>
    <Badge appearance="tint" color={status.mcp ? 'success' : 'danger'}>MCP {status.mcp ? '✓' : '✗'}</Badge>
    {userName && <span className="muted small">{userName}</span>}
    {!status.work && <Button size="small" appearance="primary" onClick={startWork}>Sign In</Button>}
    {status.work && !status.mcp && <Button size="small" onClick={startMcp}>Connect MCP</Button>}
    {status.work && status.mcp && <Button size="small" onClick={() => void signOut()}>Sign Out</Button>}
  </div>;
}
