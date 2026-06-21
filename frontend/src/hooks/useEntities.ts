import { useCallback } from 'react'
import {
  useEntitiesQuery,
  useUninstallEntityMutation,
  useMetadataSearchQuery,
  useInstallMetadataMutation,
  useUninstallMetadataMutation,
  useRefreshMetadataMutation,
} from '../lib'
import type { Entity } from '../services/types'

export function useEntities(kind: Entity['kind']) {
  const entitiesQuery = useEntitiesQuery(kind)
  const uninstallMutation = useUninstallEntityMutation()

  const uninstall = useCallback(
    async (name: string) => {
      return uninstallMutation.mutateAsync({ kind, name })
    },
    [uninstallMutation, kind],
  )

  return {
    entities: entitiesQuery.data ?? [],
    isLoading: entitiesQuery.isLoading,
    uninstall,
    isPending: uninstallMutation.isPending,
  }
}

export function useMetadata(kind: Entity['kind'], query: string) {
  const searchQuery = useMetadataSearchQuery(kind, query)
  const installMutation = useInstallMetadataMutation()
  const uninstallMutation = useUninstallMetadataMutation()
  const refreshMutation = useRefreshMetadataMutation()

  const install = useCallback(
    async (installKey: string, targetApps: string[], level?: string, projectDir?: string) => {
      return installMutation.mutateAsync({ kind, installKey, targetApps, level, projectDir })
    },
    [installMutation, kind],
  )

  const uninstall = useCallback(
    async (installKey: string, targetApps: string[]) => {
      return uninstallMutation.mutateAsync({ kind, installKey, targetApps })
    },
    [uninstallMutation, kind],
  )

  const refresh = useCallback(() => {
    return refreshMutation.mutateAsync()
  }, [refreshMutation])

  return {
    items: searchQuery.data?.items ?? [],
    total: searchQuery.data?.total ?? 0,
    isLoading: searchQuery.isLoading,
    install,
    uninstall,
    refresh,
    isPending: installMutation.isPending || uninstallMutation.isPending || refreshMutation.isPending,
  }
}
