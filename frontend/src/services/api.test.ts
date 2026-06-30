import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'

const resetSidecar = () => {
  delete window.__CAM_SIDECAR__
  vi.restoreAllMocks()
}

describe('api mock fallback', () => {
  afterEach(resetSidecar)

  it('lists tools and providers', async () => {
    await expect(api.listTools()).resolves.toEqual(expect.arrayContaining([expect.objectContaining({ command: 'claude' })]))
    await expect(api.listProviders()).resolves.toEqual(expect.arrayContaining([expect.objectContaining({ name: 'local' })]))
  })

  it('creates dry-run plans', async () => {
    const plan = await api.dryRun('claude', 'local', 'model')
    expect(plan.command).toBe('claude')
    expect(plan.provider.name).toBe('local')
    expect(plan.model).toBe('model')
  })
})

describe('api sidecar transport', () => {
  afterEach(resetSidecar)

  it('uses sidecar base URL and bearer token for provider listing', async () => {
    const providers = [{ name: 'local', endpoint: 'http://localhost:4000/v1', apiKeyEnv: 'LOCAL_KEY', supportedClient: 'claude', clients: ['claude'], models: ['m1'], keepProxyConfig: false, useProxy: false, enabled: true, description: 'local' }]
    window.__CAM_SIDECAR__ = { baseUrl: 'http://127.0.0.1:54321/', token: 'secret' }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(providers), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    await expect(api.listProviders()).resolves.toEqual(providers)

    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('http://127.0.0.1:54321/api/providers')
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer secret')
  })

  it('adds source filters to prompt search requests', async () => {
    window.__CAM_SIDECAR__ = { baseUrl: 'http://127.0.0.1:54321' }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }))

    await expect(api.searchPrompts('deploy script', 'local_prompts')).resolves.toEqual([])

    expect(fetchMock).toHaveBeenCalledOnce()
    const [url] = fetchMock.mock.calls[0]
    expect(url).toBe('http://127.0.0.1:54321/api/prompts/search?q=deploy+script&source=local_prompts')
  })
})
