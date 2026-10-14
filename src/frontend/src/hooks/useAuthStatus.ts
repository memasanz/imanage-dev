import { useCallback, useEffect, useState } from 'react';
import { apiClient, type AuthStatusResponse, type UserProfile } from '../api/client';

export function useAuthStatus() {
  const [status, setStatus] = useState<AuthStatusResponse>({ work: false, mcp: false });
  const [user, setUser] = useState<UserProfile | undefined>();
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const next = await apiClient.authStatus();
    setStatus(next);
    if (next.work) {
      try { setUser(await apiClient.usersMe()); } catch { setUser(undefined); }
    } else {
      setUser(undefined);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const run = async () => {
      try { await refresh(); } finally { if (active) setLoading(false); }
    };
    run();
    const interval = window.setInterval(run, 5 * 60 * 1000);
    return () => { active = false; window.clearInterval(interval); };
  }, [refresh]);

  const startWork = useCallback(() => { window.location.assign('/api/auth/work/start'); }, []);
  const startMcp = useCallback(() => { window.location.assign('/api/auth/mcp/start'); }, []);
  const signOut = useCallback(async () => { await apiClient.logout(); setStatus({ work: false, mcp: false }); setUser(undefined); }, []);

  return { status, user, loading, refresh, startWork, startMcp, signOut };
}
