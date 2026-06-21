import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, afterEach } from 'vitest'
import { Instructions } from './Instructions'
import { api } from '../services/api'
import type { Instruction, InstructionInstall, InstructionTarget } from '../services/types'
import { TestWrapper } from '../test/TestWrapper'

const targets: InstructionTarget[] = [
  { app: 'claude', supports: { user: true, project: true } },
  { app: 'copilot', supports: { user: false, project: true } },
]

function instruction(overrides: Partial<Instruction>): Instruction {
  return { id: 1, name: 'Instruction01', description: 'first', content: '# hi', installs: [], ...overrides }
}

function install(overrides: Partial<InstructionInstall>): InstructionInstall {
  return { id: 10, app: 'claude', level: 'user', project_dir: '', target_path: '/home/u/.claude/CLAUDE.md', link_kind: 'symlink', ...overrides }
}

describe('Instructions page', () => {
  afterEach(() => vi.restoreAllMocks())

  function stubTargets() {
    vi.spyOn(api, 'instructionTargets').mockResolvedValue(targets)
  }

  it('renders the empty state, then shows a created instruction', async () => {
    stubTargets()
    const listSpy = vi.spyOn(api, 'listInstructions').mockResolvedValueOnce([])
    vi.spyOn(api, 'createInstruction').mockResolvedValue(instruction({}))
    render(<Instructions />, { wrapper: TestWrapper })

    expect(await screen.findByText(/no instructions yet/i)).toBeInTheDocument()

    listSpy.mockResolvedValue([instruction({})])
    fireEvent.click(screen.getByRole('button', { name: /new instruction/i }))
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Instruction01' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    expect(await screen.findByText('Instruction01')).toBeInTheDocument()
  })

  it('validates the name field inline before saving', async () => {
    stubTargets()
    vi.spyOn(api, 'listInstructions').mockResolvedValue([])
    const createSpy = vi.spyOn(api, 'createInstruction')
    render(<Instructions />, { wrapper: TestWrapper })
    await screen.findByText(/no instructions yet/i)

    fireEvent.click(screen.getByRole('button', { name: /new instruction/i }))
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'bad name' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    expect(await screen.findByText(/only letters, numbers/i)).toBeInTheDocument()
    expect(createSpy).not.toHaveBeenCalled()
  })

  it('installs via the row action and shows a chip', async () => {
    stubTargets()
    const listSpy = vi.spyOn(api, 'listInstructions').mockResolvedValue([instruction({})])
    vi.spyOn(api, 'installInstruction').mockResolvedValue(install({}))
    render(<Instructions />, { wrapper: TestWrapper })
    await screen.findByText('Instruction01')

    // Click the Install button in the row actions
    fireEvent.click(screen.getByRole('button', { name: /install to claude/i }))

    listSpy.mockResolvedValue([instruction({ installs: [install({})] })])
    await waitFor(() => expect(screen.queryByText('Instruction01')).toBeInTheDocument())

    const chip = await screen.findByText(/claude \(user\)/i)
    expect(chip).toBeInTheDocument()
  })

  it('uninstalls via the chip remove button', async () => {
    stubTargets()
    const listSpy = vi.spyOn(api, 'listInstructions').mockResolvedValue([instruction({ installs: [install({})] })])
    vi.spyOn(api, 'uninstallInstruction').mockResolvedValue(undefined)
    render(<Instructions />, { wrapper: TestWrapper })
    await screen.findByText('Instruction01')

    // The chip should show the uninstall button
    const uninstallBtn = screen.getByRole('button', { name: /uninstall claude/i })
    fireEvent.click(uninstallBtn)

    listSpy.mockResolvedValue([instruction({ installs: [] })])
    await waitFor(() => expect(screen.queryByText(/claude \(user\)/i)).not.toBeInTheDocument())
  })
})
