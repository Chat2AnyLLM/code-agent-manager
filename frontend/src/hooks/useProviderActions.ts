import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import {
  useProvidersQuery,
  useAddProviderMutation,
  useUpdateProviderMutation,
  useToggleProviderMutation,
  useRemoveProviderMutation,
} from '../lib'
import type { Provider } from '../services/types'
import { extractErrorMessage } from '../lib/errors'

export function useProviderActions() {
  const { t } = useTranslation()
  const { data: providers = [], isLoading } = useProvidersQuery()
  const addMutation = useAddProviderMutation()
  const updateMutation = useUpdateProviderMutation()
  const toggleMutation = useToggleProviderMutation()
  const removeMutation = useRemoveProviderMutation()

  const addProvider = useCallback(
    async (input: Partial<Provider> & { name: string }) => {
      return addMutation.mutateAsync(input)
    },
    [addMutation],
  )

  const updateApiKey = useCallback(
    async (name: string, apiKey: string) => {
      return updateMutation.mutateAsync({ name, patch: { apiKey } })
    },
    [updateMutation],
  )

  const updateApiKeyEnv = useCallback(
    async (name: string, apiKeyEnv: string) => {
      return updateMutation.mutateAsync({ name, patch: { apiKeyEnv } })
    },
    [updateMutation],
  )

  const toggle = useCallback(
    async (name: string, enabled: boolean) => {
      return toggleMutation.mutateAsync({ name, enabled })
    },
    [toggleMutation],
  )

  const remove = useCallback(
    async (name: string) => {
      return removeMutation.mutateAsync(name)
    },
    [removeMutation],
  )

  return {
    providers,
    isLoading,
    addProvider,
    updateApiKey,
    updateApiKeyEnv,
    toggle,
    remove,
    isPending: addMutation.isPending || updateMutation.isPending || toggleMutation.isPending || removeMutation.isPending,
  }
}
