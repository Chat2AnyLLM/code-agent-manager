import { z } from 'zod'

export const providerSchema = z.object({
  name: z.string().min(1, 'Provider name is required'),
  endpoint: z.string().min(1, 'Endpoint is required').url('Must be a valid URL'),
  apiKey: z.string().optional(),
  apiKeyEnv: z.string().optional(),
})

export type ProviderFormData = z.infer<typeof providerSchema>

const INSTRUCTION_NAME_PATTERN = /^[A-Za-z0-9._-]+$/

export const instructionSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .regex(INSTRUCTION_NAME_PATTERN, 'Only letters, numbers, dots, hyphens, and underscores'),
  description: z.string(),
  content: z.string(),
})

export type InstructionFormData = z.infer<typeof instructionSchema>
