import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Library } from './Library'
import { api } from '../services/api'
import type { MetadataItem } from '../services/types'

function metadataItem(overrides: Partial<MetadataItem>): MetadataItem {
  return {
    kind: 'agent',
    name: 'sample',
    description: 'desc',
    install_key: 'owner/repo:sample',
    repo_owner: 'owner',
    repo_name: 'repo',
    repo_branch: 'main',
    target_apps: 'claude',
    installed_apps: [],
    installed: false,
    ...overrides,
  }
}

describe('Library page', () => {
  it('renders skills from the metadata index with installed badges', async () => {
    render(<Library kind="skill" />)
    expect(await screen.findByRole('heading', { name: /skills/i })).toBeInTheDocument()
    expect(await screen.findByText(/golang-testing/i)).toBeInTheDocument()
    // Installed badge for claude should appear inside the installed-agents group.
    const badges = await screen.findByLabelText(/installed agents/i)
    expect(badges.textContent).toMatch(/claude/i)
  })

  it('searches the metadata index', async () => {
    render(<Library kind="skill" />)
    expect(await screen.findByText(/golang-testing/i)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/skills search/i), { target: { value: 'golang' } })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))
    await waitFor(() => expect(screen.getByText(/golang-testing/i)).toBeInTheDocument())
  })

  it('keeps rendering when search returns a null items payload', async () => {
    vi.spyOn(api, 'searchMetadata')
      .mockResolvedValueOnce({ items: [metadataItem({ name: 'initial-skill', kind: 'skill', install_key: 'o/r:initial-skill' })], total: 1, limit: 20, offset: 0 })
      .mockResolvedValueOnce({ items: null as unknown as MetadataItem[], total: 0, limit: 20, offset: 0 })
    render(<Library kind="skill" />)

    expect(await screen.findByText(/initial-skill/i)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/skills search/i), { target: { value: 'zzzz-no-match' } })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    await waitFor(() => expect(screen.getByText(/no skills found/i)).toBeInTheDocument())
    expect(screen.getByRole('heading', { name: /skills/i })).toBeInTheDocument()
    vi.restoreAllMocks()
  })

  it('renders subagents page', async () => {
    render(<Library kind="agent" />)
    expect(await screen.findByRole('heading', { name: /subagents/i })).toBeInTheDocument()
    expect(await screen.findByText(/code-reviewer/i)).toBeInTheDocument()
  })

  it('links each resource name to its source file on GitHub', async () => {
    render(<Library kind="agent" />)
    // The mock agent lives at agents/code-reviewer.md in iannuttall/claude-agents.
    const link = await screen.findByRole('link', { name: /code-reviewer/i })
    expect(link).toHaveAttribute('href', 'https://github.com/iannuttall/claude-agents/blob/main/agents/code-reviewer.md')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('renders instructions page (replaces old prompts page)', async () => {
    render(<Library kind="instruction" />)
    expect(await screen.findByRole('heading', { name: /instructions/i })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /summarize/i })).toBeInTheDocument()
  })

  it('shows project-level install controls only for instructions', async () => {
    const installSpy = vi.spyOn(api, 'installMetadata').mockResolvedValue({ status: 'installed' })
    render(<Library kind="instruction" />)
    expect(await screen.findByText(/summarize/i)).toBeInTheDocument()

    const level = await screen.findByLabelText(/install level/i)
    fireEvent.change(level, { target: { value: 'project' } })
    fireEvent.click(screen.getByRole('button', { name: /install to claude/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/project directory is required/i)

    fireEvent.change(screen.getByLabelText(/project directory/i), { target: { value: 'C:/repo/demo' } })
    fireEvent.click(screen.getByRole('button', { name: /install to claude/i }))
    await waitFor(() => expect(installSpy).toHaveBeenCalledWith('instruction', 'anthropics/prompts:summarize', ['claude'], 'project', 'C:/repo/demo'))
    vi.restoreAllMocks()
  })

  it('does not show instruction level controls for non-instruction resources', async () => {
    render(<Library kind="skill" />)
    expect(await screen.findByText(/golang-testing/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/install level/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/project directory/i)).not.toBeInTheDocument()
  })

  it('offers a per-resource agent picker with multiple targets', async () => {
    render(<Library kind="skill" />)
    expect(await screen.findByText(/golang-testing/i)).toBeInTheDocument()
    // The dropdown trigger is unique per resource; open it to expose the options.
    fireEvent.click(await screen.findByRole('button', { name: /select agents for golang-testing/i }))
    const picker = await screen.findByLabelText(/install targets for golang-testing/i)
    expect(picker).toBeInTheDocument()
    expect(within(picker).getByLabelText(/^codex/i)).toBeInTheDocument()
    expect(within(picker).getByLabelText(/^cursor/i)).toBeInTheDocument()
  })

  it('expands a card to show full metadata and manifest content on demand', async () => {
    const detailSpy = vi.spyOn(api, 'metadataDetail').mockResolvedValue({
      item: metadataItem({ kind: 'skill', name: 'golang-testing', install_key: 'obra/superpowers:golang-testing' }),
      content: '# golang-testing\n\nGuidance for Go tests.',
      manifest_path: 'skills/golang-testing/SKILL.md',
    })
    render(<Library kind="skill" />)
    const expandButtons = await screen.findAllByRole('button', { name: /^details$/i })
    fireEvent.click(expandButtons[0])

    // The manifest content is fetched lazily and rendered in the panel.
    await waitFor(() => expect(detailSpy).toHaveBeenCalled())
    expect(await screen.findByText(/guidance for go tests/i)).toBeInTheDocument()
    expect(screen.getByText(/skills\/golang-testing\/SKILL\.md/i)).toBeInTheDocument()
    vi.restoreAllMocks()
  })

  it('filters to installed-only resources', async () => {
    const installed = metadataItem({ name: 'installed-skill', kind: 'skill', install_key: 'o/r:installed-skill', installed_apps: ['claude'] })
    const notInstalled = metadataItem({ name: 'fresh-skill', kind: 'skill', install_key: 'o/r:fresh-skill', installed_apps: [] })
    vi.spyOn(api, 'searchMetadata').mockResolvedValue({ items: [installed, notInstalled], total: 2, limit: 20, offset: 0 })
    render(<Library kind="skill" />)

    expect(await screen.findByText(/installed-skill/i)).toBeInTheDocument()
    expect(screen.getByText(/fresh-skill/i)).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText(/installed only/i))
    // Only the installed resource remains visible.
    await waitFor(() => expect(screen.queryByText(/fresh-skill/i)).not.toBeInTheDocument())
    expect(screen.getByText(/installed-skill/i)).toBeInTheDocument()
    vi.restoreAllMocks()
  })

  describe('auto-refresh on stale or empty index', () => {
    afterEach(() => vi.restoreAllMocks())

    it('auto-refreshes when a kind holds legacy repo-level (colon-less) rows', async () => {
      // Stale row: install_key has no ":" — the shape an older binary wrote when
      // it indexed one row per repo instead of one per resource.
      const stale = metadataItem({ name: 'agents', install_key: 'wshobson/agents' })
      const healthy = metadataItem({ name: 'code-reviewer', install_key: 'wshobson/agents:code-reviewer' })
      const searchSpy = vi.spyOn(api, 'searchMetadata')
        .mockResolvedValueOnce({ items: [stale], total: 1, limit: 20, offset: 0 })
        .mockResolvedValue({ items: [healthy], total: 1, limit: 20, offset: 0 })
      const refreshSpy = vi.spyOn(api, 'refreshMetadata')
        .mockResolvedValue({ sources_scanned: 1, items_added: 1, items_updated: 0, items_stale: 1, failed_sources: [] })

      render(<Library kind="agent" />)

      await waitFor(() => expect(refreshSpy).toHaveBeenCalledOnce())
      // After the refresh the healthy, resource-level row is shown.
      expect(await screen.findByText(/code-reviewer/i)).toBeInTheDocument()
      expect(searchSpy).toHaveBeenCalledTimes(2)
    })

    it('does not auto-refresh when rows are already resource-level', async () => {
      const healthy = metadataItem({ name: 'code-reviewer', install_key: 'wshobson/agents:code-reviewer' })
      vi.spyOn(api, 'searchMetadata').mockResolvedValue({ items: [healthy], total: 1, limit: 20, offset: 0 })
      const refreshSpy = vi.spyOn(api, 'refreshMetadata')

      render(<Library kind="agent" />)

      expect(await screen.findByText(/code-reviewer/i)).toBeInTheDocument()
      expect(refreshSpy).not.toHaveBeenCalled()
    })
  })
})
