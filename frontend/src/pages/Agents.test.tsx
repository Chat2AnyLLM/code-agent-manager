import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { Agents } from './Agents'
import { TestWrapper } from '../test/TestWrapper'

describe('Agents page', () => {
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
})
