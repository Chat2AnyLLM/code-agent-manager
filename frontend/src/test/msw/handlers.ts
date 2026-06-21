import { http, HttpResponse } from 'msw'
import { mockProviders, mockTools, mockMCPServers, mockMCPRegistry, mockEntities, mockDoctorChecks, mockConfigFiles, mockMetadataItems, mockTargets } from '../../services/mockData'

const BASE_URL = 'http://localhost:3000'

export const handlers = [
  // Tools
  http.get(`${BASE_URL}/api/tools`, () => {
    return HttpResponse.json(mockTools)
  }),

  http.post(`${BASE_URL}/api/tools/:name/install`, ({ params }) => {
    const tool = mockTools.find((t) => t.name === params.name) ?? mockTools[0]
    return HttpResponse.json({ result: { ok: true, message: 'installed' }, tool: { ...tool, installed: true } })
  }),

  http.post(`${BASE_URL}/api/tools/:name/upgrade`, ({ params }) => {
    const tool = mockTools.find((t) => t.name === params.name) ?? mockTools[0]
    return HttpResponse.json({ result: { ok: true, message: 'upgraded' }, tool: { ...tool, installed: true } })
  }),

  // Providers
  http.get(`${BASE_URL}/api/providers`, () => {
    return HttpResponse.json(mockProviders)
  }),

  http.post(`${BASE_URL}/api/providers`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({ ...mockProviders[0], ...body })
  }),

  http.patch(`${BASE_URL}/api/providers/:name`, async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>
    const provider = mockProviders.find((p) => p.name === params.name) ?? mockProviders[0]
    return HttpResponse.json({ ...provider, ...body })
  }),

  http.post(`${BASE_URL}/api/providers/:name/enable`, ({ params }) => {
    const provider = mockProviders.find((p) => p.name === params.name) ?? mockProviders[0]
    return HttpResponse.json({ ...provider, enabled: true })
  }),

  http.post(`${BASE_URL}/api/providers/:name/disable`, ({ params }) => {
    const provider = mockProviders.find((p) => p.name === params.name) ?? mockProviders[0]
    return HttpResponse.json({ ...provider, enabled: false })
  }),

  http.delete(`${BASE_URL}/api/providers/:name`, () => {
    return HttpResponse.json(null)
  }),

  http.get(`${BASE_URL}/api/providers/:name/models`, ({ params }) => {
    const provider = mockProviders.find((p) => p.name === params.name) ?? mockProviders[0]
    return HttpResponse.json(provider.models)
  }),

  // MCP
  http.get(`${BASE_URL}/api/mcp/clients`, () => {
    return HttpResponse.json([{ name: 'claude', userPath: '~/.claude', format: 'json', supportsUser: true, supportsProject: true }])
  }),

  http.get(`${BASE_URL}/api/mcp/servers`, () => {
    return HttpResponse.json(mockMCPServers)
  }),

  http.get(`${BASE_URL}/api/mcp/registry`, ({ request }) => {
    const url = new URL(request.url)
    const query = url.searchParams.get('q')?.toLowerCase() ?? ''
    const filtered = query ? mockMCPRegistry.filter((item) => `${item.name} ${item.description}`.toLowerCase().includes(query)) : mockMCPRegistry
    return HttpResponse.json(filtered)
  }),

  http.post(`${BASE_URL}/api/mcp/install`, () => {
    return HttpResponse.json({ status: 'installed' })
  }),

  http.post(`${BASE_URL}/api/mcp/uninstall`, () => {
    return HttpResponse.json({ status: 'removed' })
  }),

  // Entities
  http.get(`${BASE_URL}/api/entities`, ({ request }) => {
    const url = new URL(request.url)
    const kind = url.searchParams.get('kind')
    return HttpResponse.json(mockEntities.filter((e) => !kind || e.kind === kind))
  }),

  http.post(`${BASE_URL}/api/entities/uninstall`, () => {
    return HttpResponse.json({ status: 'removed' })
  }),

  // Config
  http.get(`${BASE_URL}/api/config/files`, () => {
    return HttpResponse.json(mockConfigFiles)
  }),

  // Doctor
  http.get(`${BASE_URL}/api/doctor/checks`, () => {
    return HttpResponse.json(mockDoctorChecks)
  }),

  // Launch
  http.post(`${BASE_URL}/api/launch/dry-run`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      tool: mockTools[0],
      provider: mockProviders[0],
      model: body.model ?? 'default',
      command: body.tool ?? 'claude',
      args: ['--model', String(body.model ?? 'default')],
      environment: { CAM_PROVIDER: String(body.provider ?? '') },
    })
  }),

  http.post(`${BASE_URL}/api/launch/apply`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      tool: mockTools[0],
      provider: mockProviders[0],
      model: body.model ?? 'default',
      configPath: '/home/user/.claude/settings.json',
      writes: [{ keyPath: 'api_key', value: '***', op: 'upsert' }],
    })
  }),

  // Metadata
  http.get(`${BASE_URL}/api/metadata/search`, ({ request }) => {
    const url = new URL(request.url)
    const kind = url.searchParams.get('type') ?? 'skill'
    const query = url.searchParams.get('q')?.toLowerCase() ?? ''
    const limit = parseInt(url.searchParams.get('limit') ?? '50')
    const offset = parseInt(url.searchParams.get('offset') ?? '0')
    const filtered = mockMetadataItems.filter((item) => item.kind === kind && (!query || `${item.name} ${item.description}`.toLowerCase().includes(query)))
    return HttpResponse.json({ items: filtered.slice(offset, offset + limit), total: filtered.length, limit, offset })
  }),

  http.post(`${BASE_URL}/api/metadata/refresh`, () => {
    return HttpResponse.json({ sources_scanned: 3, items_added: 10, items_updated: 0, items_stale: 0, failed_sources: [] })
  }),

  http.post(`${BASE_URL}/api/metadata/install`, () => {
    return HttpResponse.json({ status: 'installed' })
  }),

  http.post(`${BASE_URL}/api/metadata/uninstall`, () => {
    return HttpResponse.json({ status: 'uninstalled' })
  }),

  http.get(`${BASE_URL}/api/metadata/targets`, ({ request }) => {
    const url = new URL(request.url)
    const kind = url.searchParams.get('kind') ?? 'skill'
    return HttpResponse.json(mockTargets[kind] ?? ['claude'])
  }),

  http.get(`${BASE_URL}/api/metadata/detail`, ({ request }) => {
    const url = new URL(request.url)
    const kind = url.searchParams.get('kind') ?? 'skill'
    const installKey = url.searchParams.get('install_key') ?? ''
    const item = mockMetadataItems.find((entry) => entry.kind === kind && entry.install_key === installKey)
      ?? { kind, name: installKey, description: '', install_key: installKey, repo_owner: '', repo_name: '', repo_branch: 'main', target_apps: '', installed_apps: [], installed: false }
    return HttpResponse.json({ item, content: `# ${item.name}\n\n${item.description}`, manifest_path: '' })
  }),

  // Instructions
  http.get(`${BASE_URL}/api/instructions`, () => {
    return HttpResponse.json([])
  }),

  http.post(`${BASE_URL}/api/instructions`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({ id: 1, ...body, installs: [] })
  }),

  http.put(`${BASE_URL}/api/instructions/:id`, async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({ id: Number(params.id), ...body, installs: [] })
  }),

  http.delete(`${BASE_URL}/api/instructions/:id`, () => {
    return HttpResponse.json(null)
  }),

  http.get(`${BASE_URL}/api/instructions/targets`, () => {
    return HttpResponse.json([
      { app: 'claude', supports: { user: true, project: true } },
      { app: 'codex', supports: { user: true, project: true } },
      { app: 'gemini', supports: { user: true, project: true } },
    ])
  }),
]
