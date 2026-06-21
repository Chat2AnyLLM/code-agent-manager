import { mockConfigFiles, mockDoctorChecks, mockEntities, mockMCPClients, mockMCPServers, mockMCPRegistry, mockMetadataItems, mockProviders, mockTargets, mockTools } from './mockData'
import type { ApplyResult, ConfigFile, DoctorCheck, Entity, Instruction, InstructionInstall, InstructionTarget, LaunchPlan, MCPClient, MCPRegistryItem, MCPServer, MetadataDetail, MetadataRefreshSummary, MetadataSearchResponse, Prompt, PromptSource, Provider, Tool, ToolOperation } from './types'

type SidecarConfig = {
  baseUrl: string
  token?: string
}

declare global {
  interface Window { __CAM_SIDECAR__?: SidecarConfig; __TAURI_INTERNALS__?: unknown }
}

let tauriSidecar: Promise<SidecarConfig | undefined> | undefined

const configuredSidecar = (): SidecarConfig | undefined => {
  if (typeof window !== 'undefined' && window.__CAM_SIDECAR__?.baseUrl) {
    return window.__CAM_SIDECAR__
  }
  const baseUrl = import.meta.env.VITE_CAM_API_BASE_URL
  const token = import.meta.env.VITE_CAM_API_TOKEN
  return baseUrl ? { baseUrl, token } : undefined
}

const sidecar = async (): Promise<SidecarConfig | undefined> => {
  const configured = configuredSidecar()
  if (configured) return configured
  if (typeof window === 'undefined' || !('__TAURI_INTERNALS__' in window)) return undefined
  tauriSidecar ??= import('@tauri-apps/api/core')
    .then(({ invoke }) => invoke<SidecarConfig>('sidecar_config'))
    .then((config) => {
      window.__CAM_SIDECAR__ = config
      return config
    })
    .catch(() => undefined)
  return tauriSidecar
}

const normalizeBaseUrl = (baseUrl: string) => baseUrl.replace(/\/$/, '')

async function request<T>(path: string, init: RequestInit = {}): Promise<T | undefined> {
  const config = await sidecar()
  if (!config) return undefined
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (config.token) headers.set('Authorization', `Bearer ${config.token}`)
  const response = await fetch(`${normalizeBaseUrl(config.baseUrl)}${path}`, { ...init, headers })
  if (!response.ok) throw new Error(await response.text())
  return response.json() as Promise<T>
}

