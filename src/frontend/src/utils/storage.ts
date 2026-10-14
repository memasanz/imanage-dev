import type { EntityType, SearchMode } from '../api/client';

export interface StoredSearch {
  id?: string;
  name?: string;
  entity: EntityType;
  text: string;
  mode: SearchMode;
  libraries?: string[];
  timestamp: number;
}

const recentKey = 'imanage.ai.recentSearches';
const savedKey = 'imanage.ai.savedSearches';

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write<T>(key: string, value: T) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function getRecentSearches() { return read<StoredSearch[]>(recentKey, []); }
export function getSavedSearches() { return read<StoredSearch[]>(savedKey, []); }
export function clearRecentSearches() { write(recentKey, []); }

export function addRecentSearch(search: Omit<StoredSearch, 'timestamp'>) {
  const next = [
    { ...search, timestamp: Date.now() },
    ...getRecentSearches().filter((item) => !(item.entity === search.entity && item.text.trim().toLowerCase() === search.text.trim().toLowerCase()))
  ].slice(0, 10);
  write(recentKey, next);
  return next;
}

export function saveSearch(search: Omit<StoredSearch, 'id' | 'timestamp'>) {
  const next = [{ ...search, id: crypto.randomUUID(), timestamp: Date.now() }, ...getSavedSearches()];
  write(savedKey, next);
  return next;
}

export function deleteSavedSearch(id: string) {
  const next = getSavedSearches().filter((item) => item.id !== id);
  write(savedKey, next);
  return next;
}

const columnVisKey = 'imanage.ai.columnVisibility';
const columnWidthKey = 'imanage.ai.columnWidths';

export function getColumnVisibility() { return read<Record<string, boolean>>(columnVisKey, {}); }
export function setColumnVisibility(value: Record<string, boolean>) { write(columnVisKey, value); }
export function getColumnWidths() { return read<Record<string, number>>(columnWidthKey, {}); }
export function setColumnWidths(value: Record<string, number>) { write(columnWidthKey, value); }
