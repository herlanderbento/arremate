import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

export interface FieldError {
  field: string
  message: string
}

export interface ApiError {
  status: number | null
  code: string
  message: string
  details: Record<string, unknown>
}

const NETWORK_ERROR: ApiError = {
  status: null,
  code: 'NETWORK_ERROR',
  message: 'Não foi possível contactar o servidor. Tente novamente em instantes.',
  details: {},
}

export function toApiError(error: unknown): ApiError {
  if (!axios.isAxiosError(error)) return { ...NETWORK_ERROR, code: 'UNKNOWN_ERROR' }
  if (!error.response) return NETWORK_ERROR

  const body = error.response.data?.error
  return {
    status: error.response.status,
    code: body?.code ?? 'UNKNOWN_ERROR',
    message: body?.message ?? 'Ocorreu um erro inesperado.',
    details: body?.details ?? {},
  }
}

export function fieldErrors(error: ApiError | null): Record<string, string> {
  const fields = (error?.details?.fields ?? []) as FieldError[]
  return Object.fromEntries(fields.map((f) => [f.field.split('.').pop() ?? f.field, f.message]))
}

export { api }
