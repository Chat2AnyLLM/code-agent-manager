import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MCP } from './MCP'
import { api } from '../services/api'
import type { MCPRegistryItem } from '../services/types'

function registryItem(overrides: Partial<MCPRegistryItem>): MCPRegistryItem {
  return {
    name: 'sample',
    description: 'desc',
    installType: 'npm',
    installedClients: [],
    ...overrides,
  }
}

// A server's name renders in an <h3> (the Name column) and may also appear in
// the Source column, so name lookups use the heading role to stay unique.
const findRow = async (name: RegExp) => screen.findByRole('heading', { name })

describe('MCP page', () => {
  afterEach(() => vi.restoreAllMocks())

  it('shows discovered registry servers with installed badges', async () => {
    render(<MCP />)
    expect(await screen.findByRole('heading', { name: /mcp servers/i })).toBeInTheDocument()
    expect(await findRow(/github/i)).toBeInTheDocument()
    // The github mock is installed into claude — its badge sits in the
    // installed-clients group.
    const badges = await screen.findByLabelText(/installed clients/i)
    expect(badges.textContent).toMatch(/claude/i)
  })

  it('links each server name to its source repository', async () => {
    render(<MCP />)
    const link = await screen.findByRole('link', { name: /github mcp server/i })
    expect(link).toHaveAttribute('href', 'https://github.com/modelcontextprotocol/servers')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('offers a per-server agent picker with multiple targets', async () => {
    render(<MCP />)
    expect(await findRow(/github/i)).toBeInTheDocument()
    fireEvent.click(await screen.findByRole('button', { name: /select agents for github/i }))
    const picker = await screen.findByLabelText(/install targets for github/i)
    expect(picker).toBeInTheDocument()
    // Targets come from listMCPClients; the mocks include claude and gemini.
    expect(within(picker).getByLabelText(/^claude/i)).toBeInTheDocument()
    expect(within(picker).getByLabelText(/^gemini/i)).toBeInTheDocument()
  })

  it('installs a server to the selected clients', async () => {
    const installSpy = vi.spyOn(api, 'installMCPServer').mockResolvedValue({ status: 'installed' })
    vi.spyOn(api, 'searchMCPRegistry').mockResolvedValue([registryItem({ name: 'filesystem', installedClients: [] })])
    render(<MCP />)
    expect(await findRow(/filesystem/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /install to claude/i }))
    // installMCPServer is called with the server name + client list (the scope
    // default is applied inside the real function, which the spy bypasses).
    await waitFor(() => expect(installSpy).toHaveBeenCalledWith('filesystem', ['claude']))
    expect(await screen.findByText(/installed filesystem to claude/i)).toBeInTheDocument()
  })

  it('filters to installed-only servers', async () => {
    const installed = registryItem({ name: 'github', installedClients: ['claude'] })
    const fresh = registryItem({ name: 'filesystem', installedClients: [] })
    vi.spyOn(api, 'searchMCPRegistry').mockResolvedValue([installed, fresh])
    render(<MCP />)
    expect(await findRow(/github/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /filesystem/i })).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText(/installed only/i))
    await waitFor(() => expect(screen.queryByRole('heading', { name: /filesystem/i })).not.toBeInTheDocument())
    expect(screen.getByRole('heading', { name: /github/i })).toBeInTheDocument()
  })

  it('paginates the registry when there are more than a page of servers', async () => {
    const many = Array.from({ length: 25 }, (_, i) => registryItem({ name: `server-${i}` }))
    vi.spyOn(api, 'searchMCPRegistry').mockResolvedValue(many)
    render(<MCP />)
    // Page 1 shows the first 20 servers plus the pagination nav.
    expect(await findRow(/server-0/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /server-24/i })).not.toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: /pagination/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /go to page 2/i })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /go to page 2/i }))
    await waitFor(() => expect(screen.getByRole('heading', { name: /server-24/i })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /previous/i }))
    await waitFor(() => expect(screen.getByRole('heading', { name: /server-0/i })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    await waitFor(() => expect(screen.getByRole('heading', { name: /server-24/i })).toBeInTheDocument())
    vi.restoreAllMocks()
  })
})
