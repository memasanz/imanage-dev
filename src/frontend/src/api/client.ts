export type EntityType = 'documents' | 'emails' | 'folders' | 'clients' | 'matters';
export type SearchMode = 'keyword' | 'title' | 'author' | 'number';
export type AppMode = 'mock' | 'live';

export interface ApiErrorBody {
  error: { code: string; message: string; correlation_id?: string };
}

export class ApiError extends Error {
  status: number;
  code: string;
  correlationId?: string;
  bodyExcerpt: string;

  constructor(status: number, body: ApiErrorBody | string) {
    const message = typeof body === 'string' ? body : body.error.message;
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = typeof body === 'string' ? `http_${status}` : body.error.code;
    this.correlationId = typeof body === 'string' ? undefined : body.error.correlation_id;
    this.bodyExcerpt = typeof body === 'string' ? body.slice(0, 240) : JSON.stringify(body).slice(0, 240);
  }

  friendlyMessage() {
    const suffix = this.correlationId ? ` Correlation: ${this.correlationId}` : '';
    return `HTTP ${this.status}: ${this.message}${suffix}`;
  }
}

export interface HealthResponse {
  status: 'ok' | string;
  mode: AppMode;
  work_connected: boolean;
  mcp_connected: boolean;
}

export interface ConfigField {
  key: string;
  label: string;
  searchable: boolean;
  filterable: boolean;
  show_in_detail: boolean;
}

export interface ConfigResponse {
  mode: AppMode;
  fields: ConfigField[];
  entities: EntityType[];
  features: { agent?: boolean; [key: string]: boolean | undefined };
}

export interface AuthStatusResponse { work: boolean; mcp: boolean }
export interface UserProfile { id?: string; name?: string; display_name?: string; email?: string; text?: string }
export interface Library { id: string; name: string }
export interface LibrariesResponse { libraries: Library[] }
export interface NeutralValue { id?: string | number; text?: string; value?: string | number }
export type NeutralFields = Record<string, NeutralValue | string | number | boolean | null | undefined>;

export interface SearchFilter { key: string; op: 'contains' | 'is' | 'not_contains'; value: string }
export interface SearchRequest {
  entity: EntityType;
  mode: SearchMode;
  text: string;
  libraries?: string[];
  filters?: SearchFilter[];
  page: number;
  page_size: number;
}

export interface SearchResultItem {
  id: string;
  type: 'document' | 'email' | 'folder' | 'client' | 'matter' | string;
  name: string;
  extension?: string;
  version?: number;
  author?: NeutralValue;
  typist?: NeutralValue;
  class?: NeutralValue | string;
  fields?: NeutralFields;
  updated_at?: string;
  created_at?: string;
  size?: number;
  file_size?: number;
  doc_num?: string | number;
  document_number?: string | number;
  library?: string;
  workspace_id?: string;
  workspace_name?: string;
  default_security?: string;
  comments?: string;
  application?: string;
  doctype?: string;
  category?: string;
  department?: string;
  office?: string;
  [key: string]: unknown;
}

export interface SearchResponse {
  total: number;
  page: number;
  page_size: number;
  results: SearchResultItem[];
}

export interface RecentWorkspacesResponse { results: SearchResultItem[] }
export interface ChildrenResponse { results: SearchResultItem[] }
export interface DocumentDetail extends SearchResultItem { versions_count?: number }
export interface DocumentVersion { version: number; updated_at?: string; size?: number }
export interface DocumentVersionsResponse { versions: DocumentVersion[] }
export interface DocumentTextResponse { text?: string; source?: 'mcp' | 'work' | string; truncated?: boolean; [key: string]: unknown }
export interface ContextDocument { id: string; name: string; library?: string }
export interface ContextResponse { documents: ContextDocument[] }
export interface ContextAddRequest { id: string }
export interface AgentTurnRequest { message: string; document_ids: string[] }
export interface AgentCitation { id: string; name: string; library?: string; confidence?: number }
export interface AgentTraceItem { tool?: string; name?: string; status?: string; args?: unknown; ms?: number; latency_ms?: number }
export interface AgentTurnResponse { answer: string; citations: AgentCitation[]; trace: AgentTraceItem[]; correlation_id: string; needs_consent?: boolean; consent_url?: string }

async function parseError(response: Response): Promise<ApiError> {
  const text = await response.text();
  try {
    return new ApiError(response.status, JSON.parse(text) as ApiErrorBody);
  } catch {
    return new ApiError(response.status, text || response.statusText);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await fetch(path, { ...init, headers, credentials: 'same-origin' });
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const encode = (value: string) => encodeURIComponent(value);

export const apiClient = {
  health: (signal?: AbortSignal) => request<HealthResponse>('/api/health', { signal }),
  config: (signal?: AbortSignal) => request<ConfigResponse>('/api/config', { signal }),
  authStatus: (signal?: AbortSignal) => request<AuthStatusResponse>('/api/auth/status', { signal }),
  logout: () => request<void>('/api/auth/logout', { method: 'POST' }),
  usersMe: (signal?: AbortSignal) => request<UserProfile>('/api/users/me', { signal }),
  libraries: (signal?: AbortSignal) => request<LibrariesResponse>('/api/libraries', { signal }),
  clientsSearch: (q: string, signal?: AbortSignal) => request<{ results: SearchResultItem[] }>(`/api/clients/search?q=${encode(q)}`, { signal }),
  usersSearch: (q: string, signal?: AbortSignal) => request<{ results: UserProfile[] }>(`/api/users/search?q=${encode(q)}`, { signal }),
  search: (body: SearchRequest, signal?: AbortSignal) => request<SearchResponse>('/api/search', { method: 'POST', body: JSON.stringify(body), signal }),
  recentWorkspaces: (signal?: AbortSignal) => request<RecentWorkspacesResponse>('/api/workspaces/recent', { signal }),
  workspaceChildren: (id: string, signal?: AbortSignal) => request<ChildrenResponse>(`/api/workspaces/${encode(id)}/children`, { signal }),
  folderChildren: (id: string, signal?: AbortSignal) => request<ChildrenResponse>(`/api/folders/${encode(id)}/children`, { signal }),
  document: (id: string, signal?: AbortSignal) => request<DocumentDetail>(`/api/documents/${encode(id)}`, { signal }),
  documentVersions: (id: string, signal?: AbortSignal) => request<DocumentVersionsResponse>(`/api/documents/${encode(id)}/versions`, { signal }),
  documentText: (id: string, signal?: AbortSignal) => request<DocumentTextResponse>(`/api/documents/${encode(id)}/text`, { signal }),
  context: (signal?: AbortSignal) => request<ContextResponse>('/api/context', { signal }),
  addContext: (body: ContextAddRequest) => request<ContextResponse>('/api/context', { method: 'POST', body: JSON.stringify(body) }),
  removeContext: (id: string) => request<ContextResponse>(`/api/context/${encode(id)}`, { method: 'DELETE' }),
  clearContext: () => request<ContextResponse>('/api/context', { method: 'DELETE' }),
  agentTurn: (body: AgentTurnRequest, signal?: AbortSignal) => request<AgentTurnResponse>('/api/agent/turns', { method: 'POST', body: JSON.stringify(body), signal })
};
