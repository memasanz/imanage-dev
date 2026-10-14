import { useEffect, useState } from 'react';
import { apiClient, type Library } from '../api/client';

export function useLibraries() {
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    apiClient.libraries(controller.signal).then((response) => {
      setLibraries(response.libraries);
      setSelected(response.libraries.map((library) => library.id));
    }).catch(() => setLibraries([]));
    return () => controller.abort();
  }, []);

  const effectiveLibraries = selected.length && selected.length < libraries.length ? selected : undefined;
  const allSelected = libraries.length > 0 && selected.length === libraries.length;

  return { libraries, selected, setSelected, effectiveLibraries, allSelected };
}
