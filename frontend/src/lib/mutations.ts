import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '../services/api'
import { extractErrorMessage } from './errors'

export const useInstallToolMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => api.installTool(name),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['tools'] })
      toast.success('Tool installed')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Install failed: ${detail}`)
    },
  })
}

export const useUpgradeToolMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => api.upgradeTool(name),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['tools'] })
      toast.success('Tool upgraded')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Upgrade failed: ${detail}`)
    },
  })
}

export const useAddProviderMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: Parameters<typeof api.addProvider>[0]) => api.addProvider(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['providers'] })
      toast.success('Provider added')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Add failed: ${detail}`)
    },
  })
}

export const useUpdateProviderMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ name, patch }: { name: string; patch: Parameters<typeof api.updateProvider>[1] }) =>
      api.updateProvider(name, patch),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['providers'] })
      toast.success('Provider updated')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Update failed: ${detail}`)
    },
  })
}

export const useToggleProviderMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) =>
      api.toggleProvider(name, enabled),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['providers'] })
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Toggle failed: ${detail}`)
    },
  })
}

export const useRemoveProviderMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => api.removeProvider(name),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['providers'] })
      toast.success('Provider removed')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Remove failed: ${detail}`)
    },
  })
}

export const useInstallMCPServerMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ server, clients, scope }: { server: string; clients: string[]; scope?: string }) =>
      api.installMCPServer(server, clients, scope),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['mcp'] })
      toast.success('MCP server installed')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Install failed: ${detail}`)
    },
  })
}

export const useUninstallMCPServerMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ server, clients, scope }: { server: string; clients: string[]; scope?: string }) =>
      api.uninstallMCPServer(server, clients, scope),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['mcp'] })
      toast.success('MCP server uninstalled')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Uninstall failed: ${detail}`)
    },
  })
}

export const useInstallMetadataMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ kind, installKey, targetApps, level, projectDir }: {
      kind: string; installKey: string; targetApps: string[]; level?: string; projectDir?: string
    }) => api.installMetadata(kind, installKey, targetApps, level, projectDir),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['metadata'] })
      toast.success('Installed successfully')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Install failed: ${detail}`)
    },
  })
}

export const useUninstallMetadataMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ kind, installKey, targetApps }: { kind: string; installKey: string; targetApps: string[] }) =>
      api.uninstallMetadata(kind, installKey, targetApps),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['metadata'] })
      toast.success('Uninstalled successfully')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Uninstall failed: ${detail}`)
    },
  })
}

export const useUninstallEntityMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ kind, name }: { kind: string; name: string }) => api.uninstallEntity(kind, name),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['entities'] })
      toast.success('Entity uninstalled')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Uninstall failed: ${detail}`)
    },
  })
}

export const useRefreshMetadataMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.refreshMetadata(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['metadata'] })
      toast.success('Metadata refreshed')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Refresh failed: ${detail}`)
    },
  })
}

export const useApplyConfigMutation = () => {
  return useMutation({
    mutationFn: ({ tool, provider, model }: { tool: string; provider: string; model: string }) =>
      api.applyConfig(tool, provider, model),
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Apply failed: ${detail}`)
    },
  })
}

// Instructions mutations
export const useCreateInstructionMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; description: string; content: string }) =>
      api.createInstruction(body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['instructions'] })
      toast.success('Instruction created')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Create failed: ${detail}`)
    },
  })
}

export const useUpdateInstructionMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: { name: string; description: string; content: string } }) =>
      api.updateInstruction(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['instructions'] })
      toast.success('Instruction updated')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Update failed: ${detail}`)
    },
  })
}

export const useDeleteInstructionMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.deleteInstruction(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['instructions'] })
      toast.success('Instruction deleted')
    },
    onError: (error: Error) => {
      const detail = extractErrorMessage(error) || 'Unknown error'
      toast.error(`Delete failed: ${detail}`)
    },
  })
}
