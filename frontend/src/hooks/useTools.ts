import { useCallback } from 'react'
import {
  useToolsQuery,
  useResolvedModelsQuery,
  useInstallToolMutation,
  useUpgradeToolMutation,
  useApplyConfigMutation,
} from '../lib'
import type { Provider } from '../services/types'

export function useTools() {
  const query = useToolsQuery()
  const installMutation = useInstallToolMutation()
  const upgradeMutation = useUpgradeToolMutation()

  const install = useCallback(
    async (name: string) => {
      return installMutation.mutateAsync(name)
    },
    [installMutation],
  )

  const upgrade = useCallback(
    async (name: string) => {
      return upgradeMutation.mutateAsync(name)
    },
    [upgradeMutation],
  )

  return {
    tools: query.data ?? [],
    isLoading: query.isLoading,
    install,
    upgrade,
    isPending: installMutation.isPending || upgradeMutation.isPending,
  }
}

export function useResolvedModels(providerName: string, enabled = true) {
  const query = useResolvedModelsQuery(providerName, enabled)
  return {
    models: query.data ?? [],
    isLoading: query.isLoading,
  }
}

export function useApplyConfig() {
  const mutation = useApplyConfigMutation()

  const apply = useCallback(
    async (tool: string, provider: string, model: string) => {
      return mutation.mutateAsync({ tool, provider, model })
    },
    [mutation],
  )

  return {
    apply,
    isPending: mutation.isPending,
  }
}
