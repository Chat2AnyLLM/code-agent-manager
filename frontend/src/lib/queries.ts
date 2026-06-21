import { useQuery, type UseQueryResult, keepPreviousData } from '@tanstack/react-query'
import { api } from '../services/api'
import type { Provider, Tool, MCPServer, MCPRegistryItem, Entity, DoctorCheck, ConfigFile, Instruction, MetadataSearchResponse } from '../services/types'

export const useProvidersQuery = (): UseQueryResult<Provider[]> => {
  return useQuery({
    queryKey: ['providers'],
    queryFn: () => api.listProviders(),
    staleTime: 5 * 60 * 1000,
  })
}

export const useToolsQuery = (): UseQueryResult<Tool[]> => {
  return useQuery({
    queryKey: ['tools'],
    queryFn: () => api.listTools(),
    staleTime: 30 * 1000,
  })
}

export const useResolvedModelsQuery = (providerName: string, enabled = true) => {
  return useQuery<string[]>({
    queryKey: ['resolvedModels', providerName],
    queryFn: () => api.resolveModels(providerName),
    enabled: enabled && !!providerName,
    staleTime: 5 * 60 * 1000,
  })
}

export const useMCPServersQuery = (client = 'claude', scope = 'user'): UseQueryResult<MCPServer[]> => {
  return useQuery({
    queryKey: ['mcp', 'servers', client, scope],
    queryFn: () => api.listMCPServers(client, scope),
    staleTime: 30 * 1000,
  })
}

export const useMCPRegistryQuery = (query = '', scope = 'user'): UseQueryResult<MCPRegistryItem[]> => {
  return useQuery({
    queryKey: ['mcp', 'registry', query, scope],
    queryFn: () => api.searchMCPRegistry(query, scope),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  })
}

export const useEntitiesQuery = (kind: Entity['kind']): UseQueryResult<Entity[]> => {
  return useQuery({
    queryKey: ['entities', kind],
    queryFn: () => api.listEntities(kind),
    staleTime: 30 * 1000,
  })
}

export const useMetadataSearchQuery = (
  kind: Entity['kind'],
  query: string,
  limit = 50,
  offset = 0,
  enabled = true,
): UseQueryResult<MetadataSearchResponse> => {
  return useQuery({
    queryKey: ['metadata', 'search', kind, query, limit, offset],
    queryFn: () => api.searchMetadata(kind, query, limit, offset),
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  })
}

export const useDoctorQuery = (): UseQueryResult<DoctorCheck[]> => {
  return useQuery({
    queryKey: ['doctor'],
    queryFn: () => api.runDoctor(),
    staleTime: 30 * 1000,
  })
}

export const useConfigFilesQuery = (): UseQueryResult<ConfigFile[]> => {
  return useQuery({
    queryKey: ['config', 'files'],
    queryFn: () => api.listConfigFiles(),
    staleTime: 30 * 1000,
  })
}

export const useInstructionsQuery = (): UseQueryResult<Instruction[]> => {
  return useQuery({
    queryKey: ['instructions'],
    queryFn: () => api.listInstructions(),
    staleTime: 30 * 1000,
  })
}
