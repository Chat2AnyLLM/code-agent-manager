import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useMCPServersQuery,
  useMCPRegistryQuery,
  useInstallMCPServerMutation,
  useUninstallMCPServerMutation,
} from '../lib'

export function useMCP() {
  const { t } = useTranslation()

  const serversQuery = useMCPServersQuery()
  const registryQuery = useMCPRegistryQuery()
  const installMutation = useInstallMCPServerMutation()
  const uninstallMutation = useUninstallMCPServerMutation()

  const install = useCallback(
    async (server: string, clients: string[], scope = 'user') => {
      return installMutation.mutateAsync({ server, clients, scope })
    },
    [installMutation],
  )

  const uninstall = useCallback(
    async (server: string, clients: string[], scope = 'user') => {
      return uninstallMutation.mutateAsync({ server, clients, scope })
    },
    [uninstallMutation],
  )

  return {
    servers: serversQuery.data ?? [],
    registry: registryQuery.data ?? [],
    isLoading: serversQuery.isLoading || registryQuery.isLoading,
    install,
    uninstall,
    isPending: installMutation.isPending || uninstallMutation.isPending,
  }
}
