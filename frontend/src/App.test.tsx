import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App shell', () => {
  it('renders agents dashboard and navigates to all primary pages', async () => {
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByRole('heading', { name: /^agents$/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /providers/i }))
    expect(await screen.findByRole('heading', { name: /providers/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /mcp servers/i }))
    expect(await screen.findByRole('heading', { name: /mcp servers/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /instructions/i }))
    expect(await screen.findByRole('heading', { name: /instructions/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /skills/i }))
    expect(await screen.findByRole('heading', { name: /skills/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /subagents/i }))
    expect(await screen.findByRole('heading', { name: /subagents/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /plugins/i }))
    expect(await screen.findByRole('heading', { name: /plugins/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /configuration/i }))
    expect(await screen.findByRole('heading', { name: /configuration/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /diagnostics/i }))
    expect(await screen.findByRole('heading', { name: /diagnostics/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /settings/i }))
    expect(await screen.findByRole('heading', { name: /settings/i })).toBeInTheDocument()
  })

  it('toggles between dark and light themes (wintoolbox-style)', async () => {
    const user = userEvent.setup()
    render(<App />)
    // Defaults to dark.
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    const toggle = await screen.findByRole('button', { name: /toggle theme/i })
    await user.click(toggle)
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    await user.click(toggle)
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('switches the UI language between English and Chinese', async () => {
    try { localStorage.removeItem('cam.lang') } catch { /* ignore */ }
    const user = userEvent.setup()
    render(<App />)
    // Defaults to English: the agents nav button reads "Agents".
    expect(await screen.findByRole('button', { name: /^agents$/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /toggle language/i }))
    // After switching, the Chinese label for the agents nav appears.
    expect(await screen.findByRole('button', { name: '智能体' })).toBeInTheDocument()
    // And the heading is localized too.
    expect(await screen.findByRole('heading', { name: '智能体' })).toBeInTheDocument()
  })
})
