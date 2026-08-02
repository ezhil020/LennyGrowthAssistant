import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Types
export interface Session {
  id: string
  title: string
  created_at: string
  llm_provider: string
  embedding_model: string
}

export interface SourceChunk {
  chunk_id: string
  episode_title: string
  chunk_index: number
  similarity_score: number
  source_url: string
  chunk_text: string
}

export interface SourceAttribution {
  chunks: SourceChunk[]
  retrieval_mode: string
}

export interface Message {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  skill_used?: string
  routing_intent?: string
  artifact_id?: string
  sources?: SourceAttribution
  created_at: string
}

export interface Artifact {
  id: string
  message_id: string
  session_id: string
  type: 'markdown' | 'html'
  content: string
  version: number
  title?: string
  created_at: string
}

export interface HealthStatus {
  status: string
  checks: Record<string, string>
}

export interface ProviderInfo {
  name: string
  is_active: boolean
  model: string
}

// API calls
export const sessionsApi = {
  create: (provider = 'anthropic', embedding = 'ollama') =>
    api.post<Session>('/sessions', { llm_provider: provider, embedding_model: embedding }),

  list: () => api.get<{ sessions: Session[] }>('/sessions'),

  get: (id: string) =>
    api.get<{ session: Session; messages: Message[] }>(`/sessions/${id}`),

  delete: (id: string) => api.delete(`/sessions/${id}`),
}

export const artifactsApi = {
  get: (id: string) => api.get<Artifact>(`/artifacts/${id}`),
  update: (id: string, content: string, title?: string) =>
    api.patch<Artifact>(`/artifacts/${id}`, { content, title }),
}

export const configApi = {
  getProviders: () => api.get<{ providers: ProviderInfo[]; active: string }>('/config/providers'),
  setProvider: (provider: string) => api.post('/config/providers', { provider }),
}

export const healthApi = {
  check: () => api.get<HealthStatus>('/health'),
}

export const ingestApi = {
  trigger: (limit = 50) => api.post('/ingest', { limit }),
}

export default api