export const api = {
  async listTools(): Promise<Tool[]> {
    return (await request<Tool[]>('/api/tools')) ?? mockTools
  },
  async installTool(name: string): Promise<ToolOperation> {
    const fallbackTool = mockTools.find((tool) => tool.name === name || tool.command === name) ?? mockTools[0]
    return (await request<ToolOperation>(`/api/tools/${encodeURIComponent(name)}/install`, { method: 'POST', body: JSON.stringify({}) })) ?? { result: { ok: true, message: 'mock installed' }, tool: { ...fallbackTool, installed: true, version: fallbackTool.version === 'unknown' ? 'mock' : fallbackTool.version } }
  },
  async upgradeTool(name: string): Promise<ToolOperation> {
    const fallbackTool = mockTools.find((tool) => tool.name === name || tool.command === name) ?? mockTools[0]
    return (await request<ToolOperation>(`/api/tools/${encodeURIComponent(name)}/upgrade`, { method: 'POST', body: JSON.stringify({}) })) ?? { result: { ok: true, message: 'mock upgraded' }, tool: { ...fallbackTool, installed: true, version: fallbackTool.version === 'unknown' ? 'mock' : fallbackTool.version } }
  },
  async listProviders(): Promise<Provider[]> {
    return (await request<Provider[]>('/api/providers')) ?? mockProviders
  },
  // resolveModels returns the full model list for a provider: models discovered
  // from the provider's /v1/models API, merged with any statically configured
  // models and built-in defaults. Falls back to the provider's static models
  // when no sidecar is available (browser-only/mock mode).
  async resolveModels(name: string): Promise<string[]> {
    const resolved = await request<string[]>(`/api/providers/${encodeURIComponent(name)}/models`)
    if (Array.isArray(resolved)) return resolved
    const provider = mockProviders.find((p) => p.name === name)
    return provider?.models ?? []
  },
  async addProvider(input: Partial<Provider> & { name: string }): Promise<Provider> {
    return (await request<Provider>('/api/providers', { method: 'POST', body: JSON.stringify(input) })) ?? { ...mockProviders[0], ...input, clients: input.clients ?? [], models: input.models ?? [], enabled: input.enabled ?? true, endpoint: input.endpoint ?? '', apiKeyEnv: input.apiKeyEnv ?? '', supportedClient: input.supportedClient ?? '', keepProxyConfig: input.keepProxyConfig ?? false, useProxy: input.useProxy ?? false, description: input.description ?? '' }
  },
  // updateProvider applies a sparse patch (e.g. just the apiKey) to an existing
  // provider. Only non-empty fields in the patch are changed server-side.
  async updateProvider(name: string, patch: Partial<Provider>): Promise<Provider> {
    return (await request<Provider>(`/api/providers/${encodeURIComponent(name)}`, { method: 'PATCH', body: JSON.stringify(patch) })) ?? { ...mockProviders[0], ...patch, name }
  },
  async toggleProvider(name: string, enabled: boolean): Promise<Provider> {
    return (await request<Provider>(`/api/providers/${encodeURIComponent(name)}/${enabled ? 'enable' : 'disable'}`, { method: 'POST' })) ?? { ...mockProviders[0], name, enabled }
  },
  async removeProvider(name: string): Promise<void> {
    await (request<unknown>(`/api/providers/${encodeURIComponent(name)}`, { method: 'DELETE' }) ?? Promise.resolve())
  },
  async listMCPClients(): Promise<MCPClient[]> {
    return (await request<MCPClient[]>('/api/mcp/clients')) ?? mockMCPClients
  },
  async listMCPServers(client = 'claude', scope = 'user'): Promise<MCPServer[]> {
    return (await request<MCPServer[]>(`/api/mcp/servers?client=${encodeURIComponent(client)}&scope=${encodeURIComponent(scope)}`)) ?? mockMCPServers
  },
  // searchMCPRegistry returns the discovered (bundled) MCP servers, optionally
  // filtered by query, each enriched with the clients it is installed into at
  // scope. Falls back to client-side filtering of the mock catalog when no
  // sidecar is available (browser-only/mock mode).
  async searchMCPRegistry(query = '', scope = 'user'): Promise<MCPRegistryItem[]> {
    const params = new URLSearchParams({ q: query, scope })
    const resp = await request<MCPRegistryItem[]>(`/api/mcp/registry?${params.toString()}`)
    if (resp) return resp
    const q = query.trim().toLowerCase()
    return mockMCPRegistry.filter((item) => q === '' || `${item.name} ${item.displayName ?? ''} ${item.description ?? ''}`.toLowerCase().includes(q))
  },
  async installMCPServer(server: string, clients: string[], scope = 'user'): Promise<{ status: string }> {
    return (await request<{ status: string }>('/api/mcp/install', { method: 'POST', body: JSON.stringify({ server, clients, scope }) })) ?? { status: 'installed' }
  },
  async uninstallMCPServer(server: string, clients: string[], scope = 'user'): Promise<{ status: string }> {
    return (await request<{ status: string }>('/api/mcp/uninstall', { method: 'POST', body: JSON.stringify({ server, clients, scope }) })) ?? { status: 'removed' }
  },
  async listEntities(kind: Entity['kind']): Promise<Entity[]> {
    return (await request<Entity[]>(`/api/entities?kind=${encodeURIComponent(kind)}`)) ?? mockEntities.filter((entity) => entity.kind === kind)
  },
  async searchEntities(kind: Entity['kind'], query: string): Promise<Entity[]> {
    return (await request<Entity[]>(`/api/entities?kind=${encodeURIComponent(kind)}&query=${encodeURIComponent(query)}`)) ?? mockEntities.filter((entity) => entity.kind === kind && `${entity.name} ${entity.description}`.toLowerCase().includes(query.toLowerCase()))
  },
  async uninstallEntity(kind: string, name: string): Promise<{ status: string }> {
    return (await request<{ status: string }>('/api/entities/uninstall', { method: 'POST', body: JSON.stringify({ kind, name }) })) ?? { status: 'removed' }
  },
  async listConfigFiles(): Promise<ConfigFile[]> {
    return (await request<ConfigFile[]>('/api/config/files')) ?? mockConfigFiles
  },
  async runDoctor(): Promise<DoctorCheck[]> {
    return (await request<DoctorCheck[]>('/api/doctor/checks')) ?? mockDoctorChecks
  },
  async dryRun(tool: string, provider: string, model: string): Promise<LaunchPlan> {
    return (await request<LaunchPlan>('/api/launch/dry-run', { method: 'POST', body: JSON.stringify({ tool, provider, model, args: [] }) })) ?? { tool: mockTools[0], provider: mockProviders[0], model, command: tool, args: ['--model', model], environment: { CAM_PROVIDER: provider } }
  },
  // applyConfig writes a provider's config into the agent's config file without
  // launching it — the cc-switch "switch" operation.
  async applyConfig(tool: string, provider: string, model: string): Promise<ApplyResult> {
    return (await request<ApplyResult>('/api/launch/apply', { method: 'POST', body: JSON.stringify({ tool, provider, model }) })) ?? { tool: mockTools[0], provider: mockProviders[0], model, configPath: '', writes: [] }
  },
  async searchMetadata(kind: Entity['kind'], query: string, limit = 50, offset = 0): Promise<MetadataSearchResponse> {
    const params = new URLSearchParams({ type: kind, q: query, limit: String(limit), offset: String(offset) })
    const resp = await request<MetadataSearchResponse>(`/api/metadata/search?${params.toString()}`)
    if (resp) return resp
    // Browser-only fallback: filter mock items server-side style.
    const q = query.trim().toLowerCase()
    const filtered = mockMetadataItems.filter((item) => item.kind === kind && (q === '' || `${item.name} ${item.description} ${item.repo_owner}/${item.repo_name}`.toLowerCase().includes(q)))
    return { items: filtered.slice(offset, offset + limit), total: filtered.length, limit, offset }
  },
  async refreshMetadata(): Promise<MetadataRefreshSummary> {
    return (await request<MetadataRefreshSummary>('/api/metadata/refresh', { method: 'POST' })) ?? { sources_scanned: 3, items_added: mockMetadataItems.length, items_updated: 0, items_stale: 0, failed_sources: [] }
  },
  async installMetadata(kind: string, installKey: string, targetApps: string[], level?: string, projectDir?: string): Promise<{ status: string }> {
    const body: Record<string, unknown> = { kind, install_key: installKey, target_apps: targetApps }
    if (kind === 'instruction') {
      if (level) body.level = level
      if (projectDir) body.project_dir = projectDir
    }
    return (await request<{ status: string }>('/api/metadata/install', { method: 'POST', body: JSON.stringify(body) })) ?? { status: 'installed' }
  },
  async uninstallMetadata(kind: string, installKey: string, targetApps: string[]): Promise<{ status: string }> {
    return (await request<{ status: string }>('/api/metadata/uninstall', { method: 'POST', body: JSON.stringify({ kind, install_key: installKey, target_apps: targetApps }) })) ?? { status: 'uninstalled' }
  },
  async metadataTargets(kind: string): Promise<string[]> {
    return (await request<string[]>(`/api/metadata/targets?kind=${encodeURIComponent(kind)}`)) ?? mockTargets[kind] ?? ['claude']
  },
  async metadataDetail(kind: string, installKey: string): Promise<MetadataDetail> {
    const params = new URLSearchParams({ kind, install_key: installKey })
    const resp = await request<MetadataDetail>(`/api/metadata/detail?${params.toString()}`)
    if (resp) return resp
    // Browser-only fallback: synthesize a detail view from the mock index so the
    // expand panel renders without a sidecar.
    const item = mockMetadataItems.find((entry) => entry.kind === kind && entry.install_key === installKey)
      ?? { kind, name: installKey, description: '', install_key: installKey, repo_owner: '', repo_name: '', repo_branch: 'main', target_apps: '', installed_apps: [], installed: false }
    return { item, content: `# ${item.name}\n\n${item.description}`, manifest_path: '' }
  },

  async refreshMetadataItem(kind: string, installKey: string): Promise<MetadataDetail> {
    return (await request<MetadataDetail>('/api/metadata/refresh-item', { method: 'POST', body: JSON.stringify({ kind, install_key: installKey }) })) ?? this.metadataDetail(kind, installKey)
  },

  // Instructions: local CRUD + symlink install. These hit the sidecar's
  // /api/instructions/* endpoints. In browser-only/mock mode (no sidecar) the
  // mutating calls throw, and listInstructions returns an empty list so the
  // page renders its empty state rather than crashing.
  async listInstructions(): Promise<Instruction[]> {
    return (await request<Instruction[]>('/api/instructions')) ?? []
  },
  async getInstruction(id: number): Promise<Instruction> {
    const resp = await request<Instruction>(`/api/instructions/${id}`)
    if (resp) return resp
    throw new Error('sidecar unavailable')
  },
  async createInstruction(body: { name: string; description: string; content: string }): Promise<Instruction> {
    const resp = await request<Instruction>('/api/instructions', { method: 'POST', body: JSON.stringify(body) })
    if (resp) return resp
    throw new Error('sidecar unavailable')
  },
  async updateInstruction(id: number, body: { name: string; description: string; content: string }): Promise<Instruction> {
    const resp = await request<Instruction>(`/api/instructions/${id}`, { method: 'PUT', body: JSON.stringify(body) })
    if (resp) return resp
    throw new Error('sidecar unavailable')
  },
  async deleteInstruction(id: number): Promise<void> {
    await (request<unknown>(`/api/instructions/${id}`, { method: 'DELETE' }) ?? Promise.resolve())
  },
  async installInstruction(id: number, body: { app: string; level: string; project_dir?: string }): Promise<InstructionInstall> {
    const resp = await request<InstructionInstall>(`/api/instructions/${id}/installs`, { method: 'POST', body: JSON.stringify(body) })
    if (resp) return resp
    throw new Error('sidecar unavailable')
  },
  async uninstallInstruction(installId: number): Promise<void> {
    await (request<unknown>(`/api/instructions/installs/${installId}`, { method: 'DELETE' }) ?? Promise.resolve())
  },
  async instructionTargets(): Promise<InstructionTarget[]> {
    return (await request<InstructionTarget[]>('/api/instructions/targets')) ?? [
      { app: 'claude', supports: { user: true, project: true } },
      { app: 'codex', supports: { user: true, project: true } },
      { app: 'gemini', supports: { user: true, project: true } },
      { app: 'copilot', supports: { user: true, project: true } },
      { app: 'cursor', supports: { user: false, project: true } },
      { app: 'windsurf', supports: { user: true, project: true } },
      { app: 'cline', supports: { user: true, project: true } },
      { app: 'roo', supports: { user: true, project: true } },
      { app: 'aider', supports: { user: false, project: true } },
    ]
  },

  // Prompts
  async listPrompts(source?: string): Promise<Prompt[]> {
    const params = source ? `?source=${encodeURIComponent(source)}` : ''
    return (await request<Prompt[]>(`/api/prompts${params}`)) ?? []
  },
  async searchPrompts(q: string): Promise<Prompt[]> {
    return (await request<Prompt[]>(`/api/prompts/search?q=${encodeURIComponent(q)}`)) ?? []
  },
  async syncPrompts(source?: string): Promise<{ synced: number }> {
    return (await request<{ synced: number }>('/api/prompts/sync', { method: 'POST', body: JSON.stringify({ source: source ?? '' }) })) ?? { synced: 0 }
  },
  async getPromptSources(): Promise<PromptSource[]> {
    return (await request<PromptSource[]>('/api/prompts/sources')) ?? []
  },
}
