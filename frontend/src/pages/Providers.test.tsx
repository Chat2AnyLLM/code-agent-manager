import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Providers } from './Providers'
import { api } from '../services/api'
import type { Provider } from '../services/types'
import { TestWrapper } from '../test/TestWrapper'

describe('Providers page', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

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

  it('loads discovered models and saves selected models', async () => {
    const provider: Provider = {
      name: 'local',
      endpoint: 'http://localhost:4000/v1',
      apiKeyEnv: '',
      supportedClient: '',
      clients: ['claude'],
      models: ['configured-model'],
      keepProxyConfig: false,
      useProxy: false,
      enabled: true,
      description: '',
    }

    const listSpy = vi.spyOn(api, 'listProviders').mockResolvedValue([provider])
    vi.spyOn(api, 'resolveModels').mockResolvedValue(['api-model-a', 'api-model-b'])
    const updateSpy = vi.spyOn(api, 'updateProvider').mockResolvedValue({
      ...provider,
      models: ['api-model-a', 'api-model-b'],
    })

    render(<Providers />, { wrapper: TestWrapper })

    await waitFor(() => expect(listSpy).toHaveBeenCalled())
    await screen.findByText('local')

    fireEvent.click(screen.getByRole('button', { name: /details/i }))
    fireEvent.click(screen.getByRole('button', { name: /load models/i }))

    await screen.findByRole('button', { name: /select models local/i })
    fireEvent.click(screen.getByRole('button', { name: /select models local/i }))

    fireEvent.click(await screen.findByLabelText('api-model-a'))
    fireEvent.click(screen.getByLabelText('api-model-b'))
    fireEvent.click(screen.getByRole('button', { name: /save models/i }))

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith('local', { models: ['configured-model', 'api-model-a', 'api-model-b'] })
    })
  })
})
