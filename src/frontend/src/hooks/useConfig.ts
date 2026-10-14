import { useEffect, useState } from 'react';
import { apiClient, ApiError, type ConfigResponse } from '../api/client';

export function useConfig() {
  const [config, setConfig] = useState<ConfigResponse | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    apiClient.config(controller.signal)
      .then(setConfig)
      .catch((err: unknown) => {
        if ((err as Error).name !== 'AbortError') setError(err instanceof ApiError ? err.friendlyMessage() : 'Unable to load UI config.');
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  return { config, loading, error };
}
