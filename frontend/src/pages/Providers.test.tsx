import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Providers } from './Providers'
import { api } from '../services/api'
import type { Provider } from '../services/types'
import { TestWrapper } from '../test/TestWrapper'

describe('Providers page', () => {
  it('lists and adds providers', async () => {
    const initialProviders: Provider[] = [
      { name: 'local', endpoint: 'http://localhost:4000/v1', apiKeyEnv: '', supportedClient: '', clients: ['claude'], models: ['gpt-4.1', 'claude-opus-4.6'], keepProxyConfig: false, useProxy: false, enabled: true, description: '' },
    ]

    const newProvider: Provider = {
      name: 'new-provider',
      endpoint: 'http://localhost:5000/v1',
      apiKeyEnv: '',
      supportedClient: '',
      clients: ['claude'],
      models: [],
      keepProxyConfig: false,
      useProxy: false,
      enabled: true,
      description: '',
    }

    const listSpy = vi.spyOn(api, 'listProviders')
    listSpy.mockResolvedValue(initialProviders)
    vi.spyOn(api, 'addProvider').mockResolvedValue(newProvider)

    render(<Providers />, { wrapper: TestWrapper })

    // Wait for initial load
    await waitFor(() => expect(listSpy).toHaveBeenCalled())

    fireEvent.change(screen.getByLabelText(/provider name/i), { target: { value: 'new-provider' } })
    fireEvent.change(screen.getByLabelText(/provider endpoint/i), { target: { value: 'http://localhost:5000/v1' } })

    // After mutation, the query should refetch and include the new provider
    listSpy.mockResolvedValue([...initialProviders, newProvider])
    fireEvent.click(screen.getByRole('button', { name: /add provider/i }))

    // Wait for the new provider to appear in the table
    expect(await screen.findByText('new-provider')).toBeInTheDocument()
  })
})
