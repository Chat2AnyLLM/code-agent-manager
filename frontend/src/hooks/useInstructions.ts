import { useCallback } from 'react'
import {
  useInstructionsQuery,
  useCreateInstructionMutation,
  useUpdateInstructionMutation,
  useDeleteInstructionMutation,
} from '../lib'

export function useInstructions() {
  const query = useInstructionsQuery()
  const createMutation = useCreateInstructionMutation()
  const updateMutation = useUpdateInstructionMutation()
  const deleteMutation = useDeleteInstructionMutation()

  const create = useCallback(
    async (body: { name: string; description: string; content: string }) => {
      return createMutation.mutateAsync(body)
    },
    [createMutation],
  )

  const update = useCallback(
    async (id: number, body: { name: string; description: string; content: string }) => {
      return updateMutation.mutateAsync({ id, body })
    },
    [updateMutation],
  )

  const remove = useCallback(
    async (id: number) => {
      return deleteMutation.mutateAsync(id)
    },
    [deleteMutation],
  )

  return {
    instructions: query.data ?? [],
    isLoading: query.isLoading,
    create,
    update,
    remove,
    isPending: createMutation.isPending || updateMutation.isPending || deleteMutation.isPending,
  }
}
