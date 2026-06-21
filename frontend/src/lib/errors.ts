/**
 * Extract a human-readable error message from any error value.
 */
export function extractErrorMessage(error: unknown): string {
  if (!error) return ''
  if (typeof error === 'string') return error
  if (error instanceof Error && error.message.trim()) return error.message

  if (typeof error === 'object') {
    const errObject = error as Record<string, unknown>

    const candidate = errObject.message ?? errObject.error ?? errObject.detail
    if (typeof candidate === 'string' && candidate.trim()) return candidate

    const payload = errObject.payload
    if (typeof payload === 'string' && payload.trim()) return payload
    if (payload && typeof payload === 'object') {
      const payloadObj = payload as Record<string, unknown>
      const payloadCandidate = payloadObj.message ?? payloadObj.error ?? payloadObj.detail
      if (typeof payloadCandidate === 'string' && payloadCandidate.trim()) return payloadCandidate
    }
  }

  return ''
}
