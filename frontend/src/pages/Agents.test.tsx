import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Agents } from './Agents'
import { TestWrapper } from '../test/TestWrapper'
import { api } from '../services/api'
import type { Provider, Tool } from '../services/types'

describe('Agents page', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    try { localStorage.removeItem('cam.agentSelection') } catch {}
  })

  it('shows coding agent run commands and detection status, no launch buttons', async () => {
    render(<Agents />, { wrapper: TestWrapper })

    expect(await screen.findByRole('heading', { name: /agents/i })).toBeInTheDocument()
    expect(await screen.findByText('claude --allow-dangerously-skip-permissions --dangerously-skip-permissions')).toBeInTheDocument()
    expect(await screen.findByText('codex --yolo')).toBeInTheDocument()
    expect(await screen.findByText('Installed')).toBeInTheDocument()
    expect(await screen.findByText('Not installed')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /upgrade/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /install/i })).toBeInTheDocument()
    // It documents commands; it must not launch agents from the GUI.
    expect(screen.queryByRole('button', { name: /launch/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /dry-run/i })).not.toBeInTheDocument()
  })

  it('installs a missing agent tool and updates status', async () => {
    const user = userEvent.setup()
    render(<Agents />, { wrapper: TestWrapper })

    const install = await screen.findByRole('button', { name: /install/i })
    await user.click(install)

    expect(await screen.findByText('Installed codex')).toBeInTheDocument()
  })

  it('loads resolved provider models into the model dropdown', async () => {
    const user = userEvent.setup()
    const tools: Tool[] = [
      { name: 'claude-code', command: 'claude', description: 'Claude Code CLI', enabled: true, installed: true, version: 'mock' },
    ]
    const providers: Provider[] = [
      {
        name: 'omnillm',
        endpoint: 'http://localhost:4000/v1',
        apiKeyEnv: '',
        supportedClient: 'claude',
        clients: ['claude'],
        models: [],
        keepProxyConfig: false,
        useProxy: false,
        enabled: true,
        description: '',
      },
    ]

    vi.spyOn(api, 'listTools').mockResolvedValue(tools)
    vi.spyOn(api, 'listProviders').mockResolvedValue(providers)
    const resolveSpy = vi.spyOn(api, 'resolveModels').mockResolvedValue(['resolved-a', 'resolved-b'])

    render(<Agents />, { wrapper: TestWrapper })

    await user.selectOptions(await screen.findByLabelText('Provider claude-code'), 'omnillm')

    expect(resolveSpy).toHaveBeenCalledWith('omnillm')
    expect(await screen.findByRole('option', { name: 'resolved-a' })).toBeInTheDocument()

    const modelSelect = screen.getByLabelText('Model claude-code') as HTMLSelectElement
    await user.selectOptions(modelSelect, 'resolved-b')

    expect(modelSelect.value).toBe('resolved-b')
  })
})
